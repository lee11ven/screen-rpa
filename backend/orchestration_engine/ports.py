from __future__ import annotations

from typing import Any, Protocol


class ActionExecutorPort(Protocol):
    def execute(self, action_key: str, params: dict[str, Any]) -> dict[str, Any]:
        ...


class WorkflowDefinitionPort(Protocol):
    def load_published_runtime(self, workflow_id: str, version: int | None = None) -> dict[str, Any]:
        ...


class LowcodeRuntimePort(Protocol):
    def run(self, code_body: str, context: dict[str, Any], services: dict[str, Any], timeout_ms: int) -> Any:
        ...
