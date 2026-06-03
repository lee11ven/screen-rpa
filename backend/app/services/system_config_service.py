from __future__ import annotations

import unicodedata
from datetime import datetime

from app.db import models


def get_or_create_system_config() -> models.SystemConfig:
    row = models.SystemConfig.select().order_by(models.SystemConfig.id.asc()).first()
    if row:
        return row
    return models.SystemConfig.create(
        sub_image_dir="",
        fullscreen_screenshot_dir="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _normalize_dir_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # Remove invisible control/format chars (e.g. U+202A) often introduced when copying paths.
    return "".join(ch for ch in text if unicodedata.category(ch) not in {"Cc", "Cf"}).strip()


def get_system_config() -> dict[str, str]:
    row = get_or_create_system_config()
    return {
        "sub_image_dir": _normalize_dir_path(row.sub_image_dir),
        "fullscreen_screenshot_dir": _normalize_dir_path(row.fullscreen_screenshot_dir),
    }


def update_system_config(
    *,
    sub_image_dir: str | None = None,
    fullscreen_screenshot_dir: str | None = None,
) -> dict[str, str]:
    row = get_or_create_system_config()
    if sub_image_dir is not None:
        row.sub_image_dir = _normalize_dir_path(sub_image_dir)
    if fullscreen_screenshot_dir is not None:
        row.fullscreen_screenshot_dir = _normalize_dir_path(fullscreen_screenshot_dir)
    row.updated_at = datetime.utcnow()
    row.save()
    return {
        "sub_image_dir": row.sub_image_dir or "",
        "fullscreen_screenshot_dir": row.fullscreen_screenshot_dir or "",
    }
