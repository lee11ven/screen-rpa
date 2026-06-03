from __future__ import annotations

from typing import Any

from .result import CommandError, ok


_SCROLL_CHUNK_SIZE = 120


def _pyautogui() -> Any:
    import pyautogui

    return pyautogui


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    gui = _pyautogui()
    fn = function.strip().lower()
    if fn == "move":
        x = int(params["x"])
        y = int(params["y"])
        duration = max(0, int(params.get("move_duration", 200))) / 1000.0
        gui.moveTo(x, y, duration=duration)
        return ok({"x": x, "y": y})
    if fn in ("subclick", "dbclick", "rclick"):
        x = int(params["x"])
        y = int(params["y"])
        button = str(params.get("button", "left"))
        clicks = int(params.get("clicks", 1))
        interval = max(0, int(params.get("interval", 0))) / 1000.0
        if fn == "dbclick":
            clicks = 2
            button = "left"
        elif fn == "rclick":
            clicks = 1
            button = "right"
        gui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
        return ok({"x": x, "y": y, "button": button, "clicks": clicks})
    if fn == "drag":
        sx = int(params["start_x"])
        sy = int(params["start_y"])
        ex = int(params["end_x"])
        ey = int(params["end_y"])
        duration = max(0, int(params.get("duration", 500))) / 1000.0
        button = str(params.get("button", "left"))
        gui.moveTo(sx, sy, duration=min(0.2, duration))
        gui.dragTo(ex, ey, duration=duration, button=button)
        return ok({"start_x": sx, "start_y": sy, "end_x": ex, "end_y": ey})
    if fn == "scroll":
        amount = int(params["amount"])
        x = params.get("x")
        y = params.get("y")
        # Keep product semantics: positive amount means scroll down.
        px = None if x is None else int(x)
        py = None if y is None else int(y)
        remaining = abs(amount)
        direction = -1 if amount > 0 else 1
        if amount == 0:
            return ok({"amount": amount, "x": x, "y": y, "chunks": 0})
        chunks = 0
        while remaining > 0:
            step = min(_SCROLL_CHUNK_SIZE, remaining)
            gui.scroll(direction * step, x=px, y=py)
            remaining -= step
            chunks += 1
        return ok({"amount": amount, "x": x, "y": y, "chunks": chunks})
    if fn == "position":
        pos = gui.position()
        return ok({"x": int(pos.x), "y": int(pos.y)})
    raise CommandError("SYS1001", f"unsupported mouse function: {function}")

