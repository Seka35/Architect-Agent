# 🏛️ Architect-Agent Pro

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![MiniMax](https://img.shields.io/badge/MiniMax-M2.7-red)
![License](https://img.shields.io/badge/License-MIT-green)

**Production-grade multi-agent system for automated technical architecture design and review.**

Architect-Agent Pro is not just an AI wrapper. It's a sophisticated **State Machine** that orchestrates 5 specialized roles in a cyclic reflection loop — every architecture produced is planned, critiqued, and corrected automatically before delivery.

---

## 🔄 Workflow

### `full` mode (default)

```
input_task
    │
    ▼
┌─────────┐     ┌───────────┐     ┌──────────┐
│ Planner │────▶│ Generator │────▶│ Reviewer │
└─────────┘     └───────────┘     └────┬─────┘
                      ▲                │
                      │    FAILED      │  PASSED
                      │   (iter < 3)   │
                ┌─────┴──────┐         ▼
                │  Refiner   │    ┌───────────┐
                └────────────┘    │ Finalizer │
                                  └─────┬─────┘
                                        ▼
                                   final_output
```

### `quick` mode

```
input_task
    │
    ▼
┌───────────┐     ┌──────────┐     ┌───────────┐
│ Generator │────▶│ Reviewer │────▶│ Finalizer │
└───────────┘     └──────────┘     └─────┬─────┘
                                         ▼
                                    final_output
```

| Mode | Nodes | Loop | Est. Duration | Use Case |
|------|-------|------|---------------|----------|
| `full` | 5 | review/refine up to 3x | ~2-3 min | Complex architectures |
| `quick` | 3 | none, single pass | ~30 sec | Quick questions |

### The 5 nodes

| Node | Mode | Role | Output |
|------|------|------|--------|
| 🗺️ **Planner** | full | Analyzes task, defines stack & constraints, identifies risks | Structured JSON plan |
| ⚙️ **Generator** | full + quick | Produces full architecture (ASCII diagram, patterns, file tree) | Markdown draft |
| 🔍 **Reviewer** | full + quick | Audit across 5 dimensions with score 0–100 | JSON PASSED / FAILED |
| 🔧 **Refiner** | full | Fixes blocking issues, annotates changes `[FIXED]` | Revised draft |
| 📄 **Finalizer** | full + quick | Formats the final reference document in 10 sections | Deliverable document |

---

## ✨ Technical Features

- **LLM: MiniMax-M2.7** — via OpenAI-compatible API (`https://api.minimaxi.chat/v1`)
- **Two modes** — `full` for complex architectures, `quick` for rapid responses
- **SQLite persistence** — `SqliteSaver` saves every state. Resume any session using its `thread_id`
- **Robust JSON parsing** — 4-step parser (direct → strip backticks → `{.*}` regex → ValueError with debug)
- **Cross-iteration history** — Generator sees previous drafts and reviews to improve, not just rewrite
- **Universal CLI interface** — STDIN/STDOUT JSON, compatible with any CI/CD pipeline, Claude Code, or shell script
- **Structured logging** — All logs go to `stderr`, clean JSON output to `stdout`

---

## 📋 Prerequisites

- Python 3.11+
- MiniMax API key — [Get a MiniMax API key](https://platform.minimax.io/subscribe/token-plan?code=CFCvBqd627)

---

## 📦 Installation

```bash
git clone https://github.com/Seka35/Architect-Agent.git
cd Architect-Agent

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### `.env` Configuration

Create a `.env` file in the project folder — **the script loads it automatically**, no `export` needed:

```bash
cp .env.exemple .env
# Edit .env and fill in your key
echo "MINIMAX_API_KEY=sk-your-key-here" > .env
```

Get your API key: [MiniMax API](https://platform.minimax.io/subscribe/token-plan?code=CFCvBqd627)

**requirements.txt**

```
openai>=1.0.0
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=2.0.0
python-dotenv>=1.0.0
```

---

## 🚀 Usage

### Full mode — complete architecture

```bash
echo '{
  "input_task": "Microservices architecture for an e-commerce platform",
  "context": "Node.js, PostgreSQL, Kubernetes, 10k users"
}' | .venv/bin/python3 architect_agent.py
```

### Quick mode — fast answer

```bash
echo '{
  "input_task": "Redis structure for session caching",
  "mode": "quick"
}' | .venv/bin/python3 architect_agent.py
```

### Resume an existing run

```bash
echo '{
  "input_task": "...",
  "context": "...",
  "thread_id": "a1b2c3d4-..."
}' | .venv/bin/python3 architect_agent.py
```

---

## 📤 JSON Output

```json
{
  "thread_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "mode": "full",
  "plan": {
    "system_type": "REST API microservices",
    "scale": "SMB, 10k active users",
    "key_components": ["API Gateway", "Auth Service", "Task Service", "PostgreSQL", "Redis"],
    "recommended_stack": {
      "frontend": "React",
      "backend": "Node.js / Fastify",
      "database": "PostgreSQL + Redis",
      "infra": "Kubernetes / Helm"
    },
    "risks": ["Multi-tenant DB contention", "Secrets management in CI/CD"]
  },
  "final_output": "# TECHNICAL ARCHITECTURE DOCUMENT\n## 1. Executive Summary\n...",
  "review_score": 87,
  "iterations": 2,
  "status": "PASSED"
}
```

---

## 📄 Example Generated Document

Here is a real example of a document produced by the agent for the task:
> *"Create a futuristic Snake game — HTML/CSS/JS vanilla, cyberpunk/neon aesthetic"*

📎 **[View full document → examples/snake_futuriste.md](examples/snake_futuriste.md)**

The generated document includes:
- **Executive summary** — high-level overview in a few lines
- **Visual architecture** — ASCII diagram of the multi-canvas rendering pipeline
- **Detailed components** — GameState, SnakeRenderer, ParticleSystem, AudioSystem, etc.
- **Justified tech stack** — HTML5 Canvas, Web Audio API, localStorage
- **Data flows** — game loop, input → physics → render
- **Scalability & Performance** — object pool, requestAnimationFrame, devicePixelRatio
- **Project file tree** — complete structure (~20 JS files)
- **5-phase roadmap** — detailed 10-day development plan
- **Risk analysis** — probability/impact/mitigation table

> Quality score: **87/100** — Status: **PASSED** — 1 iteration (`quick` mode)

---

## 🗂️ State TypedDict

```python
class AgentState(TypedDict):
    input_task: str        # Initial task
    context: str           # Stack, constraints, environment
    plan: str              # Planner JSON plan (empty in quick mode)
    draft: str             # Latest generated architecture
    review: dict           # Structured Reviewer result
    refined_draft: str     # Post-Refiner draft (full mode only)
    final_output: str      # Final deliverable document
    iteration: int         # Cycle counter
    history: list          # Drafts + reviews history
    error: Optional[str]   # Optional error
```

---

## 🛡️ What the Reviewer Detects

| Dimension | Example issues detected |
|-----------|------------------------|
| **Security** | Secrets in plain text, exposed network surface, missing RBAC |
| **Performance** | Missing cache, N+1 queries, no pagination |
| **Scalability** | SPOF, tight coupling, no async queue |
| **Maintainability** | No tests, mixed business logic and infra |
| **Completeness** | Missing sections, undocumented flows |

---

## 🔧 Claude Code Integration (CLAUDE.md)

The `claude.md` file at the project root automatically instructs Claude Code on how to use the agent.

**What Claude Code does automatically:**
1. Checks/creates the `.venv` with all dependencies
2. Always uses `.venv/bin/python3` (never system `python3`)
3. Loads `.env` automatically (no `export` needed)
4. Picks `full` or `quick` mode based on request complexity
5. Displays score, mode, iterations, and recommended stack

```bash
# Full mode (default) — complex architecture
echo '{"input_task": "...", "context": "..."}' | .venv/bin/python3 architect_agent.py

# Quick mode — fast question
echo '{"input_task": "...", "mode": "quick"}' | .venv/bin/python3 architect_agent.py
```

| Score | Claude Code Behavior |
|-------|---------------------|
| ≥ 80  | Presents `final_output` directly |
| 60–79 | Presents with warnings from `review` field |
| < 60  | Asks user for manual guidance |
| iter ≥ 3 | Signals that manual trade-offs are needed |

---

## 📁 Project Structure

```
Architect-Agent/
├── architect_agent.py   # Main agent
├── requirements.txt     # Python dependencies
├── .env.exemple         # Environment variable template
├── .env                 # Your API key (not versioned)
├── examples/            # Sample generated documents
│   └── snake_futuriste.md
├── .gitignore
├── claude.md            # Instructions for Claude Code
└── README.md
```

**.gitignore**

```
.env
architect_runs.db
.venv/
__pycache__/
*.pyc
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).
