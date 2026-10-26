"""
SkinGen (the Appearance editor in the Modify panel) driven by script, no mouse.

Widget names come from the 2026-10-26 research (docs/ui-automation-test-steps_ja.md lists what was
confirmed on a real CC5 and what is still untested):

  qtModeSwitchPushButton        "Activate Editor" switch. Turning it off bakes the layers (~10 s)
                                and CC5 asks "exit SkinGen editing mode?" (answered Yes).
  qtFeatureTableWidget          the layer table; one cell widget per row
    qtEnableToolButton          eye button of a row. CHECKED = HIDDEN.
    qtTextLabel / qtIndexLabel  layer name / number
  qtBlendOpacityHorizontalSliderEx > qtSpinBox
                                opacity (0-100) of the SELECTED layer
  qtDeleteToolButton            delete button with a menu: Selected Layer / Current Material / All Material

The editor widgets are rebuilt whenever a layer is selected, so every step looks the widgets up
again and the jobs wait between steps. Slow work runs as a cc5_ui job (poll /ui/job).
"""

from __future__ import annotations

import math
from typing import Any, Callable, Iterator

import cc5_ui

SWITCH = "qtModeSwitchPushButton"
TABLE = "qtFeatureTableWidget"
ROW_ENABLE = "qtEnableToolButton"
ROW_NAME = "qtTextLabel"
ROW_INDEX = "qtIndexLabel"
OPACITY_BOX = "qtBlendOpacityHorizontalSliderEx"
SPIN = "qtSpinBox"
DELETE_BUTTON = "qtDeleteToolButton"
TAB_BUTTONS = {"skin": "qtSkinPushButton", "makeup": "qtMakeupPushButton", "outfits": "qtActorPartPushBtn"}
COMBOS = {"material": "qtMaterialComboBox", "channel": "qtChannelComboBoxEx",
          "resolution": "qtTextureResolutionComboBox", "blend_mode": "qtBlendModeComboBoxEx"}
STATE_NAMES = (SWITCH, TABLE, OPACITY_BOX, *TAB_BUTTONS.values(), *COMBOS.values())

DELETE_SCOPES = {"selected_layer": "selected layer", "current_material": "current material",
                 "all_material": "all material"}
ACTIONS = ("select", "show", "hide", "opacity", "delete")

REBUILD_WAIT_MS = 600               # the layer panel is rebuilt after a selection
EDITOR_FLIP_LIMIT_S = 60            # how long to wait for the Activate Editor switch to change
DEFAULT_SETTLE_S = 120


# --- reading ----------------------------------------------------------------------------

def _first(name: str, within: Any = None) -> Any:
    hits = cc5_ui.find_by_name(name, within)
    return hits[0] if hits else None


def _selected_rows(table: Any) -> list[int]:
    """Rows the selection model reports as selected (currentRow only when there is no selection model)."""
    model = cc5_ui._safe(table.selectionModel)
    if model is not None:
        return cc5_ui._safe(lambda: sorted(m.row() for m in model.selectedRows()), [])
    current = cc5_ui._safe(table.currentRow, -1)
    return [current] if isinstance(current, int) and current >= 0 else []


def _row_button(cell: Any) -> Any:
    q = cc5_ui._qt()
    for b in cc5_ui._safe(lambda: cell.findChildren(q.QToolButton), []):
        if cc5_ui._safe(b.objectName, "") == ROW_ENABLE:
            return b
    return None


def _row_labels(cell: Any, object_name: str) -> list[str]:
    q = cc5_ui._qt()
    out = []
    for lab in cc5_ui._safe(lambda: cell.findChildren(q.QLabel), []):
        if cc5_ui._safe(lab.objectName, "") == object_name:
            text = cc5_ui.clean_text(cc5_ui._safe(lab.text, ""))
            if text:
                out.append(text)
    return out


def read_layers(table: Any) -> list[dict[str, Any]]:
    """One entry per row: index, name, visible (None when the eye button is missing), selected."""
    selected = set(_selected_rows(table))
    layers: list[dict[str, Any]] = []
    for row in range(table.rowCount()):
        cell = table.cellWidget(row, 0)
        entry: dict[str, Any] = {"index": row, "name": None, "visible": None, "selected": row in selected}
        if cell is not None:
            names = _row_labels(cell, ROW_NAME)
            numbers = _row_labels(cell, ROW_INDEX)
            button = _row_button(cell)
            entry["name"] = names[0] if names else None
            if len(names) > 1:
                entry["other_labels"] = names[1:]
            if numbers:
                entry["number"] = numbers[0]
            if button is not None:
                entry["visible"] = not bool(button.isChecked())
        layers.append(entry)
    return layers


def _opacity_spin() -> Any:
    box = _first(OPACITY_BOX)
    return _first(SPIN, box) if box is not None else None


def read_state() -> dict[str, Any]:
    """Editor switch, tab, layer list and the selected layer's opacity (one pass over the widgets)."""
    found = cc5_ui.find_by_names(STATE_NAMES)
    switch = found[SWITCH][0] if found[SWITCH] else None
    table = found[TABLE][0] if found[TABLE] else None
    state: dict[str, Any] = {
        "editor_found": switch is not None,
        "editor_active": bool(switch.isChecked()) if switch is not None else None,
        "table_found": table is not None,
        "layers": read_layers(table) if table is not None else [],
    }
    selected = [layer["index"] for layer in state["layers"] if layer["selected"]]
    state["selected"] = selected[0] if selected else None
    box = found[OPACITY_BOX][0] if found[OPACITY_BOX] else None
    spin = _first(SPIN, box) if box is not None else None
    state["opacity"] = spin.value() if spin is not None else None
    if spin is not None:
        state["opacity_range"] = [spin.minimum(), spin.maximum()]
    for tab, name in TAB_BUTTONS.items():
        button = found[name][0] if found[name] else None
        if button is not None and cc5_ui._safe(button.isChecked, False):
            state["tab"] = tab
    combos = {key: cc5_ui.clean_text(cc5_ui._safe(found[name][0].currentText, ""))
              for key, name in COMBOS.items() if found[name]}
    if combos:
        state["combos"] = combos
    if not state["editor_found"] and not state["table_found"]:
        state["hint"] = ("SkinGen widgets not found. Apply a SkinGen preset (apply_preset opens the editor by "
                         "itself) or open Modify > Appearance, then read the state again.")
    return state


def ui_skingen_state(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/skingen/state: read-only view of the SkinGen editor."""
    return {"success": True, **read_state()}


def resolve_layer(layers: list[dict[str, Any]], index: Any = None, name: Any = None) -> tuple[int | None, str | None]:
    """The row a caller means: by index, or by (case-insensitive) layer name; with both they must
    agree. Returns (row, error)."""
    if index is not None:
        try:
            row = int(index)
        except (TypeError, ValueError):
            return None, f"index must be a whole number, got {index!r}"
        if not 0 <= row < len(layers):
            return None, f"layer index {row} is out of range (the editor has {len(layers)} layer(s))"
        if name and (layers[row]["name"] or "").strip().lower() != str(name).strip().lower():
            return None, f"layer {row} is named {layers[row]['name']!r}, not {name!r}"
        return row, None
    if name:
        wanted = str(name).strip().lower()
        rows = [layer["index"] for layer in layers if (layer["name"] or "").strip().lower() == wanted]
        if len(rows) == 1:
            return rows[0], None
        known = [layer["name"] for layer in layers]
        if not rows:
            return None, f"no layer named {name!r}; layers: {known}"
        return None, f"several layers are named {name!r}: rows {rows}; give index"
    return None, "give index or name"


# --- editor on / off --------------------------------------------------------------------

def _switch_is(want: bool) -> bool:
    """True once the switch reads `want`; a missing switch counts as off."""
    switch = _first(SWITCH)
    return (not want) if switch is None else bool(switch.isChecked()) == want


def _brief_windows() -> list[dict[str, Any]]:
    return [{k: cc5_ui.public_info(info)[k] for k in ("title", "text", "buttons", "progress", "needs_human")}
            for info, _w in cc5_ui.scan_windows()][:5]


def _editor_steps(p: dict[str, Any], choices: dict[str, Any]) -> Iterator[float]:
    want = bool(p["active"])
    switch = _first(SWITCH)
    if switch is None:
        return {"success": False, "error": "the Activate Editor switch was not found"}
    if bool(switch.isChecked()) == want:
        return {"success": True, "changed": False, "editor_active": want}
    baseline = cc5_ui.baseline_keys()
    cc5_ui._later(50, switch.click)               # deferred: the click raises a question / starts the bake
    waited = 0.0
    while not _switch_is(want):
        if waited >= EDITOR_FLIP_LIMIT_S:
            return {"success": False, "error": f"the switch did not change within {EDITOR_FLIP_LIMIT_S}s",
                    "windows": _brief_windows()}
        yield 1000
        waited += 1.0
    settled: dict[str, Any] = {}
    for _ in range(1 if want else 2):            # the bake starts a moment late: settle twice after Off
        yield 3000
        settled = yield from cc5_ui.settle_steps(p["timeout_s"], choices, extra_ok=lambda: _switch_is(want),
                                                 baseline=baseline)
        if not settled["ok"]:
            break
    out: dict[str, Any] = {"success": bool(settled.get("ok")), "changed": True, "editor_active": want,
                           "waited_s": settled.get("waited_s")}
    if not settled.get("ok"):
        out["error"] = cc5_ui.settle_error(settled)
        out["blocked_by"] = settled.get("blocked_by")
        out["windows"] = _brief_windows()
    return out


def _editor_budget(timeout_s: int) -> int:
    """Longest a whole editor job may take: the flip wait plus two settles."""
    return EDITOR_FLIP_LIMIT_S + 2 * (timeout_s + 10) + 60


def _editor_job(p: dict[str, Any]) -> Iterator[float]:
    choices = cc5_ui.normalize_choices({"skingen_exit": p["exit_answer"]})
    answerer = cc5_ui.WindowAnswerer(choices, max_seconds=_editor_budget(p["timeout_s"])).start()
    try:
        result = yield from _editor_steps(p, choices)
    finally:
        answered = answerer.stop()
    result["answered"] = answered
    if answerer.blocked:
        result["blocked_windows"] = answerer.blocked
    return result


def ui_skingen_editor(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/skingen/editor: turn the SkinGen editor on or off. Starts a job.

    Body: active (true/false, required), exit_answer ("yes" default | "no") for the
    "exit SkinGen editing mode?" question, timeout_s (how long CC5 may take to settle after the
    switch changed; default 120, max 600). Turning it off bakes the layers; the job ends when
    CC5 is quiet again.
    """
    p = dict(body or {})
    if not isinstance(p.get("active"), bool):
        return {"success": False, "error": "active must be true or false"}
    p["exit_answer"] = str(p.get("exit_answer", "yes")).strip().lower()
    try:
        cc5_ui.normalize_choices({"skingen_exit": p["exit_answer"]})
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    p["timeout_s"] = cc5_ui._clamp_int(p.get("timeout_s", DEFAULT_SETTLE_S), 10, 600, DEFAULT_SETTLE_S)
    if _first(SWITCH) is None:
        return {"success": False, "error": "the Activate Editor switch was not found; apply a SkinGen preset "
                                           "first (it opens the editor) or open Modify > Appearance"}
    return cc5_ui.start_job("skingen-editor", _editor_job, p, max_seconds=_editor_budget(p["timeout_s"]) + 60)


# --- layer operations -------------------------------------------------------------------

def _select_row(table: Any, row: int) -> Iterator[float]:
    """Select a row (unless it is selected) and wait for the panel to be rebuilt; True when the
    selection model reports the row."""
    if row in _selected_rows(table):
        return True
    table.selectRow(row)
    yield REBUILD_WAIT_MS
    return row in _selected_rows(_first(TABLE) or table)


def _layer_summary() -> dict[str, Any]:
    state = read_state()
    return {"layers": state["layers"], "selected": state["selected"], "opacity": state["opacity"]}


def _set_eye(p: dict[str, Any]) -> Iterator[float]:
    table = _first(TABLE)
    row = p["row"]
    button = _row_button(table.cellWidget(row, 0))
    if button is None:
        return {"success": False, "error": f"layer {row} has no eye button"}
    want_visible = p["action"] == "show"
    if (not bool(button.isChecked())) != want_visible:   # checked = hidden
        button.click()
    yield 300
    layer = read_layers(_first(TABLE))[row]
    ok = layer["visible"] is want_visible
    out: dict[str, Any] = {"success": ok, "layer": layer, **_layer_summary()}
    if not ok:
        out["error"] = f"layer {row} still reads visible={layer['visible']}"
    return out


def _set_opacity(p: dict[str, Any]) -> Iterator[float]:
    table = _first(TABLE)
    row, value = p["row"], p["opacity"]
    if not (yield from _select_row(table, row)):
        return {"success": False, "error": f"could not select layer {row}", **_layer_summary()}
    spin = _opacity_spin()
    for _ in range(3):                           # the box may not exist for a moment after the rebuild
        if spin is not None:
            break
        yield REBUILD_WAIT_MS
        spin = _opacity_spin()
    if spin is None:
        return {"success": False, "error": "the opacity box (qtBlendOpacityHorizontalSliderEx > qtSpinBox) "
                                           "was not found", **_layer_summary()}
    before = spin.value()
    spin.setValue(value)
    yield 400
    after_spin = _opacity_spin()
    after = after_spin.value() if after_spin is not None else None
    selected_now = _selected_rows(_first(TABLE) or table)
    out: dict[str, Any] = {"success": after == value and row in selected_now, "layer": row,
                           "opacity_before": before, "opacity_after": after,
                           "opacity_range": [spin.minimum(), spin.maximum()], **_layer_summary()}
    if after != value:
        out["error"] = f"the opacity box reads {after} after setting {value}"
    elif row not in selected_now:
        out["error"] = f"layer {row} is not the selected layer any more, so the value may belong to another layer"
    return out


def _select_only(p: dict[str, Any]) -> Iterator[float]:
    table = _first(TABLE)
    ok = yield from _select_row(table, p["row"])
    out = {"success": bool(ok), **_layer_summary()}
    if not ok:
        out["error"] = f"layer {p['row']} was not selected"
    return out


def _find_delete_action(scope: str) -> tuple[Callable[[], None] | None, str | None, list[str]]:
    """(callable that performs the delete, error, available menu texts)."""
    button = _first(DELETE_BUTTON)
    if button is None:
        return None, "the delete button (qtDeleteToolButton) was not found", []
    menu = cc5_ui._safe(button.menu)
    if menu is None:
        if scope == "selected_layer":
            return button.click, None, []
        return None, f"the delete button has no menu, so only scope selected_layer works (asked {scope})", []
    needle = DELETE_SCOPES[scope]
    actions = list(cc5_ui._safe(menu.actions, []))
    texts = [cc5_ui.clean_text(a.text()).replace("&", "") for a in actions]
    for action, text in zip(actions, texts):
        if needle in text.lower() and cc5_ui._safe(action.isEnabled, True):
            return action.trigger, None, texts
    return None, f"no delete menu entry for '{needle}' (or it is disabled); menu: {texts}", texts


def _delete(p: dict[str, Any]) -> Iterator[float]:
    cc5_ui.stop_active_answerer()                 # nothing is answered while deleting
    table = _first(TABLE)
    scope = p["scope"]
    before = table.rowCount()
    if scope == "selected_layer" and not (yield from _select_row(table, p["row"])):
        return {"success": False, "error": f"could not select layer {p['row']}", **_layer_summary()}
    perform, error, menu = _find_delete_action(scope)
    if perform is None:
        return {"success": False, "error": error, "menu": menu}
    baseline = cc5_ui.baseline_keys()
    cc5_ui._later(50, perform)                   # deferred: a menu / question may open
    yield 800
    # Nothing is answered here: a confirmation window means a person decides.
    settled = yield from cc5_ui.settle_steps(30, {}, grace_s=2.5, answerable=False, baseline=baseline)
    now_table = _first(TABLE)
    after = now_table.rowCount() if now_table is not None else 0
    ok = bool(settled["ok"]) and (scope != "selected_layer" or after < before)
    out: dict[str, Any] = {"success": ok, "scope": scope, "layers_before": before, "layers_after": after,
                           **(_layer_summary() if now_table is not None else {})}
    if not settled["ok"]:
        out["error"] = cc5_ui.settle_error(settled)
        out["blocked_by"] = settled.get("blocked_by")
    elif not ok:
        out["error"] = f"the layer count did not drop ({before} -> {after}): the delete may not have happened"
    return out


_ACTION_STEPS: dict[str, Callable[[dict[str, Any]], Iterator[float]]] = {
    "select": _select_only, "show": _set_eye, "hide": _set_eye, "opacity": _set_opacity, "delete": _delete,
}


def ui_skingen_layer(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/skingen/layer: select / show / hide / opacity / delete a layer. Starts a job.

    Body: action (select|show|hide|opacity|delete); index and/or name of the layer;
    opacity (0-100, for action opacity); scope (selected_layer|current_material|all_material,
    for delete) and confirm=true (required for delete: a guard against accidents, not a human
    confirmation). A confirmation window that CC5 opens is NOT answered.
    """
    p = dict(body or {})
    action = str(p.get("action") or "").lower()
    if action not in ACTIONS:
        return {"success": False, "error": f"action must be one of {list(ACTIONS)}"}
    p["action"] = action
    table = _first(TABLE)
    if table is None:
        return {"success": False, "error": "the layer table (qtFeatureTableWidget) was not found; "
                                           "apply a SkinGen preset or open Modify > Appearance first"}
    error = _validate_layer_args(p, action)
    if error:
        return {"success": False, "error": error}
    layers = read_layers(table)
    if action != "delete" or p["scope"] == "selected_layer":
        row, error = resolve_layer(layers, p.get("index"), p.get("name"))
        if error:
            return {"success": False, "error": error, "layers": layers}
        p["row"] = row
    return cc5_ui.start_job("skingen-layer", _ACTION_STEPS[action], p, max_seconds=120)


def _validate_layer_args(p: dict[str, Any], action: str) -> str | None:
    if action == "opacity":
        try:
            value = float(p.get("opacity"))
        except (TypeError, ValueError):
            return "opacity must be a number from 0 to 100"
        if not math.isfinite(value) or value != int(value) or not 0 <= value <= 100:
            return "opacity must be a whole number from 0 to 100"
        p["opacity"] = int(value)
    if action == "delete":
        p["scope"] = str(p.get("scope") or "selected_layer").lower()
        if p["scope"] not in DELETE_SCOPES:
            return f"scope must be one of {list(DELETE_SCOPES)}"
        if p.get("confirm") is not True:
            return "delete needs confirm=true (it cannot be undone from here)"
    return None


ROUTES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "/ui/skingen/state": ("ui_skingen_state", ui_skingen_state),
    "/ui/skingen/editor": ("ui_skingen_editor", ui_skingen_editor),
    "/ui/skingen/layer": ("ui_skingen_layer", ui_skingen_layer),
}
