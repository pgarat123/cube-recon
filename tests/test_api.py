import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from cuberecon.api import create_app
from cuberecon.cube import Cube
from cuberecon.io import Solve, TimedMove, VideoInfo

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")

SCRAMBLE = "R U R' U'"


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "videos").mkdir()
    (tmp_path / "labels").mkdir()
    return tmp_path


@pytest.fixture
def client(data_dir, tmp_path_factory):
    no_web = tmp_path_factory.mktemp("no_web")
    return TestClient(create_app(data_dir, web_dist=no_web))


def make_video(path, frames=24, rate="120000/1001"):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size=64x48:rate={rate}",
            "-frames:v",
            str(frames),
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            str(path),
        ],
        check=True,
    )


def solve_dict(**kwargs) -> dict:
    solve = Solve(
        scramble=SCRAMBLE,
        moves=[
            TimedMove("U", 1000.0, 1000.0),
            TimedMove("R", 1100.0, 1100.0),
            TimedMove("U'", 1500.0, 1500.0),
            TimedMove("R'", 1600.0, 1600.0),
        ],
        video=VideoInfo("videos/GX0001.MP4", 119.88, 1920, 1080, 60000.0),
        **kwargs,
    )
    return solve.to_dict()


@needs_ffmpeg
def test_list_videos_with_metadata(client, data_dir):
    make_video(data_dir / "GX0001.MP4")
    make_video(data_dir / "videos" / "GX0001.MP4")
    make_video(data_dir / "videos" / "GX0001.h264.mp4")
    (data_dir / "videos" / "notes.txt").write_text("not a video")
    videos = client.get("/api/videos").json()
    assert [v["name"] for v in videos] == ["GX0001.MP4"]
    v = videos[0]
    assert (v["fps_num"], v["fps_den"]) == (120000, 1001)
    assert v["fps"] == pytest.approx(119.88, abs=1e-3)
    assert v["frame_count"] == 24
    assert v["duration_ms"] == pytest.approx(24 * 1001 / 120, abs=1.0)
    assert (v["width"], v["height"], v["codec"]) == (64, 48, "h264")
    assert v["work_copy"] == "GX0001.h264.mp4"
    assert client.get("/api/videos/GX0001.MP4").json()["frame_count"] == 24


@needs_ffmpeg
def test_media_supports_range_requests(client, data_dir):
    path = data_dir / "videos" / "clip.mp4"
    make_video(path)
    full = client.get("/api/media/clip.mp4")
    assert full.status_code == 200
    assert full.headers["accept-ranges"] == "bytes"
    assert full.content == path.read_bytes()
    part = client.get("/api/media/clip.mp4", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206
    assert part.headers["content-range"] == f"bytes 100-199/{path.stat().st_size}"
    assert part.content == path.read_bytes()[100:200]


def test_unknown_video_and_traversal_rejected(client, data_dir):
    (data_dir / "secret.mp4").write_bytes(b"x")
    assert client.get("/api/media/nope.mp4").status_code == 404
    assert client.get("/api/media/..%2Fsecret.mp4").status_code == 404
    assert client.get("/api/videos/nope.mp4").status_code == 404


def test_create_load_update_delete_label(client, data_dir):
    assert client.get("/api/labels").json() == []
    data = solve_dict(labeling_time_ms=42000.0)
    created = client.post("/api/labels", json=data)
    assert created.status_code == 201
    name = created.json()["name"]
    assert name == "GX0001_01"
    assert client.post("/api/labels", json=data).json()["name"] == "GX0001_02"

    on_disk = Solve.load(data_dir / "labels" / f"{name}.json")
    assert on_disk.labeling_time_ms == 42000.0
    assert on_disk.segments and on_disk.stats["total_time_ms"] == 600.0

    loaded = client.get(f"/api/labels/{name}").json()
    assert loaded["name"] == name and loaded["solve"]["id"] == data["id"]

    data["moves"] = data["moves"][:2]
    updated = client.put(f"/api/labels/{name}", json=data).json()
    assert len(updated["solve"]["moves"]) == 2
    assert len(Solve.load(data_dir / "labels" / f"{name}.json").moves) == 2

    summaries = client.get("/api/labels", params={"video": "GX0001.MP4"}).json()
    assert [s["name"] for s in summaries] == ["GX0001_01", "GX0001_02"]
    assert summaries[1]["complete"] is True and summaries[1]["move_count"] == 4
    assert client.get("/api/labels", params={"video": "other.MP4"}).json() == []

    assert client.delete(f"/api/labels/{name}").status_code == 204
    assert client.get(f"/api/labels/{name}").status_code == 404


def test_label_listing_skips_foreign_json(client, data_dir):
    (data_dir / "labels" / "cstimer_export.json").write_text('{"session1": []}')
    client.post("/api/labels", json=solve_dict())
    assert [s["name"] for s in client.get("/api/labels").json()] == ["GX0001_01"]


@pytest.mark.parametrize("name", ["../evil", ".hidden", "a b", "x.json"])
def test_bad_label_names_rejected(client, name):
    assert client.put(f"/api/labels/{name}", json=solve_dict()).status_code in (400, 404)


def test_invalid_solve_rejected(client):
    data = solve_dict()
    data["moves"][0]["move"] = "Q"
    assert client.post("/api/analyze", json=data).status_code == 422
    assert client.put("/api/labels/x", json={"scramble": "R"}).status_code == 422


def test_analyze_returns_segments_cases_and_stats(client):
    out = client.post("/api/analyze", json=solve_dict()).json()
    steps = [s["step"] for s in out["segments"]]
    assert steps[0] == "inspection" and steps[-1] == "auf"
    assert out["stats"]["complete"] is True
    assert out["stats"]["moves_stm"] == 4
    assert out["stats"]["pauses"] == [{"after_move": 1, "duration_ms": 400.0}]
    assert {"oll", "pll"} <= set(out["stats"]["steps"])


def test_analyze_partial_and_empty_solves(client):
    data = solve_dict()
    data["moves"] = []
    assert client.post("/api/analyze", json=data).json()["stats"]["complete"] is False
    data["scramble"] = ""
    assert client.post("/api/analyze", json=data).status_code == 200


def test_derive_scramble(client):
    solution = ["y", "R", "U", "R'", "x", "U2", "F", "Rw'"]
    scramble = client.post("/api/scramble/derive", json={"moves": solution}).json()["scramble"]
    assert not any(c in scramble for c in "xyz")
    assert Cube().apply(scramble).apply(" ".join(solution)).is_solved()
    assert client.post("/api/scramble/derive", json={"moves": ["Q"]}).status_code == 422
    assert client.post("/api/scramble/derive", json={"moves": "R U"}).status_code == 422


def test_validate_moves(client):
    ok = client.post("/api/moves/validate", json={"moves": "R  U2’ F'"}).json()
    assert ok == {"ok": True, "normalized": "R U2 F'", "error": None}
    bad = client.post("/api/moves/validate", json={"moves": "R Q"}).json()
    assert bad["ok"] is False and bad["error"]


def test_serves_built_front(data_dir, tmp_path_factory):
    dist = tmp_path_factory.mktemp("dist")
    (dist / "index.html").write_text("<!doctype html><title>cube-recon</title>")
    client = TestClient(create_app(data_dir, web_dist=dist))
    assert "cube-recon" in client.get("/").text
    assert client.get("/api/health").json()["ok"] is True


def test_cstimer_scrambles(client, data_dir):
    assert client.get("/api/cstimer").json() == []
    (data_dir / "labels" / "csTimerExport_1.csv").write_text(
        "No.;Time;Comment;Scramble;Date;P.1\n6;13.52;;R U F;02/05/2026 17:41;13.52\n"
    )
    (data_dir / "labels" / "other.csv").write_text("a;b\n1;2\n")
    rows = client.get("/api/cstimer").json()
    assert len(rows) == 1
    assert rows[0]["file"] == "csTimerExport_1.csv"
    assert (rows[0]["no"], rows[0]["scramble"], rows[0]["time_ms"]) == (6, "R U F", 13520.0)
