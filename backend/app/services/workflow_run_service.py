from __future__ import annotations

import json
import logging
import copy
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.config import QUEUE_LEASE_SEC, QUEUE_MAX_RETRY, QUEUE_RETRY_BACKOFF_SEC
from app.db import models
from app.orchestration_adapters import build_engine
from orchestration_engine import ExecutorHooks, RunCancelledError
from app.queue import dispatcher

logger = logging.getLogger(__name__)


TERMINAL_STATES = {"SUCCESS", "FAILED", "CANCELLED", "TIMEOUT"}


def _collect_node_name_map(nodes: list[dict[str, Any]], out: dict[str, str]) -> None:
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            continue
        node_name = str(node.get("name") or "").strip() or node_id
        out[node_id] = node_name
        if str(node.get("type") or "") != "loop-container":
            continue
        cfg = node.get("config") or {}
        if not isinstance(cfg, dict):
            continue
        sub_graph = cfg.get("subGraph") or {}
        if not isinstance(sub_graph, dict):
            continue
        sub_nodes = sub_graph.get("nodes") or []
        if isinstance(sub_nodes, list):
            _collect_node_name_map(sub_nodes, out)


def create_run(
    workflow_id: str,
    input_obj: dict[str, Any],
    version: int | None = None,
    idempotency_key: str | None = None,
) -> models.WorkflowRun:
    from app.services.workflow_definition_service import get_workflow, latest_published

    try:
        wf = get_workflow(workflow_id)
    except models.Workflow.DoesNotExist as e:
        raise ValueError("workflow not found") from e
    if version is None:
        ver = latest_published(workflow_id)
        if not ver:
            raise ValueError("no published version")
        vnum = int(ver.version)
        dsl_json = ver.dsl_json
    else:
        ver = models.WorkflowVersion.get_or_none(
            (models.WorkflowVersion.workflow == wf) & (models.WorkflowVersion.version == int(version))
        )
        if not ver:
            raise ValueError("version not found")
        if ver.state != "published":
            raise ValueError("version is not published")
        vnum = int(ver.version)
        dsl_json = ver.dsl_json

    if wf.global_object_config_id is None:
        raise ValueError("workflow global object config not set")

    idem = (idempotency_key or "").strip() or None
    if idem:
        existed = models.WorkflowRun.select().where(models.WorkflowRun.idempotency_key == idem).first()
        if existed:
            return existed
    rid = new_run_id()
    run = models.WorkflowRun.create(
        run_id=rid,
        workflow=wf,
        workflow_version=vnum,
        status="QUEUED",
        input_json=json.dumps(input_obj, ensure_ascii=False),
        idempotency_key=idem,
        created_at=datetime.utcnow(),
    )
    runtime = json.loads(dsl_json)
    for n in runtime.get("nodes", []):
        nid = n.get("id")
        if not nid:
            continue
        models.WorkflowRunNode.get_or_create(
            run=run,
            node_id=str(nid),
            defaults={"status": "PENDING"},
        )
    dispatcher.enqueue_run(rid, idempotency_key=idem or rid)
    return run


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:16]}"


def execute_run_sync(run_id: str) -> None:
    run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    if run.status in TERMINAL_STATES:
        return
    if run.cancelled:
        run.status = "CANCELLED"
        run.finished_at = datetime.utcnow()
        run.save()
        return

    wf = run.workflow
    ver = models.WorkflowVersion.get(
        (models.WorkflowVersion.workflow == wf) & (models.WorkflowVersion.version == int(run.workflow_version))
    )
    runtime = json.loads(ver.dsl_json)
    input_obj = json.loads(run.input_json or "{}")
    previous_snapshot: dict[str, Any] = {}
    if run.snapshot_json:
        try:
            loaded = json.loads(run.snapshot_json)
            if isinstance(loaded, dict):
                previous_snapshot = loaded
        except Exception:  # noqa: BLE001
            previous_snapshot = {}
    global_ctx: dict[str, Any] = {}
    if wf.global_object_config_id is not None:
        row = models.GlobalObjectConfig.get_or_none(models.GlobalObjectConfig.id == int(wf.global_object_config_id))
        if row is not None:
            try:
                loaded_global_ctx = json.loads(row.config_json or "{}")
                if isinstance(loaded_global_ctx, dict):
                    global_ctx = loaded_global_ctx
            except Exception:  # noqa: BLE001
                global_ctx = {}
    runtime_ctx: dict[str, Any] = copy.deepcopy(global_ctx)
    runtime_ctx.update(input_obj)
    base_ctx = previous_snapshot.get("ctx") if isinstance(previous_snapshot, dict) else None
    if isinstance(base_ctx, dict):
        runtime_ctx.update(base_ctx)
    # runtime_ctx["input_json"] = input_obj
    # runtime_ctx["snapshot_json"] = previous_snapshot

    now = datetime.utcnow()
    run.status = "RUNNING"
    run.started_at = run.started_at or now
    run.attempt = int(run.attempt or 0) + 1
    run.lock_until = now + timedelta(seconds=QUEUE_LEASE_SEC)
    run.save()

    def on_log(level: str, node_id: str | None, message: str, ctx: dict[str, Any]) -> None:
        models.WorkflowRunLog.create(
            run=run,
            level=level,
            node_id=node_id,
            message=message,
            context_json=json.dumps(ctx, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )

    def on_node_start(node_id: str) -> None:
        try:
            row = models.WorkflowRunNode.get((models.WorkflowRunNode.run == run) & (models.WorkflowRunNode.node_id == node_id))
            row.status = "RUNNING"
            row.started_at = datetime.utcnow()
            row.save()
        except models.WorkflowRunNode.DoesNotExist:
            models.WorkflowRunNode.create(
                run=run,
                node_id=node_id,
                status="RUNNING",
                started_at=datetime.utcnow(),
            )

    def on_node_finish(node_id: str, st: str, err: str | None) -> None:
        row, _ = models.WorkflowRunNode.get_or_create(
            run=run,
            node_id=node_id,
            defaults={"status": st, "started_at": datetime.utcnow()},
        )
        row.status = st
        row.finished_at = datetime.utcnow()
        if err:
            row.error_code = err[:60]
            row.last_error = err
            row.retry_count = int(row.retry_count or 0) + 1
        row.save()

    hooks = ExecutorHooks(on_log=on_log, on_node_start=on_node_start, on_node_finish=on_node_finish)
    engine = build_engine()

    def cancel_requested() -> bool:
        latest = models.WorkflowRun.get_or_none(models.WorkflowRun.run_id == run_id)
        return bool(latest and latest.cancelled)

    ex = engine.create_executor(
        runtime=runtime,
        input_obj=input_obj,
        hooks=hooks,
        initial_ctx=runtime_ctx,
        cancel_requested=cancel_requested,
    )
    try:
        ex.run()
        run.status = "SUCCESS"
        run.snapshot_json = json.dumps(
            {"ctx": ex.ctx, "node_results": ex.node_results, "attempt": run.attempt},
            ensure_ascii=False,
            default=str,
        )
        run.finished_at = datetime.utcnow()
        run.lock_until = None
        run.locked_by = None
        run.save()
    except RunCancelledError as e:
        logger.info("run %s cancelled during execution", run_id)
        run.status = "CANCELLED"
        run.error_message = str(e)
        run.finished_at = datetime.utcnow()
        run.lock_until = None
        run.locked_by = None
        run.save()
    except Exception as e:  # noqa: BLE001
        logger.exception("run %s failed", run_id)
        if run.attempt < QUEUE_MAX_RETRY and not run.cancelled:
            run.status = "QUEUED"
        else:
            run.status = "FAILED"
        run.error_message = str(e)
        run.finished_at = datetime.utcnow() if run.status in TERMINAL_STATES else None
        run.lock_until = None
        run.locked_by = None
        run.save()
        if run.status == "QUEUED":
            delay = QUEUE_RETRY_BACKOFF_SEC * run.attempt
            schedule_at = datetime.utcnow() + timedelta(seconds=max(1, delay))
            dispatcher.enqueue_run(run.run_id, idempotency_key=run.idempotency_key or run.run_id, available_at=schedule_at)


def get_run_status(run_id: str) -> dict[str, Any]:
    try:
        run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    except models.WorkflowRun.DoesNotExist as e:
        raise ValueError("run not found") from e
    nodes = list(
        models.WorkflowRunNode.select()
        .where(models.WorkflowRunNode.run == run)
        .order_by(models.WorkflowRunNode.id)
    )
    node_name_map: dict[str, str] = {}
    ver = models.WorkflowVersion.get_or_none(
        (models.WorkflowVersion.workflow == run.workflow)
        & (models.WorkflowVersion.version == int(run.workflow_version))
    )
    if ver is not None:
        try:
            runtime = json.loads(ver.dsl_json or "{}")
            root_nodes = runtime.get("nodes")
            if isinstance(root_nodes, list):
                _collect_node_name_map(root_nodes, node_name_map)
        except Exception:  # noqa: BLE001
            node_name_map = {}
    queue_rows = (
        models.TaskQueueRecord.select()
        .where(models.TaskQueueRecord.run == run)
        .order_by(models.TaskQueueRecord.id.desc())
        .limit(10)
    )
    return {
        "run_id": run.run_id,
        "workflow_id": run.workflow_id,
        "workflow_version": run.workflow_version,
        "status": run.status,
        "attempt": run.attempt,
        "cancelled": run.cancelled,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_message": run.error_message,
        "nodes": [
            {
                "node_id": n.node_id,
                "node_name": node_name_map.get(n.node_id),
                "status": n.status,
                "started_at": n.started_at.isoformat() if n.started_at else None,
                "finished_at": n.finished_at.isoformat() if n.finished_at else None,
                "error_code": n.error_code,
            }
            for n in nodes
        ],
        "queue": [
            {
                "message_id": q.message_id,
                "queue_status": q.queue_status,
                "available_at": q.available_at.isoformat() if q.available_at else None,
                "dequeued_at": q.dequeued_at.isoformat() if q.dequeued_at else None,
                "done_at": q.done_at.isoformat() if q.done_at else None,
                "dead_at": q.dead_at.isoformat() if q.dead_at else None,
            }
            for q in queue_rows
        ],
    }


def get_run_logs(run_id: str, limit: int = 100, cursor: int | None = None) -> dict[str, Any]:
    try:
        run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    except models.WorkflowRun.DoesNotExist as e:
        raise ValueError("run not found") from e
    q = models.WorkflowRunLog.select().where(models.WorkflowRunLog.run == run).order_by(models.WorkflowRunLog.id)
    if cursor is not None:
        q = q.where(models.WorkflowRunLog.id > int(cursor))
    rows = list(q.limit(int(limit)))
    next_cursor = rows[-1].id if rows else None
    return {
        "items": [
            {
                "id": r.id,
                "level": r.level,
                "node_id": r.node_id,
                "message": r.message,
                "context_json": json.loads(r.context_json or "{}"),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "next_cursor": next_cursor,
    }


def cancel_run(run_id: str) -> dict[str, Any]:
    run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    if run.status in TERMINAL_STATES:
        return {"run_id": run.run_id, "status": run.status, "cancelled": run.cancelled}
    run.cancelled = True
    if run.status == "QUEUED":
        run.status = "CANCELLED"
        run.finished_at = datetime.utcnow()
    run.save()
    return {"run_id": run.run_id, "status": run.status, "cancelled": run.cancelled}


def list_queue_records(
    queue_status: str | None = None,
    workflow_id: str | None = None,
    run_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    query = (
        models.TaskQueueRecord.select(models.TaskQueueRecord, models.WorkflowRun, models.Workflow)
        .join(models.WorkflowRun, on=(models.TaskQueueRecord.run == models.WorkflowRun.run_id))
        .join(models.Workflow, on=(models.WorkflowRun.workflow == models.Workflow.workflow_id))
        .order_by(models.TaskQueueRecord.id.desc())
    )
    if queue_status:
        query = query.where(models.TaskQueueRecord.queue_status == queue_status)
    if workflow_id:
        query = query.where(models.Workflow.workflow_id == workflow_id)
    if run_id:
        query = query.where(models.WorkflowRun.run_id == run_id)
    rows = list(query.limit(max(1, min(int(limit), 500))))
    items: list[dict[str, Any]] = []
    for row in rows:
        retries = models.TaskRetryRecord.select().where(models.TaskRetryRecord.queue_record == row).count()
        items.append(
            {
                "id": int(row.id),
                "message_id": row.message_id,
                "queue_status": row.queue_status,
                "workflow_id": row.run.workflow_id,
                "workflow_name": row.run.workflow.name,
                "run_id": row.run_id,
                "run_status": row.run.status,
                "idempotency_key": row.idempotency_key,
                "retry_count": int(retries),
                "available_at": row.available_at.isoformat() if row.available_at else None,
                "dequeued_at": row.dequeued_at.isoformat() if row.dequeued_at else None,
                "done_at": row.done_at.isoformat() if row.done_at else None,
                "dead_at": row.dead_at.isoformat() if row.dead_at else None,
                "lease_until": row.lease_until.isoformat() if row.lease_until else None,
                "fail_reason": row.fail_reason,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return {"items": items}
