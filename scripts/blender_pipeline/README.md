# CC5 ⇄ Blender pipeline helpers (high-heel boots, 2026-10-23)

Needs CC/iC Blender Tools in Blender (`../install-blender-addon.ps1`).

| File | Runs in | What |
|------|---------|------|
| `cc5_export_for_blender.py` | CC5 (Script > Load Python) | export the avatar with the official pipeline flags (FbxKey + json + current pose). Same as `export_fbx` target_tool "Blender". |
| `v29_boot_bt.py` | `blender -b --python` | open the CC/iC Tools import, put an untouched boot on the heel-bent feet (rigid move), copy body weights, `EXPORT_CC3`. |
| `v28_boot_shift.py` | `blender -b --python` | move each boot of a pair inward / back / down by cm before the step above. |
| `cc5_import_from_blender.py` | CC5 (Script > Load Python) | `LoadFbxFile` with the FbxKey, reads the FBX path from `cc5_import_from_blender.txt`. Same as `/workflow/import_blender`. Replaces the avatar: save first. |
| `cc5_qt_dialog_probe.py` | CC5 (Script > Load Python) | list / set combo boxes of an open CC5 dialog table (boot Type → Shoes). Same as `/workflow/dialog/table_combo`. |

Paths inside the scripts point at the beyon project (`D:\OTOLUME\beyon_cc5`); change them for other work.
To run a script in CC5 without the GUI: `/workflow/dialog/native {"enable": false}` →
`/workflow/menu/trigger "Script > Load Python"` → `/workflow/dialog/file_fill {"path": ..., "press": true}`
→ native back to true.
| `cc5_load_motion.py` | CC5 | put a template motion (path in `cc5_load_motion.txt`) on the avatar, e.g. Catwalk_2Loop. |
| `cc5_try_shoes_on.py` | CC5 | load another character and a saved `.ccShoes` on it (paths in `cc5_try_shoes_on.txt`). |

Save the finished boot as custom content with `File > Export > Selected Content` (boot selected) into
`Reallusion Custom/Cloth/Shoes/<name>.ccShoes`. The .ccShoes keeps the bent feet: tested on CC4 Camila
with the Catwalk motion (2026-10-23).
