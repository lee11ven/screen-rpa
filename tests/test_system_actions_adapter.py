from __future__ import annotations

from app.orchestration_adapters import system_actions


def test_keyboard_type_text_uses_global_var_text_key(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_execute_event(domain, action, payload):
        captured["domain"] = domain
        captured["action"] = action
        captured["payload"] = payload
        return {"success": True, "code": "OK", "message": "OK", "data": {}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)

    out = system_actions.run_system_action(
        "system.keyboard_type_text",
        {
            "text_source": "global_var",
            "text_var_key": "10.0.0.8",
            "interval_ms": 30,
            "use_clipboard": True,
        },
    )

    assert out["success"] is True
    assert captured["domain"] == "keyboard"
    assert captured["action"] == "type"
    assert captured["payload"] == {"text": "10.0.0.8", "interval": 30, "use_clipboard": True}


def test_mouse_click_uses_pre_located_center(monkeypatch) -> None:
    calls: list[tuple[object, object, object]] = []

    def fake_execute_event(domain, action, payload):
        calls.append((domain, action, payload))
        if action == "match":
            return {"success": True, "code": "OK", "message": "OK", "data": {"found": True, "center": {"x": 321, "y": 654}}}
        return {"success": True, "code": "OK", "message": "OK", "data": {}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)
    out = system_actions.run_system_action(
        "system.mouse_click",
        {"pre_template_path": "a.png", "pre_page_path": "page.png", "pre_use_center_xy": True, "pre_threshold": 0.8, "x": 1, "y": 2, "interval_ms": 10},
    )
    assert out["success"] is True
    assert calls[-1] == ("mouse", "subclick", {"x": 321, "y": 654, "clicks": 1, "button": "left", "interval": 10})


def test_keyboard_hotkey_physical_maps_timing_and_post_delay(monkeypatch) -> None:
    calls: list[tuple[object, object, object]] = []
    sleep_calls: list[float] = []

    def fake_execute_event(domain, action, payload):
        calls.append((domain, action, payload))
        return {"success": True, "code": "OK", "message": "OK", "data": {}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)
    monkeypatch.setattr(system_actions.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    out = system_actions.run_system_action(
        "system.keyboard_hotkey_physical",
        {
            "keys": ["win", "r"],
            "modifier_down_gap_ms": 11,
            "main_key_hold_ms": 22,
            "release_gap_ms": 33,
            "disable_failsafe": False,
            "post_delay_ms": 120,
        },
    )
    assert out["success"] is True
    assert calls[-1] == (
        "keyboard",
        "hotkey_physical",
        {"keys": ["win", "r"], "disable_failsafe": False, "modifier_down_gap_ms": 11, "main_key_hold_ms": 22, "release_gap_ms": 33},
    )
    assert sleep_calls and sleep_calls[-1] == 0.12


def test_window_find_retries_until_timeout(monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_execute_event(domain, action, payload):
        attempts["count"] += 1
        found = attempts["count"] >= 2
        return {"success": True, "code": "OK", "message": "OK", "data": {"found": found}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)
    monkeypatch.setattr(system_actions.time, "sleep", lambda _seconds: None)
    out = system_actions.run_system_action(
        "system.window_find",
        {"title": "test", "timeout_ms": 300, "poll_interval_ms": 50},
    )
    assert out["success"] is True
    assert attempts["count"] >= 2


def test_ocr_check_text_matches_expected_order_no(monkeypatch) -> None:
    calls: list[tuple[object, object, object]] = []

    def fake_execute_event(domain, action, payload):
        calls.append((domain, action, payload))
        if action == "screenshot":
            return {"success": True, "code": "OK", "message": "OK", "data": {"output": payload.get("output", "")}}
        if domain == "ocr" and action == "recognize":
            return {
                "success": True,
                "code": "OK",
                "message": "OK",
                "data": {"lines": [{"text": "订单号: SO-20260425-001", "confidence": 0.98}]},
            }
        return {"success": True, "code": "OK", "message": "OK", "data": {}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)
    monkeypatch.setattr(system_actions, "_capture_page_to_temp", lambda: "captured.png")
    out = system_actions.run_system_action(
        "system.ocr_check_text",
        {"expected_text": "SO-20260425-001", "contains": True, "ignore_spaces": True, "min_confidence": 0.3},
    )
    assert out["success"] is True
    assert out["data"]["matched"] is True
    assert out["data"]["matched_text"] == "订单号: SO-20260425-001"
    assert ("ocr", "recognize", {"page": "captured.png", "min_confidence": 0.3}) in calls


def test_ocr_check_text_raises_when_order_no_missing(monkeypatch) -> None:
    def fake_execute_event(domain, action, payload):
        if domain == "ocr" and action == "recognize":
            return {"success": True, "code": "OK", "message": "OK", "data": {"lines": [{"text": "订单号: SO-OTHER", "confidence": 0.98}]}}
        return {"success": True, "code": "OK", "message": "OK", "data": {}}

    monkeypatch.setattr(system_actions, "execute_event", fake_execute_event)
    monkeypatch.setattr(system_actions, "_capture_page_to_temp", lambda: "captured.png")
    try:
        system_actions.run_system_action(
            "system.ocr_check_text",
            {"expected_text": "SO-20260425-001", "contains": False},
        )
    except system_actions.ActionExecutionError as exc:
        assert exc.code == "SYS1002"
        assert "ocr expected text not found" in exc.message
    else:
        raise AssertionError("expected ActionExecutionError")
