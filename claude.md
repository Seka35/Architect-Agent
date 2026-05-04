# CLAUDE.md

## SKILL: ARCHITECT_PRO

**Trigger**: Quand l'utilisateur demande un system design, une architecture,
ou un script complexe (>100 lignes avec plusieurs composants).

**Script**: `~/scripts/architect_agent.py`
**Requirements**: `~/scripts/requirements.txt`

### Choisir le mode

| Situation | Mode |
|-----------|------|
| Architecture complète, nouveau projet, système complexe | `full` |
| Question rapide, composant isolé, validation d'un choix technique | `quick` |
| Pas précisé par l'utilisateur | `full` par défaut |

### Étapes

1. **Extraire** `input_task` (demande reformulée clairement) et `context`
   (stack, contraintes, scale, environnement) depuis le message utilisateur.

2. **Choisir le mode** selon le tableau ci-dessus.

3. **Construire le payload JSON** :

   ```json
   {
     "input_task": "description précise et complète",
     "context": "stack technique, contraintes, environnement de déploiement",
     "mode": "full"
   }
   ```

4. **Exécuter** :

   ```bash
   echo '$JSON' | python3 ~/scripts/architect_agent.py
   ```

5. **Interpréter le résultat** :
   - `review_score >= 80` → Présenter `final_output` directement
   - `review_score 60–79` → Présenter avec les warnings du champ `review`
   - `review_score < 60`  → Demander guidance manuelle à l'utilisateur
   - `iterations >= 3`    → Signaler que des arbitrages manuels sont nécessaires

6. **Toujours afficher** : score final, mode utilisé, nombre d'itérations, stack recommandée.

7. **Sauvegarder le `thread_id`** retourné — permet de reprendre le run si besoin.

### Ne pas utiliser cette skill si

- La demande est un snippet simple ou une fonction isolée (<50 lignes)
- L'utilisateur demande juste une explication théorique
- Le fichier `architect_agent.py` est absent de `~/scripts/`

### Reprendre un run existant

Si l'utilisateur fournit un `thread_id` :

```bash
echo '{"input_task": "...", "context": "...", "thread_id": "abc-123"}' | python3 ~/scripts/architect_agent.py
```
