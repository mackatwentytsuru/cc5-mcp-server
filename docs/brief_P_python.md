# Brief P — Python side (CC5 plugin) for the workflow routes

Implement every route in `docs/contract_workflow_routes.md` as plain functions in `cc5-plugin/cc5_api.py`, and register them.

## Read ONLY these parts (the files are big; never read them whole)
1. `docs/contract_workflow_routes.md`: the whole file.
2. `J:/OTOLUME/parts/beyon/research/RLPy_excerpt_for_mcp.txt`: the whole file (about 400 lines). It lists the real RLPy method signatures.
   - Use only methods listed there.
   - Notes from the API stub:
     - `RIAccessory.TransferSkinWeight(strTemplateType)` and `RICloth.TransferSkinWeight(strTemplateType)` take a STRING template.
     - `RIAccessory.ConvertToHair(eHairType)` and `ConvertToFaceHair(eFaceHairType)` take enums; find the enum names in the constants list.
     - `RICloth.ConvertToAccessory(bCurrentShape)`.
     - `RICloth.Get/SetClothConformValue(strConform, value)`, then `CalculateCollision()`.
     - `RFileIO.LoadFile(path)`, `RFileIO.SaveFile(...)`, `RFileIO.ExportObjFile(...)`.
     - `RScene.RemoveObject(obj)`, `RScene.QueryObjectByID(id)`, `RScene.Show/Hide(obj)`.
     - `RIObject.SetParent(...)` / `LinkTo(...)`.
     - `RIAvatar.GetFloorContactValue/SetFloorContactValue/AutoAdjustFootHeight`.
     - `RGlobal.RenderImage(...)`.
   - Exact template strings for TransferSkinWeight are not documented. Try `"Default"`, `"Dress"`, `"Gloves"`, `"Shoes"`, `"Cloak"`, `"Other"` (title case) and say so in a comment.
3. `cc5-plugin/cc5_api.py`, these line ranges only (use Read with offset/limit):
   - 1–130: imports, logging, `_validate_path` and the other helpers.
   - 2240–2340: `list_clothes`, `list_accessories` and `remove_scene_item`. Copy their RLPy usage style.
   - 2660–2800: `set_item_visible` and `get_scene_objects`.
   - 4355–4574: `_auto_patch_server`. New entries go into its `ACTION_MAP` and `POST_ROUTES` updates.

## Rules
- Add the new code as one block of functions placed just BEFORE the line `# --- Auto-patch server ACTION_MAP on reload ---`. Use the Edit tool with that line as the anchor; never rewrite the file.
- Then add the ACTION_MAP entries (`"<function_name>": <function_name>`) and the POST_ROUTES entries (route → function name) inside `_auto_patch_server`.
- Write a helper `_wf_resolve(item_name=None, item_id=None)`. It returns `(obj, kind, error_dict_or_None)` and searches:
  - the avatars and each avatar's `GetClothes()`, `GetAccessories(True)` and `GetHairs()`;
  - `RScene.GetProps()`, the lights and the cameras.
  - When an id is given, try `RScene.QueryObjectByID` first.
- Every write function:
  - starts with `RLPy.RGlobal.BeginAction("wf_<name>")` and ends with `EndAction()` in a `finally`;
  - catches exceptions and returns `{"success": False, "error": str(e)}`.
- Paths go through `_validate_path` with allowed extensions `.fbx`, `.obj`, `.ccproject` and `.png` as needed. Never overwrite a file whose name ends with `_hs_ok.ccProject`.
- No dialogs.
  - If an RLPy call is known to open a dialog, do not call it. Return `{"success": False, "error": "needs GUI: ..."}`.
  - For shoes, refuse transfer_weights with template "shoes" when the avatar already has a shoes item, unless the body has `"replace": true`. In that case first remove the old shoes item via `RScene.RemoveObject`.
- `wf_capture_views4` may reuse the existing camera helpers in cc5_api.py; search with Grep for `frame_camera` and `capture_viewport` and read only those functions.
  - If no silent render is possible, return `{"success": False, "error": ...}`. Do not click.
- The module must still import outside CC5. Follow the existing `try: import RLPy` guard.
- Python 3.10 syntax; the file already has `from __future__ import annotations`.
- Do not touch any other file except `docs/report_P.md`. In that file write, per route: the RLPy calls used, any guesses, and what must be tested live in CC5.
- Do not run CC5. Do not commit.
