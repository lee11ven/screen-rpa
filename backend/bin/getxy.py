from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .result import CommandError, ok


def _decode_image(source: str) -> np.ndarray:
    img = cv2.imread(source, cv2.IMREAD_COLOR)
    if img is None:
        raise CommandError("SYS1001", f"unable to read image: {source}")
    return img


def locate_center(page: str, sub: str, threshold: float = 0.85) -> dict[str, Any]:
    page_img = _decode_image(page)
    sub_img = _decode_image(sub)
    result = cv2.matchTemplate(page_img, sub_img, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if float(max_val) < float(threshold):
        return {"found": False, "confidence": float(max_val)}
    x, y = max_loc
    h, w = sub_img.shape[:2]
    cx = x + w // 2
    cy = y + h // 2
    return {
        "found": True,
        "confidence": float(max_val),
        "rect": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
        "center": {"x": int(cx), "y": int(cy)},
    }


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    fn = function.strip().lower()
    if fn != "match":
        raise CommandError("SYS1001", f"unsupported getxy function: {function}")
    page = str(params.get("page", "")).strip()
    sub = str(params.get("sub", "")).strip()
    if not page or not sub:
        raise CommandError("SYS1001", "page and sub are required")
    threshold = float(params.get("threshold", 0.85))
    return ok(locate_center(page, sub, threshold=threshold))

