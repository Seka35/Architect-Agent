# 🏛️ Architect-Agent Pro

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange)
![MiniMax](https://img.shields.io/badge/MiniMax-M2.7-red)
![License](https://img.shields.io/badge/License-MIT-green)

**Système multi-agents de production pour la conception et l'audit automatisé d'architectures techniques.**

Architect-Agent Pro n'est pas un simple wrapper d'IA. C'est une **State Machine** sophistiquée qui orchestre 5 rôles spécialisés en boucle de réflexion cyclique — chaque architecture produite est planifiée, critiquée et corrigée automatiquement avant d'être livrée.

---

## 🔄 Workflow

### Mode `full` (défaut)

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

### Mode `quick`

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

| Mode | Nodes | Boucle | Durée estimée | Usage |
|------|-------|--------|---------------|-------|
| `full` | 5 | review/refine max 3x | ~2-3 min | Architectures complexes |
| `quick` | 3 | aucune, une seule passe | ~30 sec | Questions rapides |

### Les 5 nœuds

| Nœud | Mode | Rôle | Output |
|------|------|------|--------|
| 🗺️ **Planner** | full | Analyse la tâche, définit stack & contraintes, identifie les risques | Plan JSON structuré |
| ⚙️ **Generator** | full + quick | Produit l'architecture complète (diagramme ASCII, patterns, arborescence) | Draft Markdown |
| 🔍 **Reviewer** | full + quick | Audit sur 5 dimensions avec score 0–100 | JSON PASSED / FAILED |
| 🔧 **Refiner** | full | Corrige les issues bloquantes, annote les changements `[CORRIGÉ]` | Draft révisé |
| 📄 **Finalizer** | full + quick | Formate le document de référence final en 10 sections | Document livrable |

---

## ✨ Caractéristiques techniques

- **LLM : MiniMax-M2.7** — via API OpenAI-compatible (`https://api.minimaxi.chat/v1`)
- **Deux modes** — `full` pour les architectures complexes, `quick` pour les réponses rapides
- **Persistance SQLite** — `SqliteSaver` sauvegarde chaque état. Reprenez n'importe quelle session avec son `thread_id`
- **JSON robuste** — Parser 4 étapes (direct → strip backticks → regex `{.*}` → ValueError avec debug)
- **Historique inter-itérations** — Le Generator voit les drafts et reviews précédents pour progresser, pas juste réécrire
- **Interface CLI universelle** — STDIN/STDOUT JSON, compatible avec tout pipeline CI/CD, Claude Code ou script shell
- **Logging structuré** — Tous les logs partent sur `stderr`, l'output JSON propre sur `stdout`

---

## 📋 Prérequis

- Python 3.11+
- Clé API MiniMax — [Obtenir une clé API MiniMax](https://platform.minimax.io/subscribe/token-plan?code=CFCvBqd627)

---

## 📦 Installation

```bash
git clone https://github.com/Seka35/Architect-Agent.git
cd Architect-Agent

python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration `.env`

Créez un fichier `.env` dans le dossier du projet — **le script le charge automatiquement**, aucun `export` nécessaire :

```bash
cp .env.exemple .env
# Éditez .env et renseignez votre clé
echo "MINIMAX_API_KEY=sk-votre-clé-ici" > .env
```

Obtenez votre clé API : [MiniMax API](https://platform.minimax.io/subscribe/token-plan?code=CFCvBqd627)

**requirements.txt**

```
openai>=1.0.0
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=2.0.0
python-dotenv>=1.0.0
```

---

## 🚀 Utilisation

### Mode full — architecture complète

```bash
echo '{
  "input_task": "Architecture microservices Prime Circle",
  "context": "Node.js, PostgreSQL, Kubernetes, 10k users"
}' | python3 architect_agent.py
```

### Mode quick — réponse rapide

```bash
echo '{
  "input_task": "Structure Redis pour cache de sessions",
  "mode": "quick"
}' | python3 architect_agent.py
```

### Reprendre un run existant

```bash
echo '{
  "input_task": "...",
  "context": "...",
  "thread_id": "a1b2c3d4-..."
}' | python3 architect_agent.py
```

---

## 📤 Output JSON

```json
{
  "thread_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "mode": "full",
  "plan": {
    "system_type": "API REST microservices",
    "scale": "PME, 10k utilisateurs actifs",
    "key_components": ["API Gateway", "Auth Service", "Task Service", "PostgreSQL", "Redis"],
    "recommended_stack": {
      "frontend": "React",
      "backend": "Node.js / Fastify",
      "database": "PostgreSQL + Redis",
      "infra": "Kubernetes / Helm"
    },
    "risks": ["Contention DB multi-tenant", "Gestion des secrets en CI/CD"]
  },
  "final_output": "# DOCUMENT D'ARCHITECTURE TECHNIQUE\n## 1. Résumé Exécutif\n...",
  "review_score": 87,
  "iterations": 2,
  "status": "PASSED"
}
```

---

## 📄 Exemple de document généré

Voici un exemple réel de document produit par l'agent pour la tâche :
> *"Créer un jeu Snake version futuriste — HTML/CSS/JS vanilla, esthétique cyberpunk/néon"*

📎 **[Voir le document complet → examples/snake_futuriste.md](examples/snake_futuriste.md)**

Le document généré contient :
- **Résumé exécutif** — vue d'ensemble en quelques lignes
- **Architecture visuelle** — diagramme ASCII du pipeline de rendu multi-canvas
- **Composants détaillés** — GameState, SnakeRenderer, ParticleSystem, AudioSystem, etc.
- **Stack technologique justifiée** — HTML5 Canvas, Web Audio API, localStorage
- **Flux de données** — boucle de jeu, input → physics → render
- **Scalabilité & Performance** — object pool, requestAnimationFrame, devicePixelRatio
- **Arborescence du projet** — structure de fichiers complète (~20 fichiers JS)
- **Roadmap en 5 phases** — 10 jours de développement détaillés
- **Analyse des risques** — tableau probabilité/impact/mitigation

> Score qualité : **87/100** — Status : **PASSED** — 1 itération (mode `quick`)

---

## 🗂️ State TypedDict

```python
class AgentState(TypedDict):
    input_task: str        # Tâche initiale
    context: str           # Stack, contraintes, environnement
    plan: str              # Plan JSON du Planner (vide en mode quick)
    draft: str             # Dernière architecture générée
    review: dict           # Résultat structuré du Reviewer
    refined_draft: str     # Draft post-Refiner (mode full uniquement)
    final_output: str      # Document final livrable
    iteration: int         # Compteur de cycles
    history: list          # Historique drafts + reviews
    error: Optional[str]   # Erreur éventuelle
```

---

## 🛡️ Ce que le Reviewer détecte

| Dimension | Exemples d'issues détectées |
|-----------|----------------------------|
| **Sécurité** | Secrets en clair, surface réseau exposée, RBAC manquant |
| **Performance** | Absence de cache, N+1 queries, pas de pagination |
| **Scalabilité** | SPOF, couplage fort, pas de queue async |
| **Maintenabilité** | Absence de tests, couplage logique métier/infra |
| **Complétude** | Sections manquantes, flux non documentés |

---

## 🔧 Intégration Claude Code (CLAUDE.md)

```markdown
## SKILL: ARCHITECT_PRO

**Trigger**: System design, architecture, script complexe (>100 lignes, multi-composants)
**Script**: ~/scripts/architect_agent.py

1. Extraire `input_task` et `context` du message utilisateur
2. Choisir le mode : `quick` pour questions simples, `full` pour architectures complexes
3. Construire le payload JSON et piper vers le script
4. review_score >= 80 → présenter final_output directement
   review_score 60-79 → présenter avec warnings du champ review
   review_score < 60  → demander guidance manuelle
   iterations >= 3    → signaler arbitrages manuels nécessaires
```

---

## 📁 Structure du projet

```
Architect-Agent/
├── architect_agent.py   # Agent principal
├── requirements.txt     # Dépendances Python
├── .env.exemple         # Template variables d'environnement
├── .env                 # Votre clé API (non versionné)
├── examples/            # Exemples de documents générés
│   └── snake_futuriste.md
├── .gitignore
├── claude.md            # Instructions pour Claude Code
└── README.md
```

**.gitignore**

```
.env
architect_runs.db
venv/
__pycache__/
*.pyc
```

---

## 📜 Licence

MIT — voir [LICENSE](LICENSE).
