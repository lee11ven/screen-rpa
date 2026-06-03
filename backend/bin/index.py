from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import sys
from typing import Any

from . import clipboard, exec_command, getxy, keyboard, mouse, ocr, process, screenshot
from .result import CommandError


@contextlib.contextmanager
def _silence_process_stdio():
    """Temporarily silence fd-level stdout/stderr (for noisy native libs)."""
    out_fd = sys.stdout.fileno()
    err_fd = sys.stderr.fileno()
    saved_out = os.dup(out_fd)
    saved_err = os.dup(err_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull_fd, out_fd)
        os.dup2(devnull_fd, err_fd)
        yield
    finally:
        os.dup2(saved_out, out_fd)
        os.dup2(saved_err, err_fd)
        os.close(saved_out)
        os.close(saved_err)
        os.close(devnull_fd)


def execute_event(event: str | None, function: str, params: dict[str, Any]) -> dict[str, Any]:
    evt = (event or "").strip().lower()
    fn = function.strip()
    if not evt:
        return screenshot.handle(fn, params)
    if evt == "mouse":
        return mouse.handle(fn, params)
    if evt == "keyboard":
        return keyboard.handle(fn, params)
    if evt == "getxy":
        return getxy.handle(fn, params)
    if evt == "process":
        return process.handle(fn, params)
    if evt == "ocr":
        return ocr.handle(fn, params)
    if evt == "clipboard":
        return clipboard.handle(fn, params)
    if evt == "exec":
        return exec_command.handle(params)
    raise CommandError("SYS1001", f"unsupported event: {event}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="screen-rpa system operation cli")
    parser.add_argument("--event", type=str, default="")
    parser.add_argument("--function", "-f", type=str, required=True)
    parser.add_argument("--params", type=str, default="{}")
    return parser


def _parse_params(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError) as ex:
            try:
                parsed = _parse_relaxed_object(raw)
            except ValueError as relaxed_ex:
                raise CommandError("SYS1001", f"invalid params json: {relaxed_ex}") from ex
    if not isinstance(parsed, dict):
        raise CommandError("SYS1001", "params must be a JSON object")
    return parsed


def _split_top_level(raw: str, sep: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    depth = 0
    in_quote = False
    quote_char = ""
    i = 0
    while i < len(raw):
        ch = raw[i]
        if in_quote:
            cur.append(ch)
            if ch == quote_char and (i == 0 or raw[i - 1] != "\\"):
                in_quote = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_quote = True
            quote_char = ch
            cur.append(ch)
            i += 1
            continue
        if ch in ("[", "{"):
            depth += 1
        elif ch in ("]", "}"):
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    tail = "".join(cur).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_relaxed_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null":
        return None
    if s.startswith("[") and s.endswith("]"):
        body = s[1:-1].strip()
        if not body:
            return []
        return [_parse_relaxed_scalar(x) for x in _split_top_level(body, ",")]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_relaxed_object(raw: str) -> dict[str, Any]:
    s = raw.strip()
    if not (s.startswith("{") and s.endswith("}")):
        raise ValueError("params must be an object, e.g. {'x':1} or {x:1}")
    body = s[1:-1].strip()
    if not body:
        return {}
    out: dict[str, Any] = {}
    for item in _split_top_level(body, ","):
        kv = _split_top_level(item, ":")
        if len(kv) < 2:
            raise ValueError(f"invalid key/value entry: {item}")
        key_raw = kv[0].strip()
        value_raw = item[item.find(":") + 1 :].strip()
        if (key_raw.startswith('"') and key_raw.endswith('"')) or (key_raw.startswith("'") and key_raw.endswith("'")):
            key = key_raw[1:-1]
        else:
            key = key_raw
        if key == "":
            raise ValueError("empty key is not allowed")
        out[key] = _parse_relaxed_scalar(value_raw)
    return out


def main() -> int:
    args = _parser().parse_args()
    try:
        params = _parse_params(args.params)
        evt = (args.event or "").strip().lower()
        if evt == "ocr":
            with _silence_process_stdio():
                out = execute_event(args.event, args.function, params)
        else:
            out = execute_event(args.event, args.function, params)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except CommandError as ex:
        print(json.dumps({"success": False, "code": ex.code, "message": ex.message, "data": ex.data or {}}, ensure_ascii=False))
        return 1
    except Exception as ex:  # noqa: BLE001
        print(json.dumps({"success": False, "code": "SYS1999", "message": str(ex), "data": {}}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

