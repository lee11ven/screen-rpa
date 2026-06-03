from __future__ import annotations

import ctypes
import os
import time
from typing import Any
from contextlib import contextmanager

from .result import CommandError, ok


def _pyautogui() -> Any:
    import pyautogui

    return pyautogui


@contextmanager
def _temporary_failsafe(gui: Any, disable: bool):
    if not disable:
        yield
        return
    previous = bool(getattr(gui, "FAILSAFE", True))
    gui.FAILSAFE = False
    try:
        yield
    finally:
        gui.FAILSAFE = previous


def _type_with_clipboard(text: str) -> None:
    import pyperclip

    gui = _pyautogui()
    backup = None
    try:
        backup = pyperclip.paste()
    except Exception:  # noqa: BLE001
        backup = None
    try:
        pyperclip.copy(text)
        time.sleep(0.08)
        gui.keyDown("ctrl")
        gui.press("v")
        gui.keyUp("ctrl")
    finally:
        if backup is not None:
            try:
                pyperclip.copy(backup)
            except Exception:  # noqa: BLE001
                pass


def _is_windows() -> bool:
    return os.name == "nt"


def _needs_unicode_typing(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def _type_with_windows_unicode(text: str, interval: float = 0.0) -> bool:
    if not _is_windows():
        return False
    if text == "":
        return True

    user32 = ctypes.windll.user32
    if not hasattr(user32, "SendInput"):
        return False

    input_keyboard = 1
    keyeventf_keyup = 0x0002
    keyeventf_unicode = 0x0004

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("_input",)
        _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]

    def _send_char(ch: str) -> bool:
        codepoint = ord(ch)
        extra = ctypes.c_ulong(0)
        ptr = ctypes.pointer(extra)

        events = (
            INPUT(
                type=input_keyboard,
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=codepoint,
                    dwFlags=keyeventf_unicode,
                    time=0,
                    dwExtraInfo=ptr,
                ),
            ),
            INPUT(
                type=input_keyboard,
                ki=KEYBDINPUT(
                    wVk=0,
                    wScan=codepoint,
                    dwFlags=keyeventf_unicode | keyeventf_keyup,
                    time=0,
                    dwExtraInfo=ptr,
                ),
            ),
        )
        sent = user32.SendInput(
            len(events),
            ctypes.byref((INPUT * len(events))(*events)),
            ctypes.sizeof(INPUT),
        )
        return sent == len(events)

    for char in text:
        if not _send_char(char):
            return False
        if interval > 0:
            time.sleep(interval)
    return True


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    gui = _pyautogui()
    fn = function.strip().lower()
    disable_failsafe = bool(params.get("disable_failsafe", True))
    if fn == "listkeys":
        return ok({"keys": sorted(list(gui.KEYBOARD_KEYS))})
    if fn == "press":
        key = str(params["key"])
        presses = max(1, int(params.get("presses", 1)))
        interval = max(0, int(params.get("interval", 0))) / 1000.0
        with _temporary_failsafe(gui, disable_failsafe):
            gui.press(key, presses=presses, interval=interval)
        return ok({"key": key, "presses": presses})
    if fn == "hotkey":
        keys = params.get("keys")
        if isinstance(keys, str):
            key_list = [k.strip() for k in keys.split(",") if k.strip()]
        else:
            key_list = [str(k).strip() for k in (keys or []) if str(k).strip()]
        if not key_list:
            raise CommandError("SYS1001", "keys is required")
        delay = max(0, int(params.get("delay", 0))) / 1000.0
        if delay > 0:
            time.sleep(delay)
        with _temporary_failsafe(gui, disable_failsafe):
            gui.hotkey(*key_list)
        return ok({"keys": key_list})
    if fn == "hotkey_physical":
        keys = params.get("keys")
        if isinstance(keys, str):
            key_list = [k.strip() for k in keys.split(",") if k.strip()]
        else:
            key_list = [str(k).strip() for k in (keys or []) if str(k).strip()]
        if len(key_list) < 2:
            raise CommandError("SYS1001", "hotkey_physical requires at least 2 keys")
        modifier_down_gap = max(0, int(params.get("modifier_down_gap_ms", 30))) / 1000.0
        main_key_hold = max(0, int(params.get("main_key_hold_ms", 50))) / 1000.0
        release_gap = max(0, int(params.get("release_gap_ms", 20))) / 1000.0
        with _temporary_failsafe(gui, disable_failsafe):
            for key in key_list[:-1]:
                gui.keyDown(key)
                if modifier_down_gap > 0:
                    time.sleep(modifier_down_gap)
            gui.keyDown(key_list[-1])
            if main_key_hold > 0:
                time.sleep(main_key_hold)
            gui.keyUp(key_list[-1])
            if release_gap > 0:
                time.sleep(release_gap)
            for key in reversed(key_list[:-1]):
                gui.keyUp(key)
                if release_gap > 0:
                    time.sleep(release_gap)
        return ok({"keys": key_list})
    if fn in ("type", "typeascii", "unicode", "typeunicode"):
        text = str(params.get("text", ""))
        if text == "":
            return ok({"skipped": True}, "input text is empty, skipped")
        interval = max(0, int(params.get("interval", 0))) / 1000.0
        use_clipboard = bool(params.get("use_clipboard", True))
        with _temporary_failsafe(gui, disable_failsafe):
            if use_clipboard:
                _type_with_clipboard(text)
            else:
                # Windows + pyautogui.write 对中文等非 ASCII 字符输入不稳定，优先走 Unicode 注入。
                if _needs_unicode_typing(text):
                    if not _type_with_windows_unicode(text, interval=interval):
                        _type_with_clipboard(text)
                else:
                    gui.write(text, interval=interval)
        return ok({"length": len(text), "use_clipboard": use_clipboard})
    raise CommandError("SYS1001", f"unsupported keyboard function: {function}")

