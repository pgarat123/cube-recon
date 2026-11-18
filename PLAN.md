# cube-recon : plan du projet

Reconstruction assistée de solves 3x3 (CFOP) à partir d'une vidéo, sans smart cube, puis analyse de la solve (étapes, temps, pauses, rotations, regrips, à terme fingertricks).

Statut : cadrage validé le 2026-11-18. Phase 0 : repo initialisé, 3 vidéos et l'export csTimer (21 solves) dans `data/`. Phase 1 : moteur cube, analyse CFOP, format Solve et outil web de labellisation faits (2026-11-18), reste à labelliser 10 solves à la main.

---

## 1. Vision et périmètre

**Objectif produit (V1)** : l'utilisateur importe une vidéo de solve et le mélange. L'outil propose une reconstruction avec un score de confiance par mouvement et par étape. L'utilisateur corrige les passages douteux dans une interface (vidéo + cube 3D synchronisés), puis l'analyse est calculée.

**Dans le périmètre**
- Cube 3x3, méthode CFOP, solveur sub-12 (5 à 7 TPS moyen, pointes > 10 TPS).
- Mélange fourni en entrée (notation WCA).
- Vidéo filmée par l'utilisateur, cadrage fixe, slow-mo.
- Tout tourne en local sur un MacBook M1 Pro (pas de CUDA).

**Hors périmètre pour l'instant**
- Smart cube (ni en entrée, ni dans le produit).
- Vidéos de compétition quelconques (30 fps, angles variés) : phase 5.
- Autres puzzles, autres méthodes (Roux, ZZ).
- Application mobile : phase 5, en gardant les modèles exportables.
- Reconstruction 100 % automatique garantie : c'est l'horizon, pas l'objectif V1.

## 2. Principe technique

Système hybride :
- **Perception apprise (ML)** : localiser le cube, lire les couleurs, détecter qu'une couche tourne et laquelle. Sortie probabiliste.
- **Raisonnement exact (algorithmique)** : recherche sur les états légaux du cube qui combine le mélange, les lectures de couleurs, la structure CFOP, les algos de l'utilisateur et la contrainte "finit résolu". Elle garde plusieurs hypothèses et signale les endroits où elle a dû trancher : ce sont les zones à faire vérifier par l'humain.

Les corrections humaines deviennent des labels qui servent à réentraîner les modèles (boucle de données).

Référence étudiée : cubed-core (github.com/KingBobJoeIV/cubed-core, AGPL-3.0). Même philosophie (recherche d'états légaux + preuves visuelles). On s'inspire des idées, on ne copie pas le code (licence AGPL, dépendance CUDA, modèles overfit au setup de l'auteur).

## 3. Modèle de données central

Tout le système tourne autour d'un objet `Solve` sérialisé en JSON.

```
Solve
  id, created_at
  video: { path, fps, width, height, duration_ms }
  scramble: "R U2 F' ..."            # notation WCA
  color_scheme: { U: white, F: green, ... }
  calibration: { couleur -> échantillons Lab }   # optionnel
  moves: [
    { move: "R'", t_start_ms, t_end_ms, confidence: 0..1,
      source: manual | auto | corrected }
  ]
  segments: [                         # calculé
    { step: inspection | cross | f2l_1..f2l_4 | oll | pll | auf,
      t_start_ms, t_end_ms, move_range, case_id? }
  ]
  stats: { ... }                      # calculé
```

Notation supportée : faces (R U F L D B), wide (r / Rw ...), slices (M E S), rotations (x y z), modificateurs ' et 2.

## 4. Architecture du code

```
cube-recon/
  PLAN.md  CLAUDE.md  README.md
  pyproject.toml                  # uv, Python 3.11
  src/cuberecon/
    cube/        # état (54 facettes), application des mouvements, parseur, rotations
    analysis/    # segmentation CFOP, reconnaissance cas OLL/PLL, stats
    perception/  # détection cube, redressement des faces, lecture couleurs, mains
    motion/      # détection temporelle des mouvements (probabilités par frame)
    decode/      # recherche sur états légaux, scores de confiance
    io/          # lecture vidéo (PyAV), format Solve JSON
    api/         # FastAPI
  apps/web/      # React + TS + Vite + cubing.js
  tests/
  data/          # NON versionné : videos/, labels/, models/
```

## 5. Stack

| Rôle | Choix |
|---|---|
| Langage R&D | Python 3.11, gestion par `uv`, tests `pytest`, lint `ruff` |
| Vidéo | PyAV (décodage précis image par image), ffmpeg |
| Vision classique | OpenCV (homographie, espace Lab, flux optique) |
| Mains | MediaPipe Hands |
| ML | PyTorch avec backend MPS (GPU du M1), ultralytics YOLO pour détection/keypoints du cube |
| Annotation images | Label Studio ou CVAT en local |
| Backend | FastAPI |
| Front | React + TypeScript + Vite, cubing.js (`twisty-player` pour le cube 3D, parsing d'algos) |
| Stockage | Fichiers JSON + SQLite si besoin d'index |
| Mobile (plus tard) | Export ONNX / CoreML des modèles, logique cube réécrite côté app |

## 6. Protocole de capture

Setup de référence : celui que l'utilisateur utilise déjà à l'entraînement (vidéos GoPro du 2 mai 2026, dossier OneDrive « Rush cube/Training »).

- **Caméra** : GoPro en vue POV, au-dessus et derrière les épaules, plongeante vers le cube. Elle voit U et F comme le solveur, donc tout le last layer.
- **Format** : 1080p à 120 fps (HEVC), objectif grand angle. La distorsion est corrigée par calibration de l'objectif, elle est faible au centre où se trouve le cube.
- **Une vidéo = une session** de plusieurs solves. Le timer (type stackmat GAN) est visible à l'image : il sert à découper la vidéo en solves et à synchroniser début et fin.
- **Scrambles** : générés par csTimer, récupérés par l'export de session csTimer et associés aux solves grâce au temps affiché. À défaut, une solve labellisée donne son scramble par inversion de la solution.
- **Constance** : même position de caméra d'une session à l'autre, même cube.
- **À améliorer si possible** : plus de lumière (moins de flou de mouvement à 120 fps), sortir du champ les autres cubes (5x5, cube dessiné sur le tapis).
- **Option** : sessions dédiées en slow-mo 240 fps avec l'iPhone 18 Pro Max pour les solves les plus rapides, en exportant le fichier original (vérifier que le fps réel est conservé).
- **Objectif de départ** : 20 à 30 solves avec scramble identifié, plus quelques solves lentes pour valider la chaîne sur des cas faciles.

## 7. Feuille de route

Chaque phase a un livrable et un critère de fin mesurable. On ne passe pas à la suivante sans l'avoir atteint.

### Phase 0 : données et socle (surtout côté utilisateur)
- Filmer le dataset selon le protocole de la section 6.
- [x] Initialiser le repo (uv, pytest, ruff, structure).
- [x] Dataset initial existant : 3 vidéos GoPro du 2 mai 2026 (GX010395 à GX010397, 1080p 120 fps, plusieurs solves chacune).
- [x] Copier les vidéos dans `data/videos/` et exporter la session csTimer correspondante dans `data/labels/` (utilisateur). Export du 2 mai : 21 solves avec scramble.
- **Fini quand** : vidéos et export csTimer dans `data/`, au moins 20 solves avec scramble identifié, `uv run pytest` passe.

### Phase 1 : moteur cube, analyse, outil de labellisation
- [x] `cube/` : état 54 facettes, mouvements (faces, wide, slices, rotations), parseur, inverse, `strip_rotations`, test "mélange + solution = résolu".
- [x] `analysis/` : segmentation CFOP (croix sur n'importe quelle couleur, comptage des paires F2L, OLL, PLL, AUF), reconnaissance des 57 OLL et 21 PLL par l'état du cube (indépendante de l'AUF et de l'orientation, pré-AUF calculé), stats (TPS ETM/STM global et par étape, pauses, nombre de rotations, temps de reconnaissance).
- [x] `io/` : format `Solve` JSON (section 3), avec validation et `schema_version`. v2 : `solve_window` (bornes de la solve dans la vidéo), `scramble_source`, `labeling_time_ms`. Lecture des exports csTimer (CSV).
- [ ] `analysis/` : extraction automatique des algos LL de l'utilisateur à partir des solves labellisées (attend les premières solves labellisées).
- [x] Outil web de labellisation (`uv run cuberecon-label`, voir README) : API FastAPI (`api/`) et front React + cubing.js (`apps/web/`). Lecteur image par image au clavier, bornes de la solve, scramble csTimer / tapé / déduit, saisie des mouvements horodatés, cube 3D synchronisé, analyse en direct, chrono de labellisation, export `Solve` JSON. HEVC GoPro lu nativement par Chrome/Safari, copie H.264 optionnelle documentée.
- [ ] Valider la segmentation sur de vraies solves de l'utilisateur (les tests actuels utilisent des solves CFOP construites, faute de reconstruction publique accessible).
- [ ] Labelliser 10 solves à la main avec l'outil (utilisateur).
- **Fini quand** : 10 solves labellisées à la main, analysées correctement ; temps moyen de labellisation manuelle d'une solve mesuré (c'est la référence que l'outil assisté devra battre).

### Phase 2 : perception
- Découpage d'une vidéo de session en solves grâce au timer visible, et association avec les scrambles de l'export csTimer.
- Correction de la distorsion grand angle de la GoPro.
- Détection/suivi du cube (YOLO fine-tuné sur quelques centaines d'images annotées), en ignorant les autres cubes du décor.
- Redressement des faces visibles et lecture des couleurs sur les frames stables, avec calibration.
- MediaPipe Hands : masques d'occlusion et trajectoires des doigts.
- **Fini quand** : précision de lecture des facettes visibles et non masquées > 98 % sur frames stables du jeu de test.

### Phase 3 : reconstruction assistée
- `motion/` : modèle temporel qui donne, par fenêtre de frames, la probabilité de chaque mouvement.
- `decode/` : recherche (beam search / trellis) sur états légaux avec priors : mélange, lectures couleurs, structure CFOP, algos de l'utilisateur, fin résolue.
- Ordre d'attaque : last layer d'abord (classification parmi les algos connus), puis F2L, puis croix (invisible, déduite).
- Interface de correction : zones de faible confiance mises en avant, correction en quelques clics.
- **Fini quand** : sur le jeu de test, la reconstruction proposée rejoue vers résolu après correction, et le temps de correction est nettement inférieur au temps de labellisation manuelle mesuré en phase 1.

### Phase 4 : analyses avancées
- Pauses et lookahead (temps entre fin d'une paire et début de la suivante), temps de reconnaissance OLL/PLL.
- Regrips et rotations détectés par les mains.
- Comparaison entre solves, tendances dans le temps.

### Phase 5 : généralisation (optionnel)
- Autres angles, autres cubes, vidéos 60/30 fps, vidéos de compétition.
- Fingertricks (quel doigt fait quel mouvement).
- Application mobile.

## 8. Métriques

| Brique | Métrique |
|---|---|
| Détection cube | IoU / mAP sur jeu de test |
| Couleurs | précision par facette visible sur frames stables |
| Mouvements | distance d'édition entre séquence proposée et séquence labellisée, précision par étape CFOP |
| Timing | erreur moyenne (ms) sur les bornes de mouvements et d'étapes |
| Produit | % de solves qui rejouent vers résolu ; temps de correction humaine par solve |

Le jeu de test est figé dès la phase 1 (quelques solves jamais utilisées pour entraîner).

## 9. Risques identifiés

- **Occlusion par les mains** et flou de mouvement : compensés par la recherche sur états légaux et le slow-mo.
- **Croix invisible** (faite sur la face D) : déduite, jamais lue.
- **Confusions de couleurs** (rouge/orange, blanc/jaune selon la lumière) : calibration par vidéo, espace Lab.
- **F2L intuitif** : pas de prior d'algos, c'est la partie la plus dure.
- **Volume de labels** : fatigue de labellisation. Mitigation : outil rapide en phase 1, boucle de correction en phase 3.
- **Cube petit dans l'image** (environ 175 px de large en 1080p, 50 px par facette) : suffisant pour les couleurs, juste pour les mouvements rapides. Mitigation : recadrage autour du cube suivi, sessions 240 fps en option.
- **Faux positifs** : autres cubes dans le décor (5x5, illustration du tapis). Mitigation : suivi temporel du cube actif, exemples négatifs à l'annotation.
- **Overfit au setup** : assumé pour la V1, traité en phase 5.
- **Budget Claude (forfait Pro)** : voir CLAUDE.md.

## 10. Questions ouvertes

- [x] Téléphone : iPhone 18 Pro Max, slow-mo 240 fps en 1080p disponible.
- [x] Algos : pas de liste fournie. Les algos de l'utilisateur seront extraits automatiquement des solves labellisées en phase 1 (chaque LL labellisé donne l'algo réellement utilisé pour ce cas). En attendant, la reconnaissance des cas OLL/PLL se fait par l'état du cube, pas par l'algo.
- [x] Cube : stickerless, schéma de couleurs standard (blanc en haut, vert devant).
- [x] Nom du projet : cube-recon.
- [ ] Logo sur un centre (souvent le blanc) : à vérifier sur les premières vidéos, à ignorer lors de la lecture des couleurs si présent.
