# Brief: add text-only workflow tools to the CC5 MCP server

Goal: an LLM that cannot see images (DeepSeek, GLM) must be able to build a character's outfit in Character Creator 5 using only MCP tools. No mouse clicks, no file dialogs, no screenshots.

Today these steps are done by clicking the GUI:
- import FBX
- attach to bone
- Transfer Skin Weights
- Create Hair
- Conform
- delete
- save
- export OBJ

Read first, in this order:
1. `CLAUDE.md` in this repo. It covers the architecture, the hot reload of `cc5-plugin/cc5_api.py`, `_auto_patch_server`, the route tables and the exec opt-in.
2. `cc5-plugin/cc5_api.py`. Copy the existing style:
   - `remove_scene_item`
   - `set_item_visible`
   - `list_clothes`
   - `get_scene_objects`
   - `export_fbx`
   - `_validate_path`
3. `cc5-plugin/server.py`. Read the route tables.
4. `src/tools/visibility.ts`, `src/tools/scene.ts`, `src/tools/asset.ts`, `src/cc5-bridge.ts`. Copy how MCP tools are declared with zod and call the bridge.
5. The real RLPy API stub, `C:/Program Files/Reallusion/Character Creator 5/Bin64/RLPy.py` (15,708 lines; read only the needed classes). There is an index at `J:/OTOLUME/parts/beyon/research/RLPy_index_cc5.txt` (class → methods, with line numbers). Check every signature in RLPy.py before you use it, and never invent methods.

## Tools to add (Python function in cc5_api.py + route + TypeScript MCP tool + tests)

Every write action must:
- be wrapped in `RLPy.RGlobal.BeginAction("<name>")` / `EndAction()` so Undo works;
- validate its inputs;
- return `{"success": bool, ...}` with a clear `error` text;
- never open a dialog.

Paths:
- Must be absolute, use the existing `_validate_path`, and be restricted to `.fbx`/`.obj`/`.ccProject`.
- Output folders must exist.

1. `list_scene_items`. Return one flat list of everything the user may want to edit. For each entry give:
   - `name`, `id` (`GetID()`), `kind` (`avatar`|`cloth`|`accessory`|`hair`|`prop`|`light`|`camera`), `visible`, `parent` (parent object name or bone name if any);
   - `cloth_type` for cloth (`GetClotheType`), `hair_type` for hair (`GetHairType`).
   - Use `RScene.GetAvatars()`, `avatar.GetClothes()`, `GetAccessories(True)`, `GetHairs()`, and `RScene.GetProps()`.
   - Duplicate names exist (e.g. two `cc_p12_skirt`), so the id matters.
2. Make `set_item_visible` and `remove_scene_item` accept either `item_name` or `item_id`, and work for cloth, accessory, hair and prop.
   - Today they fail with "Item not found" for props imported from FBX and for accessories.
   - Use `RScene.QueryObjectByID` when an id is given.
   - Remove with `RScene.RemoveObject`.
   - Visibility via `SetVisible(RTime(0), bool)` or `RScene.Show/Hide`.
   - If a name matches more than one item, refuse and list the ids.
3. `import_fbx(file_path)`. Import an FBX as a Prop with no dialog and return the new item's name and id.
   - Check `RFileIO.LoadFbxFile`, `LoadObject` and `LoadFile` in RLPy.py; pick the one that does not raise a dialog. Document the choice in a code comment.
   - If every variant needs a dialog, return `{"success": false, "error": "...needs GUI"}`. Never click dialogs.
4. `attach_to_bone(item, bone_name)`. Attach a prop/accessory to an avatar bone, for example `CC_Base_Head` or `CC_Base_Spine02` (the GUI's Attach > Pick Parent).
   - Find the bone in `avatar.GetSkeletonComponent().GetSkinBones()` by name.
   - Use `RIObject.SetParent` or `LinkTo`, whichever RLPy.py documents for this.
   - If the bone is missing, return the list of available bone names that contain the given text.
5. `transfer_skin_weights(item, template)`. `template` is one of `default|dress|gloves|shoes|cloak|other`. This turns an accessory into cloth that follows the body.
   - Use `RIAccessory.TransferSkinWeight(...)` or `RICloth.TransferSkinWeight(...)`; check the enum names in RLPy.py.
   - CC shows "Character already has Shoes, replace?" when a second shoes item is made. If the API cannot avoid that dialog, refuse when shoes already exist, and say so.
6. `convert_to_hair(item, template)`. `template` is one of `top|base_all|rear|bangs|accessory|brows|upper_lash|lower_lash`. This is the GUI's "Create Hair, Brows, Beard, Lashes". Use `RIAccessory.ConvertToHair` / `ConvertToFaceHair` per RLPy.py.
7. `convert_cloth_to_accessory(item)`. Use `RICloth.ConvertToAccessory`.
8. `conform_cloth(item, iterations=1, settings={})`. Set the conform values (`GetClothConformValue`/`SetClothConformValue`), then `CalculateCollision`. Return the values before and after.
9. `get_transform(item)` / `set_transform(item, move=[x,y,z]?, rotate=[x,y,z]?, scale=[x,y,z]?)`.
   - Use the `"Transform"` control (`RTransformControl`) at time 0.
   - Units are as CC shows them: move in cm, rotate in degrees, scale where 100 = 100% (the GUI shows 10000 for imported FBX; report raw values and say so).
10. `save_project(file_path=None)`. With no path, save to the current project file; with a path, save there.
    - Use `RFileIO.SaveProject` / `SaveFile`.
    - Never overwrite a file whose name ends with `_hs_ok.ccProject`.
11. `export_obj(file_path, current_pose=True, with_materials=True)`. Use `RFileIO.ExportObjFile`, which takes an export setting/option object; build it per RLPy.py. Z-up.
12. `set_floor_contact(...)` / `auto_adjust_foot_height()`. Wrap `RIAvatar.GetFloorContactValue/SetFloorContactValue` and `AutoAdjustFootHeight` for high-heel shoes. Expose the raw fields RLPy returns.
13. `render_viewport(file_path)`. Save the current viewport to PNG without switching any UI panel. Use `RGlobal.RenderImage` if it can take a path silently; otherwise leave the existing `capture_viewport` and document why.

## Tests and docs
- Add vitest tests for each new TypeScript tool, in the same style as the existing tests (mock the bridge).
- Run `npm test` and `npm run build`; both must pass.
- Python: keep `cc5_api.py` importable outside CC5. Follow the existing guards.
- Update `README.md`: one line per new tool.
- Add a section "Text-only workflow (no screenshots)" with the order:
  1. `list_scene_items`
  2. `import_fbx`
  3. `attach_to_bone`
  4. `transfer_skin_weights` (or `convert_to_hair`)
  5. `conform_cloth`
  6. `save_project`
  7. `export_obj`

## Limits
- Do not enable exec_python.
- Do not change security checks (Host/Origin, path validation) except to add the new allowed extensions.
- Do not commit or push. Leave the changes in the working tree.
- Do not run CC5 or call the live bridge.
- At the end, write `docs/report_text_only_tools.md`. List each tool, the RLPy calls used (with RLPy.py line numbers), and anything you could not do and why.
