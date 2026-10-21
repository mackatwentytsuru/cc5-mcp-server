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

`/workflow/views4` saves 4 PNG check images:
- front (looking along +Y);
- side (from +X);
- top (from +Z);
- a perspective view at 45° yaw and 25° pitch.

It frames the target item, or the whole avatar if none is given, and puts the camera back afterwards. This is the "always check with 4 images" rule for image-based review.
