# CLAUDE.md

## SKILL: ARCHITECT_PRO

**Trigger**: When the user asks for a system design, architecture,
or a complex script (>100 lines with multiple components).

---

## ⚙️ Setup (first use or after git clone)

The script requires a **Python virtual environment** with its dependencies.
**Always verify the venv before running.**

```bash
# 1. Go to the project directory
cd ~/scripts/   # or the actual project path

# 2. Create the venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# 3. Install / update dependencies
.venv/bin/pip install -q -r requirements.txt

# 4. Verify critical imports work
.venv/bin/python3 -c "from langgraph.checkpoint.sqlite import SqliteSaver; print('✅ SqliteSaver OK')"
```

> ⚠️ **Never use system `python3`** — always use `.venv/bin/python3`.
> The system Python does not have the required dependencies and will cause ImportErrors.

---

## 🔑 .env Configuration

Place the `.env` file in the **same folder as the script** (`~/scripts/.env`).
The script loads it automatically — no `export` command needed.

```bash
# Create the .env (one time only)
echo "MINIMAX_API_KEY=sk-..." > ~/scripts/.env
```

The script looks for `.env` in this order:
1. Script folder (`~/scripts/.env`) ← **recommended**
2. Current working directory (`./env`)

---

## 🧠 Choosing a Mode

| Situation | Mode |
|-----------|------|
| Full architecture, new project, complex system | `full` |
| Quick question, isolated component, validating a tech choice | `quick` |
| Not specified by the user | `full` by default |

---

## 📋 Execution Steps

1. **Verify the venv** (see Setup above) — mandatory before every run.

2. **Extract** `input_task` (clearly reformulated request) and `context`
   (stack, constraints, scale, environment) from the user's message.

3. **Choose the mode** based on the table above.

4. **Build the JSON payload**:

   ```json
   {
     "input_task": "precise and complete description",
     "context": "tech stack, constraints, deployment environment",
     "mode": "full"
   }
   ```

5. **Run with the venv**:

   ```bash
   echo '$JSON' | .venv/bin/python3 ~/scripts/architect_agent.py
   ```

6. **Interpret the result**:
   - `review_score >= 80` → Present `final_output` directly
   - `review_score 60–79` → Present with warnings from the `review` field
   - `review_score < 60`  → Ask the user for manual guidance
   - `iterations >= 3`    → Signal that manual trade-offs are needed

7. **Always display**: final score, mode used, iteration count, recommended stack.

8. **Save the returned `thread_id`** — allows resuming the run if needed.

---

## 🔁 Resuming an Existing Run

If the user provides a `thread_id`:

```bash
echo '{"input_task": "...", "context": "...", "thread_id": "abc-123"}' | .venv/bin/python3 ~/scripts/architect_agent.py
```

---

## 🚫 Do NOT Use This Skill If

- The request is a simple snippet or isolated function (<50 lines)
- The user is asking for a theoretical explanation only
- The `architect_agent.py` file is missing from the project directory

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: langgraph` | System Python used | Use `.venv/bin/python3` |
| `ImportError: langgraph.checkpoint.sqlite` | Missing dependency | `.venv/bin/pip install langgraph-checkpoint-sqlite` |
| `MINIMAX_API_KEY missing` | `.env` absent or not loaded | Create `.env` with `MINIMAX_API_KEY=sk-...` |
| `⚠️ MemorySaver mode` | sqlite checkpoint not installed | `.venv/bin/pip install langgraph-checkpoint-sqlite` |
