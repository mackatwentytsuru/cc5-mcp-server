# Brief P2 — fixes after the live test in CC5 (10-22)

Live results:
- **Worked:** `/workflow/items`, `visible`, `remove`, `attach`, `transfer_weights` (default), `transform/get`, `floor_contact/get`, `save`, `open_project`, `views4`.
- **Broken:** see items 1–3 below.

Edit only `cc5-plugin/cc5_api.py`, plus a short append to `docs/report_P.md` under "## P2". Do not commit.

Read only these line ranges, with Read offset/limit:
- 3320–3520 and 3660–3780: the existing `_silent_export_*` / `silent_*` helpers. They drive CC5's own Qt dialogs from inside the plugin, with no mouse.
- 3930–4060: the `_mixer_find_*` helpers.
- 4920–4965: `wf_import_fbx`.
- 5188–5260: `wf_conform_cloth`.
- 5678–5790: `wf_capture_views4`.
- 5770–5830: `wf_open_project` / `wf_load_cloth_fbx`.
- `J:/OTOLUME/parts/beyon/research/RLPy_excerpt_for_mcp.txt` when you need RLPy names.

## 1. `wf_import_fbx` must not replace the scene
Live test: `RFileIO.LoadFile(fbx)` and `RFileIO.LoadObject(fbx)` both REPLACED the whole scene with a new Default project.
- Never call them for FBX.
- `RFileIO.LoadClotheFromFbx(avatar, path, [])` returned `[RStatus, ()]` and added nothing for an unrigged FBX. Keep that route, but report `status.IsError()` and `status.GetStatusCode()` in the reply.

Rewrite `wf_import_fbx` to drive CC5's own GUI flow through Qt from inside the plugin, the same way the `silent_*` export helpers do. Use no OS mouse and no keyboard.
1. **Open the import dialog.** Find the main window. Find the QAction for File > Import (the menu text is "Import..."; search the menu tree, as `_silent_export_find_action` does) and trigger it.
2. **Fill in the file.** A Qt or native file dialog opens. If it is a `QFileDialog`, call `selectFile(path)` and `accept()`.
   - If CC5 uses the native Windows dialog, Qt cannot reach it. In that case:
     - Before triggering, set `QFileDialog.DontUseNativeDialog` if the app allows it.
     - Otherwise return `{"success": false, "error": "needs GUI: native file dialog"}`.
   - Use `QTimer.singleShot` polling, as the existing helpers do. The dialog is modal, and the code must not block CC5's main thread forever; use a timeout of 20 s.
3. **Pick Prop.** The "Import Fbx" dialog asks Character or Prop. Click the button whose text or objectName is "Prop" (find it via `findChildren(QPushButton/QToolButton)`).
4. **Convert.** An "Import Settings" dialog follows. Press its first button: "Convert All" (some versions say OK).
5. **Report.** Diff the `_wf_scan()` ids before and after. Ignore lights and cameras in the diff, because they get new ids after a reload. Return the new prop.

If any step cannot be done through Qt, stop, close only the dialogs YOU opened (reject/close), and return a clear `"needs GUI: <step>"` error. Never leave a modal dialog open.

Make the flow asynchronous if needed. A good shape is the existing three-step export:
- `wf_import_fbx_begin` installs the timer and triggers the action;
- `wf_import_fbx_status` returns the progress or the result.

Register both routes (`/workflow/import_fbx`, `/workflow/import_fbx/status`) and describe the shape in report_P.md.

## 2. `wf_capture_views4` fixes
- The "persp" image came out identical to "top". It must be a perspective view rotated 45° around the vertical axis and tilted 25° down, looking at the target. Set the camera transform explicitly; do not reuse the top preset.
- Framing is too loose: the avatar is tiny in a 1280x720 frame. Frame the target bounds (`GetBounds()`) so the target fills about 80% of the frame height. When no target is given, use the avatar's bounds.
- Live test reply: "Camera could not be restored to its previous transform". Save the camera's transform control value before the shots and set it back after, and report whether the restore worked.

## 3. `wf_conform_cloth` returned empty before/after
The conform value keys are unknown.
- Try the names shown in CC's Conform panel: "Increase Size", "Iteration", "Subdivision Level", "Margin", "Close-fitting", "Smooth".
- Also try lower_snake versions such as "increase_size".
- Read each with `GetClothConformValue(name)` in a try block; record the names that return a number, both in the reply and in report_P.md.
- Then apply the given `values` only for keys that read OK, and call `CalculateCollision()` `iterations` times.

## Rules
Every write is wrapped in BeginAction/EndAction. Return errors instead of raising. Python 3.10. Keep the existing style.
