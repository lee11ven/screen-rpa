from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.db import models
from app.db.database import db, init_db
from app.services import global_object_config_service, workflow_definition_service, workflow_run_service
from app.worker import consumer


def _prepare_run(workflow_id: str) -> str:
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["workflow_id"] = workflow_id
    with db:
        gc = global_object_config_service.create_config(f"gc-{workflow_id}", {})
        workflow_definition_service.create_workflow(
            name=workflow_id,
            workflow_id=workflow_id,
            draft_runtime=runtime,
            global_object_config_id=int(gc.id),
        )
        workflow_definition_service.publish_workflow(workflow_id)
        run = workflow_run_service.create_run(workflow_id, input_obj={})
    return run.run_id


def test_dequeue_is_idempotent_for_same_message() -> None:
    init_db()
    run_id = _prepare_run("wf_worker_idem")
    with db:
        rec = (
            models.TaskQueueRecord.select()
            .where(models.TaskQueueRecord.run_id == run_id)
            .order_by(models.TaskQueueRecord.id.desc())
            .first()
        )
        assert rec is not None
        assert consumer._dequeue_ready_message(run_id, rec.message_id) is True
        assert consumer._dequeue_ready_message(run_id, rec.message_id) is False


def test_recover_expired_lease_creates_retry() -> None:
    init_db()
    run_id = _prepare_run("wf_worker_recover")
    with db:
        rec = (
            models.TaskQueueRecord.select()
            .where(models.TaskQueueRecord.run_id == run_id)
            .order_by(models.TaskQueueRecord.id.desc())
            .first()
        )
        assert rec is not None
        rec.queue_status = "DEQUEUED"
        rec.lease_until = datetime.utcnow() - timedelta(seconds=1)
        rec.save()
        consumer._recover_leased_tasks()
        rec2 = models.TaskQueueRecord.get(models.TaskQueueRecord.id == rec.id)
        assert rec2.queue_status in {"RETRY_WAIT", "DEAD"}
