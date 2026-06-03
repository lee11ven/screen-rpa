from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta

from app.config import QUEUE_LEASE_SEC, QUEUE_MAX_RETRY, QUEUE_RETRY_BACKOFF_SEC, RECOVERY_SCAN_INTERVAL_SEC, WORKER_ID
from app.db import models
from app.db.database import db, init_db
from app.services import workflow_run_service

logger = logging.getLogger(__name__)


def run_forever(poll_sec: float = 5.0) -> None:
    logging.basicConfig(level=logging.INFO)
    init_db()
    logger.info("workflow worker started")
    last_recovery_scan = datetime.utcnow()
    while True:
        now = datetime.utcnow()
        if (now - last_recovery_scan).total_seconds() >= RECOVERY_SCAN_INTERVAL_SEC:
            with db:
                _recover_leased_tasks()
            last_recovery_scan = now

        run_id = ""
        message_id = ""
        with db:
            msg = _take_next_ready_message()
        if not msg:
            time.sleep(max(0.1, poll_sec))
            continue
        run_id, message_id = msg
        try:
            workflow_run_service.execute_run_sync(run_id)
            with db:
                _mark_message_done(run_id, message_id)
        except Exception:  # noqa: BLE001
            logger.exception("run failed")
            try:
                with db:
                    _mark_message_failed(run_id=run_id, message_id=message_id, error="worker execution failed")
            except Exception:  # noqa: BLE001
                logger.exception("mark failed status error")


def _take_next_ready_message() -> tuple[str, str] | None:
    rec = (
        models.TaskQueueRecord.select()
        .where(
            (models.TaskQueueRecord.queue_status.in_(("ENQUEUED", "RETRY_WAIT")))
            & (models.TaskQueueRecord.available_at <= datetime.utcnow())
        )
        .order_by(models.TaskQueueRecord.id.asc())
        .first()
    )
    if not rec:
        return None
    rec.queue_status = "DEQUEUED"
    rec.dequeued_at = datetime.utcnow()
    rec.lease_until = rec.dequeued_at + timedelta(seconds=QUEUE_LEASE_SEC)
    rec.updated_at = datetime.utcnow()
    rec.save()
    run = rec.run
    run.locked_by = WORKER_ID
    run.lock_until = rec.lease_until
    run.save()
    return rec.run_id, rec.message_id


def _dequeue_ready_message(run_id: str, message_id: str) -> bool:
    """将指定队列记录领取为 DEQUEUED；若已非可领取状态则返回 False（供测试与幂等校验）。"""
    with db:
        rec = (
            models.TaskQueueRecord.select()
            .where(
                (models.TaskQueueRecord.run_id == run_id) & (models.TaskQueueRecord.message_id == message_id)
            )
            .first()
        )
        if not rec:
            return False
        if rec.queue_status not in ("ENQUEUED", "RETRY_WAIT"):
            return False
        if rec.available_at > datetime.utcnow():
            return False
        rec.queue_status = "DEQUEUED"
        rec.dequeued_at = datetime.utcnow()
        rec.lease_until = rec.dequeued_at + timedelta(seconds=QUEUE_LEASE_SEC)
        rec.updated_at = datetime.utcnow()
        rec.save()
        run = rec.run
        run.locked_by = WORKER_ID
        run.lock_until = rec.lease_until
        run.save()
        return True


def _mark_message_done(run_id: str, message_id: str) -> None:
    rec = (
        models.TaskQueueRecord.select()
        .where((models.TaskQueueRecord.run_id == run_id) & (models.TaskQueueRecord.message_id == message_id))
        .first()
    )
    if not rec:
        return
    rec.queue_status = "DONE"
    rec.done_at = datetime.utcnow()
    rec.updated_at = datetime.utcnow()
    rec.lease_until = None
    rec.save()


def _mark_message_failed(run_id: str, message_id: str, error: str) -> None:
    rec = (
        models.TaskQueueRecord.select()
        .where((models.TaskQueueRecord.run_id == run_id) & (models.TaskQueueRecord.message_id == message_id))
        .first()
    )
    if not rec:
        return
    prior = models.TaskRetryRecord.select().where(models.TaskRetryRecord.run == rec.run).count()
    if prior < QUEUE_MAX_RETRY:
        rec.queue_status = "RETRY_WAIT"
        rec.available_at = datetime.utcnow() + timedelta(seconds=max(1, (prior + 1) * QUEUE_RETRY_BACKOFF_SEC))
        rec.fail_reason = error
        rec.updated_at = datetime.utcnow()
        rec.lease_until = None
        rec.save()
        models.TaskRetryRecord.create(
            queue_record=rec,
            run=rec.run,
            attempt=prior + 1,
            status="RETRY_WAIT",
            scheduled_at=rec.available_at,
            error_message=error,
            created_at=datetime.utcnow(),
        )
        return

    rec.queue_status = "DEAD"
    rec.dead_at = datetime.utcnow()
    rec.fail_reason = error
    rec.updated_at = datetime.utcnow()
    rec.lease_until = None
    rec.save()


def _recover_leased_tasks() -> None:
    expired = (
        models.TaskQueueRecord.select()
        .where(
            (models.TaskQueueRecord.queue_status == "DEQUEUED")
            & (models.TaskQueueRecord.lease_until.is_null(False))
            & (models.TaskQueueRecord.lease_until < datetime.utcnow())
        )
        .limit(100)
    )
    for rec in expired:
        _mark_message_failed(rec.run_id, rec.message_id, "lease expired")


if __name__ == "__main__":
    run_forever()
