from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "workflow-runtime.schema.json"
EXAMPLE_PATH = ROOT / "contracts" / "examples" / "minimal-runtime.json"


def test_minimal_runtime_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()
    assert EXAMPLE_PATH.is_file()


def test_lowcode_function_runtime_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = {
        "workflow_id": "wf_schema_lowcode",
        "name": "lowcode_schema",
        "version": 0,
        "settings": {"default_timeout_sec": 60, "max_retries": 0, "max_loop_iterations": 1000},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "start", "config": {}},
            {
                "id": "low_1",
                "type": "lowcode_function",
                "name": "low",
                "config": {
                    "code_body": "return {'ok': True}",
                    "timeout_ms": 3000,
                    "retry_times": 0,
                    "enabled": True,
                },
            },
            {"id": "end_1", "type": "end", "name": "end", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "low_1"}, {"from": "low_1", "to": "end_1"}],
    }
    jsonschema.validate(instance=instance, schema=schema)


def test_loop_container_runtime_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    instance = {
        "workflow_id": "wf_schema_loop",
        "name": "loop_schema",
        "version": 0,
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
                            {"id": "loop_start_1", "type": "loop_start", "name": "ls", "config": {}},
                            {"id": "continue_1", "type": "continue", "name": "ct", "config": {"sleep_ms": 0}},
                        ],
                        "edges": [{"from": "loop_start_1", "to": "continue_1"}],
                    },
                },
            },
            {"id": "end_1", "type": "end", "name": "end", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "loop_1"}, {"from": "loop_1", "to": "end_1"}],
    }
    jsonschema.validate(instance=instance, schema=schema)
