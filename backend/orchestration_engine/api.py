from __future__ import annotations

from typing import Any, Callable

from .engine import DefaultLowcodeRuntime, RuntimeExecutor
from .ports import ActionExecutorPort, LowcodeRuntimePort, WorkflowDefinitionPort
from .types import ExecutorHooks
from .validation import validate_runtime


class OrchestrationEngine:
    def __init__(
        self,
        definition_port: WorkflowDefinitionPort,
        action_port: ActionExecutorPort | None = None,
        lowcode_runtime: LowcodeRuntimePort | None = None,
    ) -> None:
        self.definition_port = definition_port
        self.action_port = action_port
        self.lowcode_runtime = lowcode_runtime or DefaultLowcodeRuntime()

    def validate_runtime(self, runtime: dict[str, Any]) -> list[dict[str, Any]]:
        return validate_runtime(runtime)

    def create_executor(
        self,
        runtime: dict[str, Any],
        input_obj: dict[str, Any],
        hooks: ExecutorHooks | None = None,
        services: dict[str, Any] | None = None,
        initial_ctx: dict[str, Any] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> RuntimeExecutor:
        return RuntimeExecutor(
            runtime=runtime,
            input_obj=input_obj,
            hooks=hooks,
            definition_port=self.definition_port,
            action_port=self.action_port,
            lowcode_runtime=self.lowcode_runtime,
            services=services,
            initial_ctx=initial_ctx,
            cancel_requested=cancel_requested,
        )
