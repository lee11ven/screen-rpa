from __future__ import annotations

from datetime import datetime

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    BooleanField,
    TextField,
)

from app.db.database import db


class BaseModel(db.Model):
    class Meta:
        database = db


class GlobalObjectConfig(BaseModel):
    id = AutoField()
    name = CharField(max_length=255, unique=True)
    config_json = TextField(default="{}")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_global_object_config"


class SystemConfig(BaseModel):
    id = AutoField()
    sub_image_dir = TextField(default="")
    fullscreen_screenshot_dir = TextField(default="")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_system_config"


class Workflow(BaseModel):
    workflow_id = CharField(primary_key=True, max_length=128)
    name = CharField(max_length=255)
    status = CharField(max_length=32, default="active")
    protocol_version = IntegerField(default=1)
    global_object_config = ForeignKeyField(
        GlobalObjectConfig,
        null=True,
        backref="workflows",
        column_name="global_object_config_id",
        on_delete="SET NULL",
    )
    draft_runtime_json = TextField(default="{}")
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_workflow"


class WorkflowVersion(BaseModel):
    id = AutoField()
    workflow = ForeignKeyField(Workflow, field=Workflow.workflow_id, backref="versions", on_delete="CASCADE")
    version = IntegerField()
    dsl_json = TextField()
    state = CharField(max_length=32, default="published")
    published_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_workflow_version"
        indexes = ((("workflow", "version"), True),)


class WorkflowRun(BaseModel):
    run_id = CharField(primary_key=True, max_length=64)
    workflow = ForeignKeyField(Workflow, field=Workflow.workflow_id, backref="runs", on_delete="CASCADE")
    workflow_version = IntegerField()
    status = CharField(max_length=32, default="CREATED")
    input_json = TextField(default="{}")
    snapshot_json = TextField(null=True)
    error_message = TextField(null=True)
    idempotency_key = CharField(max_length=128, null=True, unique=True)
    attempt = IntegerField(default=0)
    locked_by = CharField(max_length=64, null=True)
    lock_until = DateTimeField(null=True)
    cancelled = BooleanField(default=False)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_workflow_run"


class WorkflowRunNode(BaseModel):
    id = AutoField()
    run = ForeignKeyField(WorkflowRun, field=WorkflowRun.run_id, backref="nodes", on_delete="CASCADE")
    node_id = CharField(max_length=128)
    status = CharField(max_length=32, default="PENDING")
    error_code = CharField(max_length=64, null=True)
    retry_count = IntegerField(default=0)
    last_error = TextField(null=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)

    class Meta:
        table_name = "rpa_workflow_run_node"
        indexes = ((("run", "node_id"), True),)


class WorkflowRunLog(BaseModel):
    id = AutoField()
    run = ForeignKeyField(WorkflowRun, field=WorkflowRun.run_id, backref="logs", on_delete="CASCADE")
    level = CharField(max_length=16, default="info")
    node_id = CharField(max_length=128, null=True)
    message = TextField()
    context_json = TextField(default="{}")
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_workflow_run_log"
        indexes = ((("run", "created_at"), False),)


class TaskQueueRecord(BaseModel):
    id = AutoField()
    run = ForeignKeyField(WorkflowRun, field=WorkflowRun.run_id, backref="queue_records", on_delete="CASCADE")
    queue_status = CharField(max_length=32, default="ENQUEUED")
    message_id = CharField(max_length=128, unique=True)
    idempotency_key = CharField(max_length=128)
    available_at = DateTimeField(default=datetime.utcnow)
    lease_until = DateTimeField(null=True)
    dequeued_at = DateTimeField(null=True)
    done_at = DateTimeField(null=True)
    dead_at = DateTimeField(null=True)
    fail_reason = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_task_queue_record"
        indexes = (
            (("queue_status", "available_at"), False),
            (("run", "queue_status"), False),
            (("idempotency_key",), False),
        )


class TaskRetryRecord(BaseModel):
    id = AutoField()
    queue_record = ForeignKeyField(TaskQueueRecord, backref="retries", on_delete="CASCADE")
    run = ForeignKeyField(WorkflowRun, field=WorkflowRun.run_id, backref="retries", on_delete="CASCADE")
    attempt = IntegerField(default=1)
    status = CharField(max_length=32, default="RETRY_WAIT")
    scheduled_at = DateTimeField(default=datetime.utcnow)
    executed_at = DateTimeField(null=True)
    error_message = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "rpa_task_retry_record"
        indexes = (
            (("run", "attempt"), True),
            (("queue_record", "attempt"), False),
        )
