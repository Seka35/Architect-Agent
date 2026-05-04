"""
Architect Agent — Production-grade LangGraph multi-agent system
Nodes: planner → generator → reviewer → refiner (loop max 3x) → finalizer
LLM: MiniMax via OpenAI-compatible API

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
from pathlib import Path
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    _CHECKPOINTER = "sqlite"
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    _CHECKPOINTER = "memory"
    import warnings
    warnings.warn(
        "langgraph-checkpoint-sqlite non installé — persistance désactivée (MemorySaver). "
        "Installez : pip install langgraph-checkpoint-sqlite",
        stacklevel=2
    )
from openai import OpenAI

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
log = logging.getLogger(__name__)

# ─── Chargement automatique du .env ─────────────────────────────────────────
# Cherche .env dans le dossier du script d'abord, puis dans le dossier courant
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
    # python-dotenv non installé — fallback sur variables d'environnement système
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

# ─── Client MiniMax ─────────────────────────────────────────────────────────
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
if not MINIMAX_API_KEY:
    log.error("❌ MINIMAX_API_KEY manquante. Créez un fichier .env avec : MINIMAX_API_KEY=sk-...")
    sys.exit(1)

client = OpenAI(
    api_key=MINIMAX_API_KEY,
    base_url="https://api.minimaxi.chat/v1"
)
MODEL = "MiniMax-M2.7"

# ─── State ──────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    input_task: str          # Tâche initiale de l'utilisateur
    context: str             # Contexte additionnel (stack, contraintes, etc.)
    plan: str                # Plan structuré produit par le planner
    draft: str               # Architecture produite par le generator
    review: dict             # Résultat structuré du reviewer
    refined_draft: str       # Draft après refiner
    final_output: str        # Output final mis en forme
    iteration: int           # Compteur de cycles review/refine
    history: list            # Historique des drafts pour le contexte
    error: Optional[str]     # Erreur éventuelle

MAX_ITERATIONS = 3
CHECKPOINT_DB = "architect_runs.db"

# ─── Helper LLM call ────────────────────────────────────────────────────────
def llm(system: str, messages: list, max_tokens: int = 4096) -> str:
    """Appel MiniMax via OpenAI-compatible API.
    Strip automatiquement les balises <think>...</think> des modèles reasoning (M2.x).
    """
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            *messages
        ]
    )
    content = response.choices[0].message.content
    # Strip les balises <think>...</think> (MiniMax-M2.x reasoning model)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content


def llm_json(system: str, messages: list, max_tokens: int = 2048) -> dict:
    """Appel MiniMax avec output JSON parsé — 5 étapes de nettoyage.
    MiniMax-M2.7 est un modèle 'thinking' qui wrape sa réflexion dans
    des balises <think>...</think> avant le JSON — on les strip en priorité.
    """
    system_with_json = system + "\n\nRéponds UNIQUEMENT avec du JSON valide, sans markdown, sans backticks, sans texte avant ou après."
    raw = llm(system_with_json, messages, max_tokens)

    # Étape 0 : strip les balises <think>...</think> (modèles reasoning MiniMax-M2.x)
    cleaned_think = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Étape 1 : tentative directe (après strip <think>)
    for candidate in [cleaned_think, raw]:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Étape 2 : strip les backticks markdown (```json ... ``` ou ``` ... ```)
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", cleaned_think).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Étape 3 : isoler le premier objet JSON valide dans le texte
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Étape 4 : fallback — lever une erreur claire avec le raw pour debug
    raise ValueError(f"llm_json: impossible de parser la réponse LLM.\nRaw (100 chars): {raw[:100]}")


# ─── Node 1 : PLANNER (full mode only) ──────────────────────────────────────
def planner(state: AgentState) -> dict:
    """
    Analyse la tâche et produit un plan structuré :
    type de système, contraintes, composants attendus, critères de succès.
    """
    log.info("🗺️  PLANNER — Analyse de la tâche...")
    task = state["input_task"]
    context = state.get("context", "Aucun contexte additionnel.")

    result = llm_json(
        system="""Tu es un architecte solution senior (15 ans d'expérience).
Tu analyses une demande et produis un plan d'architecture structuré.
Produis un JSON avec cette structure exacte :
{
  "system_type": "string (ex: API REST, microservices, monolithe, event-driven...)",
  "scale": "string (ex: startup MVP, PME, enterprise, haute disponibilité...)",
  "key_components": ["liste", "des", "composants", "majeurs"],
  "constraints": ["liste", "des", "contraintes", "techniques"],
  "success_criteria": ["critère 1", "critère 2", "..."],
  "recommended_stack": {"frontend": "...", "backend": "...", "database": "...", "infra": "..."},
  "risks": ["risque 1", "risque 2", "..."]
}""",
        messages=[{
            "role": "user",
            "content": f"Tâche : {task}\n\nContexte : {context}"
        }]
    )

    log.info(f"✅ Plan établi — Type: {result.get('system_type')}, Stack: {result.get('recommended_stack')}")
    return {
        "plan": json.dumps(result, ensure_ascii=False, indent=2),
        "iteration": 0,
        "history": []
    }


# ─── Node 2 : GENERATOR ─────────────────────────────────────────────────────
def generator(state: AgentState) -> dict:
    """
    Génère une architecture technique complète basée sur le plan.
    En mode quick : génère directement sans plan préalable.
    """
    log.info(f"⚙️  GENERATOR — Itération {state.get('iteration', 0) + 1}...")
    task = state["input_task"]
    context = state.get("context", "")
    plan = state.get("plan", "")
    history = state.get("history", [])

    previous_context = ""
    if history:
        last = history[-1]
        previous_context = f"""

--- ITÉRATION PRÉCÉDENTE ---
Draft précédent (à améliorer) :
{last.get('draft', '')}

Issues identifiées par le reviewer :
{json.dumps(last.get('review', {}), ensure_ascii=False, indent=2)}
----------------------------
"""

    # En mode quick, pas de plan — on intègre le context directement
    plan_section = f"Plan validé :\n{plan}" if plan else f"Contexte : {context}"

    draft = llm(
        system="""Tu es un architecte technique senior spécialisé en systèmes distribués et cloud-native.
Tu produis des architectures techniques détaillées, claires et actionables.
Ton output doit inclure :
1. Vue d'ensemble de l'architecture (diagramme ASCII ou textuel)
2. Composants et leurs responsabilités
3. Flux de données principaux
4. Choix technologiques justifiés
5. Patterns utilisés (CQRS, Event Sourcing, Circuit Breaker, etc. si pertinent)
6. Points d'attention sécurité
7. Stratégie de scalabilité
8. Exemple de structure de projet (arborescence)
Sois précis, concret et professionnel.""",
        messages=[{
            "role": "user",
            "content": f"""Tâche originale : {task}

{plan_section}
{previous_context}

Génère l'architecture complète."""
        }],
        max_tokens=6000
    )

    new_history = history + [{"draft": draft, "review": state.get("review", {})}]

    log.info("✅ Architecture générée")
    return {
        "draft": draft,
        "history": new_history,
        "iteration": state.get("iteration", 0) + 1
    }


# ─── Node 3 : REVIEWER ──────────────────────────────────────────────────────
def reviewer(state: AgentState) -> dict:
    """
    Revue technique structurée sur 5 dimensions :
    Sécurité, Performance, Scalabilité, Maintenabilité, Complétude.
    """
    log.info("🔍 REVIEWER — Analyse critique...")
    task = state["input_task"]
    plan = state.get("plan", "Aucun plan (mode quick)")
    draft = state["draft"]

    result = llm_json(
        system="""Tu es un CTO et expert en architecture logicielle.
Tu effectues une revue technique rigoureuse d'une proposition d'architecture.
Produis un JSON avec cette structure exacte :
{
  "status": "PASSED" | "FAILED",
  "score": <entier de 0 à 100>,
  "dimensions": {
    "security": {"score": <0-100>, "issues": [], "recommendations": []},
    "performance": {"score": <0-100>, "issues": [], "recommendations": []},
    "scalability": {"score": <0-100>, "issues": [], "recommendations": []},
    "maintainability": {"score": <0-100>, "issues": [], "recommendations": []},
    "completeness": {"score": <0-100>, "issues": [], "recommendations": []}
  },
  "blocking_issues": ["issues critiques qui imposent un FAILED"],
  "quick_wins": ["améliorations rapides à haute valeur"],
  "overall_feedback": "résumé en 2-3 phrases"
}
Status = PASSED si score >= 75 ET blocking_issues est vide.""",
        messages=[{
            "role": "user",
            "content": f"""Tâche originale : {task}

Plan de référence :
{plan}

Architecture à reviewer :
{draft}"""
        }]
    )

    status = result.get("status", "FAILED")
    score = result.get("score", 0)
    blocking = result.get("blocking_issues", [])
    log.info(f"{'✅' if status == 'PASSED' else '❌'} Review: {status} (score={score}, blocking={len(blocking)})")

    return {"review": result}


# ─── Node 4 : REFINER (full mode only) ──────────────────────────────────────
def refiner(state: AgentState) -> dict:
    """
    Raffine le draft en adressant spécifiquement les issues du reviewer.
    Uniquement en mode full.
    """
    log.info("🔧 REFINER — Application des corrections...")
    review = state["review"]
    draft = state["draft"]
    task = state["input_task"]

    blocking = review.get("blocking_issues", [])
    dimensions = review.get("dimensions", {})

    all_issues = []
    all_recs = []
    for dim_name, dim_data in dimensions.items():
        for issue in dim_data.get("issues", []):
            all_issues.append(f"[{dim_name.upper()}] {issue}")
        for rec in dim_data.get("recommendations", []):
            all_recs.append(f"[{dim_name.upper()}] {rec}")

    refined = llm(
        system="""Tu es un architecte senior en charge de corriger et améliorer une architecture technique.
Tu adresses TOUS les points bloquants et les recommandations prioritaires.
Reproduis l'architecture complète avec les corrections intégrées.
Indique clairement ce qui a changé avec des annotations [CORRIGÉ] ou [AMÉLIORÉ].""",
        messages=[{
            "role": "user",
            "content": f"""Tâche : {task}

Architecture actuelle :
{draft}

Points BLOQUANTS à corriger obligatoirement :
{chr(10).join(f'- {i}' for i in blocking) or '(aucun bloquant)'}

Issues à adresser :
{chr(10).join(f'- {i}' for i in all_issues) or '(aucune issue)'}

Recommandations à intégrer :
{chr(10).join(f'- {r}' for r in all_recs) or '(aucune recommandation)'}

Produis l'architecture révisée complète."""
        }],
        max_tokens=6000
    )

    log.info("✅ Architecture raffinée")
    return {"refined_draft": refined, "draft": refined}


# ─── Node 5 : FINALIZER ─────────────────────────────────────────────────────
def finalizer(state: AgentState) -> dict:
    """
    Produit le document final d'architecture : propre, structuré, prêt à livrer.
    """
    log.info("📄 FINALIZER — Production du document final...")
    task = state["input_task"]
    raw_plan = state.get("plan", "{}")
    plan = json.loads(raw_plan) if raw_plan else {}
    draft = state.get("refined_draft") or state["draft"]
    review = state.get("review", {})
    iterations = state.get("iteration", 1)

    final = llm(
        system="""Tu es un architecte senior qui produit un document d'architecture de référence.
Tu synthétises le travail effectué en un document clair, complet et professionnel.
Structure :
# DOCUMENT D'ARCHITECTURE TECHNIQUE
## 1. Résumé Exécutif
## 2. Vue d'Architecture
## 3. Composants & Responsabilités
## 4. Stack Technologique
## 5. Flux de Données
## 6. Sécurité
## 7. Scalabilité & Performance
## 8. Structure du Projet
## 9. Roadmap d'Implémentation
## 10. Points d'Attention & Risques""",
        messages=[{
            "role": "user",
            "content": f"""Tâche : {task}

Plan :
{json.dumps(plan, ensure_ascii=False, indent=2)}

Architecture finale (après {iterations} itération(s)) :
{draft}

Score de qualité final : {review.get('score', 'N/A')}/100
Feedback : {review.get('overall_feedback', 'N/A')}

Produis le document d'architecture final."""
        }],
        max_tokens=8000
    )

    log.info(f"✅ Document final produit ({len(final)} chars, {iterations} itération(s))")
    return {"final_output": final}


# ─── Routers ─────────────────────────────────────────────────────────────────
def router_full(state: AgentState) -> str:
    """Router mode full : boucle review/refine jusqu'à PASSED ou max iter."""
    review = state.get("review", {})
    status = review.get("status", "FAILED")
    iteration = state.get("iteration", 0)

    if status == "PASSED":
        log.info("→ Router full: PASSED → finalizer")
        return "finalizer"
    if iteration >= MAX_ITERATIONS:
        log.info(f"→ Router full: max iterations ({MAX_ITERATIONS}) atteint → finalizer")
        return "finalizer"
    log.info(f"→ Router full: FAILED (iter={iteration}) → refiner")
    return "refiner"


def router_quick(state: AgentState) -> str:
    """Router mode quick : toujours finalizer, une seule passe."""
    score = state.get("review", {}).get("score", 0)
    log.info(f"→ Router quick: score={score} → finalizer (une seule passe)")
    return "finalizer"


# ─── Graph Assembly ──────────────────────────────────────────────────────────
def build_graph(checkpointer=None, mode: str = "full"):
    workflow = StateGraph(AgentState)

    if mode == "quick":
        log.info("🏃 Mode QUICK — 3 nodes, une seule passe")
        workflow.add_node("generator", generator)
        workflow.add_node("reviewer", reviewer)
        workflow.add_node("finalizer", finalizer)

        workflow.set_entry_point("generator")
        workflow.add_edge("generator", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            router_quick,
            {"finalizer": "finalizer"}
        )
        workflow.add_edge("finalizer", END)

    else:
        log.info("🏗️  Mode FULL — 5 nodes, boucle review/refine")
        workflow.add_node("planner", planner)
        workflow.add_node("generator", generator)
        workflow.add_node("reviewer", reviewer)
        workflow.add_node("refiner", refiner)
        workflow.add_node("finalizer", finalizer)

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "generator")
        workflow.add_edge("generator", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            router_full,
            {
                "refiner": "refiner",
                "finalizer": "finalizer"
            }
        )
        workflow.add_edge("refiner", "reviewer")
        workflow.add_edge("finalizer", END)

    return workflow.compile(checkpointer=checkpointer)


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Usage:
        # Mode full (défaut) — 5 nodes, boucle review/refine
        echo '{"input_task": "Architecture microservices", "context": "Node.js, K8s"}' | python architect_agent.py

        # Mode quick — 3 nodes, une seule passe (~30s)
        echo '{"input_task": "Structure Redis pour cache sessions", "mode": "quick"}' | python architect_agent.py

        # Reprendre un run existant
        echo '{"input_task": "...", "thread_id": "abc-123"}' | python architect_agent.py

    Variables d'environnement requises:
        MINIMAX_API_KEY  — clé API MiniMax (https://api.minimaxi.chat)

    Output JSON :
        thread_id    — ID du run (pour reprise éventuelle)
        mode         — "full" | "quick"
        plan         — analyse structurée initiale (vide en mode quick)
        final_output — document d'architecture final
        review_score — score qualité 0-100
        iterations   — nombre de cycles effectués
        status       — PASSED | FAILED | UNKNOWN
    """
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            print(json.dumps({"error": "Aucune entrée fournie. Attendu: JSON avec 'input_task'"}))
            sys.exit(1)

        task_data = json.loads(raw)

        if "input_task" not in task_data:
            print(json.dumps({"error": "Champ 'input_task' manquant"}))
            sys.exit(1)

        # Extraire mode et thread_id avant invoke
        mode = task_data.pop("mode", "full")
        if mode not in ("full", "quick"):
            print(json.dumps({"error": f"Mode invalide '{mode}'. Valeurs acceptées : 'full' | 'quick'"}))
            sys.exit(1)

        thread_id = task_data.pop("thread_id", None) or str(uuid.uuid4())
        log.info(f"🧵 thread_id: {thread_id} | mode: {mode}")

        # Valeurs par défaut du state
        task_data.setdefault("context", "")
        task_data.setdefault("draft", "")
        task_data.setdefault("review", {})
        task_data.setdefault("refined_draft", "")
        task_data.setdefault("final_output", "")
        task_data.setdefault("plan", "")
        task_data.setdefault("iteration", 0)
        task_data.setdefault("history", [])
        task_data.setdefault("error", None)

        log.info(f"🚀 Démarrage — Task: {task_data['input_task'][:80]}...")
        log.info(f"🤖 Modèle: {MODEL} via MiniMax API")

        if _CHECKPOINTER == "sqlite":
            with SqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
                app = build_graph(checkpointer=checkpointer, mode=mode)
                config = {"configurable": {"thread_id": thread_id}}
                result = app.invoke(task_data, config=config)
        else:
            log.warning("⚠️  Mode MemorySaver — pas de persistance entre sessions (thread_id ignoré)")
            checkpointer = MemorySaver()
            app = build_graph(checkpointer=checkpointer, mode=mode)
            config = {"configurable": {"thread_id": thread_id}}
            result = app.invoke(task_data, config=config)

        # Parser le plan seulement s'il existe (absent en mode quick)
        raw_plan = result.get("plan", "")
        plan_output = {}
        if raw_plan:
            try:
                plan_output = json.loads(raw_plan)
            except json.JSONDecodeError:
                plan_output = {}

        output = {
            "thread_id": thread_id,
            "mode": mode,
            "plan": plan_output,
            "final_output": result.get("final_output", ""),
            "review_score": result.get("review", {}).get("score"),
            "iterations": result.get("iteration", 1),
            "status": result.get("review", {}).get("status", "UNKNOWN")
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON invalide en entrée: {str(e)}"}))
        sys.exit(1)
    except Exception as e:
        log.exception("Erreur fatale")
        print(json.dumps({"error": str(e)}))
        sys.exit(1)