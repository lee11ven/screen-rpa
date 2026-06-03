from __future__ import annotations

import orchestration_engine.engine as engine_module
from orchestration_engine.api import OrchestrationEngine
from orchestration_engine.engine import DefaultLowcodeRuntime


class StubDefinitionPort:
    def load_published_runtime(self, workflow_id: str, version: int | None = None) -> dict:
        return {
            "workflow_id": workflow_id,
            "name": workflow_id,
            "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
            "nodes": [
                {"id": "start_1", "type": "start", "name": "开始", "config": {}},
                {"id": "end_1", "type": "end", "name": "结束", "config": {}},
            ],
            "edges": [{"from": "start_1", "to": "end_1"}],
        }


def test_validate_action_requires_action_key() -> None:
    engine = OrchestrationEngine(definition_port=StubDefinitionPort())
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {"id": "action_1", "type": "action", "name": "动作", "config": {}},
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    errors = engine.validate_runtime(runtime)
    assert any("action 节点必须配置 action_key" in str(e["message"]) for e in errors)


class StubActionPort:
    def execute(self, action_key: str, params: dict) -> dict:
        return {"success": True, "code": "OK", "message": action_key, "data": params}


class FailThenSuccessActionPort:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def execute(self, action_key: str, params: dict) -> dict:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("temporary failure")
        return {"success": True, "code": "OK", "message": action_key, "data": params}


def test_action_node_executes_with_rendered_params() -> None:
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), action_port=StubActionPort())
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "action_1",
                "type": "action",
                "name": "动作",
                "config": {"action_key": "system.exec_command", "params": {"command": "${input.cmd}", "timeout_ms": "1200"}},
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={"cmd": "echo hello"})
    executor.run()
    node_result = executor.node_results["action_1"]
    assert node_result["success"] is True
    assert node_result["message"] == "system.exec_command"
    assert node_result["data"]["command"] == "echo hello"
    assert node_result["data"]["timeout_ms"] == 1200


def test_action_node_supports_bare_ctx_path_value() -> None:
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), action_port=StubActionPort())
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "action_1",
                "type": "action",
                "name": "动作",
                "config": {"action_key": "system.keyboard_type_text", "params": {"text": "ctx.ip"}},
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={}, initial_ctx={"ip": "10.0.0.8"})
    executor.run()
    node_result = executor.node_results["action_1"]
    assert node_result["success"] is True
    assert node_result["data"]["text"] == "10.0.0.8"


def test_lowcode_new_signature_run_context_services() -> None:
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), lowcode_runtime=DefaultLowcodeRuntime())
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "low_1",
                "type": "lowcode_function",
                "name": "低代码",
                "config": {"code_body": "ctx['x']=services['value']\nreturn {'ok': True, 'data': ctx['x']}"},
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "low_1"}, {"from": "low_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={}, services={"value": 7})
    executor.run()
    assert executor.ctx["x"] == 7
    assert executor.node_results["low_1"]["data"] == 7


def test_action_node_applies_post_delay_ms(monkeypatch) -> None:
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(engine_module.time, "sleep", fake_sleep)
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), action_port=StubActionPort())
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "action_1",
                "type": "action",
                "name": "动作",
                "config": {
                    "action_key": "system.exec_command",
                    "params": {"command": "echo hello"},
                    "post_delay_ms": 120,
                    "jitter_ms": 0,
                },
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={})
    executor.run()
    assert sleep_calls
    assert sleep_calls[-1] == 0.12


def test_action_node_retries_then_succeeds() -> None:
    action_port = FailThenSuccessActionPort(fail_times=1)
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), action_port=action_port)
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "action_1",
                "type": "action",
                "name": "动作",
                "config": {
                    "action_key": "system.exec_command",
                    "params": {"command": "echo hello"},
                    "retry_times": 2,
                    "retry_interval_ms": 0,
                    "success_condition": {"kind": "none", "params": {}},
                },
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={})
    executor.run()
    assert action_port.calls == 2
    assert executor.node_results["action_1"]["success"] is True


def test_action_node_skip_on_error_when_retries_exhausted() -> None:
    action_port = FailThenSuccessActionPort(fail_times=10)
    engine = OrchestrationEngine(definition_port=StubDefinitionPort(), action_port=action_port)
    runtime = {
        "workflow_id": "wf_test",
        "name": "t",
        "settings": {"default_timeout_sec": 10, "max_retries": 0, "max_loop_iterations": 5},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "action_1",
                "type": "action",
                "name": "动作",
                "config": {"action_key": "system.exec_command", "params": {"command": "echo hello"}, "retry_times": 1, "success_condition": {"kind": "none", "params": {}}},
                "on_error": "skip",
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}],
    }
    executor = engine.create_executor(runtime=runtime, input_obj={})
    executor.run()
    assert executor.node_results["action_1"]["code"] == "SKIPPED"
