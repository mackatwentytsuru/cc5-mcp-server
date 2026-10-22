# Task: fix the file-dialog step of the CC5 FBX import automation

Edit only `C:/Users/macka/Projects/cc5-mcp-server/cc5-plugin/cc5_api.py`, in `wf_import_fbx_tick()`, inside the `if state["phase"] == "file_dialog":` branch. Read lines 5060–5660 first. Do not run anything and do not commit.

## Live problem (10-22)
- After `File > Import` the non-native `QFileDialog` opens. The tick calls `dlg.selectFile(path)` and then `_wf_qt_later(dlg, "accept", 150)`.
- The dialog then stays open, so the phase stays `file_dialog` until the 60 s timeout.
- So `selectFile` + `accept` does not take. Probable cause: `QFileDialog.accept()` validates the text in its file-name line edit, and `selectFile` on an already-visible dialog did not fill it.

## Wanted behaviour
1. When the dialog is first seen (not yet in `state["accepted"]`):
   - `dlg.setDirectory(os.path.dirname(path))`, then `dlg.selectFile(os.path.basename(path))`.
   - Find the dialog's file-name `QLineEdit`: prefer `dlg.findChild(QLineEdit, "fileNameEdit")`, otherwise the first visible `QLineEdit` child. Call `setText(path)` on it (the full absolute path).
   - Find the `QDialogButtonBox` child. Take its `QDialogButtonBox.Open` button, or else the first button whose `buttonRole()` is `AcceptRole`. Click it later with `_wf_qt_later(btn, "click", 200)`. If there is no such button, use `_wf_qt_later(dlg, "accept", 200)`.
   - Record what was done in `state["notes"]` (line-edit found yes/no, button text).
   - Append `id(dlg)` to `state["accepted"]`, add `dlg` to `state["dialogs"]`, and store `state["file_dialog_seen_at"] = time.time()`.
2. While the same dialog is still visible more than 2.5 s after that:
   - Do this only once (use a flag in `state`, for example `state["file_dialog_retry"]`).
   - Note the current line-edit text and `dlg.selectedFiles()` in `state["notes"]`.
   - Then fall back to `dlg.done(QDialog.Accepted)` through a small validity-checked deferred call. Write a local closure like `_wf_qt_later` does; `_wf_qt_later` cannot pass arguments.
3. Keep everything else unchanged: the `return` paths, the move to `prop_dialog` once the dialog is gone and `state["accepted"]` is non-empty, the timeouts, and the deny check.
4. Add `"file_dialog_seen_at": 0.0` and `"file_dialog_retry": False` both to `_WF_IMPORT_FBX_STATE` and to the `state.update({...})` in `wf_import_fbx_begin`.

Imports: `QLineEdit`, `QDialogButtonBox` and `QDialog` come from `PySide2.QtWidgets`; import them locally inside the function, as the file already does. Keep the existing style and comment density.

When done, reply `DONE` with a 5-line summary of the change.
