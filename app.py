import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys

app = FastAPI(title="Architect Agent Pro UI")

# Monter le dossier statique
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = static_dir / "index.html"
    if not index_path.exists():
        return "Frontend non trouvé. Veuillez vérifier le dossier static/index.html."
    return index_path.read_text(encoding="utf-8")

@app.post("/api/run")
async def run_agent(request: Request):
    data = await request.json()
    
    # On force le mode stream pour récupérer les logs sur stderr
    data["stream"] = True

    async def event_generator():
        # Lancer le script via asyncio subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable, "architect_agent.py",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(Path(__file__).parent)
        )
        
        # Envoyer les données en JSON sur stdin
        process.stdin.write(json.dumps(data).encode("utf-8"))
        process.stdin.write(b"\n")
        await process.stdin.drain()
        process.stdin.close()

        # Fonction pour lire stderr ligne par ligne et l'envoyer comme événement
        async def read_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                line_str = line.decode('utf-8').strip()
                if line_str:
                    yield {"event": "log", "data": line_str}

        # Fonction pour lire stdout (qui contiendra le JSON final)
        async def read_stdout():
            stdout_data = await process.stdout.read()
            if stdout_data:
                yield {"event": "result", "data": stdout_data.decode('utf-8').strip()}

        # On intercale la lecture de stderr jusqu'à la fin du process
        async for msg in read_stderr():
            yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
            
        await process.wait()
        
        async for msg in read_stdout():
            # JSON brut dans data (pour éviter double escape)
            yield f"event: {msg['event']}\ndata: {msg['data']}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
