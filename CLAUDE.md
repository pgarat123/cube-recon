# CLAUDE.md : règles de travail pour cube-recon

Lire PLAN.md pour la vision, l'architecture et la feuille de route. Ce fichier ne contient que les règles de travail.

## Contexte
- Projet perso / portfolio, sans deadline.
- Machine : MacBook M1 Pro. Pas de CUDA : PyTorch en MPS, rien qui dépende de NVIDIA.
- L'utilisateur est sub-12 en CFOP : il connaît la notation et les algos, inutile de lui expliquer le cubing.

## Budget (forfait Claude Pro, à respecter)
- Une session = un module ou une tâche de PLAN.md. Pas de dérive de périmètre.
- Lire ciblé : ne pas parcourir tout le repo, partir de PLAN.md et des fichiers concernés.
- Pas de multi-agents ni de workflows sauf demande explicite.
- Pas de recherches web larges : une recherche ciblée si une info manque vraiment.
- Les tâches manuelles (filmer, annoter, tester sur le vrai cube) reviennent à l'utilisateur. Le dire clairement plutôt que de les contourner.
- Avant une tâche lourde (entraînement, gros refactor), annoncer le coût estimé et demander.

## Conventions
- Langue : français pour la doc et les échanges, anglais pour le code (noms, docstrings, commits).
- Style d'écriture : pas de tiret em (—), phrases simples.
- Python 3.11, `uv` pour l'environnement, `ruff` pour lint/format, `pytest` pour les tests.
- Code métier (cube/, analysis/, decode/) : pur Python, testé, sans dépendance à la vidéo.
- Toute logique de cube passe par `cuberecon.cube` : jamais de manipulation d'état ailleurs.
- Les données (`data/`) ne sont jamais versionnées.
- Mettre à jour PLAN.md (cases à cocher, statut) quand une phase avance.

## Commandes
- `uv sync` : installer / mettre à jour l'environnement (Python 3.11, `.venv/`)
- `uv run pytest` : tests
- `uv run ruff check .` et `uv run ruff format .` : lint et formatage
- `uv add <pkg>` : ajouter une dépendance (ne pas éditer pyproject à la main pour ça)

Les dépendances lourdes (torch, opencv, mediapipe, ultralytics) ne sont ajoutées qu'à la phase qui en a besoin.
