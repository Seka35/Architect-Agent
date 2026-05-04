# CLAUDE.md

## SKILL: ARCHITECT_PRO

**Trigger**: Quand l'utilisateur demande un system design, une architecture,
ou un script complexe (>100 lignes avec plusieurs composants).

---

## ⚙️ Setup (première utilisation ou après git clone)

Le script requiert un **environnement virtuel Python** avec ses dépendances.
**Toujours vérifier le venv avant d'exécuter.**

```bash
# 1. Se placer dans le répertoire du projet
cd ~/scripts/   # ou le chemin réel du projet

# 2. Créer le venv s'il n'existe pas
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# 3. Installer / mettre à jour les dépendances
.venv/bin/pip install -q -r requirements.txt

# 4. Vérifier que les imports critiques fonctionnent
.venv/bin/python3 -c "from langgraph.checkpoint.sqlite import SqliteSaver; print('✅ SqliteSaver OK')"
```

> ⚠️ **Ne jamais utiliser `python3` système** — toujours `.venv/bin/python3`.
> Le Python système n'a pas les dépendances nécessaires et causera des ImportError.

---

## 🔑 Configuration du .env

Mettre le fichier `.env` dans le **même dossier que le script** (`~/scripts/.env`).
Le script le charge automatiquement — aucune commande `export` nécessaire.

```bash
# Créer le .env (une seule fois)
echo "MINIMAX_API_KEY=sk-..." > ~/scripts/.env
```

Le script cherche le `.env` dans cet ordre :
1. Dossier du script (`~/scripts/.env`) ← **recommandé**
2. Dossier courant (`./env`)

---

## 🧠 Choisir le mode

| Situation | Mode |
|-----------|------|
| Architecture complète, nouveau projet, système complexe | `full` |
| Question rapide, composant isolé, validation d'un choix technique | `quick` |
| Pas précisé par l'utilisateur | `full` par défaut |

---

## 📋 Étapes d'exécution

1. **Vérifier le venv** (voir Setup ci-dessus) — obligatoire avant chaque run.

2. **Extraire** `input_task` (demande reformulée clairement) et `context`
   (stack, contraintes, scale, environnement) depuis le message utilisateur.

3. **Choisir le mode** selon le tableau ci-dessus.

4. **Construire le payload JSON** :

   ```json
   {
     "input_task": "description précise et complète",
     "context": "stack technique, contraintes, environnement de déploiement",
     "mode": "full"
   }
   ```

5. **Exécuter avec le venv** :

   ```bash
   echo '$JSON' | .venv/bin/python3 ~/scripts/architect_agent.py
   ```

6. **Interpréter le résultat** :
   - `review_score >= 80` → Présenter `final_output` directement
   - `review_score 60–79` → Présenter avec les warnings du champ `review`
   - `review_score < 60`  → Demander guidance manuelle à l'utilisateur
   - `iterations >= 3`    → Signaler que des arbitrages manuels sont nécessaires

7. **Toujours afficher** : score final, mode utilisé, nombre d'itérations, stack recommandée.

8. **Sauvegarder le `thread_id`** retourné — permet de reprendre le run si besoin.

---

## 🔁 Reprendre un run existant

Si l'utilisateur fournit un `thread_id` :

```bash
echo '{"input_task": "...", "context": "...", "thread_id": "abc-123"}' | .venv/bin/python3 ~/scripts/architect_agent.py
```

---

## 🚫 Ne pas utiliser cette skill si

- La demande est un snippet simple ou une fonction isolée (<50 lignes)
- L'utilisateur demande juste une explication théorique
- Le fichier `architect_agent.py` est absent du répertoire projet

---

## 🐛 Dépannage

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ModuleNotFoundError: langgraph` | Python système utilisé | Utiliser `.venv/bin/python3` |
| `ImportError: langgraph.checkpoint.sqlite` | Dépendance manquante | `.venv/bin/pip install langgraph-checkpoint-sqlite` |
| `MINIMAX_API_KEY manquante` | `.env` absent ou non chargé | `export $(cat .env \| xargs)` avant d'exécuter |
| `⚠️ Mode MemorySaver` | sqlite checkpoint non installé | `.venv/bin/pip install langgraph-checkpoint-sqlite` |
