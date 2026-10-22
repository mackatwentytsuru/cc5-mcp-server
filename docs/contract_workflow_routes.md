# Contract: workflow routes (shared by the Python bridge and the TypeScript MCP tools)

Every route is a POST with a JSON body, and every reply is JSON.
- On success the reply is `{"success": true, ...}`.
- On failure it is `{"success": false, "error": "<clear text>"}`.

**Item selector.** Many routes take an item selector:
- `item_name` (string, optional) and `item_id` (string, optional). At least one must be given.
- Ids come from `list_scene_items`.
- If a name matches more than one item, fail with the error `"ambiguous name"` and add `"matches": [{name,id,kind}]`.

| Route | Python function | Body | Success reply |
|---|---|---|---|
| `/workflow/items` | `list_scene_items` | `{}` | `{"success":true,"items":[{"name","id","kind","visible","parent","cloth_type"?,"hair_type"?}]}`. `kind` is one of `avatar,cloth,accessory,hair,prop,light,camera` |
| `/workflow/visible` | `wf_set_visible` | `{item selector, "visible": bool}` | `{"success":true,"name","id","visible"}` |
| `/workflow/remove` | `wf_remove_item` | `{item selector}` | `{"success":true,"removed":{"name","id","kind"}}` |
| `/workflow/import_fbx` | `wf_import_fbx` | `{"file_path"}` | `{"success":true,"item":{"name","id","kind"}}` |
| `/workflow/attach` | `wf_attach_to_bone` | `{item selector, "bone_name"}` | `{"success":true,"name","bone"}`. If the bone is unknown, the error lists `"bones"` with up to 40 candidate names that contain the text |
| `/workflow/transfer_weights` | `wf_transfer_skin_weights` | `{item selector, "template": "default"|"dress"|"gloves"|"shoes"|"cloak"|"other"}` | `{"success":true,"name","template","kind_after"}` |
| `/workflow/convert_hair` | `wf_convert_to_hair` | `{item selector, "template": "top"|"base_all"|"rear"|"bangs"|"accessory"|"brows"|"upper_lash"|"lower_lash"}` | `{"success":true,"name","template"}` |
| `/workflow/cloth_to_accessory` | `wf_cloth_to_accessory` | `{item selector, "keep_current_shape": bool=true}` | `{"success":true,"name"}` |
| `/workflow/conform` | `wf_conform_cloth` | `{item selector, "iterations": int 1..10 = 1, "values": {"<conform key>": number}?}` | `{"success":true,"name","before":{...},"after":{...}}` |
| `/workflow/transform/get` | `wf_get_transform` | `{item selector}` | `{"success":true,"name","move":[x,y,z],"rotate":[x,y,z],"scale":[x,y,z]}` |
| `/workflow/transform/set` | `wf_set_transform` | `{item selector, "move"?:[3], "rotate"?:[3], "scale"?:[3]}` | `{"success":true,"name","move","rotate","scale"}` (the values after the change) |
| `/workflow/save` | `wf_save_project` | `{"file_path"?: string}` | `{"success":true,"path"}` |
| `/workflow/export_obj` | `wf_export_obj` | `{"file_path", "current_pose": bool=true, "with_materials": bool=true}` | `{"success":true,"path","bytes"}` |
| `/workflow/floor_contact/get` | `wf_get_floor_contact` | `{}` | `{"success":true,"value":<raw>}` |
| `/workflow/floor_contact/set` | `wf_set_floor_contact` | `{"value": <object as returned by get>}` | `{"success":true}` |
| `/workflow/foot_auto` | `wf_auto_adjust_foot_height` | `{}` | `{"success":true}` |
| `/workflow/render` | `wf_render_viewport` | `{"file_path"}` (.png) | `{"success":true,"path"}` |
| `/workflow/views4` | `wf_capture_views4` | `{"folder", "prefix", "target"?: item selector}` | `{"success":true,"files":[front,side,top,persp]}` |
| `/workflow/physics/info` | `wf_physics_info` | `{item selector}` | `{"success":true,"name","kind","activate":bool\|null,"meshes":[{"mesh","materials":[...]}],"properties":[...],"weight_map_import":bool}` |
| `/workflow/physics/activate` | `wf_physics_activate` | `{item selector, "enable": bool}` | `{"success":true,"name","activate","verified"}` (read back with IsActivatePhysicsEnable) |
| `/workflow/physics/weight_map` | `wf_physics_load_weight_map` | `{item selector, physics target, "file_path"}` (.png) | `{"success":true,"name","mesh","material","path","weight_map_present"}`. On failure `"gui_only": true` means: load it by hand in the CC5 GUI |
| `/workflow/physics/params/get` | `wf_physics_get_params` | `{item selector, physics target, "names"?: [...]}` | `{"success":true,"name","mesh","material","params":{...},"unreadable"?}` |
| `/workflow/physics/params/set` | `wf_physics_set_params` | `{item selector, physics target, "values": {name: number\|bool}}` | `{"success":true,"name","mesh","material","before","after"}`; fails with `"mismatched"` when the read-back differs |
| `/workflow/physics/collision/get` | `wf_physics_get_collision` | `{item selector, physics target, "collision_names"?: [...]}` | `{"success":true,"shapes":[{"name","enabled","value"}],"probed","unknown"?}` |
| `/workflow/physics/collision/set` | `wf_physics_set_collision` | `{item selector, physics target, "shapes": [{"name","enabled"?,"value"?}]}` | `{"success":true,"shapes":[{"name","before","after","errors"?}]}` |

`/workflow/views4` saves 4 PNG check images:
- front (looking along +Y);
- side (from +X);
- top (from +Z);
- a perspective view at 45° yaw and 25° pitch.

It frames the target item, or the whole avatar if none is given, and puts the camera back afterwards. This is the "always check with 4 images" rule for image-based review.

## Physics (Soft Cloth) routes

Not yet tried in a live CC5; every RLPy call is guarded and fails with a clear error.

**Physics target.** `mesh_name` and `material_name` (both optional strings) pick one
soft-cloth material. If the item has only one soft-cloth mesh, or the mesh has only
one material, it is picked automatically. Otherwise the error lists `"meshes":
[{mesh, materials}]`. An unknown mesh/material is an error, except for
`/workflow/physics/weight_map`: there it is only noted, because loading the weight
map may be what turns soft cloth on for that material.

RLPy calls used (all exist in CC5's `RLPy.py`):
- `GetPhysicsComponent()` on `RICloth`, `RIAccessory`, `RIHair` and `RIAvatar`. `RIProp` has none, so props must become cloth or accessories first.
- `RIPhysicsComponent`:
  - `GetSoftPhysicsMeshNameList()` and `GetSoftPhysicsMaterialNameList(strMeshName)`
  - `IsActivatePhysicsEnable()` and `SetActivatePhysicsEnable(bActivate)`. This is one switch for the whole item; there is no per-material switch.
  - `GetSoftPhysXProperty(strMeshName, strMaterialName, strPropertyName)` and `SetSoftPhysXProperty(..., fValue)`
  - `GetSoftPhysXCollisionEnable/Value(strMeshName, strMaterialName, strCollisionName)`, `SetSoftPhysXCollisionEnable(..., bEnable)` and `SetSoftPhysXCollisionValue(..., fValue)`
  - `SetPhysicsSoftColthWeightMap(strMeshName, strMaterialName, strFilePath)` (`_RLPy.pyd` also has an overload that takes an `RIImagePtr`) and `GetPhysicsSoftColthWeightMap(strMeshName, strMaterialName)`

**Soft PhysX property names.** `RLPy.py` does not document them. These are CC5's own
soft-cloth keys, taken from `CharacterCreator.exe`:
- `Mass`, `Friction`, `SolverFrequency`, `Damping`, `TetherLimit`, `Drag`, `Elasticity`
- `Stretch`, `Bending`, `Inertia`, `SoftVsRigidCollisionMargin`, `SelfCollisionMargin`
- `SoftVsRigidCollision` and `SelfCollision`. These two are on/off switches and are written as 1/0.

Names are matched without regard to case, spaces or underscores. An unknown name is
rejected before anything is written.

**Collision shapes.** RLPy has no call that lists collision shapes, so names are
probed: either the given `collision_names`, or every skin bone of the owning avatar.
`value` is what RLPy calls the collision value; it is most likely the margin. There is
no API for shape type, size or radius.

**Weight map.** It is loaded with the file-path overload of
`SetPhysicsSoftColthWeightMap`. If this RLPy build lacks the method, or CC5 refuses the
file, the reply has `"gui_only": true`. In that case load the map by hand in the GUI
(画面で読み込む): select the item, then Modify panel > Physics > Weight Map.
