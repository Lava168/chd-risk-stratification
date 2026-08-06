"""Desktop launcher: native window + bundled local FastAPI backend.

Builds into a standalone macOS app with PyInstaller (see chd_risk_desktop.spec).
Run `python desktop.py` to launch in a pywebview window; `--no-window` starts
only the HTTP server (used for headless verification).
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
from pathlib import Path


def _bundle_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _setup_paths() -> Path:
    base = _bundle_base()
    # Model bundle: prefer bundled copy.
    bundled_model = base / "models" / "trained_model_bundle.joblib"
    if bundled_model.exists():
        os.environ["CHD_RISK_MODEL_PATH"] = str(bundled_model)
    else:
        os.environ.setdefault(
            "CHD_RISK_MODEL_PATH", str(Path(__file__).resolve().parent / "models" / "trained_model_bundle.joblib")
        )
    # macOS: expose libomp so xgboost can load its OpenMP runtime.
    libomp_dir = base / "libomp"
    if not libomp_dir.exists():
        # Dev fallback: libomp lives in the local venv.
        venv_libomp = Path(__file__).resolve().parent / ".venv" / "lib" / "libomp"
        if venv_libomp.exists():
            libomp_dir = venv_libomp
    if libomp_dir.exists():
        fallback_paths = os.environ.get(
            "DYLD_FALLBACK_LIBRARY_PATH", "/usr/local/lib:/usr/lib"
        )
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{libomp_dir}:{fallback_paths}"
    return base


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(app, port: int):
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    return server, thread


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CHD Risk Stratification desktop app")
    parser.add_argument("--no-window", action="store_true", help="Start server only (headless test)")
    parser.add_argument("--port", type=int, default=0, help="Port; 0 = pick a free port")
    args = parser.parse_args(argv)

    _setup_paths()
    from chd_risk.api import app

    port = args.port or _free_port()
    server, _thread = _start_server(app, port)
    url = f"http://127.0.0.1:{port}/ui/"
    print(f"[chd-risk] server ready at {url}")

    if args.no_window:
        print("[chd-risk] headless mode: press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.should_exit = True
        return 0

    import webview

    window = webview.create_window(
        "冠心病风险分层管理平台",
        url,
        width=1280,
        height=820,
        min_size=(1024, 700),
    )
    window.events.closed += lambda: setattr(server, "should_exit", True)
    webview.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
