# Task: add CC5 "High Heels" routes to the plugin

Edit only `C:/Users/macka/Projects/cc5-mcp-server/cc5-plugin/cc5_api.py`. Do not run anything and do not commit.

Start by reading these parts of the file:
- the `_wf_qt_valid`, `_wf_qt_later`, `_wf_dialog_title` and `_wf_import_fbx_text` helpers (search for them);
- `_wf_resolve`;
- the route table at the end (search `"/workflow/bone/rotation"`);
- the function-name table (search `"wf_bone_rotation":`).

## Background
CC5 has no RLPy API for High Heels. In the GUI:
1. Select the shoes item.
2. In the Modify panel, Attribute tab, press the button whose text is **"High Heels"**.
3. A dialog titled **"High Heels"** opens. It has the text "Make current result with the Heel Height slider.", a slider, a spin box (a number, starting at 0), and the buttons **"Ok"** and **"Cancel"**.

## Routes to add
### 1. `/workflow/high_heels/open` → `wf_high_heels_open(body)`
- Body: `{"item_name"|"item_id"}` for the shoes.
- Resolve the item with `_wf_resolve`. Then `RLPy.RScene.ClearSelectObjects()` and `RLPy.RScene.SelectObject(obj)`.
- Find a visible `QAbstractButton` whose text, after `_wf_import_fbx_text`, equals `"high heels"`. It must not live inside any dialog: `button.window()` must be the main window, which is a `QMainWindow`.
- Click it with `_wf_qt_later(btn, "click", 150)`.
- Return `{"success": True, "clicked": True}`. If no button is found, return `{"success": False, "error": "High Heels button not visible (open Modify > Attribute with the shoes selected)"}`.

### 2. `/workflow/high_heels/state` → `wf_high_heels_state(body)`
- Find a visible top-level dialog whose `windowTitle().strip().lower() == "high heels"`.
- Return its spin-box value(s) (`QSpinBox` / `QDoubleSpinBox`): value, minimum, maximum. Also return its slider (`QSlider`): value, minimum, maximum.
- If no such dialog is open, return `{"success": True, "open": False}`.

### 3. `/workflow/high_heels/set` → `wf_high_heels_set(body)`
- Body: `{"value": number, "press": "ok"|"cancel"|null}`.
- Find the "High Heels" dialog as in route 2. If it is not open, return an error.
- Set the first spin box with `setValue(value)`, clamped to its min/max. Then call `editingFinished.emit()` if that signal exists.
- If `press` is given, find the button in that dialog whose text is "ok" or "cancel" (use `_wf_import_fbx_text`) and click it with `_wf_qt_later(btn, "click", 200)`.
- Never click any button outside this dialog.
- Return the value that was set and the state after setting it.

Register all three in both tables, next to `wf_bone_rotation`. Import PySide2 inside each function, as the file does. Return errors instead of raising. Keep the style and the comment density.

When done, reply `DONE` and list the functions you added.
