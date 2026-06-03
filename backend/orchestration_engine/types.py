from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ExecutorHooks:
    on_log: Callable[[str, str | None, str, dict[str, Any]], None] | None = None
    on_node_start: Callable[[str], None] | None = None
    on_node_finish: Callable[[str, str, str | None], None] | None = None


ALLOWED_TOP_LEVEL_NODE_TYPES = {"start", "end", "action", "if", "loop-container", "subflow", "wait", "lowcode_function"}
ALLOWED_LOOP_NODE_TYPES = {"continue", "break", "action", "if", "subflow", "wait", "lowcode_function", "loop_start"}
