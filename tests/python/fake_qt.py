"""
A tiny stand-in for the parts of PySide2 that cc5_ui / cc5_skingen use, so their logic
runs under plain CPython (no CC5, no Qt). Widgets keep their state in plain attributes.

Usage in a test:

    import fake_qt
    q = fake_qt.make_qt()                         # namespace with QApplication, QDialog, ...
    with mock.patch.object(cc5_ui, "_qt", return_value=q):
        ...
"""

from __future__ import annotations

import types
from typing import Any, Callable


class Signal:
    """Records connected callbacks; emit() calls them."""

    def __init__(self) -> None:
        self.slots: list[Callable[..., Any]] = []

    def connect(self, fn: Callable[..., Any]) -> None:
        self.slots.append(fn)

    def emit(self, *args: Any) -> None:
        for fn in list(self.slots):
            fn(*args)


class Widget:
    """Base fake widget: a tree with objectName, visibility and a window title."""

    def __init__(self, name: str = "", title: str = "", visible: bool = True, parent: "Widget | None" = None) -> None:
        self._name = name
        self._title = title
        self._visible = visible
        self._parent = parent
        self.children: list[Widget] = []
        self._enabled = True
        self._modal = False
        self.grabbed = 0
        self._props: dict[str, Any] = {}
        if parent is not None:
            parent.children.append(self)
        Widget.registry.append(self)

    registry: list["Widget"] = []

    # --- tree ---
    def parent(self) -> "Widget | None":
        return self._parent

    _is_window = False

    def window(self) -> "Widget":
        """The nearest ancestor (or self) that is a top-level window, as in Qt."""
        node = self
        while not node._is_window and node._parent is not None:
            node = node._parent
        return node

    def property(self, name: str) -> Any:
        return self._props.get(name)

    def setProperty(self, name: str, value: Any) -> bool:
        self._props[name] = value
        return True

    def objectName(self) -> str:
        return self._name

    def windowTitle(self) -> str:
        return self._title

    def isVisible(self) -> bool:
        return self._visible

    def isEnabled(self) -> bool:
        return self._enabled

    def isModal(self) -> bool:
        return self._modal

    def findChildren(self, cls: type) -> list["Widget"]:
        out: list[Widget] = []
        for child in self.children:
            if isinstance(child, cls):
                out.append(child)
            out.extend(child.findChildren(cls))
        return out

    def metaObject(self) -> Any:
        return types.SimpleNamespace(className=lambda: type(self).__name__)

    def geometry(self) -> Any:
        return types.SimpleNamespace(x=lambda: 10, y=lambda: 20, width=lambda: 300, height=lambda: 120)

    def grab(self) -> "Pixmap":
        self.grabbed += 1
        return Pixmap(300, 120)


class Pixmap:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h

    def isNull(self) -> bool:
        return False

    def width(self) -> int:
        return self.w

    def height(self) -> int:
        return self.h

    def scaledToWidth(self, width: int, _mode: Any = None) -> "Pixmap":
        return Pixmap(width, max(1, round(self.h * width / self.w)))

    def save(self, target: Any, _fmt: str = "PNG") -> bool:
        # A QBuffer target gets some bytes whose length follows the pixel count.
        if hasattr(target, "write_bytes"):
            target.write_bytes(b"PNG" + bytes(self.w * self.h // 100))
        return True


class MainWindow(Widget):
    _is_window = True


class Dialog(Widget):
    _is_window = True


class Menu(Widget):
    pass


class Label(Widget):
    def __init__(self, text: str, parent: Widget, name: str = "", visible: bool = True) -> None:
        super().__init__(name=name, parent=parent, visible=visible)
        self._text = text

    def text(self) -> str:
        return self._text


class AbstractButton(Widget):
    def __init__(self, text: str, parent: Widget, name: str = "", visible: bool = True, checked: bool = False) -> None:
        super().__init__(name=name, parent=parent, visible=visible)
        self._text = text
        self._checked = checked
        self.clicks = 0
        self.on_click: Callable[[], None] | None = None

    def text(self) -> str:
        return self._text

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        self._checked = bool(value)

    def click(self) -> None:
        self.clicks += 1
        if self.on_click:
            self.on_click()


class PushButton(AbstractButton):
    pass


class ToolButton(AbstractButton):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._menu: Menu | None = None

    def menu(self) -> "Menu | None":
        return self._menu


class CheckBox(AbstractButton):
    pass


class RadioButton(AbstractButton):
    pass


class ProgressBar(Widget):
    pass


class GroupBox(Widget):
    def __init__(self, title: str, parent: Widget) -> None:
        super().__init__(parent=parent)
        self._group_title = title

    def title(self) -> str:
        return self._group_title


class LineEdit(Widget):
    Normal = 0
    Password = 2

    def __init__(self, parent: Widget, text: str = "", echo: int = 0, placeholder: str = "", name: str = "") -> None:
        super().__init__(name=name, parent=parent)
        self._text, self._echo, self._placeholder = text, echo, placeholder

    def text(self) -> str:
        return self._text

    def echoMode(self) -> int:
        return self._echo

    def placeholderText(self) -> str:
        return self._placeholder


class TextEdit(Widget):
    def __init__(self, parent: Widget, text: str = "") -> None:
        super().__init__(parent=parent)
        self._text = text

    def toPlainText(self) -> str:
        return self._text


class PlainTextEdit(TextEdit):
    pass


class Action:
    def __init__(self, text: str, enabled: bool = True, on_trigger: Callable[[], None] | None = None) -> None:
        self._text = text
        self._enabled = enabled
        self.triggered = 0
        self.on_trigger = on_trigger

    def text(self) -> str:
        return self._text

    def isEnabled(self) -> bool:
        return self._enabled

    def trigger(self) -> None:
        self.triggered += 1
        if self.on_trigger:
            self.on_trigger()


class ActionMenu(Menu):
    def __init__(self, actions: list[Action], parent: Widget | None = None) -> None:
        super().__init__(parent=parent)
        self._actions = actions

    def actions(self) -> list[Action]:
        return self._actions


class SpinBox(Widget):
    def __init__(self, parent: Widget, name: str = "", value: int = 100, lo: int = 0, hi: int = 100) -> None:
        super().__init__(name=name, parent=parent)
        self._value, self._lo, self._hi = value, lo, hi
        self.editingFinished = Signal()

    def value(self) -> int:
        return self._value

    def minimum(self) -> int:
        return self._lo

    def maximum(self) -> int:
        return self._hi

    def setValue(self, v: int) -> None:
        self._value = max(self._lo, min(self._hi, int(v)))


class ComboBox(Widget):
    def __init__(self, parent: Widget, name: str = "", text: str = "") -> None:
        super().__init__(name=name, parent=parent)
        self._text = text

    def currentText(self) -> str:
        return self._text


class _Selection:
    def __init__(self, table: "Table") -> None:
        self.table = table

    def selectedRows(self) -> list[Any]:
        return [types.SimpleNamespace(row=lambda r=r: r) for r in self.table.selected]


class Table(Widget):
    """Rows hold one cell widget each (like SkinGen's layer table)."""

    def __init__(self, parent: Widget, name: str = "") -> None:
        super().__init__(name=name, parent=parent)
        self.cells: list[Widget] = []
        self.selected: list[int] = []
        self.select_calls: list[int] = []

    def rowCount(self) -> int:
        return len(self.cells)

    def cellWidget(self, row: int, _col: int) -> Widget:
        return self.cells[row]

    def selectRow(self, row: int) -> None:
        self.select_calls.append(row)
        self.selected = [row]

    def currentRow(self) -> int:
        return self.selected[0] if self.selected else -1

    def selectionModel(self) -> _Selection:
        return _Selection(self)


class Buffer:
    def __init__(self, _ba: Any = None) -> None:
        self.data = b""

    def open(self, _mode: Any = None) -> bool:
        return True

    def close(self) -> None:
        pass

    def write_bytes(self, data: bytes) -> None:
        self.data = data


class ByteArray:
    def __init__(self) -> None:
        self._buf: Buffer | None = None

    def data(self) -> bytes:
        return self._buf.data if self._buf else b""


def _buffer_factory(ba: ByteArray) -> Buffer:
    buf = Buffer(ba)
    ba._buf = buf
    return buf


class Timer:
    """QTimer stand-in with a fake clock. Repeating timers only record; singleShot() calls are
    queued with a due time and run by drain(), which also moves the clock forward."""

    clock: list[float] = [1000.0]
    singles: list[tuple[float, int, Callable[[], None]]] = []
    active_timers: list["Timer"] = []
    _seq = 0

    def __init__(self) -> None:
        self.timeout = Signal()
        self.active = False
        self.interval = 0

    def start(self, ms: int = 0) -> None:
        self.active = True
        self.interval = ms
        if self not in Timer.active_timers:
            Timer.active_timers.append(self)

    def stop(self) -> None:
        self.active = False
        if self in Timer.active_timers:
            Timer.active_timers.remove(self)

    def fire(self) -> None:
        self.timeout.emit()

    @staticmethod
    def singleShot(ms: int, fn: Callable[[], None]) -> None:
        Timer._seq += 1
        Timer.singles.append((Timer.clock[0] + ms / 1000.0, Timer._seq, fn))

    @staticmethod
    def pending_ms() -> list[int]:
        return [round((due - Timer.clock[0]) * 1000) for due, _s, _f in sorted(Timer.singles)]


def drain(limit: int = 500, tick_timers: bool = True) -> int:
    """Run the queued singleShot callbacks in due order (the clock jumps to each due time).
    Repeating timers that are running (the window answerer) fire once after each callback."""
    ran = 0
    while Timer.singles and ran < limit:
        Timer.singles.sort(key=lambda item: (item[0], item[1]))
        due, _seq, fn = Timer.singles.pop(0)
        Timer.clock[0] = max(Timer.clock[0], due)
        fn()
        if tick_timers:
            for timer in list(Timer.active_timers):
                timer.fire()
        ran += 1
    return ran


def now() -> float:
    return Timer.clock[0]


class Rect:
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x_, self.y_, self.w, self.h = x, y, w, h


class Image:
    """QImage stand-in: files maps a path to its (width, height); saved records writes."""

    files: dict[str, tuple[int, int]] = {}
    saved: dict[str, tuple[int, int]] = {}

    def __init__(self, path: str = "", w: int = 0, h: int = 0) -> None:
        self.w, self.h = (w, h) if not path else Image.files.get(path, (0, 0))

    def isNull(self) -> bool:
        return self.w == 0

    def width(self) -> int:
        return self.w

    def height(self) -> int:
        return self.h

    def copy(self, rect: Rect) -> "Image":
        return Image(w=rect.w, h=rect.h)

    def scaledToWidth(self, width: int, _mode: Any = None) -> "Image":
        return Image(w=width, h=max(1, round(self.h * width / self.w)))

    def save(self, target: Any, _fmt: str = "PNG") -> bool:
        if isinstance(target, str):
            Image.saved[target] = (self.w, self.h)
        elif hasattr(target, "write_bytes"):
            target.write_bytes(b"PNG" + bytes(max(1, self.w * self.h // 100)))
        return True


class Application:
    """QApplication stand-in. Like Qt, topLevelWidgets() and allWidgets() are static."""

    _instance: "Application | None" = None
    tops: list[Widget] = []

    @classmethod
    def instance(cls) -> "Application | None":
        return cls._instance

    @staticmethod
    def topLevelWidgets() -> list[Widget]:
        return list(Application.tops)

    @staticmethod
    def allWidgets() -> list[Widget]:
        return list(Widget.registry)


def make_qt() -> types.SimpleNamespace:
    """A fresh fake Qt namespace; Application.instance() returns a new empty app."""
    Widget.registry = []
    Timer.singles = []
    Timer.active_timers = []
    Timer.clock[0] = 1000.0
    Image.files, Image.saved = {}, {}
    app = Application()
    Application.tops = []
    Application._instance = app
    return types.SimpleNamespace(
        app=app,
        QApplication=Application,
        QWidget=Widget,
        QMainWindow=MainWindow,
        QDialog=Dialog,
        QMenu=Menu,
        QLabel=Label,
        QAbstractButton=AbstractButton,
        QPushButton=PushButton,
        QToolButton=ToolButton,
        QCheckBox=CheckBox,
        QRadioButton=RadioButton,
        QProgressBar=ProgressBar,
        QGroupBox=GroupBox,
        QLineEdit=LineEdit,
        QTextEdit=TextEdit,
        QPlainTextEdit=PlainTextEdit,
        QSpinBox=SpinBox,
        QComboBox=ComboBox,
        QTableWidget=Table,
        QTimer=Timer,
        QBuffer=_buffer_factory,
        QByteArray=ByteArray,
        QIODevice=types.SimpleNamespace(WriteOnly=2),
        Qt=types.SimpleNamespace(SmoothTransformation=1),
        QRect=Rect,
        QImage=Image,
    )


def make_dialog(q: types.SimpleNamespace, title: str, text: str, buttons: list[str],
                checkboxes: list[tuple[str, bool]] | None = None, visible: bool = True) -> Dialog:
    """A visible dialog registered as a top-level window."""
    dlg = Dialog(title=title, visible=visible)
    Label(text, dlg)
    for label in buttons:
        PushButton(label, dlg)
    for label, checked in checkboxes or []:
        CheckBox(label, dlg, checked=checked)
    q.app.tops.append(dlg)
    return dlg
