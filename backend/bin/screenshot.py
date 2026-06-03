from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .result import CommandError, ok


def _pyautogui() -> Any:
    import pyautogui

    return pyautogui


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    gui = _pyautogui()
    fn = function.strip().lower()
    if fn != "screenshot":
        raise CommandError("SYS1001", f"unsupported screenshot function: {function}")
    output = str(params.get("output", "")).strip()
    region = params.get("region")
    if not output:
        output = str(Path.cwd() / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if region:
        left, top, width, height = [int(x) for x in region]
        image = gui.screenshot(region=(left, top, width, height))
    else:
        image = gui.screenshot()
    image.save(output_path)
    return ok({"path": str(output_path.resolve())})

