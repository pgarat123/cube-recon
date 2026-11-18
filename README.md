# cube-recon

Reconstruction assistée de solves 3x3 (CFOP) à partir d'une vidéo, puis analyse de la solve.

Voir [PLAN.md](PLAN.md) pour la feuille de route.

## Démarrage

```bash
uv sync
uv run pytest
uv run ruff check .
```

## Outil de labellisation (phase 1)

Outil web local : on parcourt une vidéo de session image par image, on saisit les mouvements au
clavier avec leur timestamp, le cube 3D suit, l'analyse CFOP est calculée par `cuberecon.analysis`
et la solve est enregistrée en `Solve` JSON dans `data/labels/`.

Prérequis : `ffmpeg` (pour `ffprobe`), Node.js, les vidéos dans `data/videos/`.

Première fois (et après chaque modification du front) :

```bash
npm --prefix apps/web ci
npm --prefix apps/web run build
```

Lancer l'outil (ouvre http://127.0.0.1:8765 dans le navigateur) :

```bash
uv run cuberecon-label
```

Options : `--port`, `--data-dir`, `--no-browser`.

Mode développement du front (rechargement à chaud), dans deux terminaux :

```bash
uv run cuberecon-label --no-browser
```

```bash
npm --prefix apps/web run dev
```

puis ouvrir http://localhost:5173 (Vite redirige `/api` vers le port 8765).

### Déroulé d'une solve

1. Choisir la vidéo, cliquer sur « Nouvelle solve ».
2. Aller au début de la solve (inspection terminée, mains qui partent) et taper `i`. Marquer la fin
   avec `o` (le timer s'arrête). La durée de la fenêtre s'affiche pour comparer avec le timer.
3. Scramble : le choisir dans le menu « Export csTimer » (tout CSV csTimer posé dans
   `data/labels/` est lu, on reconnaît la solve à son temps), ou le coller, ou le laisser vide et
   cliquer sur « Déduire de la solution » une fois tous les mouvements saisis.
4. Saisir les mouvements : se placer sur l'image où le mouvement commence et taper sa lettre.
   Le cube montre l'état après le scramble et les mouvements déjà commencés à l'image courante.
5. Vérifier l'analyse (étapes, cas OLL/PLL, TPS, pauses), puis `⌘S`.

### Clavier

| Touche | Action |
|---|---|
| `←` `→` | 1 image (`Maj` : 10 images, `Alt` : 120 images, environ 1 s) |
| `Espace` | lecture / pause |
| `v` (`Maj+v`) | vitesse suivante (précédente) : ×1, ×0.5, ×0.25, ×0.1 |
| `i` / `o` | début / fin de la solve dans la vidéo |
| `u r f d l b` | mouvement de face à l'image courante (`Maj` : prime) |
| `m e s`, `x y z` | slices, rotations |
| `'` `2` `w` | prime, double, wide sur le mouvement sélectionné |
| `↑` `↓` | mouvement précédent / suivant (et la vidéo s'y place) |
| `Entrée` | recaler le mouvement sélectionné sur l'image courante (`Maj` : fixer sa fin) |
| `⌫` | supprimer le mouvement sélectionné |
| `⌘Z` / `⌘S` | annuler / enregistrer |

Double-clic sur un mouvement de la liste pour corriger sa notation. Les touches sont choisies
pour marcher en QWERTY comme en AZERTY.

### Conventions des labels

- Les temps (`t_start_ms`, `t_end_ms`, `solve_window`) sont en ms depuis le début de la vidéo, et
  calés sur le temps de présentation exact de l'image (image n à n × 1001 / 120 ms pour 119.88 fps).
- Un mouvement saisi au clavier a `t_end_ms = t_start_ms` (instant de début). `Maj+Entrée` permet
  de fixer une fin si besoin.
- `labeling_time_ms` : temps actif passé à labelliser la solve. Le chrono tourne quand l'onglet est
  visible, se met en pause seul après 60 s sans clavier ni souris, et peut être mis en pause à la
  main. C'est la métrique de référence de la phase 1.
- `scramble_source` : `cstimer`, `manual` (tapé) ou `derived` (inverse de la solution, sans
  rotations).

### Vidéos GoPro (HEVC 120 fps)

Les vidéos GoPro (HEVC Main 8 bits, `hvc1`, 1080p à 119.88 fps, une image clé par seconde) sont
lues directement par Chrome et Safari sur Mac (décodage matériel). Vérifié le 2026-11-18 dans
Chromium 156 : positionnement exact à l'image près, en avant comme en arrière, environ 70 à 170 ms
par déplacement. Aucune conversion n'est donc nécessaire.

Si un navigateur ne lit pas le HEVC (Firefox par exemple), créer une copie de travail H.264 à côté
de l'original. L'outil l'utilise automatiquement si elle s'appelle `<nom>.h264.mp4` :

```bash
ffmpeg -i data/videos/GX010395.MP4 -map 0:v:0 -c:v libx264 -preset veryfast -crf 18 -g 24 -pix_fmt yuv420p -fps_mode passthrough -movflags +faststart -an data/videos/GX010395.h264.mp4
```

`-fps_mode passthrough` garde chaque image avec son timestamp d'origine (même fps 120000/1001, même
départ à 0), donc les labels restent valables sur l'original. `-g 24` (une image clé toutes les
24 images) rend le retour en arrière plus rapide. Compter environ 0.6 × la durée de la vidéo sur
un M1 Pro.

### API

FastAPI dans `src/cuberecon/api/` (documentation interactive sur `/docs`) :

- `GET /api/videos` : vidéos de `data/videos/` avec fps réel, nombre d'images, durée, codec.
- `GET /api/media/{nom}` : fichier vidéo, avec requêtes Range.
- `GET /api/labels[?video=]`, `GET|PUT|DELETE /api/labels/{nom}`, `POST /api/labels` : labels
  `Solve` de `data/labels/` (analysés à l'enregistrement).
- `POST /api/analyze` : segmentation CFOP, cas OLL/PLL et stats d'un `Solve`, sans l'enregistrer.
- `POST /api/scramble/derive`, `POST /api/moves/validate` : scramble déduit, validation de notation.
- `GET /api/cstimer` : solves des exports csTimer présents dans `data/labels/`.
