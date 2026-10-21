# Report P — Python side (CC5 plugin) for the workflow routes

Scope: `cc5-plugin/cc5_api.py` only. One new block (helpers + routes) was inserted
immediately before `# --- Auto-patch server ACTION_MAP on reload ---`, and entries were
added inside `_auto_patch_server` (`ACTION_MAP` + `POST_ROUTES`). No other file changed.

## Cross-cutting notes

- **Dispatch shape.** `server._execute_sync` calls `handler(params)`, so registering a plain
  function (`"wf_x": wf_x`, as the brief asked) only works if the function accepts the JSON
  body dict positionally. Every workflow route therefore has the signature
  `def wf_x(body: dict | None = None, **kwargs)`, and starts with
  `params = _wf_params(body, kwargs)`. Both call styles work:
  `wf_x({"item_name": "Hat"})` and `wf_x(item_name="Hat")`.
- **Import guard.** The brief says "follow the existing `try: import RLPy` guard" — there is
  no such guard in this file: line 18 is a bare `import RLPy`, and `_EOMTYPE_MATERIAL` is
  resolved at import time. I did **not** change the imports (out of the allowed edit scope),
  and nothing I added touches `RLPy` at import time. Consequence: the module still cannot be
  imported outside CC5, exactly as before my change. If importing outside CC5 is a real
  requirement, the import block at the top of the file has to change in a follow-up.
- **Item scan / resolve.** `_wf_scan()` walks `RScene.GetAvatars()` plus each avatar's
  `GetClothes()`, `GetAccessories(True)`, `GetHairs()`, then `RScene.GetProps()`, then
  `RScene.FindObjects()` for the three light enums, then `RScene.GetCameras()`, deduped by
  `GetID()`. Kind comes from the collection it was found in, else from `GetType()` compared
  against `EObjectType_*`. `_wf_resolve()` tries `RScene.QueryObjectByID` first when an id is
  given (both `str(id)` and `int(id)`), otherwise matches names; multiple name matches return
  `{"success": false, "error": "ambiguous name", "matches": [...]}`.
- **No dialogs, no clicks.** Nothing new opens a dialog. Where a documented API is missing
  (eyelash hair enums, transform setter, floor-contact enum on odd builds) the route returns
  `{"success": false, "error": "needs GUI: ..."}` rather than guessing at UI automation.
- Paths use the existing `_validate_path` (`.fbx`/`.obj`, `.obj`, `.ccproject`, `.png`).
  `wf_save_project` refuses any basename ending in `_hs_ok.ccproject` (case-insensitive).
- Every write route wraps its RLPy calls in `RGlobal.BeginAction("wf_...")` /
  `finally: RGlobal.EndAction()` and returns `{"success": false, "error": str(e)}` on
  exceptions.
- I could not run `python -m py_compile` in this sandbox (the shell rejects Python
  execution: "requires approval"), so the file was only reviewed by hand. Please run
  `python -m py_compile cc5-plugin/cc5_api.py` once before loading the plugin.

## Per route

### `/workflow/items` — `list_scene_items`
RLPy: `RScene.GetAvatars/GetProps/GetCameras/FindObjects`, `avatar.GetClothes/GetAccessories(True)/GetHairs`,
`RIObject.GetID/GetName/GetParent`, `GetClotheType`, `GetHairType`, `IsVisible(RGlobal.GetTime())`.
Guesses / limits:
- `visible` is `null` for cloth and hair: `RICloth`/`RIHair` have no `IsVisible` in the API.
- `parent` is `GetParent().GetName()`; may be `null` when the API returns a non-object node.

### `/workflow/visible` — `wf_set_visible`
RLPy: `RScene.Show` / `RScene.Hide` (generic; `RICloth`/`RIHair` have no `SetVisible`),
`RGlobal.ObjectModified(obj, EObjectModifiedType_Attribute)`, `ForceViewportUpdate`.
Guesses: none. Test live: that showing/hiding a *cloth* item works through `RScene.Hide`.

### `/workflow/remove` — `wf_remove_item`
RLPy: `RScene.RemoveObject`, `RGlobal.ObjectModified(owner avatar, ...)`.
Guesses: none. Test live: removing a prop/light that is not avatar-owned.

### `/workflow/import_fbx` — `wf_import_fbx`
RLPy: `RFileIO.LoadFile(path)`, fallback `RFileIO.LoadFbxFile(path)`.
Guesses / limits: the new object is found by diffing `_wf_scan()` ids before/after; the
last new item is reported. If a format loads several objects, only the last is returned.
Test live: `.fbx` and `.obj` loads, and whether `LoadFile` reports failure by exception or
by return value (we assume exception).

### `/workflow/attach` — `wf_attach_to_bone`
RLPy: `avatar.GetSkeletonComponent()`, `skeleton.GetSkinBones()`, `bone.GetName()`,
then `obj.LinkTo(bone)`, `obj.LinkTo(RGlobal.GetTime(), bone)`, `obj.SetParent(bone)`
tried in that order.
Guesses: `LinkTo(*args)` / `SetParent(*args)` arities are undocumented; the first call that
does not raise is assumed to be correct. Test live: which arity actually parents the item,
and whether the item follows the bone afterwards.

### `/workflow/transfer_weights` — `wf_transfer_skin_weights`
RLPy: `RICloth.TransferSkinWeight(str)` / `RIAccessory.TransferSkinWeight(str)`, plus
`avatar.GetClothes()`, `cloth.GetClotheType()` and `RScene.RemoveObject` for the shoes rule.
Guesses:
- Exact template strings: `"Default"`, `"Dress"`, `"Gloves"`, `"Shoes"`, `"Cloak"`,
  `"Other"` (title case). Not documented anywhere; must be verified live.
- Shoes rule: if the avatar already has a cloth whose `GetClotheType() == EClotheType_Shoes`
  (or whose type string contains "Shoes"), the call fails unless the body has
  `"replace": true`, in which case the old shoes are removed first.
- `kind_after` is recomputed with `_wf_kind_of(obj)`; if the object is replaced by the
  transfer this can be wrong. Test live.

### `/workflow/convert_hair` — `wf_convert_to_hair`
RLPy: `RIAccessory`/`RIHair` `ConvertToHair(EHairType_*)` and `ConvertToFaceHair(EFaceHairType_*)`.
Mapping: top→`EHairType_Hair_Top`, base_all→`EHairType_Hair_Base`, rear→`EHairType_Hair_Rear`,
bangs→`EHairType_Hair_Bangs`, accessory→`EHairType_Hair_Accessory`,
brows→`EFaceHairType_Eyebrows` (routed through `ConvertToFaceHair`).
Guesses / limits:
- `upper_lash` / `lower_lash` have **no** constant in the exposed `EHairType_`/`EFaceHairType_`
  list, so they return `needs GUI: ...` instead of guessing an enum value.
- `base_all` is mapped to `EHairType_Hair_Base`; there is no "_All" hair type constant.
Test live: whether cloth items expose `ConvertToHair` in this build (the reference lists it
only on `RIAccessory`/`RIHair`).

### `/workflow/cloth_to_accessory` — `wf_cloth_to_accessory`
RLPy: `RICloth.ConvertToAccessory(bCurrentShape)`.
Guesses: none (`keep_current_shape` defaults to `true`). Test live: that the item is still
addressable (same id) after conversion so the reply `name` is meaningful.

### `/workflow/conform` — `wf_conform_cloth`
RLPy: `obj.GetClothConformValue(key)`, `obj.SetClothConformValue(key, value)`,
`obj.CalculateCollision()` (called once per iteration, iterations clamped to 1..10).
Guesses:
- The conform key strings are not documented, so only keys supplied in `values` are read
  back. `before`/`after` are `{}` when `values` is omitted.
- With no `values`, only `CalculateCollision()` runs (a conform pass).

### `/workflow/transform/get` — `wf_get_transform`
RLPy: `RIObject.LocalTransform()`, then `RTransform.T()/R()/S()`, read through `.x/.y/.z`.
Guesses: values are the raw local transform numbers (rotation order/units are whatever
`RTransform.R()` returns — likely radians, unverified).

### `/workflow/transform/set` — `wf_set_transform`
RLPy: `RTransform()`, `RTransform.T/R/S(vector)`, `RVector3(x,y,z)`, `RIObject.GetControl`,
`RTransformControl.SetValue(RGlobal.GetTime(), transform)`, `RGlobal.ObjectModified`.
Guesses / limits:
- **`RIObject`/`RICamera` have no documented transform setter** (the reference only has
  `RTransformKey.SetTransform`). The route tries, in order: the object control
  `GetControl("Transform")` / `GetControl("KT_Transform")`, then any undocumented
  `SetLocalTransform`/`SetWorldTransform`/`SetTransform`, then mutating the `RTransform`
  returned by `LocalTransform()` in place.
- Success is only reported if `LocalTransform()` reads back the requested values
  (tolerance 1e-3); otherwise the reply is
  `{"success": false, "error": "needs GUI: ..."}` with the actual values.
Test live: which (if any) of the three paths sticks.

### `/workflow/save` — `wf_save_project`
RLPy: `RFileIO.SaveProject(path)`, fallback `RFileIO.SaveFile(avatar, ESaveFileType_Project, path)`.
`RApplication.GetCurrentProjectPath()` is used when `file_path` is omitted.
Guesses: none on names (all four are in the generated reference), but whether `SaveProject`
opens any dialog is untested. Refuses `*_hs_ok.ccproject`.

### `/workflow/export_obj` — `wf_export_obj`
RLPy: `RFileIO.ExportObjFile(*args)`.
Guesses: signature undocumented; the route tries `(obj, path, current_pose, with_materials)`,
then `(obj, path, current_pose)`, then `(obj, path)`, and accepts the first call that leaves
a file on disk. `bytes` is `os.path.getsize(file_path)`. Test live which arity works, and
whether `with_materials` writes a `.mtl` next to the `.obj`.

### `/workflow/floor_contact/get` — `wf_get_floor_contact`
RLPy: `RIAvatar.GetFloorContactValue(eType)`; the enum is discovered by scanning `dir(RLPy)`
for names starting with `EFloorContact` (the generated reference has
`EFloorContactType_Hand*`, `Foot*` and `All`). `EFloorContactType_All` is skipped on read.
Guesses: values come back as a `{type_name: value}` object (the contract says "raw"); if the
build exposes no such constants we fall back to a no-argument call.

### `/workflow/floor_contact/set` — `wf_set_floor_contact`
RLPy: `RIAvatar.SetFloorContactValue(eType, fValue)`.
Accepts the object returned by `get` (keys must be known `EFloorContact*` names), a bare
number when the build exposes exactly one type, or a list ordered like the sorted type names.
`EFloorContactType_All` is accepted here. Test live: whether a partial dict is enough or CC5
needs all channels at once.

### `/workflow/foot_auto` — `wf_auto_adjust_foot_height`
RLPy: `RIAvatar.AutoAdjustFootHeight()`. Guesses: none.

### `/workflow/render` — `wf_render_viewport`
RLPy: `RGlobal.RenderImage(path)` with `_set_render_resolution(1280, 720)` first, plus one
`ForceViewportUpdate()` + retry. Silent only: the existing `_capture_window_screenshot`
fallback is deliberately **not** used here; if no file appears the route returns
`{"success": false, "error": "RenderImage did not create ... (refusing to click the UI)"}`.

### `/workflow/views4` — `wf_capture_views4`
RLPy: `RScene.GetCurrentCamera()`, `camera.SetCameraLocation(ECameraLocationType_*)`
(the same call `frame_camera` uses), `RScene.SelectObject` / `ClearSelectObjects`,
`RGlobal.RenderImage`, `RScene.SetCurrentCamera`.
Map: front→`Front`, side→`Right`, top→`Top`, persp→`Home` (or `Focus` when a target item is
selected). Files are `<folder>/<prefix>_<view>.png`, written front, side, top, persp.
Guesses / limits:
- `SetCameraLocation` cannot express "45° yaw / 25° pitch", so the perspective image is a
  preset view, not exactly that angle. The side view assumes `ECameraLocationType_Right`
  looks from +X.
- Framing: presets frame the scene; a target item is selected and only the perspective view
  uses `Focus`.
- Camera restore: the saved `WorldTransform()` is written back through
  `GetControl("Transform").SetValue(...)` or an undocumented `Set*Transform` — neither is in
  the API reference, so the reply may carry
  `"warning": "Camera could not be restored to its previous transform"`. Test live.
- No screenshot fallback (same rule as `/workflow/render`): if `RenderImage` writes nothing,
  the route fails instead of clicking.

## Sources consulted
- `docs/contract_workflow_routes.md` (whole), `J:/OTOLUME/parts/beyon/research/RLPy_excerpt_for_mcp.txt`
  (whole), plus targeted greps in `docs/rlpy-api-reference.md` for `EFloorContactType`,
  `RFileIO_ExportObjFile`, `RTransform`, `RVector3`, `RICamera`,
  `RApplication.GetCurrentProjectPath` and for any `Set*Transform` (none exists on `RIObject`).

## P2

### `/workflow/import_fbx` — GUI flow, no mouse (`wf_import_fbx_begin` + `wf_import_fbx_status`)
`RFileIO.LoadFile` / `LoadObject` are **never** called for FBX: both replaced the whole scene
with a new Default project in the 10-22 live test. The route now drives CC5's own
File > Import flow through Qt, the same way the `silent_*` export helpers drive their dialogs.

Shape (asynchronous, because a modal Qt dialog must not block CC5's main thread):
1. `POST /workflow/import_fbx {"file_path"}` → `wf_import_fbx_begin`.
   Finds the `Import...` QAction by walking the menu tree, sets
   `Qt.AA_DontUseNativeDialogs` (when available, restored afterwards), installs a
   `QApplication` event filter that fills/accepts `QFileDialog`, starts a 200 ms `QTimer`
   state machine, triggers the action, and returns
   `{"success":true,"phase":"file_dialog","non_native_dialog":<bool>,"poll_endpoint":...}`.
2. `GET /workflow/import_fbx/status` → `wf_import_fbx_status`.
   Phases: `file_dialog` → `prop_dialog` → `settings_dialog` → `settling` → `done`/`error`.
   - file: `QFileDialog.selectFile(path)` + `accept()` (event filter and timer both try;
     each dialog id is accepted once).
   - Prop: clicks the visible `QAbstractButton` whose text is `Prop` (or objectName contains
     `prop`).
   - Settings: clicks the first button containing `Convert` (`Convert All` preferred), else OK.
   - settle: `_wf_scan()` id diff, lights/cameras ignored; a prop is preferred in the result.
   - timeout 20 s. Failure returns `"needs GUI: <step>"` (`native file dialog`,
     `Import Fbx Character/Prop dialog`, `Import Settings dialog`, ...); cleanup stops the
     timer, removes the filter, restores the app attribute and rejects only the dialogs this
     flow opened. No OS mouse/keyboard is used.
   - `done` reply: `{"success":true,"phase":"done","item":{name,id,kind},"new_items":[...]}`.
   CC5's own menu action owns the undo transaction for this import; the plugin performs no
   direct RLPy write, so there is no enclosing `BeginAction`.

`/workflow/load_cloth_fbx` keeps `RFileIO.LoadClotheFromFbx(avatar, path, [])`; the reply now
also returns `status_error` (`RStatus.IsError()`) and `status_code` (`GetStatusCode()`),
plus the failed-mesh list it returns.

### `/workflow/conform` — conform key names
The key strings are undocumented. The route probes, in a try block, both the CC5 Conform panel
labels and lower_snake variants: `Increase Size`, `Iteration`, `Subdivision Level`, `Margin`,
`Close-fitting`, `Smooth` and `increase_size`, `iteration`, `subdivision_level`, `margin`,
`close_fitting`, `smooth`.
- Every name that returns a number from `GetClothConformValue` is listed in the reply as
  `available_keys` (`[{"key","value"}, ...]`) — that list is the live record of the names that
  actually work in this CC5 build (no live test was run while writing this patch).
- `values` are matched case/underscore/hyphen-insensitively to those readable names; unmatched
  keys go to `skipped_values` and are not written.
- `before`/`after` use the readable (actual) key names. `CalculateCollision()` still runs
  `iterations` times even when no key is readable; a `warning` says so.

### `/workflow/views4` — perspective angle, framing, camera restore
- `persp` no longer uses the Top/Home/Focus preset. It takes the Front preset pose as the base
  and builds the transform explicitly: 45° yaw around the vertical (Z) axis, 25° down tilt,
  camera moved to `center + horizontal_dir * d*cos25 + Z * d*sin25`; the pose is
  `Rz(45) * Rx(-25) * front_pose` through `RMatrix4` → `RTransform.From`, written with
  `GetControl(<transform key>).SetValue`, fallback `SetWorldTransform`/`SetLocalTransform`.
  If no writable transform exists the route returns
  `"needs GUI: camera transform control is not writable"`.
- Framing: target bounds come from `RIObject.GetBounds()` (tolerant of return-style vs
  out-parameter `RVector3` bindings); with no target the first avatar's bounds are used.
  Distance is computed from `RICamera.GetAngleOfView` so the bounds fill 80% of the 1280x720
  frame height; front/side frame Z extent, top frames max(X, Y). Front/side/top keep the preset
  orientation but are moved to that distance along the preset direction.
- Restore: the camera's transform control value is saved before the shots
  (`GetValue(now, RTransform())`, with `WorldTransform()` as fallback) and written back after,
  then read back and compared (`camera_restored`). The reply also carries `framing` and
  per-view `method`/`position` (and `yaw_deg`/`pitch_deg` for `persp`); the old warning remains
  when the read-back does not match.
