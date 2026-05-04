# 🏛️ Architect-Agent Pro v2.0

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![LiteLLM](https://img.shields.io/badge/LiteLLM-Multi--Model-blueviolet)
![FastAPI](https://img.shields.io/badge/FastAPI-Web_UI-009688)
![License](https://img.shields.io/badge/License-MIT-green)

**Production-grade multi-agent system for automated technical architecture design and review.**

Architect-Agent Pro is a sophisticated **State Machine** that orchestrates 5 specialized roles in a cyclic reflection loop. Every architecture produced is planned, critiqued, and corrected automatically before delivery. 

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

| Node | Role |
|------|------|
| 🗺️ **Planner** | Analyzes task, defines stack & constraints |
| ⚙️ **Generator** | Produces architecture (diagrams, patterns, code) |
| 🔍 **Reviewer** | Audit across 5 dimensions with score 0–100 |
| 🔧 **Refiner** | Fixes blocking issues from reviewer |
| 📄 **Finalizer** | Formats final document and triggers file generation |

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

# Default model used by the agent
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
echo '{
  "input_task": "Microservices architecture for an e-commerce platform",
  "context": "Node.js, PostgreSQL, Kubernetes"
}' | .venv/bin/python3 architect_agent.py
```

**Quick mode:**
```bash
echo '{
  "input_task": "Redis structure for session caching",
  "mode": "quick"
}' | .venv/bin/python3 architect_agent.py
```

---

## 📂 Project Structure

```
Architect-Agent/
├── app.py               # FastAPI Web Server
├── architect_agent.py   # Core LangGraph agent logic
├── prompts/             # Externalized AI prompts
│   ├── planner.md
│   ├── generator.md
│   ├── reviewer.md
│   ├── refiner.md
│   └── finalizer.md
├── static/              # Web UI assets
│   └── index.html
├── workspace_out/       # Generated actionable files (auto-created)
├── architect_runs.db    # SQLite states & metrics (auto-created)
├── requirements.txt     # Python dependencies
├── .env.exemple         # Env template
└── README.md
```

---

## 📄 Output Generation

If the agent generates code blocks with filenames (e.g. ` ```yaml docker-compose.yml `), they are automatically extracted and saved to:
`workspace_out/<thread_id>/docker-compose.yml`

This allows the agent to produce ready-to-use boilerplate and infra configurations alongside the architecture document.

---

## 📜 License

MIT — see [LICENSE](LICENSE).
