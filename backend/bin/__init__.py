from __future__ import annotations

from typing import Any

__all__ = ["execute_event"]


def execute_event(event: str | None, function: str, params: dict[str, Any]) -> dict[str, Any]:
    # Lazy import avoids runtime warning when running `python -m bin.index`.
    from .index import execute_event as _execute_event

    return _execute_event(event, function, params)
