"""
Architect Agent Pro — Production-grade LangGraph multi-agent system
Nodes: planner → generator → reviewer → refiner (loop max 3x) → finalizer
LLM: Multi-LLM via LiteLLM

Modes:
  full  — 5 nodes, boucle review/refine, pour architectures complexes
  quick — 3 nodes, une seule passe, pour questions rapides
"""

import sys
import json
import logging
import uuid
import os
import re
import sqlite3
from pathlib import Path
from typing import TypedDict, Optional, Generator
from langgraph.graph import StateGraph, END

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    _CHECKPOINTER = "sqlite"
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    _CHECKPOINTER = "memory"
    import warnings
    warnings.warn(
        "langgraph-checkpoint-sqlite non installé — persistance désactivée.",
        stacklevel=2
    )

import litellm

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────
_script_dir = Path(__file__).resolve().parent
_env_candidates = [_script_dir / ".env", Path.cwd() / ".env"]
try:
    from dotenv import load_dotenv
    for _env_path in _env_candidates:
        if _env_path.exists():
            load_dotenv(_env_path)
            log.info(f"📄 .env chargé depuis : {_env_path}")
            break
except ImportError:
    for _env_path in _env_candidates:
        if _env_path.exists():
            with open(_env_path) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        os.environ.setdefault(_k.strip(), _v.strip())
            log.info(f"📄 .env chargé manuellement depuis : {_env_path}")
            break

# LiteLLM supporte nativement MINIMAX_API_KEY, OPENAI_API_KEY, etc.
MODEL = os.environ.get("LLM_MODEL", "minimax/MiniMax-M2.7")

# ─── State ──────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    input_task: str
    context: str
    plan: str
    draft: str
    review: dict
    refined_draft: str
    final_output: str
    iteration: int
    history: list
    error: Optional[str]

MAX_ITERATIONS = 3
CHECKPOINT_DB = str(_script_dir / "architect_runs.db")

# ─── Métriques SQLite ───────────────────────────────────────────────────────
def init_metrics_db():
    conn = sqlite3.connect(CHECKPOINT_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            task TEXT,
            score INTEGER,
            iteration INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_metric(thread_id: str, task: str, score: int, iteration: int):
    try:
        conn = sqlite3.connect(CHECKPOINT_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO metrics (thread_id, task, score, iteration) VALUES (?, ?, ?, ?)",
            (thread_id, task, score, iteration)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"⚠️ Impossible d'enregistrer la métrique: {e}")

init_metrics_db()

# ─── Prompts ────────────────────────────────────────────────────────────────
def load_prompt(name: str) -> str:
    prompt_path = _script_dir / "prompts" / f"{name}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    log.warning(f"⚠️ Prompt {name}.md introuvable dans prompts/")
    return ""

# ─── Helper LLM call ────────────────────────────────────────────────────────
def llm(system: str, messages: list, max_tokens: int = 4096, stream: bool = False):
    """Appel générique via LiteLLM."""
    response = litellm.completion(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            *messages
        ],
        stream=stream
    )
    if stream:
        return response
    
    content = response.choices[0].message.content
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content

def llm_json(system: str, messages: list, max_tokens: int = 2048) -> dict:
    """Appel LLM avec parsing JSON."""
    system_with_json = system + "\n\nRéponds UNIQUEMENT avec du JSON valide."
    raw = llm(system_with_json, messages, max_tokens)
    cleaned_think = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    
    for candidate in [cleaned_think, raw]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", cleaned_think).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"llm_json: impossible de parser.\nRaw: {raw[:100]}")

# ─── Extracteur de Fichiers (Output Actionnable) ────────────────────────────
def extract_files(final_markdown: str, thread_id: str):
    """Extrait les blocs de code markdown avec des noms de fichiers et les écrit."""
    out_dir = _script_dir / "workspace_out" / thread_id
    pattern = r"```\w+\s+([a-zA-Z0-9_\-\.\/]+)\n(.*?)```"
    matches = re.findall(pattern, final_markdown, re.DOTALL)
    
    saved_files = []
    if matches:
        out_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"📂 Fichiers actionnables détectés : {len(matches)}")
        for filename, content in matches:
            filepath = out_dir / filename.strip()
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content.strip(), encoding="utf-8")
            log.info(f"   ↳ Créé: {filepath}")
            saved_files.append(str(filepath))
    return saved_files

# ─── Nodes ──────────────────────────────────────────────────────────────────
def planner(state: AgentState) -> dict:
    log.info("🗺️  PLANNER — Analyse de la tâche...")
    task = state["input_task"]
    context = state.get("context", "")
    system_prompt = load_prompt("planner")
    
    result = llm_json(
        system=system_prompt,
        messages=[{"role": "user", "content": f"Tâche : {task}\n\nContexte : {context}"}]
    )
    log.info(f"✅ Plan établi — Type: {result.get('system_type')}")
    return {"plan": json.dumps(result, ensure_ascii=False, indent=2), "iteration": 0, "history": []}

def generator(state: AgentState) -> dict:
    log.info(f"⚙️  GENERATOR — Itération {state.get('iteration', 0) + 1}...")
    task = state["input_task"]
    context = state.get("context", "")
    plan = state.get("plan", "")
    history = state.get("history", [])
    
    previous_context = ""
    if history:
        last = history[-1]
        previous_context = f"--- ITÉRATION PRÉCÉDENTE ---\nDraft: {last.get('draft', '')}\nIssues: {json.dumps(last.get('review', {}))}\n"
    
    plan_section = f"Plan validé :\n{plan}" if plan else f"Contexte : {context}"
    system_prompt = load_prompt("generator")
    
    draft = llm(
        system=system_prompt,
        messages=[{"role": "user", "content": f"Tâche originale : {task}\n\n{plan_section}\n{previous_context}\nGénère l'architecture complète."}],
        max_tokens=6000
    )
    new_history = history + [{"draft": draft, "review": state.get("review", {})}]
    log.info("✅ Architecture générée")
    return {"draft": draft, "history": new_history, "iteration": state.get("iteration", 0) + 1}

def reviewer(state: AgentState) -> dict:
    log.info("🔍 REVIEWER — Analyse critique...")
    task = state["input_task"]
    plan = state.get("plan", "")
    draft = state["draft"]
    
    system_prompt = load_prompt("reviewer")
    result = llm_json(
        system=system_prompt,
        messages=[{"role": "user", "content": f"Tâche : {task}\n\nPlan :\n{plan}\n\nArchitecture :\n{draft}"}]
    )
    
    status = result.get("status", "FAILED")
    score = result.get("score", 0)
    blocking = result.get("blocking_issues", [])
    log.info(f"{'✅' if status == 'PASSED' else '❌'} Review: {status} (score={score}, blocking={len(blocking)})")
    
    return {"review": result}

def refiner(state: AgentState) -> dict:
    log.info("🔧 REFINER — Application des corrections...")
    review = state["review"]
    draft = state["draft"]
    task = state["input_task"]
    
    blocking = review.get("blocking_issues", [])
    dimensions = review.get("dimensions", {})
    all_issues = [f"[{k}] {i}" for k, v in dimensions.items() for i in v.get("issues", [])]
    all_recs = [f"[{k}] {r}" for k, v in dimensions.items() for r in v.get("recommendations", [])]
    
    system_prompt = load_prompt("refiner")
    refined = llm(
        system=system_prompt,
        messages=[{"role": "user", "content": f"Tâche : {task}\nDraft:\n{draft}\nBloquants:\n{blocking}\nIssues:\n{all_issues}\nRecommandations:\n{all_recs}"}],
        max_tokens=6000
    )
    log.info("✅ Architecture raffinée")
    return {"refined_draft": refined, "draft": refined}

def finalizer(state: AgentState) -> dict:
    log.info("📄 FINALIZER — Production du document final...")
    task = state["input_task"]
    plan = state.get("plan", "{}")
    draft = state.get("refined_draft") or state["draft"]
    review = state.get("review", {})
    iterations = state.get("iteration", 1)
    
    system_prompt = load_prompt("finalizer")
    final = llm(
        system=system_prompt,
        messages=[{"role": "user", "content": f"Tâche : {task}\nPlan :\n{plan}\nArchitecture:\n{draft}\nScore : {review.get('score')}/100\nFeedback: {review.get('overall_feedback')}"}],
        max_tokens=8000
    )
    log.info(f"✅ Document final produit ({len(final)} chars)")
    return {"final_output": final}

# ─── Routers ─────────────────────────────────────────────────────────────────
def router_full(state: AgentState) -> str:
    status = state.get("review", {}).get("status", "FAILED")
    iteration = state.get("iteration", 0)
    if status == "PASSED": return "finalizer"
    if iteration >= MAX_ITERATIONS: return "finalizer"
    return "refiner"

def router_quick(state: AgentState) -> str:
    return "finalizer"

# ─── Graph Assembly ──────────────────────────────────────────────────────────
def build_graph(checkpointer=None, mode: str = "full"):
    workflow = StateGraph(AgentState)
    if mode == "quick":
        workflow.add_node("generator", generator)
        workflow.add_node("reviewer", reviewer)
        workflow.add_node("finalizer", finalizer)
        workflow.set_entry_point("generator")
        workflow.add_edge("generator", "reviewer")
        workflow.add_conditional_edges("reviewer", router_quick, {"finalizer": "finalizer"})
        workflow.add_edge("finalizer", END)
    else:
        workflow.add_node("planner", planner)
        workflow.add_node("generator", generator)
        workflow.add_node("reviewer", reviewer)
        workflow.add_node("refiner", refiner)
        workflow.add_node("finalizer", finalizer)
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "generator")
        workflow.add_edge("generator", "reviewer")
        workflow.add_conditional_edges("reviewer", router_full, {"refiner": "refiner", "finalizer": "finalizer"})
        workflow.add_edge("refiner", "reviewer")
        workflow.add_edge("finalizer", END)
    return workflow.compile(checkpointer=checkpointer)

# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            print(json.dumps({"error": "Aucune entrée"}))
            sys.exit(1)

        task_data = json.loads(raw)
        mode = task_data.pop("mode", "full")
        stream_mode = task_data.pop("stream", False)
        thread_id = task_data.pop("thread_id", None) or str(uuid.uuid4())
        
        log.info(f"🧵 thread_id: {thread_id} | mode: {mode} | stream: {stream_mode}")
        log.info(f"🤖 Modèle: {MODEL} via LiteLLM")

        if _CHECKPOINTER == "sqlite":
            with SqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
                app = build_graph(checkpointer=checkpointer, mode=mode)
                config = {"configurable": {"thread_id": thread_id}}
                
                if stream_mode:
                    for output in app.stream(task_data, config=config, stream_mode="updates"):
                        for node_name, state_update in output.items():
                            log.info(f"🔄 Nœud terminé : {node_name}")
                            if node_name == "reviewer" and "review" in state_update:
                                log_metric(thread_id, task_data.get("input_task", ""), state_update["review"].get("score", 0), state_update.get("iteration", 1))
                    result = app.get_state(config).values
                else:
                    # En mode classique, on écoute aussi les events pour logger la review
                    # Mais invoke ne retourne que l'état final. on le loggue à la fin.
                    result = app.invoke(task_data, config=config)
                    if "review" in result:
                        log_metric(thread_id, task_data.get("input_task", ""), result["review"].get("score", 0), result.get("iteration", 1))
        else:
            checkpointer = MemorySaver()
            app = build_graph(checkpointer=checkpointer, mode=mode)
            config = {"configurable": {"thread_id": thread_id}}
            result = app.invoke(task_data, config=config)

        raw_plan = result.get("plan", "")
        plan_output = {}
        if raw_plan:
            try: plan_output = json.loads(raw_plan)
            except: pass
            
        final_output = result.get("final_output", "")
        saved_files = []
        if final_output:
            saved_files = extract_files(final_output, thread_id)

        output = {
            "thread_id": thread_id,
            "mode": mode,
            "plan": plan_output,
            "final_output": final_output,
            "saved_files": saved_files,
            "review_score": result.get("review", {}).get("score"),
            "iterations": result.get("iteration", 1),
            "status": result.get("review", {}).get("status", "UNKNOWN")
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    except Exception as e:
        log.exception("Erreur fatale")
        print(json.dumps({"error": str(e)}))
        sys.exit(1)