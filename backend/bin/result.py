from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandError(Exception):
    code: str
    message: str
    data: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


def ok(data: dict[str, Any] | None = None, message: str = "OK") -> dict[str, Any]:
    return {"success": True, "code": "OK", "message": message, "data": data or {}}

