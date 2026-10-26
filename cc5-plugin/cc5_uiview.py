"""
Reading CC5's interface and taking pictures, no mouse: window list with PNGs (QWidget.grab), a
read-only widget finder, and the framed capture (render big, cut a fixed box).

Everything here is read-only except writing the PNG files of the framed capture. See cc5_ui.py
for jobs and the windows we may answer.
"""

from __future__ import annotations

import base64
import os
import tempfile
import uuid
from typing import Any, Callable, Iterator

import cc5_ui

PNG_MAX_BYTES = 1_500_000
PREVIEW_WIDTH = 1400                # the preview of a full render, so a box can be measured on it
MAX_RENDER_SIZE = 5600              # Qt 5.15 refuses to load images over ~128 MB (5600 x 5600 x 4 = 125 MB)


# --- pictures ----------------------------------------------------------------------------

def png_bytes(q: Any, image: Any) -> bytes | None:
    """A QPixmap or QImage as PNG bytes, through a QBuffer."""
    array = q.QByteArray()
    buffer = q.QBuffer(array)
    buffer.open(q.QIODevice.WriteOnly)
    ok = image.save(buffer, "PNG")
    buffer.close()
    return bytes(array.data()) if ok else None


def grab_png(widget: Any, max_width: int = 900) -> dict[str, Any]:
    """QWidget.grab() as base64 PNG, scaled down until it fits PNG_MAX_BYTES."""
    q = cc5_ui._qt()
    pixmap = widget.grab()
    if cc5_ui._safe(pixmap.isNull, True):
        return {"error": "grab returned an empty image"}
    width = pixmap.width()
    target = min(width, max_width) if max_width else width
    for _ in range(4):
        shot = pixmap if target >= width else pixmap.scaledToWidth(target, q.Qt.SmoothTransformation)
        data = png_bytes(q, shot)
        if data is not None and len(data) <= PNG_MAX_BYTES:
            return {"png_base64": base64.b64encode(data).decode("ascii"), "png_size": [shot.width(), shot.height()]}
        target = max(200, target // 2)
    return {"error": "image too large to return"}


# --- windows -----------------------------------------------------------------------------

def ui_windows(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/windows: the windows CC5 has open right now (read-only).

    Body: screenshot (PNG of each, default false), max_width (default 900), target
    "dialogs" (default) | "main" (also the main window), include_other (floating tool windows).
    Works while a question window is open (the bridge still drains its queue in the modal loop).
    """
    p = body or {}
    shoot = bool(p.get("screenshot", False))
    max_width = cc5_ui._clamp_int(p.get("max_width", 900), 200, 2400, 900)
    windows: list[dict[str, Any]] = []
    for index, (info, w) in enumerate(cc5_ui.scan_windows(bool(p.get("include_other", False)))):
        entry = {"index": index, **cc5_ui.public_info(info)}
        decision = cc5_ui.decide(info, dict(cc5_ui.DEFAULT_CHOICES)) or {}
        entry["answerable_as"] = decision.get("rule") if "press" in decision else None
        if "blocked" in decision:
            entry["blocked_reason"] = decision["blocked"]
        if shoot:
            entry.update(grab_png(w, max_width))
        windows.append(entry)
    out: dict[str, Any] = {"success": True, "count": len(windows), "windows": windows}
    if p.get("target") == "main":
        out["main_window"] = _main_window_report(shoot, max_width)
    return out


def _main_window_report(shoot: bool, max_width: int) -> dict[str, Any]:
    q = cc5_ui._qt()
    for w in q.QApplication.instance().topLevelWidgets():
        if isinstance(w, q.QMainWindow) and cc5_ui._safe(w.isVisible, False):
            report: dict[str, Any] = {"title": cc5_ui.clean_text(cc5_ui._safe(w.windowTitle, ""))}
            if shoot:
                report.update(grab_png(w, max_width))
            return report
    return {"error": "main window not found"}


# --- widget finder -----------------------------------------------------------------------

def _is_free_text(w: Any) -> bool:
    """A text input (line edit, text box): what a person typed (a mail address, a key) is never read."""
    q = cc5_ui._qt()
    return isinstance(w, (q.QLineEdit, q.QTextEdit, q.QPlainTextEdit))


def widget_state(w: Any) -> dict[str, Any]:
    """Name, class and the values a widget exposes, as plain data. The text of line edits and text
    boxes (passwords, mail addresses, keys) is never returned."""
    safe = cc5_ui._safe
    out: dict[str, Any] = {"object_name": safe(w.objectName, ""), "class": cc5_ui._class_of(w),
                           "visible": bool(safe(w.isVisible, False)), "enabled": bool(safe(w.isEnabled, True))}
    secret = _is_free_text(w)
    for key, getter in (("text", "text"), ("current_text", "currentText"), ("value", "value"),
                        ("checked", "isChecked"), ("tooltip", "toolTip")):
        fn = getattr(w, getter, None)
        if secret and key in ("text", "current_text"):
            continue
        if callable(fn):
            value = safe(fn)
            if value is not None and value != "":
                out[key] = cc5_ui.clean_text(value) if isinstance(value, str) else value
    if secret:
        out["text_hidden"] = True
    chain: list[str] = []
    parent = safe(w.parent)
    while parent is not None and len(chain) < 6:
        chain.append(safe(parent.objectName, "") or cc5_ui._class_of(parent))
        parent = safe(parent.parent)
    out["path"] = " < ".join(chain)
    return out


def ui_widgets(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/widgets: read-only widget finder.

    Body: object_name (exact) | name_contains | class_name | text_contains (at least one),
    ancestor (objectName or class of a parent), visible_only (default true), limit (default 50).
    """
    p = body or {}
    name, contains, cls, text = (p.get("object_name"), p.get("name_contains"),
                                 p.get("class_name"), p.get("text_contains"))
    if not any((name, contains, cls, text)):
        return {"success": False, "error": "give at least one of object_name, name_contains, class_name, text_contains"}
    limit = cc5_ui._clamp_int(p.get("limit", 50), 1, 200, 50)
    visible_only = p.get("visible_only", True) is not False
    ancestor = str(p.get("ancestor") or "").lower()
    out: list[dict[str, Any]] = []
    total = 0
    for w in cc5_ui._qt().QApplication.allWidgets():
        wname = cc5_ui._safe(w.objectName, "")
        if name and wname != name:
            continue
        if contains and str(contains).lower() not in wname.lower():
            continue
        if cls and str(cls).lower() not in (cc5_ui._class_of(w).lower(), type(w).__name__.lower()):
            continue
        if text and (_is_free_text(w) or str(text).lower() not in cc5_ui.clean_text(cc5_ui._safe(lambda: w.text(), "")).lower()):
            continue
        if visible_only and not cc5_ui._safe(w.isVisible, False):
            continue
        state = widget_state(w)
        if ancestor and ancestor not in state["path"].lower():
            continue
        total += 1
        if len(out) < limit:
            out.append(state)
    return {"success": True, "count": total, "shown": len(out), "widgets": out}


# --- framed capture: render big, cut a fixed box ----------------------------------------

def crop_box(p: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int] | None:
    """(x0, y0, x1, y1) in pixels from p["crop"] (pixels) or p["crop_fraction"] (0..1)."""
    box = p.get("crop")
    if box is None and p.get("crop_fraction") is not None:
        fx0, fy0, fx1, fy1 = (float(v) for v in p["crop_fraction"])
        box = [fx0 * width, fy0 * height, fx1 * width, fy1 * height]
    if box is None:
        return None
    x0, y0, x1, y1 = (int(round(float(v))) for v in box)
    x0, x1 = max(0, min(x0, x1)), min(width, max(x0, x1))
    y0, y1 = max(0, min(y0, y1)), min(height, max(y0, y1))
    return (x0, y0, x1, y1) if x1 - x0 >= 2 and y1 - y0 >= 2 else None


def _select_avatar(name: str) -> None:
    import RLPy

    avatars = list(RLPy.RScene.GetAvatars() or [])
    avatar = next((a for a in avatars if a.GetName() == name), None) if name else (avatars[0] if avatars else None)
    if avatar is not None:
        RLPy.RScene.ClearSelectObjects()
        RLPy.RScene.SelectObject(avatar)


def _capture_crop_steps(p: dict[str, Any]) -> Iterator[float]:
    api = cc5_ui._api()
    _select_avatar(p.get("avatar_name", ""))
    framed = api.frame_camera(p["view"])
    if isinstance(framed, dict) and framed.get("success") is False:
        return {"success": False, "error": f"frame_camera failed: {framed.get('error')}"}
    yield p["settle_ms"]
    full_path = p["full_path"]
    cap = api.capture_viewport(full_path, p["size"], p["size"])
    if not cap.get("success"):
        return {"success": False, "error": f"capture failed: {cap.get('error')}"}
    if cap.get("fallback"):
        return {"success": False, "path": full_path, "error":
                "RenderImage failed, so the capture is a window screenshot and not a "
                f"{p['size']}x{p['size']} render; a crop of it would not be comparable. {cap.get('warning', '')}"}
    q = cc5_ui._qt()
    image = q.QImage(full_path)
    if cc5_ui._safe(image.isNull, True):
        return {"success": False, "path": full_path, "error": "cannot read the capture back as an image"}
    width, height = image.width(), image.height()
    out: dict[str, Any] = {"success": True, "view": p["view"], "full_path": full_path, "render_size": [width, height]}
    if (width, height) != (p["size"], p["size"]):
        out["warning"] = f"asked {p['size']}x{p['size']} but the render is {width}x{height}"
    box = crop_box(p, width, height)
    if box is None:
        if p.get("crop") is not None or p.get("crop_fraction") is not None:
            return {"success": False, "path": full_path, "error": f"crop box is outside the {width}x{height} render"}
        _add_preview(out, q, image)
        return out
    x0, y0, x1, y1 = box
    piece = image.copy(q.QRect(x0, y0, x1 - x0, y1 - y0))
    if not piece.save(p["output_path"], "PNG"):
        return {"success": False, "error": f"cannot save the crop to {p['output_path']}"}
    out.update({"crop_path": p["output_path"], "crop_box": [x0, y0, x1, y1], "crop_size": [x1 - x0, y1 - y0]})
    data = png_bytes(q, piece)
    if data is not None and len(data) <= PNG_MAX_BYTES:
        out["png_base64"] = base64.b64encode(data).decode("ascii")
    else:
        out["note"] = "the crop is too large to return inline; open crop_path"
    return out


def _add_preview(out: dict[str, Any], q: Any, image: Any) -> None:
    """A scaled-down picture of the whole render, to measure a crop box on (scale = full / preview)."""
    small = image.scaledToWidth(PREVIEW_WIDTH, q.Qt.SmoothTransformation) if image.width() > PREVIEW_WIDTH else image
    data = png_bytes(q, small)
    if data is not None and len(data) <= PNG_MAX_BYTES:
        out["png_base64"] = base64.b64encode(data).decode("ascii")
        out["preview_size"] = [small.width(), small.height()]
        out["preview_scale"] = round(image.width() / small.width(), 4)


def _png_target(p: dict[str, Any], key: str, stem: str, overwrite: bool) -> str | None:
    """Fill p[key] (a fresh temp name by default) and return the problem with it, or None."""
    default = os.path.join(tempfile.gettempdir(), f"{stem}_{uuid.uuid4().hex[:10]}.png")
    p[key] = str(p.get(key) or default).replace("\\", "/")
    problem = cc5_ui.path_problem(p[key], {".png"})
    if problem:
        return f"{key}: {problem}"
    if os.path.exists(p[key]) and not overwrite:
        return f"{key}: {p[key]} already exists; give another name or overwrite=true"
    return None


def ui_capture_crop(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/capture_crop: frame the face, render BIG, cut a fixed box. Starts a job.

    Same framing every time (no dolly), so crops of different options are the same scale.
    Body: view (default "face"), size (default 3600, square, max 5600), crop [x0,y0,x1,y1] in
    render pixels OR crop_fraction [x0,y0,x1,y1] in 0..1 (none: the reply carries a scaled-down
    preview of the whole render), output_path / full_path (.png; new temp names by default; an
    existing file is only replaced with overwrite=true), avatar_name (selected before framing),
    settle_ms (default 800).
    """
    p = dict(body or {})
    p["view"] = str(p.get("view") or "face")
    p["size"] = cc5_ui._clamp_int(p.get("size", 3600), 256, MAX_RENDER_SIZE, 3600)
    p["settle_ms"] = cc5_ui._clamp_int(p.get("settle_ms", 800), 0, 10000, 800)
    p["avatar_name"] = str(p.get("avatar_name") or "")
    overwrite = p.get("overwrite") is True
    for key, stem in (("output_path", "cc5_framed_crop"), ("full_path", "cc5_framed_full")):
        problem = _png_target(p, key, stem, overwrite)
        if problem:
            return {"success": False, "error": problem}
    if p["output_path"] == p["full_path"]:
        return {"success": False, "error": "output_path and full_path must be different files"}
    for key in ("crop", "crop_fraction"):
        value = p.get(key)
        if value is not None and not (isinstance(value, (list, tuple)) and len(value) == 4
                                      and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)):
            return {"success": False, "error": f"{key} must be 4 numbers [x0, y0, x1, y1]"}
    if p.get("crop") is not None and p.get("crop_fraction") is not None:
        return {"success": False, "error": "give crop or crop_fraction, not both"}
    fraction = p.get("crop_fraction")
    if fraction is not None and not (0 <= fraction[0] < fraction[2] <= 1 and 0 <= fraction[1] < fraction[3] <= 1):
        return {"success": False, "error": "crop_fraction must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1"}
    started = cc5_ui.start_job("crop", _capture_crop_steps, p, max_seconds=300 + p["settle_ms"] / 1000)
    if started.get("success"):                    # only a started job makes folders (the job runs a moment later)
        for key in ("output_path", "full_path"):
            os.makedirs(os.path.dirname(p[key]) or ".", exist_ok=True)
    return started


ROUTES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "/ui/windows": ("ui_windows", ui_windows),
    "/ui/widgets": ("ui_widgets", ui_widgets),
    "/ui/capture_crop": ("ui_capture_crop", ui_capture_crop),
}
