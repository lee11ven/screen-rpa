from __future__ import annotations

import contextlib
import io
import importlib.util
import os
from pathlib import Path
from typing import Any

from .result import CommandError, ok

_OCR_ENGINE: Any = None
_PAGE_LINES_CACHE: dict[tuple[str, int, int], list[dict[str, Any]]] = {}


def _configure_paddle_runtime() -> None:
    # Some Paddle/PaddleOCR combinations on Windows hit oneDNN+PIR runtime errors.
    # Keep these as best-effort defaults and allow users to override explicitly.
    os.environ.setdefault("FLAGS_enable_pir_api", "0")
    os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    with contextlib.suppress(Exception):
        import paddle  # type: ignore[import-untyped]

        paddle.set_flags(
            {
                "FLAGS_enable_pir_api": False,
                "FLAGS_enable_pir_in_executor": False,
                "FLAGS_use_mkldnn": False,
            }
        )


@contextlib.contextmanager
def _mute_stdout_stderr():
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        yield


def _load_engine() -> Any:
    global _OCR_ENGINE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE
    _configure_paddle_runtime()
    try:
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]
    except ImportError as ex:
        raise CommandError("SYS1001", "paddleocr not installed; please install with `pip install .[ocr]`") from ex
    if importlib.util.find_spec("paddle") is None:
        raise CommandError("SYS1001", "paddlepaddle not installed; please install with `pip install .[ocr]`")
    init_variants = [
        {"use_angle_cls": True, "lang": "ch", "show_log": False, "enable_mkldnn": False, "ocr_version": "PP-OCRv4"},
        {"use_angle_cls": True, "lang": "ch", "show_log": False, "enable_mkldnn": False},
        {"use_angle_cls": True, "lang": "ch", "enable_mkldnn": False, "ocr_version": "PP-OCRv4"},
        {"use_angle_cls": True, "lang": "ch", "enable_mkldnn": False},
        {"use_angle_cls": True, "lang": "ch", "show_log": False},
        {"use_angle_cls": True, "lang": "ch"},
    ]
    last_error: Exception | None = None
    for kwargs in init_variants:
        try:
            with _mute_stdout_stderr():
                _OCR_ENGINE = PaddleOCR(**kwargs)
            break
        except Exception as ex:  # noqa: BLE001
            last_error = ex
            continue
    if _OCR_ENGINE is None:
        raise CommandError("SYS1001", f"failed to initialize PaddleOCR: {last_error}") from last_error
    return _OCR_ENGINE


def _read_image(page: str) -> Any:
    if not page:
        raise CommandError("SYS1001", "page is required")
    src = Path(page).expanduser()
    if not src.exists():
        raise CommandError("SYS1001", f"image not found: {src}")
    try:
        import cv2
    except ImportError as ex:
        raise CommandError("SYS1001", "opencv-python not installed; please install with `pip install .[ocr]`") from ex
    image = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if image is None:
        raise CommandError("SYS1001", f"unable to read image: {src}")
    return image


def _build_cache_key(page: str) -> tuple[str, int, int]:
    src = Path(page).expanduser().resolve()
    stat = src.stat()
    return (str(src), stat.st_mtime_ns, stat.st_size)


def _run_ocr(engine: Any, image: Any, cls: bool) -> Any:
    with _mute_stdout_stderr():
        try:
            return engine.ocr(image, cls=cls)
        except TypeError:
            return engine.ocr(image)


def _extract_lines(raw: Any) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    if not raw:
        return lines
    first = raw[0] if isinstance(raw, list) and raw else []
    for item in first or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        quad = item[0]
        txt_conf = item[1]
        if not isinstance(txt_conf, (list, tuple)) or len(txt_conf) < 2:
            continue
        text = str(txt_conf[0] or "")
        confidence = float(txt_conf[1] or 0.0)
        if not isinstance(quad, (list, tuple)) or len(quad) < 4:
            continue
        points: list[list[int]] = []
        for p in quad:
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                continue
            points.append([int(p[0]), int(p[1])])
        if len(points) < 4:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        w = max(1, x1 - x0)
        h = max(1, y1 - y0)
        lines.append(
            {
                "text": text,
                "confidence": confidence,
                "points": points,
                "box": {"x": x0, "y": y0, "width": w, "height": h},
                "center": {"x": x0 + w // 2, "y": y0 + h // 2},
            }
        )
    return lines


def _needs_retry(lines: list[dict[str, Any]]) -> bool:
    if not lines:
        return True
    avg_conf = sum(float(x.get("confidence", 0.0)) for x in lines) / max(1, len(lines))
    return avg_conf < 0.65


def _score_lines(lines: list[dict[str, Any]]) -> float:
    if not lines:
        return 0.0
    conf_sum = sum(float(x.get("confidence", 0.0)) for x in lines)
    return conf_sum + len(lines) * 0.25


def _enhance_for_ocr(image: Any) -> Any:
    try:
        import cv2
    except ImportError:
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    height, width = enhanced.shape[:2]
    # 小图/远距离文字常见漏识别，适度放大通常能明显提升召回率。
    if min(width, height) < 900:
        enhanced = cv2.resize(enhanced, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    return enhanced


def _predict_lines(page: str) -> list[dict[str, Any]]:
    image = _read_image(page)
    cache_key = _build_cache_key(page)
    cached = _PAGE_LINES_CACHE.get(cache_key)
    if cached is not None:
        return cached
    engine = _load_engine()
    fast_lines = _extract_lines(_run_ocr(engine, image, cls=False))
    lines = fast_lines
    if _needs_retry(fast_lines):
        enhanced_image = _enhance_for_ocr(image)
        robust_lines = _extract_lines(_run_ocr(engine, enhanced_image, cls=True))
        if _score_lines(robust_lines) >= _score_lines(fast_lines):
            lines = robust_lines
    _PAGE_LINES_CACHE.clear()
    _PAGE_LINES_CACHE[cache_key] = lines
    return lines


def _handle_recognize(params: dict[str, Any]) -> dict[str, Any]:
    page = str(params.get("page", "")).strip()
    min_confidence = float(params.get("min_confidence", 0.0))
    lines = [x for x in _predict_lines(page) if float(x.get("confidence", 0.0)) >= min_confidence]
    return ok({"page": str(Path(page).expanduser().resolve()), "lines": lines})


def _handle_locate_text(params: dict[str, Any]) -> dict[str, Any]:
    page = str(params.get("page", "")).strip()
    target = str(params.get("text", "")).strip()
    if not target:
        raise CommandError("SYS1001", "text is required")
    contains = bool(params.get("contains", True))
    min_confidence = float(params.get("min_confidence", 0.5))
    lines = _predict_lines(page)
    best: dict[str, Any] | None = None
    best_score: tuple[int, int, int, float] | None = None
    for line in lines:
        text = str(line.get("text", ""))
        conf = float(line.get("confidence", 0.0))
        if conf < min_confidence:
            continue
        matched = target in text if contains else text == target
        if not matched:
            continue
        box = line.get("box", {}) if isinstance(line.get("box", {}), dict) else {}
        x = int(box.get("x", 0))
        y = int(box.get("y", 0))
        width = max(1, int(box.get("width", 1)))
        height = max(1, int(box.get("height", 1)))
        if contains and text:
            start = text.find(target)
            if start >= 0 and len(target) < len(text):
                unit = width / max(1, len(text))
                sub_x = x + int(round(start * unit))
                sub_w = max(1, int(round(len(target) * unit)))
                max_w = x + width - sub_x
                width = max(1, min(sub_w, max_w))
                x = sub_x
        candidate = dict(line)
        candidate["box"] = {"x": x, "y": y, "width": width, "height": height}
        candidate["center"] = {"x": x + width // 2, "y": y + height // 2}

        exact_penalty = 0 if text == target else 1
        extra_chars = max(0, len(text) - len(target))
        area = width * height
        score = (exact_penalty, extra_chars, area, -conf)
        if best is None or best_score is None or score < best_score:
            best = candidate
            best_score = score
    if best is None:
        return ok(
            {
                "page": str(Path(page).expanduser().resolve()),
                "text": target,
                "contains": contains,
                "found": False,
            }
        )
    return ok(
        {
            "page": str(Path(page).expanduser().resolve()),
            "text": target,
            "contains": contains,
            "found": True,
            "confidence": float(best.get("confidence", 0.0)),
            "box": best.get("box", {}),
            "center": best.get("center", {}),
            "line": best,
        }
    )


def handle(function: str, params: dict[str, Any]) -> dict[str, Any]:
    fn = function.strip().lower()
    if fn == "recognize":
        return _handle_recognize(params)
    if fn == "locate_text":
        return _handle_locate_text(params)
    raise CommandError("SYS1001", f"unsupported ocr function: {function}")
