from __future__ import annotations

from typing import Any

from orchestration_engine import OrchestrationEngine

from .action_port import BinActionPort
from .definition_port import PeeweeDefinitionPort
from .system_actions import is_supported_system_action_key, run_system_action


class AppOrchestrationEngine(OrchestrationEngine):
    def create_executor(
        self,
        runtime: dict[str, Any],
        input_obj: dict[str, Any],
        hooks: Any = None,
        services: dict[str, Any] | None = None,
        initial_ctx: dict[str, Any] | None = None,
        cancel_requested: Any = None,
    ):
        merged_services: dict[str, Any] = {
            "run_system_action": run_system_action,
            "is_supported_system_action_key": is_supported_system_action_key,
        }
        if services:
            merged_services.update(services)
        return super().create_executor(
            runtime=runtime,
            input_obj=input_obj,
            hooks=hooks,
            services=merged_services,
            initial_ctx=initial_ctx,
            cancel_requested=cancel_requested,
        )


def build_engine() -> OrchestrationEngine:
    return AppOrchestrationEngine(
        definition_port=PeeweeDefinitionPort(),
        action_port=BinActionPort(),
    )
