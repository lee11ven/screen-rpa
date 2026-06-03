from __future__ import annotations

from peewee import SqliteDatabase

from app.config import DATABASE_PATH

db = SqliteDatabase(
    str(DATABASE_PATH),
    pragmas={
        "journal_mode": "wal",
        "foreign_keys": 1,
        "synchronous": 1,
        "cache_size": -20000,
        "busy_timeout": 5000,
    },
)


def init_db() -> None:
    db.connect(reuse_if_open=True)
    from app.db import models  # noqa: PLC0415

    table_models = [
        models.GlobalObjectConfig,
        models.SystemConfig,
        models.Workflow,
        models.WorkflowVersion,
        models.WorkflowRun,
        models.WorkflowRunNode,
        models.WorkflowRunLog,
        models.TaskQueueRecord,
        models.TaskRetryRecord,
    ]
    db.create_tables(table_models, safe=True)
    _apply_compat_migrations()


def _table_columns(table_name: str) -> set[str]:
    rows = db.execute_sql(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(r[1]) for r in rows}


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    columns = _table_columns(table_name)
    if column_name in columns:
        return
    db.execute_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _apply_compat_migrations() -> None:
    _ensure_column("rpa_system_config", "sub_image_dir", "sub_image_dir TEXT NOT NULL DEFAULT ''")
    _ensure_column(
        "rpa_system_config",
        "fullscreen_screenshot_dir",
        "fullscreen_screenshot_dir TEXT NOT NULL DEFAULT ''",
    )
    _ensure_column("rpa_workflow", "global_object_config_id", "global_object_config_id INTEGER")
    _ensure_column("rpa_workflow_run", "idempotency_key", "idempotency_key VARCHAR(128)")
    _ensure_column("rpa_workflow_run", "attempt", "attempt INTEGER NOT NULL DEFAULT 0")
    _ensure_column("rpa_workflow_run", "locked_by", "locked_by VARCHAR(64)")
    _ensure_column("rpa_workflow_run", "lock_until", "lock_until DATETIME")
    _ensure_column("rpa_workflow_run", "cancelled", "cancelled INTEGER NOT NULL DEFAULT 0")
    _ensure_column("rpa_workflow_run_node", "last_error", "last_error TEXT")
