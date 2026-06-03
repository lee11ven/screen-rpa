from __future__ import annotations

from bin import keyboard


class _DummyGui:
    def __init__(self) -> None:
        self.FAILSAFE = True
        self.calls: list[tuple] = []
        self.KEYBOARD_KEYS = {"win", "r", "ctrl", "v"}

    def hotkey(self, *keys):
        self.calls.append(("hotkey", *keys, self.FAILSAFE))

    def keyDown(self, key: str) -> None:
        self.calls.append(("down", key, self.FAILSAFE))

    def keyUp(self, key: str) -> None:
        self.calls.append(("up", key, self.FAILSAFE))

    def press(self, key: str, presses: int = 1, interval: float = 0) -> None:
        self.calls.append(("press", key, presses, interval, self.FAILSAFE))


def test_hotkey_temporarily_disables_failsafe(monkeypatch) -> None:
    gui = _DummyGui()
    monkeypatch.setattr(keyboard, "_pyautogui", lambda: gui)

    out = keyboard.handle("hotkey", {"keys": ["win", "r"], "disable_failsafe": True})

    assert out["success"] is True
    assert gui.calls[0] == ("hotkey", "win", "r", False)
    assert gui.FAILSAFE is True


def test_hotkey_physical_executes_key_sequence(monkeypatch) -> None:
    gui = _DummyGui()
    monkeypatch.setattr(keyboard, "_pyautogui", lambda: gui)

    out = keyboard.handle(
        "hotkey_physical",
        {
            "keys": ["ctrl", "shift", "s"],
            "modifier_down_gap_ms": 0,
            "main_key_hold_ms": 0,
            "release_gap_ms": 0,
        },
    )

    assert out["success"] is True
    assert gui.calls == [
        ("down", "ctrl", False),
        ("down", "shift", False),
        ("down", "s", False),
        ("up", "s", False),
        ("up", "shift", False),
        ("up", "ctrl", False),
    ]
    assert gui.FAILSAFE is True
