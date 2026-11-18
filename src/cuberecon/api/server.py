"""``cuberecon-label``: run the labeling tool (API + built web front) locally."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

import uvicorn

from .app import create_app, default_data_dir, default_web_dist


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="cube-recon labeling tool")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=None, help="default: <repo>/data")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    args = parser.parse_args(argv)

    data_dir = args.data_dir or default_data_dir()
    if not (default_web_dist() / "index.html").is_file():
        print("Front not built: run `npm --prefix apps/web ci && npm --prefix apps/web run build`")
        print("(or use the Vite dev server, see README). The API still starts.")
    url = f"http://{args.host}:{args.port}/"
    print(f"cube-recon labeling tool on {url} (data: {data_dir})")
    if not args.no_browser:
        webbrowser.open(url)
    uvicorn.run(create_app(data_dir), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
