# cube-recon : plan du projet

Reconstruction assistée de solves 3x3 (CFOP) à partir d'une vidéo, sans smart cube, puis analyse de la solve (étapes, temps, pauses, rotations, regrips, à terme fingertricks).

Statut : cadrage validé le 2026-11-18. Phase 0 : repo initialisé (uv, pytest, ruff), dataset vidéo à filmer.

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

## 6. Protocole de capture (à respecter pour le dataset initial)

- Téléphone sur trépied, vue de face légèrement au-dessus, cube entier dans le cadre pendant toute la solve.
- iPhone 18 Pro Max en slow-mo 240 fps, 1080p. Exporter le fichier original, pas la version ralentie "lue" : vérifier que le fps réel est conservé.
- Lumière diffuse, fond uni, même cube à chaque fois.
- Quelques secondes de cube immobile avant l'inspection (calibration couleurs).
- Mélange généré par csTimer et noté avec l'horodatage de la vidéo.
- Objectif de départ : 20 à 30 solves normales + 5 solves lentes (pour valider la chaîne sur cas faciles).

## 7. Feuille de route

Chaque phase a un livrable et un critère de fin mesurable. On ne passe pas à la suivante sans l'avoir atteint.

### Phase 0 : données et socle (surtout côté utilisateur)
- Filmer le dataset selon le protocole de la section 6.
- [x] Initialiser le repo (uv, pytest, ruff, structure).
- [ ] Filmer le dataset (utilisateur).
- **Fini quand** : 20 vidéos + mélanges dans `data/`, `uv run pytest` passe sur un repo vide.

### Phase 1 : moteur cube, analyse, outil de labellisation
- `cube/` : état, mouvements (y compris wide, slices, rotations), parseur, inverse, test "mélange + solution = résolu".
- `analysis/` : segmentation CFOP (croix sur n'importe quelle couleur, comptage des paires F2L, OLL, PLL, AUF), reconnaissance des cas OLL/PLL avec AUF (par l'état du cube), extraction automatique des algos LL de l'utilisateur à partir des solves labellisées, stats (TPS global et par étape, pauses, nombre de rotations, temps de reconnaissance).
- Outil web de labellisation : lecteur vidéo image par image au clavier, saisie des mouvements avec timestamps, cube 3D synchronisé, export `Solve` JSON.
- **Fini quand** : 10 solves labellisées à la main, analysées correctement ; temps moyen de labellisation manuelle d'une solve mesuré (c'est la référence que l'outil assisté devra battre).

### Phase 2 : perception
- Détection/suivi du cube (YOLO fine-tuné sur quelques centaines d'images annotées).
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
- **Overfit au setup** : assumé pour la V1, traité en phase 5.
- **Budget Claude (forfait Pro)** : voir CLAUDE.md.

## 10. Questions ouvertes

- [x] Téléphone : iPhone 18 Pro Max, slow-mo 240 fps en 1080p disponible.
- [x] Algos : pas de liste fournie. Les algos de l'utilisateur seront extraits automatiquement des solves labellisées en phase 1 (chaque LL labellisé donne l'algo réellement utilisé pour ce cas). En attendant, la reconnaissance des cas OLL/PLL se fait par l'état du cube, pas par l'algo.
- [x] Cube : stickerless, schéma de couleurs standard (blanc en haut, vert devant).
- [x] Nom du projet : cube-recon.
- [ ] Logo sur un centre (souvent le blanc) : à vérifier sur les premières vidéos, à ignorer lors de la lecture des couleurs si présent.
