"""FastAPI app of the labeling tool: videos, Solve labels and analysis.

Cube logic stays in ``cuberecon.cube`` / ``cuberecon.analysis``: the web front only
sends move tokens and displays what this API returns.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cuberecon.analysis import analyze
from cuberecon.cube import NotationError, format_moves, invert, parse_moves, strip_rotations
from cuberecon.io import Solve, SolveFormatError, is_cstimer_export, parse_cstimer_csv

from .media import MediaError, is_work_copy, list_videos, probe, work_copy_name

REPO_ROOT = Path(__file__).resolve().parents[3]
LABEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
JsonBody = Annotated[dict[str, Any], Body()]
MEDIA_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime"}


def default_data_dir() -> Path:
    return Path(os.environ.get("CUBERECON_DATA_DIR", REPO_ROOT / "data"))


def default_web_dist() -> Path:
    return REPO_ROOT / "apps" / "web" / "dist"


def _parse_solve(data: dict[str, Any]) -> Solve:
    try:
        return Solve.from_dict(data)
    except (SolveFormatError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _check_label_name(name: str) -> str:
    if not LABEL_NAME_RE.match(name) or name.endswith(".json"):
        raise HTTPException(status_code=400, detail=f"invalid label name {name!r}")
    return name


def _summary(name: str, solve: Solve) -> dict[str, Any]:
    return {
        "name": name,
        "id": solve.id,
        "video": None if solve.video is None else solve.video.path,
        "solve_window": None if solve.solve_window is None else vars(solve.solve_window),
        "scramble": solve.scramble,
        "move_count": len(solve.moves),
        "complete": bool(solve.stats.get("complete", False)),
        "total_time_ms": solve.stats.get("total_time_ms"),
        "labeling_time_ms": solve.labeling_time_ms,
    }


def create_app(data_dir: Path | None = None, web_dist: Path | None = None) -> FastAPI:
    data_dir = Path(data_dir) if data_dir is not None else default_data_dir()
    videos_dir = data_dir / "videos"
    labels_dir = data_dir / "labels"
    app = FastAPI(title="cube-recon labeling tool")

    def video_path(name: str) -> Path:
        path = videos_dir / name
        if path not in list_videos(videos_dir):
            raise HTTPException(status_code=404, detail=f"unknown video {name!r}")
        return path

    def label_path(name: str) -> Path:
        return labels_dir / f"{_check_label_name(name)}.json"

    def load_label(path: Path) -> Solve:
        try:
            return Solve.load(path)
        except (SolveFormatError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=f"{path.name}: {exc}") from exc

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "data_dir": str(data_dir)}

    @app.get("/api/videos")
    def videos() -> list[dict[str, Any]]:
        files = list_videos(videos_dir)
        names = {p.name for p in files}
        out = []
        for path in files:
            if is_work_copy(path):
                continue
            try:
                meta = probe(path).to_dict()
            except MediaError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            work = work_copy_name(path.name)
            meta["work_copy"] = work if work in names else None
            out.append(meta)
        return out

    @app.get("/api/videos/{name}")
    def video_meta(name: str) -> dict[str, Any]:
        try:
            return probe(video_path(name)).to_dict()
        except MediaError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/media/{name}")
    def media(name: str) -> FileResponse:
        """Raw video file. Starlette's FileResponse answers Range requests (206)."""
        path = video_path(name)
        return FileResponse(path, media_type=MEDIA_TYPES.get(path.suffix.lower(), "video/mp4"))

    @app.get("/api/labels")
    def labels(video: str | None = None) -> list[dict[str, Any]]:
        if not labels_dir.is_dir():
            return []
        out = []
        for path in sorted(labels_dir.glob("*.json")):
            try:
                solve = Solve.load(path)
            except (SolveFormatError, ValueError):
                continue  # not a Solve (e.g. a csTimer export)
            if video is not None and (solve.video is None or Path(solve.video.path).name != video):
                continue
            out.append(_summary(path.stem, solve))
        return out

    @app.get("/api/labels/{name}")
    def get_label(name: str) -> dict[str, Any]:
        path = label_path(name)
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"no label {name!r}")
        return {"name": name, "solve": load_label(path).to_dict()}

    @app.post("/api/labels", status_code=201)
    def create_label(data: JsonBody) -> dict[str, Any]:
        """Save a new label, named ``<video stem>_<nn>``."""
        solve = analyze(_parse_solve(data))
        stem = Path(solve.video.path).stem if solve.video else "solve"
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", stem)
        labels_dir.mkdir(parents=True, exist_ok=True)
        n = 1
        while (labels_dir / f"{stem}_{n:02d}.json").exists():
            n += 1
        name = f"{stem}_{n:02d}"
        solve.save(labels_dir / f"{name}.json")
        return {"name": name, "solve": solve.to_dict()}

    @app.put("/api/labels/{name}")
    def put_label(name: str, data: JsonBody) -> dict[str, Any]:
        path = label_path(name)
        solve = analyze(_parse_solve(data))
        labels_dir.mkdir(parents=True, exist_ok=True)
        solve.save(path)
        return {"name": name, "solve": solve.to_dict()}

    @app.delete("/api/labels/{name}", status_code=204)
    def delete_label(name: str) -> None:
        path = label_path(name)
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"no label {name!r}")
        path.unlink()

    @app.get("/api/cstimer")
    def cstimer() -> list[dict[str, Any]]:
        """Solves of every csTimer CSV export found in ``data/labels/`` (scramble picker)."""
        out = []
        for path in sorted(labels_dir.glob("*.csv")) if labels_dir.is_dir() else []:
            text = path.read_text(encoding="utf-8", errors="replace")
            if not is_cstimer_export(text):
                continue
            for s in parse_cstimer_csv(text):
                out.append({"file": path.name, **vars(s)})
        return out

    @app.post("/api/analyze")
    def analyze_solve(data: JsonBody) -> dict[str, Any]:
        """Segments (CFOP steps, OLL/PLL cases) and stats of a Solve, without saving it."""
        return analyze(_parse_solve(data)).to_dict()

    @app.post("/api/scramble/derive")
    def derive_scramble(data: JsonBody) -> dict[str, str]:
        """Scramble that the labeled moves solve: inverse of the moves, rotations removed."""
        moves = data.get("moves")
        if not isinstance(moves, list) or not all(isinstance(m, str) for m in moves):
            raise HTTPException(status_code=422, detail="'moves' must be a list of move strings")
        try:
            solution = parse_moves(" ".join(moves))
        except NotationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"scramble": format_moves(invert(strip_rotations(solution)))}

    @app.post("/api/moves/validate")
    def validate_moves(data: JsonBody) -> dict[str, Any]:
        """Check a move sequence (e.g. a typed scramble). Returns the normalized form."""
        text = data.get("moves", "")
        if not isinstance(text, str):
            raise HTTPException(status_code=422, detail="'moves' must be a string")
        try:
            return {"ok": True, "normalized": format_moves(parse_moves(text)), "error": None}
        except NotationError as exc:
            return {"ok": False, "normalized": None, "error": str(exc)}

    dist = web_dist if web_dist is not None else default_web_dist()
    if (dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app
