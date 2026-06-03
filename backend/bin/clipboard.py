from __future__ import annotations

from typing import Any

from .result import CommandError, ok


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    import pyperclip

    fn = function.strip().lower()
    if fn == "set_text":
        text = str(params.get("text", ""))
        pyperclip.copy(text)
        return ok({"text_length": len(text)})
    if fn == "get_text":
        text = pyperclip.paste()
        return ok({"text": text})
    raise CommandError("SYS1001", f"unsupported clipboard function: {function}")

