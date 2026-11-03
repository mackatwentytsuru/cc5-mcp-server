# CC5 ⇄ Blender pipeline helpers

Needs CC/iC Blender Tools in Blender (`../install-blender-addon.ps1`).

| File | Runs in | What |
|------|---------|------|
| `cc5_export_for_blender.py` | CC5 (Script > Load Python) | export the avatar with the official pipeline flags (FbxKey + json + current pose). Same as `export_fbx` target_tool "Blender". |
| `cc5_import_from_blender.py` | CC5 (Script > Load Python) | `LoadFbxFile` with the FbxKey, reads the FBX path from `cc5_import_from_blender.txt`. Same as `/workflow/import_blender`. Replaces the avatar: save first. |
| `cc5_qt_dialog_probe.py` | CC5 (Script > Load Python) | list / set combo boxes of an open CC5 dialog table (e.g. an item's Type → Shoes). Same as `/workflow/dialog/table_combo`. |
| `cc5_load_motion.py` | CC5 | put a template motion (path in `cc5_load_motion.txt`) on the avatar, e.g. Catwalk_2Loop. |

Paths: the scripts read and write in one work folder. Set the environment variable `CC5_PIPELINE_DIR`
to choose it (default: `~/cc5_pipeline`). `cc5_qt_dialog_probe.py` also reads `CC5_PROBE_ROW`
(the row name prefix to set; default `my_item`).
To run a script in CC5 without the GUI: `/workflow/dialog/native {"enable": false}` →
`/workflow/menu/trigger "Script > Load Python"` → `/workflow/dialog/file_fill {"path": ..., "press": true}`
→ native back to true.

Save a finished custom item with `File > Export > Selected Content` into the matching
`Reallusion Custom/...` folder.
