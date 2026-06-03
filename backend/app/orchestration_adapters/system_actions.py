from __future__ import annotations

import random
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from bin import execute_event
from bin.result import CommandError
from app.services import system_config_service


class ActionExecutionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


_PATH_CONTROL_CHARS = dict.fromkeys(map(ord, "\u202a\u202b\u202c\u202d\u202e\ufeff"), None)
SUPPORTED_SYSTEM_ACTION_KEYS = {
    "system.mouse_move",
    "system.mouse_click",
    "system.mouse_drag",
    "system.mouse_scroll",
    "system.mouse_smartclick",
    "system.keyboard_type_text",
    "system.keyboard_press_key",
    "system.keyboard_hotkey",
    "system.keyboard_hotkey_physical",
    "system.image_locate_center",
    "system.image_click_center",
    "system.window_find",
    "system.window_activate",
    "system.clipboard_set_text",
    "system.clipboard_get_text",
    "system.exec_command",
    "system.ocr_check_text",
}


def is_supported_system_action_key(action_key: Any) -> bool:
    return str(action_key or "").strip() in SUPPORTED_SYSTEM_ACTION_KEYS


def _sanitize_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.translate(_PATH_CONTROL_CHARS)
    return text.strip().strip('"').strip("'")


def _build_screenshot_output_path(filename: str) -> Path:
    system_cfg = system_config_service.get_system_config()
    configured_dir = str(system_cfg.get("fullscreen_screenshot_dir", "")).strip()
    if configured_dir:
        base = Path(configured_dir).expanduser()
        base.mkdir(parents=True, exist_ok=True)
        return (base / filename).resolve()
    tmp = tempfile.NamedTemporaryFile(prefix="rpa_page_", suffix=".png", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    return tmp_path.resolve()


def _capture_page_to_temp() -> str:
    filename = f"rpa_page_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    path = str(_build_screenshot_output_path(filename))
    execute_event(None, "screenshot", {"output": path})
    return path


def _locate_center(template_path: str, threshold: float, page_path: str | None = None) -> dict[str, Any]:
    clean_template = _sanitize_path(template_path)
    if not clean_template:
        raise ActionExecutionError("SYS1001", "template_path is required")
    resolved_page = _sanitize_path(page_path) or _capture_page_to_temp()
    located = execute_event(
        "getxy",
        "match",
        {"page": resolved_page, "sub": clean_template, "threshold": float(threshold)},
    )
    data = located.get("data", {})
    if not data.get("found"):
        raise ActionExecutionError("SYS1002", "target not found")
    center = data.get("center") or {}
    return {"x": int(center.get("x", 0)), "y": int(center.get("y", 0)), "page_path": resolved_page}


def _to_ms(value: Any, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return value if isinstance(value, str) else str(value)


def _resolve_keyboard_text(params: dict[str, Any]) -> str:
    text_source = str(params.get("text_source", "literal")).strip().lower()
    if text_source == "global_var":
        return _to_text(params.get("text_var_key"), "")
    return _to_text(params.get("text"), "")


def _resolve_xy_with_pre(
    params: dict[str, Any],
    *,
    x_key: str = "x",
    y_key: str = "y",
    template_key: str = "pre_template_path",
    threshold_key: str = "pre_threshold",
    use_center_key: str = "pre_use_center_xy",
) -> tuple[int, int]:
    x = int(params.get(x_key, 0))
    y = int(params.get(y_key, 0))
    pre_template = _to_text(params.get(template_key), "").strip()
    if pre_template and _to_bool(params.get(use_center_key), False):
        pre_page_path_key = template_key.replace("template_path", "page_path")
        pre_page_path = _to_text(params.get(pre_page_path_key), "").strip() or None
        located = _locate_center(pre_template, float(params.get(threshold_key, 0.85)), pre_page_path)
        x = int(located["x"])
        y = int(located["y"])
    return x, y


def _run_window_find(params: dict[str, Any]) -> dict[str, Any]:
    timeout_ms = max(0, _to_ms(params.get("timeout_ms"), 0))
    poll_interval_ms = max(50, _to_ms(params.get("poll_interval_ms"), 150))
    started = time.perf_counter()
    while True:
        result = execute_event(
            "process",
            "window_find",
            {
                "title": _to_text(params.get("title"), ""),
                "process_name": _to_text(params.get("process_name"), ""),
                "class_name": _to_text(params.get("class_name"), ""),
            },
        )
        data = result.get("data") or {}
        if bool(data.get("found", False)) or timeout_ms <= 0:
            return result
        elapsed = int((time.perf_counter() - started) * 1000)
        if elapsed >= timeout_ms:
            return result
        time.sleep(poll_interval_ms / 1000.0)


def _focus_before_keyboard_action(params: dict[str, Any]) -> None:
    pre_template = _to_text(params.get("pre_template_path"), "").strip()
    if not pre_template or not _to_bool(params.get("pre_use_center_xy"), False):
        return
    x, y = _resolve_xy_with_pre(params)
    execute_event("mouse", "subclick", {"x": x, "y": y, "button": "left", "clicks": 1, "interval": 0})


def _normalize_for_compare(text: str, *, ignore_case: bool, ignore_spaces: bool) -> str:
    normalized = text
    if ignore_spaces:
        normalized = "".join(normalized.split())
    if ignore_case:
        normalized = normalized.lower()
    return normalized


def _run_ocr_check_text(params: dict[str, Any]) -> dict[str, Any]:
    expected_text = _to_text(params.get("expected_text"), "").strip()
    if not expected_text:
        raise ActionExecutionError("SYS1001", "expected_text is required")
    page_path = _sanitize_path(params.get("page_path"))
    if not page_path:
        page_path = _capture_page_to_temp()
    ignore_case = _to_bool(params.get("ignore_case"), False)
    ignore_spaces = _to_bool(params.get("ignore_spaces"), True)
    contains = _to_bool(params.get("contains"), True)
    min_confidence = float(params.get("min_confidence", 0.5))
    ocr_out = execute_event(
        "ocr",
        "recognize",
        {"page": page_path, "min_confidence": min_confidence},
    )
    lines = (ocr_out.get("data") or {}).get("lines") or []
    expected_normalized = _normalize_for_compare(expected_text, ignore_case=ignore_case, ignore_spaces=ignore_spaces)
    matched_line: dict[str, Any] | None = None
    for line in lines:
        text = _to_text((line or {}).get("text"), "")
        candidate = _normalize_for_compare(text, ignore_case=ignore_case, ignore_spaces=ignore_spaces)
        is_match = expected_normalized in candidate if contains else candidate == expected_normalized
        if is_match:
            matched_line = line
            break
    if matched_line is None:
        raise ActionExecutionError("SYS1002", f"ocr expected text not found: {expected_text}")
    return {
        "success": True,
        "code": "OK",
        "message": "OK",
        "data": {
            "page_path": page_path,
            "expected_text": expected_text,
            "contains": contains,
            "ignore_case": ignore_case,
            "ignore_spaces": ignore_spaces,
            "matched": True,
            "matched_text": _to_text(matched_line.get("text"), ""),
            "confidence": float(matched_line.get("confidence", 0.0)),
            "line": matched_line,
        },
    }


def run_system_action(action_key: str, params: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if action_key == "system.mouse_move":
            x, y = _resolve_xy_with_pre(params)
            if _to_bool(params.get("relative"), False):
                pos = execute_event("mouse", "position", {})
                pos_data = pos.get("data") or {}
                x += int(pos_data.get("x", 0))
                y += int(pos_data.get("y", 0))
            result = execute_event("mouse", "move", {"x": x, "y": y, "move_duration": _to_ms(params.get("duration_ms"), 200)})
        elif action_key == "system.mouse_click":
            x, y = _resolve_xy_with_pre(params)
            result = execute_event(
                "mouse",
                "subclick",
                {"x": x, "y": y, "clicks": int(params.get("clicks", 1)), "button": params.get("button", "left"), "interval": _to_ms(params.get("interval_ms"), 0)},
            )
        elif action_key == "system.mouse_drag":
            start_x, start_y = _resolve_xy_with_pre(
                params,
                x_key="start_x",
                y_key="start_y",
                template_key="pre_start_template_path",
                threshold_key="pre_start_threshold",
                use_center_key="pre_start_use_center_xy",
            )
            end_x, end_y = _resolve_xy_with_pre(
                params,
                x_key="end_x",
                y_key="end_y",
                template_key="pre_end_template_path",
                threshold_key="pre_end_threshold",
                use_center_key="pre_end_use_center_xy",
            )
            jitter_px = max(0, int(params.get("jitter_px", 0)))
            if jitter_px > 0:
                end_x += random.randint(-jitter_px, jitter_px)
                end_y += random.randint(-jitter_px, jitter_px)
            result = execute_event(
                "mouse",
                "drag",
                {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y, "duration": _to_ms(params.get("duration_ms"), 500), "button": params.get("button", "left")},
            )
        elif action_key == "system.mouse_scroll":
            x, y = _resolve_xy_with_pre(params)
            result = execute_event("mouse", "scroll", {"amount": int(params.get("delta", params.get("amount", 3))), "x": x, "y": y})
        elif action_key == "system.mouse_smartclick":
            target_sub = str(params.get("target_sub", "")).strip()
            located = _locate_center(target_sub, float(params.get("threshold", 0.85)))
            result = execute_event("mouse", "subclick", {"x": located["x"], "y": located["y"], "button": params.get("button", "left")})
        elif action_key == "system.keyboard_type_text":
            _focus_before_keyboard_action(params)
            result = execute_event(
                "keyboard",
                "type",
                {
                    "text": _resolve_keyboard_text(params),
                    "interval": _to_ms(params.get("interval_ms"), 0),
                    "use_clipboard": _to_bool(params.get("use_clipboard"), True),
                },
            )
        elif action_key == "system.keyboard_press_key":
            _focus_before_keyboard_action(params)
            result = execute_event(
                "keyboard",
                "press",
                {"key": params.get("key", "enter"), "interval": _to_ms(params.get("hold_ms"), 0), "presses": 1, "disable_failsafe": _to_bool(params.get("disable_failsafe"), True)},
            )
        elif action_key in ("system.keyboard_hotkey", "system.keyboard_hotkey_physical"):
            _focus_before_keyboard_action(params)
            function = "hotkey_physical" if action_key.endswith("physical") else "hotkey"
            payload = {"keys": params.get("keys", []), "disable_failsafe": _to_bool(params.get("disable_failsafe"), True)}
            if function == "hotkey":
                payload["delay"] = _to_ms(params.get("hold_ms"), 0)
            else:
                payload["modifier_down_gap_ms"] = _to_ms(params.get("modifier_down_gap_ms"), 30)
                payload["main_key_hold_ms"] = _to_ms(params.get("main_key_hold_ms"), 50)
                payload["release_gap_ms"] = _to_ms(params.get("release_gap_ms"), 20)
            result = execute_event("keyboard", function, payload)
            post_delay_ms = _to_ms(params.get("post_delay_ms"), 0)
            if post_delay_ms > 0:
                time.sleep(post_delay_ms / 1000.0)
        elif action_key == "system.image_locate_center":
            result = {"success": True, "code": "OK", "message": "OK", "data": _locate_center(str(params.get("template_path", "")), float(params.get("threshold", 0.85)), str(params.get("page_path", "")).strip() or None)}
        elif action_key == "system.image_click_center":
            located = _locate_center(str(params.get("template_path", "")), float(params.get("threshold", 0.85)))
            result = execute_event("mouse", "subclick", {"x": located["x"], "y": located["y"], "button": params.get("button", "left"), "clicks": int(params.get("clicks", 1)), "interval": _to_ms(params.get("interval_ms"), 0)})
        elif action_key == "system.window_find":
            result = _run_window_find(params)
        elif action_key == "system.window_activate":
            result = execute_event("process", "window_activate", params)
        elif action_key == "system.clipboard_set_text":
            result = execute_event("clipboard", "set_text", {"text": _to_text(params.get("text"), "")})
        elif action_key == "system.clipboard_get_text":
            result = execute_event("clipboard", "get_text", {})
        elif action_key == "system.exec_command":
            result = execute_event("exec", "run", params)
        elif action_key == "system.ocr_check_text":
            result = _run_ocr_check_text(params)
        else:
            raise ActionExecutionError("SYS1001", f"unsupported action_key: {action_key}")
    except CommandError as ex:
        raise ActionExecutionError(ex.code, ex.message) from ex
    except ActionExecutionError:
        raise
    except Exception as ex:  # noqa: BLE001
        raise ActionExecutionError("SYS1999", str(ex)) from ex
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {"success": bool(result.get("success", False)), "code": result.get("code", "OK"), "message": result.get("message", "OK"), "data": result.get("data", {}), "duration_ms": duration_ms}
