from __future__ import annotations

import uuid
from datetime import datetime

from app.db import models


def enqueue_run(run_id: str, idempotency_key: str | None = None, available_at: datetime | None = None) -> str:
    message_id = f"msg_{uuid.uuid4().hex[:20]}"
    run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    rec = models.TaskQueueRecord.create(
        run=run,
        queue_status="ENQUEUED",
        message_id=message_id,
        idempotency_key=idempotency_key or run_id,
        available_at=available_at or datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return rec.message_id
