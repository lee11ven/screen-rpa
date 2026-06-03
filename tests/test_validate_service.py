from __future__ import annotations

import json
from pathlib import Path

from app.db.database import db, init_db
from app.services import workflow_definition_service, workflow_validate_service


def test_validate_minimal_example_ok() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert errs == []


def test_validate_rejects_two_starts() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["nodes"].append({"id": "start_2", "type": "start", "name": "x", "config": {}})
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert any("start" in e["message"] for e in errs)


def test_subflow_requires_published_child() -> None:
    init_db()
    with db:
        workflow_definition_service.create_workflow("parent", workflow_id="wf_parent")
        workflow_definition_service.create_workflow("child", workflow_id="wf_child")
        parent = json.loads(workflow_definition_service.get_workflow("wf_parent").draft_runtime_json)
        parent["nodes"].extend(
            [
                {
                    "id": "sf1",
                    "type": "subflow",
                    "name": "sub",
                    "config": {"workflow_id": "wf_child", "input_mapping": {}, "output_mapping": {}},
                }
            ]
        )
        parent["edges"] = [
            {"from": "start_1", "to": "sf1"},
            {"from": "sf1", "to": "end_1"},
        ]
        errs = workflow_validate_service.validate_runtime_dsl(parent)
        assert any("未发布" in e["message"] or "子流程" in e["message"] for e in errs)


def test_validate_rejects_unsupported_top_level_action_node() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["nodes"][1]["type"] = "action"
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert any("action 节点必须配置 action_key" in e["message"] for e in errs)


def test_validate_lowcode_function_compile_error() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["nodes"][1] = {
        "id": "low_1",
        "type": "lowcode_function",
        "name": "lowcode",
        "config": {
            "code_body": "if True print('x')",
            "timeout_ms": 3000,
            "retry_times": 0,
            "enabled": True,
        },
    }
    runtime["edges"] = [{"from": "start_1", "to": "low_1"}, {"from": "low_1", "to": "end_1"}]
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert any("CompileError" in e["message"] for e in errs)


def test_validate_lowcode_function_ok() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["nodes"][1] = {
        "id": "low_1",
        "type": "lowcode_function",
        "name": "lowcode",
        "config": {
            "code_body": "return {'ok': True, 'data': {'v': 1}}",
            "timeout_ms": 3000,
            "retry_times": 0,
            "enabled": True,
        },
    }
    runtime["edges"] = [{"from": "start_1", "to": "low_1"}, {"from": "low_1", "to": "end_1"}]
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert errs == []


def test_validate_loop_container_ok() -> None:
    init_db()
    runtime = {
        "workflow_id": "wf_loop_ok",
        "name": "loop",
        "settings": {"default_timeout_sec": 60, "max_retries": 0, "max_loop_iterations": 1000},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "start", "config": {}},
            {
                "id": "loop_1",
                "type": "loop-container",
                "name": "loop",
                "config": {
                    "loopId": "loop_1",
                    "maxIterations": 5,
                    "subGraph": {
                        "nodes": [
                            {"id": "ls", "type": "loop_start", "name": "ls", "config": {}},
                            {"id": "ct", "type": "continue", "name": "ct", "config": {"sleep_ms": 0}},
                        ],
                        "edges": [{"from": "ls", "to": "ct"}],
                    },
                },
            },
            {"id": "end_1", "type": "end", "name": "end", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "loop_1"}, {"from": "loop_1", "to": "end_1"}],
    }
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert errs == []


def test_validate_rejects_top_level_continue() -> None:
    init_db()
    runtime = {
        "workflow_id": "wf_loop_bad",
        "name": "loop",
        "settings": {"default_timeout_sec": 60, "max_retries": 0, "max_loop_iterations": 1000},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "start", "config": {}},
            {"id": "ct", "type": "continue", "name": "ct", "config": {"sleep_ms": 0}},
            {"id": "end_1", "type": "end", "name": "end", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "ct"}, {"from": "ct", "to": "end_1"}],
    }
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert any("不支持的节点类型" in e["message"] for e in errs)


def test_validate_rejects_negative_action_timeout() -> None:
    init_db()
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["nodes"][1] = {
        "id": "action_1",
        "type": "action",
        "name": "动作",
        "config": {"action_key": "system.mouse_click", "params": {"x": 1, "y": 2}, "timeout_ms": -1},
    }
    runtime["edges"] = [{"from": "start_1", "to": "action_1"}, {"from": "action_1", "to": "end_1"}]
    with db:
        errs = workflow_validate_service.validate_runtime_dsl(runtime)
    assert any("timeout_ms 必须是非负整数" in e["message"] for e in errs)
