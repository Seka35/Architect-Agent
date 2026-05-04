# 🏛️ Architect-Agent Pro v2.0

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![LiteLLM](https://img.shields.io/badge/LiteLLM-Multi--Model-blueviolet)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_UI-009688)
![License](https://img.shields.io/badge/License-MIT-green)

**Production-grade multi-agent system for automated technical architecture design and review.**

Architect-Agent Pro is not just an AI wrapper. It's a sophisticated **State Machine** that orchestrates 5 specialized roles in a cyclic reflection loop — every architecture produced is planned, critiqued, and corrected automatically before delivery.

---

## 🆕 What's new in v2.0?

1. **Multi-LLM Support (via LiteLLM)**: No longer locked to MiniMax. Use OpenAI (`gpt-4o`), Anthropic (`claude-3.5-sonnet`), Gemini, or MiniMax seamlessly via `.env`.
2. **Beautiful Web UI**: Real-time streaming and graph visualization using **FastAPI** and Vanilla JS (Server-Sent Events).
3. **Actionable Outputs**: Automatically extracts generated files (e.g. `docker-compose.yml`, `README.md`) to the `workspace_out/<thread_id>/` folder.
4. **Externalized Prompts**: Tweak agent behaviors without changing code via markdown files in the `prompts/` directory.
5. **Quality Metrics**: The reviewer's scores are saved locally in a SQLite `metrics` table to track your system's output quality over time.

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
                                 (Files Extracted)
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
| ⚙️ **Generator** | full + quick | Produces full architecture (ASCII diagram, patterns, code) | Markdown draft |
| 🔍 **Reviewer** | full + quick | Audit across 5 dimensions with score 0–100 | JSON PASSED / FAILED |
| 🔧 **Refiner** | full | Fixes blocking issues from reviewer | Revised draft |
| 📄 **Finalizer** | full + quick | Formats final document and triggers file generation | Deliverable document |

---

## 📋 Prerequisites

- Python 3.11+
- At least one API key (OpenAI, Anthropic, MiniMax, Gemini...)

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

Create a `.env` file from the example:

```bash
cp .env.exemple .env
```
Fill in your preferred provider key and specify the model:
```env
MINIMAX_API_KEY="sk-..."
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
GEMINI_API_KEY="AIza..."

# Default model used by the agent (LiteLLM format)
LLM_MODEL="minimax/MiniMax-M2.7"
```

---

## 🚀 Usage

### 🌐 Method 1: Web Interface (Recommended)

Start the local server to access the visual dashboard:

```bash
source .venv/bin/activate
python app.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser. 
- Watch the LangGraph state machine light up in real-time.
- View real-time terminal logs.
- Explore generated files and scores directly from the UI.

### 💻 Method 2: CLI Interface (For CI/CD & Automation)

Pass a JSON payload via STDIN:

```bash
# Full mode (default) — complex architecture
echo '{
  "input_task": "Microservices architecture for an e-commerce platform",
  "context": "Node.js, PostgreSQL, Kubernetes"
}' | .venv/bin/python3 architect_agent.py

# Quick mode — fast answer
echo '{
  "input_task": "Redis structure for session caching",
  "mode": "quick"
}' | .venv/bin/python3 architect_agent.py

# Streaming mode — Watch logs in real-time in CLI
echo '{
  "input_task": "...",
  "stream": true
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
    "key_components": ["API Gateway", "Auth Service", "PostgreSQL", "Redis"]
  },
  "final_output": "# TECHNICAL ARCHITECTURE DOCUMENT\n...",
  "saved_files": [
    "/absolute/path/to/workspace_out/f47ac10b.../docker-compose.yml"
  ],
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
- **Executive summary**
- **Visual architecture**
- **Detailed components**
- **Justified tech stack**
- **Data flows**
- **Scalability & Performance**
- **Project file tree & Roadmap**
- **Risk analysis**

> Quality score: **87/100** — Status: **PASSED**

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
5. Displays score, mode, iterations, and generated actionable files

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
├── app.py               # FastAPI Web Server (New)
├── architect_agent.py   # Core LangGraph agent logic
├── prompts/             # Externalized AI prompts (New)
│   ├── planner.md
│   ├── generator.md
│   ├── reviewer.md
│   ├── refiner.md
│   └── finalizer.md
├── static/              # Web UI assets (New)
│   └── index.html
├── workspace_out/       # Generated actionable files (Auto-created)
├── architect_runs.db    # SQLite states & metrics (Auto-created)
├── examples/            # Sample generated documents
├── claude.md            # Instructions for Claude Code
├── requirements.txt     # Python dependencies
├── .env.exemple         # Env template
└── README.md
```

---

## 📜 License

MIT — see [LICENSE](LICENSE).
