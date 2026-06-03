from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any

import psutil

from .result import CommandError, ok

user32 = ctypes.windll.user32


def _find_top_window_by_pid(pid: int) -> int | None:
    handles: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_windows_proc(hwnd: int, lparam: int) -> bool:
        del lparam
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid and user32.IsWindowVisible(hwnd):
            handles.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum_windows_proc, 0)
    return handles[0] if handles else None


def _activate_window(hwnd: int) -> bool:
    SW_RESTORE = 9
    SW_SHOW = 5
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    else:
        user32.ShowWindow(hwnd, SW_SHOW)
    if user32.SetForegroundWindow(hwnd):
        return True
    return False


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    fn = function.strip().lower()
    if fn == "pid":
        process_name = str(params.get("process_name", "")).strip().lower()
        if not process_name:
            raise CommandError("SYS1001", "process_name is required")
        pids = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = str(proc.info.get("name") or "").lower()
                if name == process_name:
                    pids.append(int(proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return ok({"process_name": process_name, "pids": pids})
    if fn == "kill":
        pid = int(params.get("pid", 0))
        if pid <= 0:
            raise CommandError("SYS1001", "pid must be positive")
        try:
            psutil.Process(pid).kill()
            killed = True
        except psutil.NoSuchProcess:
            killed = False
        return ok({"pid": pid, "killed": killed})
    if fn == "activate_process_window":
        pid = int(params.get("pid", 0))
        if pid <= 0:
            raise CommandError("SYS1001", "pid must be positive")
        hwnd = _find_top_window_by_pid(pid)
        if not hwnd:
            return ok({"pid": pid, "activated": False})
        return ok({"pid": pid, "activated": _activate_window(hwnd), "hwnd": int(hwnd)})
    if fn == "window_find":
        title = str(params.get("title", "")).lower()
        process_name = str(params.get("process_name", "")).lower()
        if not title and not process_name:
            raise CommandError("SYS1001", "title or process_name is required")
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if process_name and str(proc.info.get("name", "")).lower() != process_name:
                    continue
                hwnd = _find_top_window_by_pid(int(proc.info["pid"]))
                if not hwnd:
                    continue
                text = user32.GetWindowTextW(hwnd, ctypes.create_unicode_buffer(512), 512)
                _ = text
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                window_title = buf.value
                if title and title not in window_title.lower():
                    continue
                return ok({"found": True, "hwnd": int(hwnd), "title": window_title, "pid": int(proc.info["pid"])})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return ok({"found": False})
    if fn == "window_activate":
        hwnd = int(params.get("hwnd", 0))
        title = str(params.get("title", "")).strip().lower()
        if hwnd <= 0 and not title:
            raise CommandError("SYS1001", "hwnd or title is required")
        target = hwnd
        if target <= 0:
            found = handle("window_find", {"title": title})
            target = int(found["data"].get("hwnd", 0))
        if target <= 0:
            return ok({"activated": False, "hwnd": 0})
        return ok({"activated": _activate_window(target), "hwnd": int(target)})
    raise CommandError("SYS1001", f"unsupported process function: {function}")

