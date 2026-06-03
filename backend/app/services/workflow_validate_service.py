from __future__ import annotations

from typing import Any

from orchestration_engine import (
    LowcodeCompileError,
    LowcodeProtocolError,
    LowcodeRuntimeError,
    LowcodeTimeoutError,
)
from app.orchestration_adapters import build_engine
from app.db import models


def validate_runtime_dsl(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    engine = build_engine()
    errors = engine.validate_runtime(runtime)
    for n in runtime.get("nodes", []):
        if n.get("type") != "subflow":
            continue
        cfg = n.get("config") or {}
        wid = cfg.get("workflow_id")
        node_id = str(n.get("id", ""))
        if not isinstance(wid, str) or not wid:
            errors.append({"path": f"nodes:{node_id}.config.workflow_id", "message": "subflow 必须配置 workflow_id", "node_id": node_id})
            continue
        child = models.Workflow.get_or_none(models.Workflow.workflow_id == wid)
        if not child:
            errors.append({"path": f"nodes:{node_id}.config.workflow_id", "message": f"子流程不存在: {wid}", "node_id": node_id})
            continue
        published = (
            models.WorkflowVersion.select()
            .where((models.WorkflowVersion.workflow == child) & (models.WorkflowVersion.state == "published"))
            .first()
        )
        if not published:
            errors.append({"path": f"nodes:{node_id}.config.workflow_id", "message": f"子流程未发布: {wid}", "node_id": node_id})
    return errors


def execute_lowcode_test_runtime(runtime: dict[str, Any]) -> dict[str, Any]:
    lowcode_nodes = [n for n in runtime.get("nodes", []) if n.get("type") == "lowcode_function"]
    if len(lowcode_nodes) != 1:
        raise ValueError("函数体测试需要且仅支持一个 lowcode_function 节点")

    node = lowcode_nodes[0]
    node_id = str(node.get("id") or "lowcode_1")
    cfg = node.get("config") or {}
    test_ctx_raw = cfg.get("test_ctx")
    test_ctx = dict(test_ctx_raw) if isinstance(test_ctx_raw, dict) else {}
    initial_ctx: dict[str, Any] = dict(test_ctx)
    runtime_copy = dict(runtime)
    runtime_copy["nodes"] = [
        {"id": "start_1", "type": "start", "name": "开始", "config": {}},
        {"id": node_id, "type": "lowcode_function", "name": "低代码函数", "config": cfg},
        {"id": "end_1", "type": "end", "name": "结束", "config": {}},
    ]
    runtime_copy["edges"] = [{"from": "start_1", "to": node_id}, {"from": node_id, "to": "end_1"}]
    try:
        engine = build_engine()
        executor = engine.create_executor(runtime=runtime_copy, input_obj={}, initial_ctx=initial_ctx)
        executor.run()
    except (LowcodeCompileError, LowcodeRuntimeError, LowcodeTimeoutError, LowcodeProtocolError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise LowcodeRuntimeError(str(exc)) from exc

    result = executor.node_results.get(node_id)
    if isinstance(result, dict):
        normalized = dict(result)
        if "ok" not in normalized:
            normalized["ok"] = True
        if "code" not in normalized:
            normalized["code"] = "OK" if bool(normalized.get("ok")) else "ERR"
        if "message" not in normalized:
            normalized["message"] = "OK" if bool(normalized.get("ok")) else "ERROR"
        if "data" not in normalized:
            normalized["data"] = None
        return normalized
    if result is None:
        raise LowcodeProtocolError("lowcode return value missing")
    return {"ok": True, "code": "OK", "message": "OK", "data": result}
