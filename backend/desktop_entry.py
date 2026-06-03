"""桌面端入口：内置 HTTP 服务 + 可选队列 Worker 子进程（PyInstaller 打包为 ScreenRPA.exe）。"""

from __future__ import annotations

import atexit
import os
import subprocess
import sys
import threading
import time
import webbrowser
from copy import deepcopy
from pathlib import Path

_worker: subprocess.Popen | None = None
_fallback_streams: list[object] = []


def _bootstrap_env() -> None:
    """在导入 app 之前执行，使 SCREEN_RPA_STATIC_DIST 等环境变量生效。"""
    if getattr(sys, "frozen", False):
        return
    repo = Path(__file__).resolve().parent.parent
    dist = repo / "frontend" / "dist"
    if dist.is_dir():
        os.environ.setdefault("SCREEN_RPA_STATIC_DIST", str(dist))


_bootstrap_env()


def _stop_worker() -> None:
    global _worker
    if _worker is None or _worker.poll() is not None:
        return
    _worker.terminate()
    try:
        _worker.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _worker.kill()


def _start_worker_subprocess() -> None:
    global _worker
    if "--no-worker" in sys.argv:
        return
    flags = 0
    if sys.platform == "win32":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = [sys.executable, "--worker"]
    _worker = subprocess.Popen(cmd, creationflags=flags)
    atexit.register(_stop_worker)


def _open_ui(url: str) -> None:
    time.sleep(1.0)
    webbrowser.open(url)


def _run_worker() -> None:
    from app.worker.consumer import run_forever

    run_forever()


def _run_server() -> None:
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    # Windowed (no-console) mode may leave stdio as None.
    # Uvicorn's default formatter calls stream.isatty(), which then crashes.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
        _fallback_streams.append(sys.stdout)
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
        _fallback_streams.append(sys.stderr)

    log_config = deepcopy(LOGGING_CONFIG)
    if "formatters" in log_config:
        for name in ("default", "access"):
            formatter = log_config["formatters"].get(name)
            if isinstance(formatter, dict):
                formatter["use_colors"] = False

    _start_worker_subprocess()
    port = int(os.environ.get("SCREEN_RPA_PORT", "8765"))
    host = os.environ.get("SCREEN_RPA_HOST", "127.0.0.1")
    url = f"http://{host}:{port}/"
    threading.Thread(target=_open_ui, args=(url,), daemon=True).start()
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        factory=False,
        log_level=os.environ.get("SCREEN_RPA_LOG_LEVEL", "info"),
        log_config=log_config,
    )


def main() -> None:
    if "--worker" in sys.argv:
        _run_worker()
        return
    _run_server()


if __name__ == "__main__":
    main()
