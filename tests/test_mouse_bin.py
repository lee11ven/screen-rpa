from __future__ import annotations

from bin import mouse


class _DummyGui:
    def __init__(self) -> None:
        self.scroll_calls: list[tuple[int, int | None, int | None]] = []

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> None:
        self.scroll_calls.append((int(clicks), x, y))


def test_mouse_scroll_chunked_on_large_amount(monkeypatch) -> None:
    gui = _DummyGui()
    monkeypatch.setattr(mouse, "_pyautogui", lambda: gui)

    out = mouse.handle("scroll", {"amount": 500000, "x": 10, "y": 20})

    # product semantics: positive means scroll down -> pyautogui negative clicks
    assert gui.scroll_calls[0] == (-120, 10, 20)
    assert gui.scroll_calls[-1][0] < 0
    assert len(gui.scroll_calls) == 4167
    assert out["success"] is True
    assert out["data"]["chunks"] == 4167

