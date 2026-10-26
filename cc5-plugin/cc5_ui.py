"""
Qt-side core for working CC5's own windows without a mouse (jobs, windows, the few answers we allow).

Built from what worked on 2026-10-26 (eyelash presets, SkinGen lip makeup; see
docs/ui-automation-test-steps_ja.md):

  * answer the few question windows a script causes, and ONLY those (WINDOW_RULES);
    licence / purchase / login / update / terms windows are never pressed, and while one is open
    nothing is pressed at all;
  * long UI work runs as a "job": the bridge call returns at once and the work goes on in CC5's
    Qt event loop, one small step at a time, so the bridge keeps answering (list windows, read
    state) while a question window is open or CC5 is baking; other bridge commands are refused
    while a job runs (install_job_guard) because RLPy is not re-entrant;
  * read the visible windows (title, text, buttons, check boxes) as plain data.

Companions: cc5_uiview.py (widget finder, window pictures, framed capture), cc5_skingen.py,
cc5_content.py. All are loaded by cc5_api (_load_ui_modules); none may import cc5_api at module
level. PySide2 is imported lazily (_qt) so the logic runs in tests.
"""

from __future__ import annotations

import dataclasses
import html
import inspect
import os
import re
import sys
import time
import types
import unicodedata
from typing import Any, Callable, Iterator

import RLPy  # noqa: F401  (kept so the module fails the same way as cc5_api outside CC5)

# --- constants ---------------------------------------------------------------------------

# Window text that means "CC5 is busy, this goes away by itself" (taken from the lip run).
BUSY_WORDS = ("baking", "please wait", "mipmap", "processing", "loading", "dynamic", "generating")

MAX_TEXT_CHARS = 400                # window text returned to callers
MAX_FULL_CHARS = 6000               # window text used for the safety check
LONG_TEXT_CHARS = 600               # a text box this long is a licence / terms document
JOB_KEEP = 30                       # finished jobs kept for /ui/job
JOB_STALE_SECONDS = 900             # a "running" job older than this (unless it says more) no longer blocks
ANSWERER_MAX_SECONDS = 600          # the answering timer stops itself after this (jobs pass their own)
MAX_PRESSES_PER_WINDOW = 3          # the same window pressed more often than this is stuck
MAX_TOTAL_PRESSES = 60              # presses per answerer run
PRESS_PROPERTY = "cc5_ui_presses"   # Qt dynamic property that counts presses on a window

_HTML_TAGS = ("html|head|body|style|p|div|span|a|b|i|u|s|em|strong|small|big|sub|sup|br|hr|center|font|h[1-6]|ul|ol|li"
              "|table|tr|td|th|tbody|thead|img|code|pre|blockquote|nobr")
_TAG_RE = re.compile(r"</?(?:" + _HTML_TAGS + r")(?:\s[^>]*)?/?>", re.IGNORECASE)
MAX_RAW_CHARS = 8000                # one label is cut here before the tag regex runs
# Typographic characters that may appear in the plain-English windows we answer.
_TYPOGRAPHIC_OK = frozenset("\u2018\u2019\u201c\u201d\u2026\u00a0\u2013\u2014\u00b7")


# --- the safety word list ----------------------------------------------------------------

def norm(text: Any) -> str:
    """Text for comparing: NFKD, no combining marks / invisible format characters, case-folded.
    (So 'LİCENSE', 'Lic­ense' and full-width letters all read as plain 'license'.)"""
    decomposed = unicodedata.normalize("NFKD", "" if text is None else str(text))
    kept = "".join(ch for ch in decomposed if unicodedata.category(ch) not in ("Mn", "Cf") and ch != "&")
    return kept.casefold()


# Stems matched at the start of a word (so 'industrial' does not match 'trial').
_WORD_STEMS = (
    "licen", "purchas", "repurchas", "buy", "log in", "log-in", "login", "logging in", "sign in", "sign-in",
    "signin", "password", "passcode", "updat", "upgrad", "agree", "terms", "eula", "activat", "deactivat",
    "reactivat", "subscri", "unsubscri", "payment", "checkout", "credit card", "trial", "serial", "register",
    "renew", "redeem", "coupon", "unlock", "account", "bought", "billing", "invoice", "refund", "premium", "expire",
    "product key", "authoriz", "membership", "voucher", "sign up", "log out", "logged", "lizenz", "kaufen", "passwort",
    "aktualisier", "acheter", "mise a jour", "mot de passe", "comprar", "contrasena", "actualiz", "лицензи",
)
# Strong stems also searched with spaces and punctuation removed ('Lic ense', 'Lic<b>ense</b>').
_COMPACT_STEMS = ("licen", "purchas", "password", "login", "subscri", "payment", "checkout", "eula")
# Japanese: no word boundaries, matched anywhere (after norm(), which drops the dakuten marks).
_JAPANESE_STEMS = ("ライセンス", "購入", "購買", "ログイン", "サインイン", "更新", "アップデート", "規約", "同意",
                   "決済", "支払", "認証", "有効化", "アクティベ", "試用", "体験版", "パスワード", "シリアル",
                   "登録", "会員", "課金", "契約",
                   "라이선스", "구매", "로그인", "비밀번호", "업데이트", "许可证", "授权", "购买", "登录", "密码")

_WORD_RE = re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(norm(s)) for s in _WORD_STEMS) + ")")
_COMPACT_NEEDLES = tuple(norm(s) for s in _COMPACT_STEMS)
_JAPANESE_NEEDLES = tuple(norm(s) for s in _JAPANESE_STEMS)


def forbidden_reason(*parts: Any) -> str | None:
    """The word that makes a window off limits (licence, purchase, login, ...), or None."""
    text = norm(" ".join(str(p) for p in parts if p))
    match = _WORD_RE.search(text)
    if match:
        return match.group(0).strip()
    compact = re.sub(r"[\W_]+", "", text)
    for needle in _COMPACT_NEEDLES:
        if needle in compact:
            return needle
    for needle in _JAPANESE_NEEDLES:
        if needle in text:
            return needle
    return None


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
        QLineEdit=QtWidgets.QLineEdit, QTextEdit=QtWidgets.QTextEdit,
        QPlainTextEdit=QtWidgets.QPlainTextEdit, QGroupBox=QtWidgets.QGroupBox,
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
    text = "" if value is None else str(value)[:MAX_RAW_CHARS]
    text = html.unescape(_TAG_RE.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def _squash_tags(value: Any) -> str:
    """The same text with tags removed WITHOUT a space ('Act<b>ivate</b>' -> 'Activate'), for the safety check."""
    return html.unescape(_TAG_RE.sub("", "" if value is None else str(value)[:MAX_RAW_CHARS]))


def label_text(widget: Any) -> str:
    """A button's text without the & shortcut marker."""
    return clean_text(_safe(widget.text, "")).replace("&", "")


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError, OverflowError):
        return default


def path_problem(path: Any, allowed_exts: Any) -> str | None:
    """Why a file path is refused (null byte, '..', network or stream path, wrong extension), or None."""
    text = str(path or "").replace("\\", "/").strip()
    if not text:
        return "empty path"
    if text.startswith("//"):
        return "network (UNC) paths are not allowed"
    rest = text[2:] if re.match(r"^[A-Za-z]:/", text) else text
    if ":" in rest:
        return "a ':' inside the path is not allowed (drive letter only)"
    return _api()._validate_path(text, set(allowed_exts))


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

def _texts(w: Any, cls: Any, getter: str) -> list[str]:
    """Visible, non-empty, unique texts of the children of one class."""
    out: list[str] = []
    for child in _safe(lambda: w.findChildren(cls), []):
        if not _safe(child.isVisible, True):
            continue
        text = clean_text(_safe(getattr(child, getter), ""))
        if text and text not in out:
            out.append(text)
    return out


def describe_window(w: Any, q: Any = None) -> dict[str, Any]:
    """Title, text, buttons and check boxes of one top-level window, as plain data.

    Keys starting with '_' are private (the full text used for the safety check): use
    public_info() before returning a description to a caller.
    """
    q = q or _qt()
    title = clean_text(_safe(w.windowTitle, ""))
    labels = _texts(w, q.QLabel, "text")
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
    other = _group_titles(w, q)
    long_text, secret = False, False
    for cls in (q.QTextEdit, q.QPlainTextEdit):          # QTextBrowser is a QTextEdit
        for edit in _safe(lambda cls=cls: w.findChildren(cls), []):
            body = clean_text(_safe(edit.toPlainText, ""))
            other.append(body)
            long_text = long_text or len(body) > LONG_TEXT_CHARS
    for line in _safe(lambda: w.findChildren(q.QLineEdit), []):
        secret = secret or _safe(line.echoMode, q.QLineEdit.Normal) != q.QLineEdit.Normal
        other.append(clean_text(_safe(line.placeholderText, "")))
    text = " ".join(labels)
    full = " ".join([title, text, *buttons, *(b["text"] for b in boxes), *other])
    squashed = " ".join(_squash_tags(_safe(c.text, "")) for c in _safe(lambda: w.findChildren(q.QLabel), []))
    needs_human = (forbidden_reason(full[:MAX_FULL_CHARS], squashed[:MAX_FULL_CHARS])
                   or ("password field" if secret else None)
                   or ("long text (a licence or terms?)" if long_text else None)
                   or ("text too long to check" if len(full) > MAX_FULL_CHARS else None))
    full = full[:MAX_FULL_CHARS]
    lowered = norm(f"{title} {text}")
    progress = not needs_human and (
        bool(_safe(lambda: w.findChildren(q.QProgressBar), [])) or any(word in lowered for word in BUSY_WORDS))
    rect = _safe(w.geometry)
    return {
        "title": title,
        "class": _safe(lambda: w.metaObject().className(), type(w).__name__),
        "text": text[:MAX_TEXT_CHARS],
        "buttons": buttons,
        "checkboxes": boxes,
        "modal": bool(_safe(w.isModal, False)),
        "progress": progress,
        "geometry": [rect.x(), rect.y(), rect.width(), rect.height()] if rect is not None else None,
        "needs_human": needs_human,
        "dialog": True,
        "_full": full,
    }


def _group_titles(w: Any, q: Any) -> list[str]:
    return [t for t in (clean_text(_safe(g.title, "")) for g in _safe(lambda: w.findChildren(q.QGroupBox), [])) if t]


def public_info(info: dict[str, Any]) -> dict[str, Any]:
    """A window description without the private keys, safe to return to a caller."""
    return {k: v for k, v in info.items() if not k.startswith("_")}


def window_key(info: dict[str, Any]) -> tuple[str, str, str]:
    """What identifies a window across polls (a new question under the same title is a new window)."""
    return (info["title"], info["class"], info["text"][:120])


def scan_windows(include_other: bool = False) -> list[tuple[dict[str, Any], Any]]:
    """Visible top-level windows with something in them, as (description, widget); never the main
    window or a menu. Dialogs (QDialog or modal) always; other windows only when include_other."""
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
        info["dialog"] = is_dialog
        if not (info["text"] or info["buttons"] or info["checkboxes"] or info["progress"]):
            continue                              # empty frames, tool tips, drag handles, ...
        found.append((info, w))
    return found


def baseline_keys() -> set[tuple[str, str, str]]:
    """Windows already open now (and harmless): a job does not wait for those."""
    return {window_key(info) for info, _w in scan_windows() if not info["needs_human"]}


# --- windows: the answers we allow -------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class WindowRule:
    """A question window we may answer. A window matches when its title is one of `titles`
    (exact, normalised) and/or its text has `text_has`, and its buttons are within `allowed`."""

    key: str                                    # name of the caller's choice
    titles: tuple[str, ...]
    text_has: str
    allowed: frozenset[str] | None              # every button must be one of these (None: any)
    answers: tuple[str, ...]                    # buttons the caller may select
    default: str


# The ONLY windows that are ever answered automatically.
WINDOW_RULES: tuple[WindowRule, ...] = (
    WindowRule("layer_choice", (), "add a new layer or replace", frozenset({"add", "replace", "cancel"}),
               ("replace", "add"), "replace"),
    WindowRule("skingen_exit", (), "exit skingen editing mode", frozenset({"yes", "no", "cancel"}),
               ("yes", "no"), "yes"),
    WindowRule("apply_preset", ("apply character preset", "apply eyelash elements"), "", None,
               ("apply",), "apply"),
)
RESTORE_LASH_FRAGMENT = "neutral lash"          # "Restore neutral lash strip" check box
DEFAULT_CHOICES: dict[str, Any] = {"layer_choice": "replace", "skingen_exit": "yes", "restore_neutral_lash": True}


def normalize_choices(raw: Any = None) -> dict[str, Any]:
    """Validate the caller's answers. Unknown keys and values are refused, not ignored."""
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("answers must be an object like {\"layer_choice\": \"replace\"}")
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


def _plain_english(text: str) -> bool:
    """ASCII plus a few typographic marks: the windows we answer are plain English, so look-alike letters
    (Cyrillic, Greek, ...) mean it is not one of ours."""
    return all(ord(ch) < 128 or ch in _TYPOGRAPHIC_OK for ch in text)


def decide(info: dict[str, Any], choices: dict[str, Any]) -> dict[str, Any] | None:
    """What to do with one window: {"rule", "press", "ticks"}, or {"rule", "blocked"}, or None
    (not one of ours)."""
    title = " ".join(norm(info["title"]).split())
    haystack = norm(info.get("_full") or info["text"])
    buttons = {norm(label) for label in info["buttons"]}
    for rule in WINDOW_RULES:
        if rule.titles and title not in rule.titles:
            continue
        if rule.text_has and rule.text_has not in haystack:
            continue
        if not rule.titles and not rule.text_has:
            continue
        if rule.allowed is not None and not buttons <= rule.allowed:
            continue                            # a window of another shape that mentions the question
        if info.get("needs_human"):
            return {"rule": rule.key, "blocked": f"window mentions '{info['needs_human']}': a person must decide"}
        if not (_plain_english(info["title"]) and _plain_english(info.get("_full") or info["text"])):
            return {"rule": rule.key, "blocked": "the window text has characters outside plain English: a person must look"}
        want = rule.default if rule.key == "apply_preset" else choices.get(rule.key, rule.default)
        if want not in buttons:
            return {"rule": rule.key, "blocked": f"no '{want}' button (buttons: {info['buttons']})"}
        decision: dict[str, Any] = {"rule": rule.key, "press": want}
        if rule.key == "apply_preset":
            decision["ticks"] = [(RESTORE_LASH_FRAGMENT, bool(choices.get("restore_neutral_lash", True)))]
        return decision
    return None


def _press_count(w: Any) -> int:
    return _clamp_int(_safe(lambda: w.property(PRESS_PROPERTY)), 0, 10_000, 0)


def _same_widget(a: Any, b: Any) -> bool:
    return a is b or bool(_safe(lambda: a == b, False))


class WindowAnswerer:
    """A repeating Qt timer that answers WINDOW_RULES windows while a script runs.

    The timer fires inside CC5's nested event loops too, so it works while LoadFile or a modal
    question blocks the caller. It never presses anything while a window that needs a person is
    open, stops itself after max_seconds (touch() restarts the clock), and gives up on a window
    it has pressed MAX_PRESSES_PER_WINDOW times.
    """

    def __init__(self, choices: dict[str, Any], interval_ms: int = 250,
                 max_seconds: float = ANSWERER_MAX_SECONDS, max_presses: int = MAX_TOTAL_PRESSES) -> None:
        self.choices = choices
        self.interval_ms = interval_ms
        self.max_seconds = max_seconds
        self.max_presses = max_presses
        self.log: list[dict[str, Any]] = []
        self.blocked: list[dict[str, Any]] = []
        self._timer: Any = None
        self._started = 0.0

    def start(self) -> "WindowAnswerer":
        stop_active_answerer()                    # never two pressers at once
        q = _qt()
        self._started = _now()
        self._timer = q.QTimer()
        self._timer.timeout.connect(self.tick)
        self._timer.start(self.interval_ms)
        _holder()._cc5_ui_answerer = self         # keeps the timer alive after the caller returns
        return self

    def touch(self) -> None:
        """Restart the time limit (a long batch calls this before each file)."""
        self._started = _now()

    def stop(self) -> list[dict[str, Any]]:
        if self._timer is not None:
            _safe(self._timer.stop)
            self._timer = None
        holder = _holder()
        if getattr(holder, "_cc5_ui_answerer", None) is self:
            holder._cc5_ui_answerer = None
        return list(self.log)

    def _note(self, info: dict[str, Any], why: str) -> None:
        if not any(b["title"] == info["title"] and b["why"] == why for b in self.blocked):
            self.blocked.append({"title": info["title"], "why": why})

    def tick(self) -> None:
        if self._timer is None:
            return
        if _now() - self._started > self.max_seconds:
            self.stop()
            return
        try:
            windows = scan_windows(include_other=True)
            for info, _w in windows:
                if info["dialog"] and info["needs_human"]:
                    self._note(info, f"mentions '{info['needs_human']}': nothing is pressed while it is open")
                    return
            for info, w in windows:
                decision = decide(info, self.choices)
                if decision is None:
                    continue
                if "blocked" in decision:
                    self._note(info, decision["blocked"])
                    continue
                if len(self.log) >= self.max_presses:
                    self._note(info, f"already pressed {self.max_presses} times in this run")
                    return
                if self._answer(info, w, decision):
                    return                        # one answer per tick, like the verified script
        except Exception as exc:                  # a timer callback must never raise
            print(f"[CC5 MCP Bridge] answerer tick failed: {exc}")

    def _answer(self, info: dict[str, Any], w: Any, decision: dict[str, Any]) -> bool:
        q = _qt()
        count = _press_count(w)
        if count >= MAX_PRESSES_PER_WINDOW:
            self._note(info, f"pressed {count} times and still open")
            return False
        for fragment, want in decision.get("ticks", []):
            for box in _safe(lambda: w.findChildren(q.QCheckBox), []):
                if (fragment in norm(label_text(box)) and _safe(box.isVisible, True) and _safe(box.isEnabled, True)
                        and _same_widget(_safe(box.window), w) and bool(box.isChecked()) != want):
                    box.setChecked(want)
        for b in _safe(lambda: w.findChildren(q.QAbstractButton), []):
            if isinstance(b, (q.QCheckBox, q.QRadioButton)) or not _same_widget(_safe(b.window), w):
                continue
            if norm(label_text(b)) == decision["press"] and _safe(b.isVisible, True) and _safe(b.isEnabled, True):
                _safe(lambda: w.setProperty(PRESS_PROPERTY, count + 1))
                self.log.append({"rule": decision["rule"], "pressed": decision["press"],
                                 "window": info["title"], "text": info["text"][:80]})
                b.click()
                return True
        return False


def stop_active_answerer() -> None:
    """Stop the running answerer, if any (a job that must answer nothing calls this first)."""
    previous = getattr(_holder(), "_cc5_ui_answerer", None)
    if previous is not None:
        previous.stop()


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
        if job["state"] in ("queued", "running") and _now() - job["started"] < job.get("max_seconds", JOB_STALE_SECONDS):
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
        _later(max(0.0, float(delay)), lambda: _advance(job, gen))
    except StopIteration as stop:
        _finish(job, stop.value)
    except Exception as exc:
        gen.close()                               # runs the generator's finally blocks
        _fail(job, exc)


def start_job(kind: str, make: Callable[[dict[str, Any]], Any], params: dict[str, Any],
              max_seconds: float | None = None) -> dict[str, Any]:
    """Queue make(params) to run on the Qt main thread. make returns a dict, or is a generator
    that yields waits (ms) and returns the result dict. One job at a time. max_seconds is how
    long the job may take (after that it no longer blocks the next job)."""
    busy = running_job()
    if busy is not None:
        return {"success": False, "error": f"another UI job is still running: {busy['id']} ({busy['kind']}); "
                                           "wait for it (/ui/job, tool get_ui_job) before starting the next"}
    jobs = _jobs()
    job: dict[str, Any] = {"id": f"{kind}-{_next_job_number()}", "kind": kind, "state": "queued",
                           "started": _now(), "finished": None, "result": None,
                           "max_seconds": float(max_seconds or JOB_STALE_SECONDS)}
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

    try:
        _later(0, begin)
    except Exception as exc:
        _fail(job, exc)
        return {"success": False, "error": f"could not schedule the job: {exc}"}
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
        out["windows"] = [{k: public_info(info)[k] for k in ("title", "text", "buttons", "progress", "needs_human")}
                          for info, _w in scan_windows()][:5]
    return out


# While a job runs, other bridge commands are refused: LoadFile and the bake run nested Qt event
# loops, and the bridge's own timer would otherwise run other RLPy calls inside them.
GUARD_ALLOWED = frozenset({"ui_job", "ui_windows", "ui_widgets", "ui_skingen_state"})
GUARD_SKIP = GUARD_ALLOWED | {"ui_apply_preset", "ui_skingen_editor", "ui_skingen_layer", "ui_capture_crop",
                              "ui_modules_missing"}


def job_guard_message(action: str) -> str | None:
    """Why `action` must wait because a UI job is running, or None."""
    if action in GUARD_ALLOWED or os.environ.get("CC5_UI_JOB_GUARD", "1") == "0":
        return None
    job = running_job()
    if job is None:
        return None
    return (f"CC5 is busy with the UI job {job['id']} ({job['kind']}); '{action}' was NOT run. "
            "Read progress with /ui/job (tool get_ui_job) or /ui/windows, and send this again when it is done. "
            "(CC5_UI_JOB_GUARD=0 turns this check off.)")


def install_job_guard(action_map: dict[str, Callable[..., Any]]) -> None:
    """Wrap every bridge action (except the read-only UI ones) with the job guard. Safe to repeat."""
    def guarded(action: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(params: Any) -> Any:
            message = job_guard_message(action)
            if message:
                return {"success": False, "error": message}
            return fn(params)

        wrapper._cc5_guarded = fn                  # type: ignore[attr-defined]
        return wrapper

    for action, handler in list(action_map.items()):
        original = getattr(handler, "_cc5_guarded", handler)
        action_map[action] = original if action in GUARD_SKIP else guarded(action, original)


# --- waiting until CC5 is quiet ----------------------------------------------------------

def settle_steps(limit_s: float, choices: dict[str, Any], extra_ok: Callable[[], bool] | None = None,
                 quiet_needed: int = 2, poll_ms: int = 1000, grace_s: float = 4.0,
                 answerable: bool = True, baseline: set[tuple[str, str, str]] | None = None) -> Iterator[float]:
    """Generator (use with `yield from`): wait until no window is open for quiet_needed polls in a
    row. A window that needs a person stops the wait at once; progress windows (baking, loading)
    are waited out; a question the answerer will press is waited out (answerable=False: nothing
    is answered, so it stops the wait too); any other window stops the wait after grace_s;
    windows in `baseline` (open before the job began) are ignored. The time limit counts the
    polls, not the minutes CC5 spent frozen. Returns {"ok", "waited_s", "blocked_by"}."""
    waited = 0.0
    last = _now()
    quiet = 0
    unknown_for = 0.0
    while waited < limit_s:
        now = _now()
        step = min(now - last, 2 * poll_ms / 1000.0)
        last = now
        waited += max(step, 0.0)
        windows = [(i, w) for i, w in scan_windows()
                   if i["needs_human"] or baseline is None or window_key(i) not in baseline]
        stuck = next((i for i, _w in windows if i["needs_human"]), None)
        if stuck is None:
            for info, w in windows:
                if info["progress"]:
                    continue
                decision = decide(info, choices) if answerable else None
                if decision is not None and "press" in decision and _press_count(w) < MAX_PRESSES_PER_WINDOW:
                    continue
                stuck = info
                break
        if stuck is not None:
            unknown_for += max(step, 0.0)
            if stuck["needs_human"] or unknown_for >= grace_s:
                return {"ok": False, "waited_s": round(waited, 1), "blocked_by": public_info(stuck)}
        else:
            unknown_for = 0.0
        if not windows and (extra_ok is None or _safe(extra_ok, False)):
            quiet += 1
            if quiet >= quiet_needed:
                return {"ok": True, "waited_s": round(waited, 1), "blocked_by": None}
        else:
            quiet = 0
        yield poll_ms
    return {"ok": False, "waited_s": round(waited, 1), "blocked_by": None, "timeout": True}


def settle_error(settled: dict[str, Any]) -> str:
    """One sentence for a settle_steps result that is not ok."""
    blocked = settled.get("blocked_by")
    if blocked:
        return (f"a window needs a person: '{blocked['title']}' {blocked['text'][:120]!r} "
                f"(buttons: {blocked['buttons']}). Not answered on purpose.")
    return "CC5 was still busy when the time limit ran out"


# --- widgets: lookup by name -------------------------------------------------------------

def _class_of(w: Any) -> str:
    return str(_safe(lambda: w.metaObject().className(), type(w).__name__))


def find_by_names(names: Any) -> dict[str, list[Any]]:
    """One pass over every widget: {objectName: [widgets, visible ones first]} for the names given."""
    wanted = set(names)
    hits: dict[str, list[Any]] = {name: [] for name in wanted}
    for w in _qt().QApplication.allWidgets():
        name = _safe(w.objectName, "")
        if name in wanted:
            hits[name].append(w)
    for found in hits.values():
        found.sort(key=lambda w: 0 if _safe(w.isVisible, False) else 1)
    return hits


def find_by_name(object_name: str, within: Any = None) -> list[Any]:
    """Every widget with this objectName (under `within` when given); visible ones first."""
    if within is None:
        return find_by_names([object_name])[object_name]
    q = _qt()
    found = [w for w in _safe(lambda: within.findChildren(q.QWidget), []) if _safe(w.objectName, "") == object_name]
    found.sort(key=lambda w: 0 if _safe(w.isVisible, False) else 1)
    return found


ROUTES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "/ui/job": ("ui_job", ui_job),
}
