from __future__ import annotations

import subprocess
from typing import Any

from .result import CommandError, ok


ALLOWED_SHELLS = {"powershell", "cmd"}


def handle(params: dict[str, Any]) -> dict[str, Any]:
    command = str(params.get("command", "")).strip()
    if not command:
        raise CommandError("SYS1001", "command is required")
    shell = str(params.get("shell", "powershell")).strip().lower()
    if shell not in ALLOWED_SHELLS:
        raise CommandError("SYS1001", f"unsupported shell: {shell}")
    timeout_ms = max(0, int(params.get("timeout_ms", 5000)))
    encoding = str(params.get("encoding", "utf-8")).strip() or "utf-8"

    try:
        if shell == "powershell":
            args = ["powershell", "-NoProfile", "-Command", command]
        else:
            args = ["cmd", "/c", command]
        proc = subprocess.run(  # noqa: S603
            args,
            capture_output=True,
            timeout=timeout_ms / 1000.0 if timeout_ms > 0 else None,
            text=False,
            check=False,
        )
    except subprocess.TimeoutExpired as ex:
        raise CommandError("SYS1005", "command timeout", {"timeout_ms": timeout_ms}) from ex
    except Exception as ex:  # noqa: BLE001
        raise CommandError("SYS1007", f"command execution failed: {ex}") from ex

    stdout = proc.stdout.decode(encoding, errors="replace") if proc.stdout else ""
    stderr = proc.stderr.decode(encoding, errors="replace") if proc.stderr else ""
    return ok({"exit_code": int(proc.returncode), "stdout": stdout, "stderr": stderr})

