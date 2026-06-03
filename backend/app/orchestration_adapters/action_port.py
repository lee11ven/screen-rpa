from __future__ import annotations

from typing import Any

from app.orchestration_adapters.system_actions import run_system_action


class BinActionPort:
    def execute(self, action_key: str, params: dict[str, Any]) -> dict[str, Any]:
        return run_system_action(action_key, params)
