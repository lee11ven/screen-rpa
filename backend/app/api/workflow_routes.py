from __future__ import annotations

import json
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import PROTOCOL_VERSION
from app.db.database import db
from orchestration_engine import LowcodeCompileError, LowcodeProtocolError, LowcodeRuntimeError, LowcodeTimeoutError
from app.services import global_object_config_service, system_config_service, workflow_definition_service, workflow_validate_service
from app.services import workflow_run_service

router = APIRouter(prefix="/workflow", tags=["workflow"])


class ApiResponse(BaseModel):
    success: bool = True
    code: int = 0
    message: str = "ok"
    data: Any = None


class CreateBody(BaseModel):
    name: str
    global_object_config_id: int
    workflow_id: str | None = None
    draft_runtime: dict[str, Any] | None = None


class UpdateBody(BaseModel):
    workflow_id: str
    name: str | None = None
    global_object_config_id: int | None = None
    draft_runtime: dict[str, Any] | None = None
    status: str | None = None


class ValidateBody(BaseModel):
    runtime: dict[str, Any]


class RunBody(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    version: int | None = None
    idempotency_key: str | None = None


class GlobalObjectConfigCreateBody(BaseModel):
    name: str
    config: dict[str, Any]


class GlobalObjectConfigUpdateBody(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None


class SystemConfigUpdateBody(BaseModel):
    sub_image_dir: str | None = None
    fullscreen_screenshot_dir: str | None = None


class SelectDirectoryBody(BaseModel):
    initial_dir: str | None = None


class UploadSubImageTemplateResult(BaseModel):
    filename: str
    saved_path: str


_PATH_CONTROL_CHARS = dict.fromkeys(map(ord, "\u202a\u202b\u202c\u202d\u202e\ufeff"), None)


def _sanitize_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text.translate(_PATH_CONTROL_CHARS).strip().strip('"').strip("'")


def _to_abs_path(value: str) -> str:
    raw = _sanitize_path(value)
    if not raw:
        return ""
    return str(Path(raw).expanduser().resolve(strict=False))


def _ok(data: Any = None) -> ApiResponse:
    return ApiResponse(data=data)


def _json_safe(value: Any, *, _seen: set[int] | None = None) -> Any:
    if _seen is None:
        _seen = set()
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    oid = id(value)
    if oid in _seen:
        return "<circular_ref>"
    if isinstance(value, dict):
        _seen.add(oid)
        out: dict[str, Any] = {}
        for k, v in value.items():
            out[str(k)] = _json_safe(v, _seen=_seen)
        _seen.remove(oid)
        return out
    if isinstance(value, (list, tuple, set)):
        _seen.add(oid)
        out = [_json_safe(v, _seen=_seen) for v in value]
        _seen.remove(oid)
        return out
    return str(value)


def _fail(code: int, message: str, http: int = 400) -> None:
    raise HTTPException(status_code=http, detail={"success": False, "code": code, "message": message, "data": None})


def _terminate_backend_async(delay_seconds: float = 0.2) -> None:
    """异步终止当前后端进程及其子进程，确保先返回 HTTP 响应。"""

    def _terminate() -> None:
        time.sleep(delay_seconds)
        try:
            current = psutil.Process(os.getpid())
            children = current.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
            _, alive = psutil.wait_procs(children, timeout=2)
            for child in alive:
                try:
                    child.kill()
                except Exception:
                    pass
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=_terminate, daemon=True).start()


@router.get("/meta/protocol", response_model=ApiResponse)
def protocol_meta() -> ApiResponse:
    return _ok({"protocol_version": PROTOCOL_VERSION})


@router.post("/create", response_model=ApiResponse)
def workflow_create(body: CreateBody) -> ApiResponse:
    with db:
        try:
            wf = workflow_definition_service.create_workflow(
                name=body.name,
                global_object_config_id=body.global_object_config_id,
                workflow_id=body.workflow_id,
                draft_runtime=body.draft_runtime,
            )
        except ValueError as e:
            _fail(4004, str(e))
        return _ok({"workflow_id": wf.workflow_id, "name": wf.name})


@router.post("/update", response_model=ApiResponse)
def workflow_update(body: UpdateBody) -> ApiResponse:
    with db:
        try:
            wf = workflow_definition_service.update_workflow(
                body.workflow_id,
                name=body.name,
                global_object_config_id=body.global_object_config_id,
                draft_runtime=body.draft_runtime,
                status=body.status,
            )
        except ValueError as e:
            _fail(4004, str(e))
        return _ok({"workflow_id": wf.workflow_id, "updated": True})


@router.get("/list", response_model=ApiResponse)
def workflow_list(status: str | None = None, q: str | None = None) -> ApiResponse:
    with db:
        rows = workflow_definition_service.list_workflows(status=status, q=q)
        return _ok({"items": rows})


@router.get("/system-config", response_model=ApiResponse)
def system_config_get() -> ApiResponse:
    with db:
        return _ok(system_config_service.get_system_config())


@router.post("/system-config/update", response_model=ApiResponse)
def system_config_update(body: SystemConfigUpdateBody) -> ApiResponse:
    with db:
        data = system_config_service.update_system_config(
            sub_image_dir=body.sub_image_dir,
            fullscreen_screenshot_dir=body.fullscreen_screenshot_dir,
        )
        return _ok(data)


@router.post("/system/select-directory", response_model=ApiResponse)
def system_select_directory(body: SelectDirectoryBody) -> ApiResponse:
    initial_dir = _to_abs_path(body.initial_dir or "")
    if initial_dir and not Path(initial_dir).exists():
        initial_dir = ""
    root: tk.Tk | None = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        selected = filedialog.askdirectory(
            initialdir=initial_dir or os.getcwd(),
            title="选择文件夹",
            mustexist=False,
        )
        selected_abs = _to_abs_path(selected)
        return _ok({"selected": bool(selected_abs), "path": selected_abs})
    except Exception as exc:  # noqa: BLE001
        _fail(5002, f"open directory picker failed: {exc}", http=500)
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


@router.post("/system/kill-backend", response_model=ApiResponse)
def system_kill_backend() -> ApiResponse:
    _terminate_backend_async()
    return _ok({"scheduled": True})


@router.post("/sub-image-template/upload", response_model=ApiResponse)
async def upload_sub_image_template(file: UploadFile = File(...)) -> ApiResponse:
    raw_name = (file.filename or "").strip()
    filename = Path(raw_name).name
    if not filename:
        _fail(4005, "filename is required")
    with db:
        system_config = system_config_service.get_system_config()
    sub_image_dir = _sanitize_path(system_config.get("sub_image_dir", ""))
    if not sub_image_dir:
        _fail(4006, "sub_image_dir is empty, please set system config first")
    target_dir = Path(sub_image_dir).expanduser()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        target_file = target_dir / filename
        target_file.write_bytes(content)
    except OSError as exc:
        _fail(5001, f"save upload file failed: {exc}", http=500)
    return _ok(UploadSubImageTemplateResult(filename=filename, saved_path=str(target_file.resolve())))


@router.get("/{workflow_id}", response_model=ApiResponse)
def workflow_get(workflow_id: str) -> ApiResponse:
    with db:
        wf = workflow_definition_service.get_workflow(workflow_id)
        latest = workflow_definition_service.latest_published(workflow_id)
        draft = json.loads(wf.draft_runtime_json)
        return _ok(
            {
                "workflow_id": wf.workflow_id,
                "name": wf.name,
                "status": wf.status,
                "protocol_version": wf.protocol_version,
                "global_object_config_id": int(wf.global_object_config_id) if wf.global_object_config_id else None,
                "draft_runtime": draft,
                "published_version": int(latest.version) if latest else None,
            }
        )


@router.get("/global-config/list", response_model=ApiResponse)
def global_config_list(q: str | None = None) -> ApiResponse:
    with db:
        return _ok({"items": global_object_config_service.list_configs(q=q)})


@router.get("/global-config/{config_id}", response_model=ApiResponse)
def global_config_get(config_id: int) -> ApiResponse:
    with db:
        try:
            row = global_object_config_service.get_config(config_id)
        except Exception:  # noqa: BLE001
            _fail(4042, "global config not found", http=404)
        return _ok(
            {
                "id": int(row.id),
                "name": row.name,
                "config": global_object_config_service.parse_config_value(row),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )


@router.post("/global-config/create", response_model=ApiResponse)
def global_config_create(body: GlobalObjectConfigCreateBody) -> ApiResponse:
    with db:
        row = global_object_config_service.create_config(body.name, body.config)
        return _ok({"id": int(row.id), "name": row.name})


@router.post("/global-config/{config_id}/update", response_model=ApiResponse)
def global_config_update(config_id: int, body: GlobalObjectConfigUpdateBody) -> ApiResponse:
    with db:
        try:
            row = global_object_config_service.update_config(config_id, name=body.name, config=body.config)
        except Exception:  # noqa: BLE001
            _fail(4042, "global config not found", http=404)
        return _ok({"id": int(row.id), "updated": True})


@router.post("/global-config/{config_id}/delete", response_model=ApiResponse)
def global_config_delete(config_id: int) -> ApiResponse:
    with db:
        try:
            global_object_config_service.delete_config(config_id)
        except ValueError as e:
            _fail(4003, str(e))
        except Exception:  # noqa: BLE001
            _fail(4042, "global config not found", http=404)
        return _ok({"id": int(config_id), "deleted": True})


@router.post("/validate", response_model=ApiResponse)
def workflow_validate(body: ValidateBody) -> ApiResponse:
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(body.runtime)
        data: dict[str, Any] = {"valid": len(errs) == 0, "errors": errs}
        is_lowcode_test_runtime = str(body.runtime.get("workflow_id", "")).strip() == "__lowcode_test__"
        if not errs and is_lowcode_test_runtime:
            try:
                raw_lowcode_return = workflow_validate_service.execute_lowcode_test_runtime(body.runtime)
                data["lowcode_return"] = _json_safe(raw_lowcode_return)
            except (LowcodeCompileError, LowcodeRuntimeError, LowcodeTimeoutError, LowcodeProtocolError) as exc:
                data["valid"] = False
                data["errors"] = [
                    {
                        "path": "nodes:lowcode_1.config.code_body",
                        "message": f"{type(exc).__name__}: {exc}",
                        "node_id": "lowcode_1",
                    }
                ]
        return _ok(data)


@router.post("/{workflow_id}/publish", response_model=ApiResponse)
def workflow_publish(workflow_id: str) -> ApiResponse:
    with db:
        try:
            ver = workflow_definition_service.publish_workflow(workflow_id)
        except ValueError as e:
            try:
                errs = json.loads(str(e))
            except json.JSONDecodeError:
                _fail(4001, str(e))
            else:
                return ApiResponse(success=False, code=4001, message="validation failed", data={"errors": errs})
        return _ok({"workflow_id": workflow_id, "version": int(ver.version)})


@router.post("/{workflow_id}/run", response_model=ApiResponse)
def workflow_run(workflow_id: str, body: RunBody) -> ApiResponse:
    with db:
        try:
            run = workflow_run_service.create_run(
                workflow_id,
                body.input,
                version=body.version,
                idempotency_key=body.idempotency_key,
            )
        except ValueError as e:
            _fail(4002, str(e))
        return _ok({"run_id": run.run_id, "status": run.status})


@router.get("/run/{run_id}/status", response_model=ApiResponse)
def workflow_run_status(run_id: str) -> ApiResponse:
    with db:
        try:
            st = workflow_run_service.get_run_status(run_id)
        except ValueError:
            _fail(4040, "run not found", http=404)
        return _ok(st)


@router.get("/run/{run_id}/logs", response_model=ApiResponse)
def workflow_run_logs(run_id: str, limit: int = 100, cursor: int | None = None) -> ApiResponse:
    with db:
        try:
            logs = workflow_run_service.get_run_logs(run_id, limit=limit, cursor=cursor)
        except ValueError:
            _fail(4040, "run not found", http=404)
        return _ok(logs)


@router.post("/run/{run_id}/cancel", response_model=ApiResponse)
def workflow_run_cancel(run_id: str) -> ApiResponse:
    with db:
        try:
            data = workflow_run_service.cancel_run(run_id)
        except Exception:  # noqa: BLE001
            _fail(4040, "run not found", http=404)
        return _ok(data)


@router.get("/queue/list", response_model=ApiResponse)
def workflow_queue_list(
    queue_status: str | None = None,
    workflow_id: str | None = None,
    run_id: str | None = None,
    limit: int = 100,
) -> ApiResponse:
    with db:
        data = workflow_run_service.list_queue_records(
            queue_status=queue_status,
            workflow_id=workflow_id,
            run_id=run_id,
            limit=limit,
        )
        return _ok(data)


@router.get("/{workflow_id}/versions", response_model=ApiResponse)
def workflow_versions(workflow_id: str) -> ApiResponse:
    with db:
        rows = workflow_definition_service.list_versions(workflow_id)
        return _ok(
            {
                "items": [
                    {
                        "version": int(r.version),
                        "state": r.state,
                        "published_at": r.published_at.isoformat() if r.published_at else None,
                    }
                    for r in rows
                ]
            }
        )


@router.get("/{workflow_id}/versions/{version}", response_model=ApiResponse)
def workflow_version_get(workflow_id: str, version: int) -> ApiResponse:
    with db:
        try:
            r = workflow_definition_service.get_version(workflow_id, version)
        except Exception:  # noqa: BLE001
            _fail(4041, "version not found", http=404)
        return _ok({"version": int(r.version), "state": r.state, "runtime": json.loads(r.dsl_json)})
