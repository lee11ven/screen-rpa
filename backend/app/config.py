from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def meipass_dir() -> Path | None:
    raw = getattr(sys, "_MEIPASS", None)
    return Path(raw) if raw else None


def _repo_root() -> Path:
    """开发态为仓库根目录；PyInstaller 打包后为 exe 所在目录（用于 data 等可写文件）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return BACKEND_ROOT.parent


REPO_ROOT = _repo_root()


def _default_db_path() -> Path:
    p = REPO_ROOT / "data" / "rpa.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", str(_default_db_path()))).resolve()


def _default_schema_path() -> Path:
    me = meipass_dir()
    if me is not None:
        bundled = me / "contracts" / "workflow-runtime.schema.json"
        if bundled.is_file():
            return bundled.resolve()
    return (REPO_ROOT / "contracts" / "workflow-runtime.schema.json").resolve()


SCHEMA_PATH = Path(
    os.environ.get("WORKFLOW_RUNTIME_SCHEMA_PATH", str(_default_schema_path())),
).resolve()


def static_dist_dir() -> Path | None:
    """存在时由 FastAPI 挂载前端构建产物（桌面 / 一体化部署）。"""
    raw = os.environ.get("SCREEN_RPA_STATIC_DIST", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_dir() else None
    external_dist = REPO_ROOT / "dist"
    if external_dist.is_dir():
        return external_dist
    me = meipass_dir()
    if me is not None:
        bundled = me / "frontend_dist"
        if bundled.is_dir():
            return bundled
    return None


SCREEN_RPA_STATIC_DIST = static_dist_dir()

PROTOCOL_VERSION = 1

WORKER_ID = os.environ.get("WORKER_ID", "worker-1")
QUEUE_LEASE_SEC = int(os.environ.get("QUEUE_LEASE_SEC", "60"))
QUEUE_MAX_RETRY = int(os.environ.get("QUEUE_MAX_RETRY", "3"))
QUEUE_RETRY_BACKOFF_SEC = int(os.environ.get("QUEUE_RETRY_BACKOFF_SEC", "5"))
RECOVERY_SCAN_INTERVAL_SEC = int(os.environ.get("RECOVERY_SCAN_INTERVAL_SEC", "15"))
