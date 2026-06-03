from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from peewee import JOIN, fn

from app.config import PROTOCOL_VERSION
from app.db import models


def _new_workflow_id() -> str:
    return f"wf_{uuid.uuid4().hex[:12]}"


def create_workflow(
    name: str,
    workflow_id: str | None = None,
    draft_runtime: dict[str, Any] | None = None,
    global_object_config_id: int | None = None,
) -> models.Workflow:
    wid = workflow_id or _new_workflow_id()
    body = draft_runtime or _default_draft(wid, name)
    cfg = None
    if global_object_config_id is not None:
        cfg = models.GlobalObjectConfig.get_or_none(models.GlobalObjectConfig.id == int(global_object_config_id))
        if cfg is None:
            raise ValueError("global object config not found")
    wf = models.Workflow.create(
        workflow_id=wid,
        name=name,
        status="active",
        protocol_version=PROTOCOL_VERSION,
        global_object_config=cfg,
        draft_runtime_json=json.dumps(body, ensure_ascii=False),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return wf


def _default_draft(workflow_id: str, name: str) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "name": name,
        "version": 0,
        "settings": {"default_timeout_sec": 60, "max_retries": 0, "max_loop_iterations": 1000},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "end_1"}],
    }


def update_workflow(
    workflow_id: str,
    name: str | None = None,
    draft_runtime: dict[str, Any] | None = None,
    status: str | None = None,
    global_object_config_id: int | None = None,
) -> models.Workflow:
    wf = models.Workflow.get(models.Workflow.workflow_id == workflow_id)
    runtime_obj: dict[str, Any] | None = None
    if draft_runtime is not None:
        runtime_obj = draft_runtime
    else:
        try:
            runtime_obj = json.loads(wf.draft_runtime_json or "{}")
            if not isinstance(runtime_obj, dict):
                runtime_obj = {}
        except json.JSONDecodeError:
            runtime_obj = {}
    if name is not None:
        wf.name = name
        runtime_obj["name"] = name
    if draft_runtime is not None:
        wf.draft_runtime_json = json.dumps(runtime_obj, ensure_ascii=False)
    elif name is not None:
        wf.draft_runtime_json = json.dumps(runtime_obj, ensure_ascii=False)
    if status is not None:
        wf.status = status
    if global_object_config_id is not None:
        cfg = models.GlobalObjectConfig.get_or_none(models.GlobalObjectConfig.id == int(global_object_config_id))
        if cfg is None:
            raise ValueError("global object config not found")
        wf.global_object_config = cfg
    wf.updated_at = datetime.utcnow()
    wf.save()
    return wf


def get_workflow(workflow_id: str) -> models.Workflow:
    return models.Workflow.get(models.Workflow.workflow_id == workflow_id)


def list_workflows(status: str | None = None, q: str | None = None) -> list[dict[str, Any]]:
    version_subquery = (
        models.WorkflowVersion.select(
            models.WorkflowVersion.workflow.alias("workflow_id"),
            fn.MAX(models.WorkflowVersion.version).alias("published_version"),
        )
        .where(models.WorkflowVersion.state == "published")
        .group_by(models.WorkflowVersion.workflow)
        .alias("wf_pub")
    )

    query = (
        models.Workflow.select(models.Workflow, version_subquery.c.published_version)
        .join(
            version_subquery,
            JOIN.LEFT_OUTER,
            on=(models.Workflow.workflow_id == version_subquery.c.workflow_id),
        )
        .order_by(models.Workflow.updated_at.desc())
    )
    if status:
        query = query.where(models.Workflow.status == status)
    if q:
        qq = q.strip()
        if qq:
            query = query.where(
                models.Workflow.workflow_id.contains(qq) | models.Workflow.name.contains(qq)
            )
    items: list[dict[str, Any]] = []
    for row in query.dicts():
        published_version = row.get("published_version")
        global_object_config_id = row.get("global_object_config_id", row.get("global_object_config"))
        updated_at = row.get("updated_at")
        items.append(
            {
                "workflow_id": row["workflow_id"],
                "name": row["name"],
                "status": row["status"],
                "protocol_version": int(row["protocol_version"]),
                "global_object_config_id": int(global_object_config_id) if global_object_config_id else None,
                "published_version": int(published_version) if published_version is not None else None,
                "updated_at": updated_at.isoformat() if updated_at else None,
            }
        )
    return items


def publish_workflow(workflow_id: str) -> models.WorkflowVersion:
    from app.services import workflow_validate_service

    wf = get_workflow(workflow_id)
    runtime = json.loads(wf.draft_runtime_json)
    errs = workflow_validate_service.validate_runtime_dsl(runtime)
    if errs:
        raise ValueError(json.dumps(errs, ensure_ascii=False))
    _freeze_subflow_versions(runtime)
    latest = (
        models.WorkflowVersion.select()
        .where(models.WorkflowVersion.workflow == wf)
        .order_by(models.WorkflowVersion.version.desc())
        .first()
    )
    next_v = (latest.version + 1) if latest else 1
    ver = models.WorkflowVersion.create(
        workflow=wf,
        version=next_v,
        dsl_json=json.dumps(runtime, ensure_ascii=False),
        state="published",
        published_at=datetime.utcnow(),
    )
    wf.updated_at = datetime.utcnow()
    wf.save()
    return ver


def _freeze_subflow_versions(runtime: dict[str, Any]) -> None:
    for node in runtime.get("nodes", []):
        if node.get("type") != "subflow":
            continue
        cfg = node.get("config") or {}
        wid = cfg.get("workflow_id")
        if not isinstance(wid, str) or not wid:
            continue
        child = latest_published(wid)
        if not child:
            continue
        cfg["workflow_version"] = int(child.version)
        node["config"] = cfg


def list_versions(workflow_id: str) -> list[models.WorkflowVersion]:
    wf = get_workflow(workflow_id)
    return list(
        models.WorkflowVersion.select()
        .where(models.WorkflowVersion.workflow == wf)
        .order_by(models.WorkflowVersion.version.desc())
    )


def get_version(workflow_id: str, version: int) -> models.WorkflowVersion:
    wf = get_workflow(workflow_id)
    return models.WorkflowVersion.get((models.WorkflowVersion.workflow == wf) & (models.WorkflowVersion.version == version))


def latest_published(workflow_id: str) -> models.WorkflowVersion | None:
    wf = get_workflow(workflow_id)
    return (
        models.WorkflowVersion.select()
        .where((models.WorkflowVersion.workflow == wf) & (models.WorkflowVersion.state == "published"))
        .order_by(models.WorkflowVersion.version.desc())
        .first()
    )
