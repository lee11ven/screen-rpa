from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import models
from app.db.database import db, init_db
from app.main import app
from app.services import workflow_run_service

_API = "/api/workflow"


def _global_config_id(c: TestClient) -> int:
    name = f"gc-test-{uuid.uuid4().hex[:10]}"
    r = c.post(f"{_API}/global-config/create", json={"name": name, "config": {}})
    assert r.status_code == 200, r.text
    return int(r.json()["data"]["id"])


def test_workflow_list() -> None:
    init_db()
    c = TestClient(app)
    gcid = _global_config_id(c)
    r = c.post(
        f"{_API}/create",
        json={"name": "list_me", "workflow_id": "wf_list_test", "global_object_config_id": gcid},
    )
    assert r.status_code == 200
    r2 = c.get(f"{_API}/list")
    assert r2.status_code == 200
    body = r2.json()
    assert body["success"] is True
    ids = {x["workflow_id"] for x in body["data"]["items"]}
    assert "wf_list_test" in ids


def test_create_publish_run_status() -> None:
    init_db()
    c = TestClient(app)
    gcid = _global_config_id(c)
    r = c.post(
        f"{_API}/create",
        json={"name": "t1", "workflow_id": "wf_api_test", "global_object_config_id": gcid},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["workflow_id"] = "wf_api_test"
    r2 = c.post(f"{_API}/update", json={"workflow_id": "wf_api_test", "draft_runtime": runtime})
    assert r2.status_code == 200

    r3 = c.post(f"{_API}/wf_api_test/publish")
    assert r3.status_code == 200, r3.text
    assert r3.json()["data"]["version"] == 1

    r4 = c.post(f"{_API}/wf_api_test/run", json={"input": {"order_id": "o1"}})
    assert r4.status_code == 200
    run_id = r4.json()["data"]["run_id"]

    with db:
        workflow_run_service.execute_run_sync(run_id)

    r5 = c.get(f"{_API}/run/{run_id}/status")
    assert r5.status_code == 200
    assert r5.json()["data"]["status"] == "SUCCESS"


def test_run_idempotency_key_reuses_existing_run() -> None:
    init_db()
    c = TestClient(app)
    gcid = _global_config_id(c)
    c.post(
        f"{_API}/create",
        json={"name": "idem", "workflow_id": "wf_api_idem", "global_object_config_id": gcid},
    )
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["workflow_id"] = "wf_api_idem"
    c.post(f"{_API}/update", json={"workflow_id": "wf_api_idem", "draft_runtime": runtime})
    c.post(f"{_API}/wf_api_idem/publish")

    body = {"input": {"x": 1}, "idempotency_key": "idem-key-1"}
    r1 = c.post(f"{_API}/wf_api_idem/run", json=body)
    r2 = c.post(f"{_API}/wf_api_idem/run", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["data"]["run_id"] == r2.json()["data"]["run_id"]


def test_run_cancel_endpoint() -> None:
    init_db()
    c = TestClient(app)
    gcid = _global_config_id(c)
    c.post(
        f"{_API}/create",
        json={"name": "cancel", "workflow_id": "wf_api_cancel", "global_object_config_id": gcid},
    )
    raw = Path(__file__).resolve().parents[1] / "contracts" / "examples" / "minimal-runtime.json"
    runtime = json.loads(raw.read_text(encoding="utf-8"))
    runtime["workflow_id"] = "wf_api_cancel"
    c.post(f"{_API}/update", json={"workflow_id": "wf_api_cancel", "draft_runtime": runtime})
    c.post(f"{_API}/wf_api_cancel/publish")
    run_resp = c.post(f"{_API}/wf_api_cancel/run", json={"input": {}})
    run_id = run_resp.json()["data"]["run_id"]

    cancel_resp = c.post(f"{_API}/run/{run_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["data"]["cancelled"] is True


def test_lowcode_workflow_validate_publish_run_success() -> None:
    init_db()
    c = TestClient(app)
    gcid = _global_config_id(c)
    c.post(
        f"{_API}/create",
        json={"name": "lowcode", "workflow_id": "wf_api_lowcode", "global_object_config_id": gcid},
    )
    cfg_update = c.post(
        f"{_API}/global-config/{gcid}/update",
        json={"name": "cfg-lowcode", "config": {"tenant": {"code": "t-001"}, "retry_limit": 3}},
    )
    assert cfg_update.status_code == 200
    runtime = {
        "workflow_id": "wf_api_lowcode",
        "name": "lowcode",
        "version": 0,
        "settings": {"default_timeout_sec": 60, "max_retries": 0, "max_loop_iterations": 1000},
        "nodes": [
            {"id": "start_1", "type": "start", "name": "开始", "config": {}},
            {
                "id": "low_1",
                "type": "lowcode_function",
                "name": "函数",
                "config": {
                    "code_body": (
                        "return {'ok': True, 'data': {"
                        "'order_id': context.get('order_id'),"
                        "'tenant_code': ((context.get('tenant') or {}).get('code')),"
                        "'retry_limit': context.get('retry_limit'),"
                        "'has_input_key': ('input' in context),"
                        "'has_vars_key': ('vars' in context),"
                        "'has_output_key': ('output' in context),"
                        "'has_meta_key': ('meta' in context)"
                        "}}"
                    ),
                    "timeout_ms": 3000,
                    "retry_times": 0,
                    "enabled": True,
                },
            },
            {"id": "end_1", "type": "end", "name": "结束", "config": {}},
        ],
        "edges": [{"from": "start_1", "to": "low_1"}, {"from": "low_1", "to": "end_1"}],
    }
    validate_resp = c.post(f"{_API}/validate", json={"runtime": runtime})
    assert validate_resp.status_code == 200
    assert validate_resp.json()["data"]["valid"] is True

    c.post(f"{_API}/update", json={"workflow_id": "wf_api_lowcode", "draft_runtime": runtime})
    publish_resp = c.post(f"{_API}/wf_api_lowcode/publish")
    assert publish_resp.status_code == 200

    run_resp = c.post(f"{_API}/wf_api_lowcode/run", json={"input": {"order_id": "oid-1"}})
    assert run_resp.status_code == 200
    run_id = run_resp.json()["data"]["run_id"]
    with db:
        workflow_run_service.execute_run_sync(run_id)
    status_resp = c.get(f"{_API}/run/{run_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "SUCCESS"
    logs_resp = c.get(f"{_API}/run/{run_id}/logs")
    assert logs_resp.status_code == 200
    with db:
        run = models.WorkflowRun.get(models.WorkflowRun.run_id == run_id)
    snap = json.loads(run.snapshot_json or "{}")
    low_data = ((snap.get("node_results") or {}).get("low_1") or {}).get("data") or {}
    assert low_data.get("order_id") == "oid-1"
    assert low_data.get("tenant_code") == "t-001"
    assert low_data.get("retry_limit") == 3
    assert low_data.get("has_input_key") is False
    assert low_data.get("has_vars_key") is False
    assert low_data.get("has_output_key") is False
    assert low_data.get("has_meta_key") is False
