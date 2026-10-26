"""
Qt-side helpers that let the bridge work CC5's own windows without a mouse.

Built from what worked on 2026-10-26 (eyelash presets, SkinGen lip makeup, see
docs/ui-automation-test-steps_ja.md):

  * answer the few question windows a script causes, and ONLY those (WINDOW_RULES);
    licence / purchase / login / update / terms windows are never pressed;
  * long UI work runs as a "job": the bridge call returns at once and the work goes on
    in CC5's Qt event loop, one small step at a time, so the bridge keeps answering
    (list windows, read state) while a question window is open or CC5 is baking;
  * read the visible windows (title, text, buttons) and grab them as PNG with Qt
    (QWidget.grab), so nobody needs a desktop screenshot over ssh;
  * a read-only widget finder, to discover object names for new automation.

This module is loaded by cc5_api (see cc5_api._load_ui_modules). It must not import
cc5_api at module level. PySide2 is imported lazily (_qt) so the logic runs in tests.
"""

from __future__ import annotations

import base64
import dataclasses
import html
import inspect
import os
import re
import sys
import tempfile
import time
import types
from typing import Any, Callable, Iterator

import RLPy

# --- constants ---------------------------------------------------------------------------

# Window text that means "CC5 is busy, this goes away by itself" (taken from the lip run).
BUSY_WORDS = ("baking", "please wait", "mipmap", "processing", "loading", "dynamic", "generating")

# A window mentioning any of these is never answered, whatever else it says.
FORBIDDEN_RE = re.compile(
    r"\b(licen[cs]e|purchas|buy|log ?in|sign ?in|password|updat|upgrad|agree|terms|eula|"
    r"activat|subscri|payment|credit card|trial|serial)",
    re.IGNORECASE,
)

MAX_TEXT_CHARS = 400
JOB_KEEP = 30                       # finished jobs kept for /ui/job
JOB_STALE_SECONDS = 900             # a "running" job older than this no longer blocks new ones
ANSWERER_MAX_SECONDS = 600          # the answering timer stops itself after this
MAX_PRESSES_PER_WINDOW = 3          # same window pressed more often than this means it is stuck
PNG_MAX_BYTES = 1_500_000

_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


# --- tiny helpers (patched in tests) -----------------------------------------------------

def _qt() -> Any:
    """The PySide2 classes this module uses, as one namespace. Imported lazily."""
    from PySide2 import QtCore, QtGui, QtWidgets

    return types.SimpleNamespace(
        QApplication=QtWidgets.QApplication, QWidget=QtWidgets.QWidget,
        QMainWindow=QtWidgets.QMainWindow, QDialog=QtWidgets.QDialog, QMenu=QtWidgets.QMenu,
        QLabel=QtWidgets.QLabel, QAbstractButton=QtWidgets.QAbstractButton,
        QPushButton=QtWidgets.QPushButton, QToolButton=QtWidgets.QToolButton,
        QCheckBox=QtWidgets.QCheckBox, QRadioButton=QtWidgets.QRadioButton,
        QProgressBar=QtWidgets.QProgressBar, QSpinBox=QtWidgets.QSpinBox,
        QComboBox=QtWidgets.QComboBox, QTableWidget=QtWidgets.QTableWidget,
        QTimer=QtCore.QTimer, QBuffer=QtCore.QBuffer, QByteArray=QtCore.QByteArray,
        QIODevice=QtCore.QIODevice, Qt=QtCore.Qt, QRect=QtCore.QRect, QImage=QtGui.QImage,
    )


def _now() -> float:
    return time.time()


def _later(ms: float, fn: Callable[[], None]) -> None:
    """Run fn on the Qt main thread after ms milliseconds."""
    _qt().QTimer.singleShot(int(ms), fn)


def _api() -> Any:
    """cc5_api (imported lazily: it imports this module)."""
    module = sys.modules.get("cc5_api")
    if module is None:
        import cc5_api as module  # type: ignore[no-redef]
    return module


def _safe(fn: Callable[[], Any], default: Any = None) -> Any:
    """Call fn(); a dead Qt wrapper or a missing method gives the default."""
    try:
        return fn()
    except Exception:
        return default


def clean_text(value: Any) -> str:
    """Plain text of a label: rich-text tags removed, white space collapsed."""
    text = "" if value is None else str(value)
    text = html.unescape(_TAG_RE.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def label_text(widget: Any) -> str:
    """A button's text without the & shortcut marker."""
    return clean_text(_safe(widget.text, "")).replace("&", "")


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _holder() -> Any:
    """Where per-session state lives: the QApplication object (survives a hot reload)."""
    app = _safe(lambda: _qt().QApplication.instance())
    return app if app is not None else _FALLBACK_HOLDER


_FALLBACK_HOLDER = types.SimpleNamespace()


def _state(name: str, factory: Callable[[], Any]) -> Any:
    holder = _holder()
    if not hasattr(holder, name):
        setattr(holder, name, factory())
    return getattr(holder, name)


# --- windows: read and classify ----------------------------------------------------------

def forbidden_reason(*parts: str) -> str | None:
    """The word that makes a window off limits (licence, purchase, login, ...), or None."""
    match = FORBIDDEN_RE.search(" ".join(parts))
    return match.group(0).lower() if match else None


def describe_window(w: Any, q: Any = None) -> dict[str, Any]:
    """Title, text, buttons and check boxes of one top-level window, as plain data."""
    q = q or _qt()
    title = clean_text(_safe(w.windowTitle, ""))
    labels: list[str] = []
    for lab in _safe(lambda: w.findChildren(q.QLabel), []):
        text = clean_text(_safe(lab.text, ""))
        if text and _safe(lab.isVisible, True) and text not in labels:
            labels.append(text)
    text = " ".join(labels)
    buttons: list[str] = []
    boxes: list[dict[str, Any]] = []
    for b in _safe(lambda: w.findChildren(q.QAbstractButton), []):
        if not _safe(b.isVisible, True):
            continue
        label = label_text(b)
        if isinstance(b, (q.QCheckBox, q.QRadioButton)):
            boxes.append({"text": label, "checked": bool(_safe(b.isChecked, False))})
        elif label:
            buttons.append(label)
    lowered = f"{title} {text}".lower()
    progress = bool(_safe(lambda: w.findChildren(q.QProgressBar), [])) or any(
        word in lowered for word in BUSY_WORDS)
    rect = _safe(w.geometry)
    geometry = [rect.x(), rect.y(), rect.width(), rect.height()] if rect is not None else None
    return {
        "title": title,
        "class": _safe(lambda: w.metaObject().className(), type(w).__name__),
        "text": text[:MAX_TEXT_CHARS],
        "buttons": buttons,
        "checkboxes": boxes,
        "modal": bool(_safe(w.isModal, False)),
        "progress": progress,
        "geometry": geometry,
        "needs_human": forbidden_reason(title, text),
    }


def scan_windows(include_other: bool = False) -> list[tuple[dict[str, Any], Any]]:
    """Visible dialog-like top-level windows as (description, widget). Never the main window."""
    q = _qt()
    app = q.QApplication.instance()
    if app is None:
        return []
    found: list[tuple[dict[str, Any], Any]] = []
    for w in app.topLevelWidgets():
        if not _safe(w.isVisible, False) or isinstance(w, (q.QMainWindow, q.QMenu)):
            continue
        is_dialog = isinstance(w, q.QDialog) or bool(_safe(w.isModal, False))
        if not is_dialog and not include_other:
            continue
        info = describe_window(w, q)
        if not is_dialog and not (info["title"] or info["buttons"]):
            continue                              # tool tips, drag handles, ...
        found.append((info, w))
    return found


# --- windows: the answers we allow -------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class WindowRule:
    """A question window we may answer. key names the caller's choice; answers are the
    button labels it may select (lower case)."""

    key: str
    title_prefix: str
    text_has: str
    answers: tuple[str, ...]
    default: str


# The ONLY windows that are ever answered automatically. Text rules come first, so a
# question window wins over a generic "Apply" title (same order as the lip run).
WINDOW_RULES: tuple[WindowRule, ...] = (
    WindowRule("layer_choice", "", "add a new layer or replace", ("replace", "add"), "replace"),
    WindowRule("skingen_exit", "", "exit skingen editing mode", ("yes", "no"), "yes"),
    WindowRule("apply_preset", "apply", "", ("apply",), "apply"),   # Apply Character Preset / Apply Eyelash Elements
)
RESTORE_LASH_FRAGMENT = "neutral lash"          # "Restore neutral lash strip" check box
DEFAULT_CHOICES: dict[str, Any] = {"layer_choice": "replace", "skingen_exit": "yes", "restore_neutral_lash": True}


def normalize_choices(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate the caller's answers. Unknown keys and values are refused, not ignored."""
    out = dict(DEFAULT_CHOICES)
    by_key = {rule.key: rule for rule in WINDOW_RULES}
    for key, value in (raw or {}).items():
        if key == "restore_neutral_lash":
            if not isinstance(value, bool):
                raise ValueError("answers.restore_neutral_lash must be true or false")
            out[key] = value
        elif key in ("layer_choice", "skingen_exit"):
            wanted = str(value).strip().lower()
            if wanted not in by_key[key].answers:
                raise ValueError(f"answers.{key} must be one of {list(by_key[key].answers)}")
            out[key] = wanted
        else:
            raise ValueError(f"unknown answer {key!r}; allowed: layer_choice, skingen_exit, restore_neutral_lash")
    return out


def decide(info: dict[str, Any], choices: dict[str, Any]) -> dict[str, Any] | None:
    """What to do with one window: {"rule", "press", "ticks"} or {"rule", "blocked"} or None."""
    title = info["title"].lower()
    text = info["text"].lower()
    buttons = {label.lower() for label in info["buttons"]}
    for rule in WINDOW_RULES:
        if rule.title_prefix and not title.startswith(rule.title_prefix):
            continue
        if rule.text_has and rule.text_has not in text:
            continue
        bad = forbidden_reason(title, text)
        if bad:
            return {"rule": rule.key, "blocked": f"window mentions '{bad}': a person must decide"}
        want = rule.default if rule.key == "apply_preset" else choices.get(rule.key, rule.default)
        if want not in buttons:
            return {"rule": rule.key, "blocked": f"no '{want}' button (buttons: {info['buttons']})"}
        decision: dict[str, Any] = {"rule": rule.key, "press": want}
        if rule.key == "apply_preset":
            decision["ticks"] = [(RESTORE_LASH_FRAGMENT, bool(choices.get("restore_neutral_lash", True)))]
        return decision
    return None


class WindowAnswerer:
    """A repeating Qt timer that answers WINDOW_RULES windows while a script runs.

    The timer fires inside CC5's nested event loops too, so it works while LoadFile or a
    modal question blocks the caller. It stops itself after ANSWERER_MAX_SECONDS.
    """

    def __init__(self, choices: dict[str, Any], interval_ms: int = 250) -> None:
        self.choices = choices
        self.interval_ms = interval_ms
        self.log: list[dict[str, Any]] = []
        self.blocked: list[dict[str, Any]] = []
        self._timer: Any = None
        self._started = 0.0
        self._presses: dict[int, int] = {}

    def start(self) -> "WindowAnswerer":
        previous = getattr(_holder(), "_cc5_ui_answerer", None)
        if previous is not None and previous is not self:
            previous.stop()                       # never two pressers at once
        q = _qt()
        self._started = _now()
        self._timer = q.QTimer()
        self._timer.timeout.connect(self.tick)
        self._timer.start(self.interval_ms)
        _holder()._cc5_ui_answerer = self         # keeps the timer alive after the caller returns
        return self

    def stop(self) -> list[dict[str, Any]]:
        if self._timer is not None:
            _safe(self._timer.stop)
            self._timer = None
        holder = _holder()
        if getattr(holder, "_cc5_ui_answerer", None) is self:
            holder._cc5_ui_answerer = None
        return list(self.log)

    def tick(self) -> None:
        if self._timer is None:
            return
        if _now() - self._started > ANSWERER_MAX_SECONDS:
            self.stop()
            return
        try:
            for info, w in scan_windows():
                decision = decide(info, self.choices)
                if decision is None:
                    continue
                if "blocked" in decision:
                    if not any(b["title"] == info["title"] for b in self.blocked):
                        self.blocked.append({"title": info["title"], "why": decision["blocked"]})
                    continue
                if self._answer(info, w, decision):
                    return                        # one answer per tick, like the verified script
        except Exception as exc:                  # a timer callback must never raise
            print(f"[CC5 MCP Bridge] answerer tick failed: {exc}")

    def _answer(self, info: dict[str, Any], w: Any, decision: dict[str, Any]) -> bool:
        q = _qt()
        count = self._presses.get(id(w), 0)
        if count >= MAX_PRESSES_PER_WINDOW:
            return False
        for fragment, want in decision.get("ticks", []):
            for box in w.findChildren(q.QCheckBox):
                if fragment in label_text(box).lower() and bool(box.isChecked()) != want:
                    box.setChecked(want)
        for b in w.findChildren(q.QAbstractButton):
            if isinstance(b, (q.QCheckBox, q.QRadioButton)):
                continue
            if label_text(b).lower() == decision["press"] and _safe(b.isVisible, True) and _safe(b.isEnabled, True):
                self._presses[id(w)] = count + 1
                self.log.append({"rule": decision["rule"], "pressed": decision["press"],
                                 "window": info["title"], "text": info["text"][:80]})
                b.click()
                return True
        return False


# --- jobs: work that goes on after the bridge call returned ------------------------------

def _jobs() -> dict[str, dict[str, Any]]:
    return _state("_cc5_ui_jobs", dict)


def _next_job_number() -> int:
    counter = _state("_cc5_ui_job_counter", lambda: [0])
    counter[0] += 1
    return counter[0]


def running_job() -> dict[str, Any] | None:
    """A job that is still queued or running (and not stale), else None."""
    for job in _jobs().values():
        if job["state"] in ("queued", "running") and _now() - job["started"] < JOB_STALE_SECONDS:
            return job
    return None


def _finish(job: dict[str, Any], result: Any) -> None:
    job["result"] = result if isinstance(result, dict) else {"success": True, "value": result}
    job["state"] = "done"
    job["finished"] = _now()


def _fail(job: dict[str, Any], exc: BaseException) -> None:
    print(f"[CC5 MCP Bridge] job {job['id']} failed: {exc!r}")
    job["result"] = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
    job["state"] = "failed"
    job["finished"] = _now()


def _advance(job: dict[str, Any], gen: Iterator[float]) -> None:
    """Run the job's next step; a yielded number is how many ms to wait before the one after."""
    try:
        delay = next(gen)
    except StopIteration as stop:
        _finish(job, stop.value)
        return
    except Exception as exc:
        _fail(job, exc)
        return
    _later(max(0.0, float(delay)), lambda: _advance(job, gen))


def start_job(kind: str, make: Callable[[dict[str, Any]], Any], params: dict[str, Any]) -> dict[str, Any]:
    """Queue make(params) to run on the Qt main thread. make returns a dict, or is a generator
    that yields waits (ms) and returns the result dict. One job at a time."""
    busy = running_job()
    if busy is not None:
        return {"success": False, "error": f"another UI job is still running: {busy['id']} ({busy['kind']}); "
                                           "wait for it (ui/job) before starting the next"}
    jobs = _jobs()
    job: dict[str, Any] = {"id": f"{kind}-{_next_job_number()}", "kind": kind, "state": "queued",
                           "started": _now(), "finished": None, "result": None}
    jobs[job["id"]] = job
    for old in list(jobs)[:-JOB_KEEP]:
        jobs.pop(old, None)

    def begin() -> None:
        job["state"] = "running"
        try:
            out = make(params)
        except Exception as exc:
            _fail(job, exc)
            return
        if inspect.isgenerator(out):
            _advance(job, out)
        else:
            _finish(job, out)

    _later(0, begin)
    return {"success": True, "job_id": job["id"], "state": "queued"}


def ui_job(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/job: state of a job, with its result once it is done. Body: {"job_id"}."""
    job_id = str((body or {}).get("job_id") or "")
    job = _jobs().get(job_id)
    if job is None:
        return {"success": False, "error": f"unknown job {job_id!r}", "known": list(_jobs())[-5:]}
    out: dict[str, Any] = {"success": True, "job_id": job["id"], "kind": job["kind"], "state": job["state"],
                           "elapsed_s": round((job["finished"] or _now()) - job["started"], 1)}
    if job["state"] in ("done", "failed"):
        out["result"] = job["result"]
    else:
        out["windows"] = [{k: info[k] for k in ("title", "text", "buttons", "progress", "needs_human")}
                          for info, _w in scan_windows()][:5]
    return out


# --- waiting until CC5 is quiet ----------------------------------------------------------

def settle_steps(limit_s: float, choices: dict[str, Any], extra_ok: Callable[[], bool] | None = None,
                 quiet_needed: int = 2, poll_ms: int = 1000, grace_s: float = 4.0,
                 answerable: bool = True) -> Iterator[float]:
    """Generator (use with `yield from`): wait until no window is open for quiet_needed polls in a
    row. Progress windows (baking, loading) are waited out; a question the answerer will press
    is waited out (answerable=False: nothing is being answered, so it stops the wait too); any
    other window stops the wait. Returns {"ok", "waited_s", "blocked_by"}."""
    t0 = _now()
    quiet = 0
    unknown_since: float | None = None
    while _now() - t0 < limit_s:
        windows = scan_windows()
        stuck = None
        for info, _w in windows:
            if info["progress"]:
                continue
            decision = decide(info, choices) if answerable else None
            if decision is not None and "press" in decision:
                continue
            stuck = info
            break
        if stuck is not None:
            unknown_since = unknown_since if unknown_since is not None else _now()
            if stuck["needs_human"] or _now() - unknown_since >= grace_s:
                return {"ok": False, "waited_s": round(_now() - t0, 1), "blocked_by": stuck}
        else:
            unknown_since = None
        if not windows and (extra_ok is None or _safe(extra_ok, False)):
            quiet += 1
            if quiet >= quiet_needed:
                return {"ok": True, "waited_s": round(_now() - t0, 1), "blocked_by": None}
        else:
            quiet = 0
        yield poll_ms
    return {"ok": False, "waited_s": round(_now() - t0, 1), "blocked_by": None, "timeout": True}


def settle_error(settled: dict[str, Any]) -> str:
    """One sentence for a settle_steps result that is not ok."""
    blocked = settled.get("blocked_by")
    if blocked:
        return (f"a window needs a person: '{blocked['title']}' {blocked['text'][:120]!r} "
                f"(buttons: {blocked['buttons']}). Not answered on purpose.")
    return "CC5 was still busy when the time limit ran out"


# --- widgets: finding and reading --------------------------------------------------------

def _class_of(w: Any) -> str:
    return str(_safe(lambda: w.metaObject().className(), type(w).__name__))


def find_by_name(object_name: str, within: Any = None, visible_first: bool = True) -> list[Any]:
    """Every widget with this objectName (under `within` when given); visible ones first."""
    q = _qt()
    pool = _safe(lambda: within.findChildren(q.QWidget), []) if within is not None else q.QApplication.allWidgets()
    hits = [w for w in pool if _safe(w.objectName, "") == object_name]
    if visible_first:
        hits.sort(key=lambda w: 0 if _safe(w.isVisible, False) else 1)
    return hits


def widget_state(w: Any) -> dict[str, Any]:
    """Name, class and the values a widget exposes, as plain data."""
    out: dict[str, Any] = {"object_name": _safe(w.objectName, ""), "class": _class_of(w),
                           "visible": bool(_safe(w.isVisible, False)), "enabled": bool(_safe(w.isEnabled, True))}
    for key, getter in (("text", "text"), ("current_text", "currentText"), ("value", "value"),
                        ("checked", "isChecked"), ("tooltip", "toolTip")):
        fn = getattr(w, getter, None)
        if callable(fn):
            value = _safe(fn)
            if value is not None and value != "":
                out[key] = clean_text(value) if isinstance(value, str) else value
    chain: list[str] = []
    parent = _safe(w.parent)
    while parent is not None and len(chain) < 6:
        chain.append(_safe(parent.objectName, "") or _class_of(parent))
        parent = _safe(parent.parent)
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
    limit = _clamp_int(p.get("limit", 50), 1, 200, 50)
    visible_only = p.get("visible_only", True) is not False
    ancestor = str(p.get("ancestor") or "").lower()
    out: list[dict[str, Any]] = []
    total = 0
    for w in _qt().QApplication.allWidgets():
        wname = _safe(w.objectName, "")
        if name and wname != name:
            continue
        if contains and str(contains).lower() not in wname.lower():
            continue
        if cls and str(cls).lower() not in (_class_of(w).lower(), type(w).__name__.lower()):
            continue
        if text and str(text).lower() not in clean_text(_safe(lambda: w.text(), "")).lower():
            continue
        if visible_only and not _safe(w.isVisible, False):
            continue
        state = widget_state(w)
        if ancestor and ancestor not in state["path"].lower():
            continue
        total += 1
        if len(out) < limit:
            out.append(state)
    return {"success": True, "count": total, "shown": len(out), "widgets": out}


# --- windows: report and grab ------------------------------------------------------------

def _png_bytes(q: Any, image: Any) -> bytes | None:
    """A QPixmap or QImage as PNG bytes, through a QBuffer."""
    array = q.QByteArray()
    buffer = q.QBuffer(array)
    buffer.open(q.QIODevice.WriteOnly)
    ok = image.save(buffer, "PNG")
    buffer.close()
    return bytes(array.data()) if ok else None


def grab_png(widget: Any, max_width: int = 900) -> dict[str, Any]:
    """QWidget.grab() as base64 PNG, scaled down until it fits PNG_MAX_BYTES."""
    q = _qt()
    pixmap = widget.grab()
    if _safe(pixmap.isNull, True):
        return {"error": "grab returned an empty image"}
    width = pixmap.width()
    target = min(width, max_width) if max_width else width
    for _ in range(4):
        shot = pixmap if target >= width else pixmap.scaledToWidth(target, q.Qt.SmoothTransformation)
        data = _png_bytes(q, shot)
        if data is not None and len(data) <= PNG_MAX_BYTES:
            return {"png_base64": base64.b64encode(data).decode("ascii"),
                    "png_size": [shot.width(), shot.height()]}
        target = max(200, target // 2)
    return {"error": "image too large to return"}


def ui_windows(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/windows: the windows CC5 has open right now (read-only).

    Body: screenshot (PNG of each, default false), max_width (default 900), target
    "dialogs" (default) | "main" (also the main window) , include_other (floating tool windows).
    Works while a question window is open (the bridge still drains its queue in the modal loop).
    """
    p = body or {}
    shoot = bool(p.get("screenshot", False))
    max_width = _clamp_int(p.get("max_width", 900), 200, 2400, 900)
    windows: list[dict[str, Any]] = []
    for index, (info, w) in enumerate(scan_windows(bool(p.get("include_other", False)))):
        entry = {"index": index, **info}
        decision = decide(info, dict(DEFAULT_CHOICES)) or {}
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
    q = _qt()
    for w in q.QApplication.instance().topLevelWidgets():
        if isinstance(w, q.QMainWindow) and _safe(w.isVisible, False):
            report: dict[str, Any] = {"title": clean_text(_safe(w.windowTitle, ""))}
            if shoot:
                report.update(grab_png(w, max_width))
            return report
    return {"error": "main window not found"}


# --- framed capture: render big, cut a fixed box ----------------------------------------

def _crop_box(p: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int] | None:
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


def _capture_crop_steps(p: dict[str, Any]) -> Iterator[float]:
    api = _api()
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
                f"{p['size']}x{p['size']} render; the crop would not be comparable. {cap.get('warning', '')}"}
    q = _qt()
    image = q.QImage(full_path)
    if _safe(image.isNull, True):
        return {"success": False, "path": full_path, "error": "cannot read the capture back as an image"}
    width, height = image.width(), image.height()
    out: dict[str, Any] = {"success": True, "view": p["view"], "full_path": full_path,
                           "render_size": [width, height]}
    if (width, height) != (p["size"], p["size"]):
        out["warning"] = f"asked {p['size']}x{p['size']} but the render is {width}x{height}"
    box = _crop_box(p, width, height)
    if box is None:
        if p.get("crop") is not None or p.get("crop_fraction") is not None:
            return {"success": False, "path": full_path, "error": f"crop box is outside the {width}x{height} render"}
        return out
    x0, y0, x1, y1 = box
    piece = image.copy(q.QRect(x0, y0, x1 - x0, y1 - y0))
    if not piece.save(p["output_path"], "PNG"):
        return {"success": False, "error": f"cannot save the crop to {p['output_path']}"}
    out.update({"crop_path": p["output_path"], "crop_box": [x0, y0, x1, y1], "crop_size": [x1 - x0, y1 - y0]})
    data = _png_bytes(q, piece)
    if data is not None and len(data) <= PNG_MAX_BYTES:
        out["png_base64"] = base64.b64encode(data).decode("ascii")
    return out


def ui_capture_crop(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/capture_crop: frame the face, render BIG, cut a fixed box. Starts a job.

    Same framing every time (no dolly), so crops of different options are the same scale.
    Body: view (default "face"), size (default 3600, square), crop [x0,y0,x1,y1] in render
    pixels OR crop_fraction [x0,y0,x1,y1] in 0..1, output_path (.png, default temp),
    full_path (.png, default temp), settle_ms (default 800).
    """
    p = dict(body or {})
    api = _api()
    p["view"] = str(p.get("view") or "face")
    p["size"] = _clamp_int(p.get("size", 3600), 256, 8192, 3600)
    p["settle_ms"] = _clamp_int(p.get("settle_ms", 800), 0, 10000, 800)
    tmp = tempfile.gettempdir()
    p["output_path"] = str(p.get("output_path") or os.path.join(tmp, "cc5_framed_crop.png")).replace("\\", "/")
    p["full_path"] = str(p.get("full_path") or os.path.join(tmp, "cc5_framed_full.png")).replace("\\", "/")
    for key in ("output_path", "full_path"):
        error = api._validate_path(p[key], {".png"})
        if error:
            return {"success": False, "error": f"{key}: {error}"}
    for key in ("crop", "crop_fraction"):
        value = p.get(key)
        if value is not None and not (isinstance(value, (list, tuple)) and len(value) == 4):
            return {"success": False, "error": f"{key} must be 4 numbers [x0, y0, x1, y1]"}
    return start_job("crop", lambda params: _capture_crop_steps(params), p)


ROUTES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "/ui/windows": ("ui_windows", ui_windows),
    "/ui/widgets": ("ui_widgets", ui_widgets),
    "/ui/job": ("ui_job", ui_job),
    "/ui/capture_crop": ("ui_capture_crop", ui_capture_crop),
}
