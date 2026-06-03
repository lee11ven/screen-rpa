from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.db import models


def list_configs(q: str | None = None) -> list[dict[str, Any]]:
    query = models.GlobalObjectConfig.select().order_by(models.GlobalObjectConfig.updated_at.desc())
    if q:
        qq = q.strip()
        if qq:
            query = query.where(models.GlobalObjectConfig.name.contains(qq))
    items: list[dict[str, Any]] = []
    for row in query:
        items.append(
            {
                "id": int(row.id),
                "name": row.name,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return items


def create_config(name: str, config: dict[str, Any]) -> models.GlobalObjectConfig:
    return models.GlobalObjectConfig.create(
        name=name.strip(),
        config_json=json.dumps(config, ensure_ascii=False),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def get_config(config_id: int) -> models.GlobalObjectConfig:
    return models.GlobalObjectConfig.get(models.GlobalObjectConfig.id == int(config_id))


def update_config(config_id: int, name: str | None = None, config: dict[str, Any] | None = None) -> models.GlobalObjectConfig:
    row = get_config(config_id)
    if name is not None:
        row.name = name.strip()
    if config is not None:
        row.config_json = json.dumps(config, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    row.save()
    return row


def delete_config(config_id: int) -> None:
    row = get_config(config_id)
    used = models.Workflow.select().where(models.Workflow.global_object_config == row).count()
    if used > 0:
        raise ValueError("config is referenced by workflows")
    row.delete_instance()


def parse_config_value(row: models.GlobalObjectConfig) -> dict[str, Any]:
    try:
        val = json.loads(row.config_json or "{}")
    except json.JSONDecodeError:
        val = {}
    if not isinstance(val, dict):
        return {}
    return val
