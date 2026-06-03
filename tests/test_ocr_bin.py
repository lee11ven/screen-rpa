from __future__ import annotations

import pytest

from bin import ocr
from bin.result import CommandError


def test_ocr_recognize_success(monkeypatch, tmp_path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"fake")

    monkeypatch.setattr(
        ocr,
        "_predict_lines",
        lambda _page: [
            {"text": "提交", "confidence": 0.9, "box": {"x": 1, "y": 2, "width": 10, "height": 12}, "center": {"x": 6, "y": 8}, "points": []},
            {"text": "取消", "confidence": 0.3, "box": {"x": 2, "y": 3, "width": 9, "height": 11}, "center": {"x": 6, "y": 8}, "points": []},
        ],
    )
    out = ocr.handle("recognize", {"page": str(page), "min_confidence": 0.5})
    assert out["success"] is True
    assert len(out["data"]["lines"]) == 1
    assert out["data"]["lines"][0]["text"] == "提交"


def test_ocr_locate_text_found(monkeypatch, tmp_path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"fake")
    monkeypatch.setattr(
        ocr,
        "_predict_lines",
        lambda _page: [
            {"text": "提交按钮", "confidence": 0.8, "box": {"x": 11, "y": 22, "width": 33, "height": 44}, "center": {"x": 27, "y": 44}, "points": []}
        ],
    )
    out = ocr.handle("locate_text", {"page": str(page), "text": "提交", "contains": True, "min_confidence": 0.5})
    assert out["success"] is True
    assert out["data"]["found"] is True
    assert out["data"]["box"]["width"] < 33
    assert out["data"]["center"]["x"] < 27


def test_ocr_locate_text_contains_refine_box(monkeypatch, tmp_path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"fake")
    monkeypatch.setattr(
        ocr,
        "_predict_lines",
        lambda _page: [
            {"text": "保存并提交", "confidence": 0.8, "box": {"x": 100, "y": 200, "width": 120, "height": 20}, "center": {"x": 160, "y": 210}, "points": []}
        ],
    )
    out = ocr.handle("locate_text", {"page": str(page), "text": "提交", "contains": True, "min_confidence": 0.5})
    assert out["success"] is True
    assert out["data"]["found"] is True
    # 目标子串位于原文本后半段，返回框应向右收窄而不是整行宽度。
    assert out["data"]["box"]["x"] > 100
    assert out["data"]["box"]["width"] < 120


def test_ocr_locate_text_not_found(monkeypatch, tmp_path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"fake")
    monkeypatch.setattr(ocr, "_predict_lines", lambda _page: [])
    out = ocr.handle("locate_text", {"page": str(page), "text": "提交"})
    assert out["success"] is True
    assert out["data"]["found"] is False


def test_ocr_locate_text_requires_text(tmp_path) -> None:
    page = tmp_path / "page.png"
    page.write_bytes(b"fake")
    with pytest.raises(CommandError):
        ocr.handle("locate_text", {"page": str(page), "text": ""})


def test_ocr_recognize_page_not_found() -> None:
    with pytest.raises(CommandError):
        ocr.handle("recognize", {"page": "D:/not_exists_xxx.png"})

