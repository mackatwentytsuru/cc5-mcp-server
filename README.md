# CC5 MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP SDK](https://img.shields.io/badge/MCP%20SDK-1.29-green.svg)](https://github.com/modelcontextprotocol/sdk)

An MCP (Model Context Protocol) server that lets LLMs like Claude control **Reallusion Character Creator 5** through natural language. Adjust facial features, apply body presets, capture viewport screenshots, load assets, and export FBX files -- all via conversational commands.

## Architecture

```
┌─────────────┐     stdio      ┌──────────────────┐    HTTP :5101    ┌──────────────────┐     RLPy     ┌─────┐
│  LLM Client │ ◄────────────► │  MCP Server      │ ◄──────────────► │  CC5 Plugin      │ ◄──────────► │ CC5 │
│  (Claude)   │                │  (Node.js / TS)  │                  │  (Python / Qt)   │              │     │
└─────────────┘                └──────────────────┘                  └──────────────────┘              └─────┘
```

The MCP server communicates with Claude via **stdio** transport and forwards commands over **HTTP** to a Python plugin running inside CC5. The plugin executes all RLPy API calls on the main thread via a QTimer-driven command queue, ensuring thread safety.

## Features

### MCP Tools (100)

The MCP server provides 100 tools (registered in 23 modules under `src/tools/`) for controlling CC5. This list matches the code: there is one `server.tool(` call per tool in `src/tools/*.ts` (100 in total, all with unique names).

#### Scene & Avatar Management (8)
| Tool | Description |
|------|-------------|
| `check_cc5_connection` | Verify CC5 is running and the bridge plugin is active |
| `list_avatars` | List all avatars in the current scene |
| `get_scene_objects` | List all scene objects (avatars, props, lights, cameras) |
| `get_avatar_info` | Get avatar details including all non-zero morph values |
| `create_avatar` | Create a new neutral base avatar in the scene |
| `delete_avatar` | Delete an avatar by name, or all avatars |
| `capture_viewport` | Capture a screenshot of the CC5 3D viewport |
| `set_subdivision_level` | Set HD subdivision level (0 = base, 1 = medium, 2 = HD) |

#### Morph Controls & Character (7)
| Tool | Description |
|------|-------------|
| `search_morphs` | Search morph catalog by keyword |
| `adjust_morph` | Adjust a single morph slider (-1.0 to 1.0) |
| `adjust_multiple_morphs` | Batch-adjust multiple morph sliders at once |
| `get_morph_value` | Query the current value of a morph slider |
| `reset_morphs` | Reset all morphs to zero |
| `apply_body_preset` | Apply a body type preset (athletic, muscular, slim, heavy, average) |
| `describe_character` | Natural language description of current character appearance |

#### Facial Expressions & Profiles (5)
| Tool | Description |
|------|-------------|
| `get_expression_info` | Get available expression groups and sliders |
| `set_expression` | Set one or more expression sliders by name (weights 0.0-1.0) |
| `reset_expression` | Reset all expression sliders to neutral |
| `get_facial_profile` | Detect the current avatar's facial (expression) profile — authoritative RLPy profile type (CC5MetaHuman/CC4Extended/CC4Standard/Traditional), expression-set UID, per-category slider counts, and a heuristic ExPlus/HD/MetaHuman/Traditional class + ARKit capability. Read-only. |
| `convert_facial_profile` | Swap the active facial profile by loading a target `.ccFacialProfile` asset (`RIFacialProfileComponent.LoadProfile`). RLPy has no direct profile-type / one-click-ExPlus-upgrade API, so a pre-built target profile file is required. `dry_run` defaults to **true** (inspect + validate only). Intended as a temporary switch before export → convert back to a backup to restore. |

#### Content & Assets (9)
| Tool | Description |
|------|-------------|
| `list_clothes` | List clothing on the current avatar |
| `list_hair` | List hair on the current avatar |
| `list_accessories` | List accessories on the current avatar |
| `remove_scene_item` | Remove clothing, hair, or accessories by name |
| `set_item_visible` | Show or hide a scene item (clothing, hair, accessory, prop, light) |
| `browse_content` | Browse CC5 content folders (clothes, shoes, poses, motions, etc.) |
| `load_asset` | Load a CC5 asset file (.iAvatar, .ccm, .iClothes, etc.) |
| `export_fbx` | Export the current avatar as an FBX file. Mirrors the CC5 "Export FBX" dialog: `target_tool` preset, `export_motion` ("Mesh and Motion"), `sub_d_level` (HD subdivision), `embed_textures`, `fps`, `motion_range`, `convert_image_format`, `texture_size`. A bare filename exports into `D:\CC5Export` (override via `CC5_EXPORT_DIR`). |
| `create_actor_mixer` | Generate ActorMIXER PRO mixer assets (.ccMixerPreset) from the open avatar. `confirm_create` gates a dry-run (false, CANCELs) vs real creation (true). Requires the ActorMIXER PRO plugin. |

#### Materials & Shaders (9)
| Tool | Description |
|------|-------------|
| `get_material_info` | Get mesh and material names |
| `get_diffuse_color` | Get diffuse color of a material |
| `set_diffuse_color` | Set diffuse color (RGB, 0.0-1.0) |
| `get_material_properties` | Get opacity, glossiness, and specular values of a material |
| `set_material_opacity` | Set opacity (0.0 = transparent, 1.0 = opaque) |
| `set_material_glossiness` | Set glossiness (0.0 = matte, 1.0 = glossy) |
| `set_material_specular` | Set specular weight |
| `get_shader_parameters` | Get Digital Human Shader parameters of a material |
| `set_shader_parameter` | Set one Digital Human Shader parameter (skin roughness, SSS, micro-normal, ...) |

#### Colors (4)
| Tool | Description |
|------|-------------|
| `set_eye_color` | Set eye color (convenience shortcut) |
| `set_hair_color` | Set hair color (convenience shortcut) |
| `set_lip_color` | Set lip color (convenience shortcut) |
| `set_skin_color` | Set a uniform skin tone across all body skin materials |

#### Camera (3)
| Tool | Description |
|------|-------------|
| `get_camera_info` | Get camera position and focal length |
| `set_camera_focal_length` | Set camera focal length |
| `frame_camera` | Move the viewport camera to a preset view (face close-up, home, ...) |
| `list_cameras` | List cameras with position, focal length, angle of view and whether scripts can move them (the Preview Camera cannot) |
| `dolly_camera` | Move the viewport camera toward/away from the subject like the mouse wheel (15 cm per notch at the face view at first; **the step size can change during a session**, it became 42 cm once, so use `capture_framed_crop` to compare options at equal size), without moving the user's mouse |
| `list_avatar_parts` | List brows, eyelashes, beard, eyes, teeth and other avatar parts (HD brows are parts, not hairs) |
| `remove_avatar_part` | Remove brow or beard parts by name or type |

#### Lighting (9)
| Tool | Description |
|------|-------------|
| `get_lights` | List all lights in the scene |
| `get_light_info` | Get color and multiplier of a named light |
| `set_light_color` | Set light color (RGB) |
| `set_light_multiplier` | Set light intensity multiplier |
| `set_light_active` | Turn a light on or off |
| `set_light_shadow` | Toggle shadow casting and/or set shadow darkness |
| `get_visual_settings` | Get ambient color and IBL state |
| `set_ambient` | Set the scene ambient (fill) light color |
| `set_ibl` | Enable/disable image-based lighting, optionally loading an HDRI |

#### Edit & History (2)
| Tool | Description |
|------|-------------|
| `undo` | Undo the last operation |
| `redo` | Redo an undone operation |

#### Pop-up (dialog) detection
| Tool | Description |
|------|-------------|
| `list_dialogs` | List the dialogs currently open in CC5 and Reallusion Hub (title, body text, button labels, process, foreground) with a PNG of each when Windows can render it. **Read-only**; works even while CC5's main thread is blocked by a modal dialog. It never clicks. The only tool that presses a button by name is `click_ui_button` (below), and it refuses licence / purchase / delete / login buttons and presses nothing while such a window is open. |

**Automatic warning (Japanese):** while a dialog is open, *every* tool result starts with `⚠ CC5 に小窓が出ています ...` (or `ℹ Reallusion Hub に小窓 ...`) showing title / body / buttons. Dialogs that look like agreements, purchases, logins, updates, deletes or overwrites are flagged "人が判断". Scans are cached ~4 s (about 1 s when a rescan is needed). Implemented by `scripts/list-dialogs.ps1` (EnumWindows + UI Automation), independent of the bridge. Set `CC5_DIALOG_WATCH=0` to disable, `CC5_DIALOG_WATCH_IGNORE_HUB=1` to hide Hub-only notices.

#### UI automation: presets, SkinGen, windows, framed capture, one button (10) -- no mouse

See [UI automation without the mouse](#ui-automation-without-the-mouse) for how it works and what it will and will not press.

| Tool | Description |
|------|-------------|
| `apply_preset` | Apply preset file(s) to the avatar with `RFileIO.LoadFile`: eyelash presets (`.ccAvatarPreset`), eyelash strips (`.rlEyelashElement`), SkinGen makeup (`.ccSkinGenPreset`), hair, cloth, ... (a fixed list of types; never a project, character or FBX). Answers only the known question windows (Apply Character Preset / Eyelash Elements, add-or-replace layer, exit SkinGen editing mode) and reports every other window with a screenshot. Reports what was added/removed in the scene |
| `list_presets` | List preset files that are on disk, by category (`eyelash_preset`, `eyelash_element`, `makeup_lip`, `makeup_eye`, `makeup_eyelash`, ...) or `$/...` content folder; `names` shows which wanted presets are missing (cloud items are not on disk) |
| `skingen_state` | Read the SkinGen editor: on/off, tab, layers (visible / HIDDEN, selected) and the selected layer's opacity |
| `skingen_editor` | Turn the SkinGen editor on/off; off bakes (~10 s), answers "exit SkinGen editing mode?" and waits until CC5 is quiet |
| `skingen_layer` | Select / show / hide / set opacity (0-100) / delete a SkinGen layer, by index or name; reads the result back. Delete needs `confirm_delete=true`; a confirmation window is never answered |
| `list_cc5_windows` | The pop-up / question windows CC5 has open right now, read inside CC5 with Qt: title, text, buttons, check boxes, progress or needs-a-person flags, plus a PNG of each (`QWidget.grab`). Read-only; works behind an ssh tunnel |
| `get_ui_job` | Look at or wait for a job the tools above started (use the job id from a "Still running" reply) |
| `find_ui_widgets` | Read-only finder for CC5's own Qt widgets by objectName / class / text, to discover names for new automation |
| `capture_framed_crop` | Frame a preset view, render it big (default 3600 px) and cut a fixed box, so options are compared at the same scale (does not depend on `dolly_camera`) |
| `click_ui_button` | Press ONE named button of a CC5 window, dialog or dock panel with Qt's `click()` (works while the Windows screen is locked), or one entry of its drop-down menu (`menu_item`). Refuses ambiguous, hidden or disabled buttons and every button about points (except Body Wrap's exact "Generate Wrap Points" and "Align Points" and the menu entries "Save Wrap Points" / "Load Wrap Points", the owner's exception of 2026-10-31), buying, deleting / removing, licences, activation, upgrades, credits, subscriptions or payment. Returns a picture of the window and the dialogs that are open; never answers a window it opened. See [Pressing one named button](#pressing-one-named-button-click_ui_button) |

#### MetaHuman (2)
| Tool | Description |
|------|-------------|
| `bake_skin_textures` | Open CC5's Skin Editor / SkinGen "Bake Textures" workflow (Mesh-to-MetaHuman prep) |
| `export_head_metahuman` | Trigger CC5's "Export Head > Mesh to MetaHuman" pipeline (opens the dialog; you confirm output path and gender) |

#### Advanced (1)
| Tool | Description |
|------|-------------|
| `exec_python` | Execute Python code inside CC5's RLPy environment. **Off by default** -- runs only when `CC5_ALLOW_EXEC=1` is set in the environment CC5 was started from (the bridge decides; the MCP server has no switch of its own and shows the bridge's answer), see [Security](#security) |

#### Text-only workflow tools (25)

These tools drive the `/workflow/*` routes. They work without the GUI and are meant for text-only models; after every change, call `capture_views4` and check all 4 images (front X, side Y, top Z, perspective).

| Tool | Description |
|------|-------------|
| `list_scene_items` | List every scene item with name, id, kind, visibility and parent |
| `set_visible` | Show or hide one item by name or id |
| `remove_item` | Remove one clothing, hair, accessory or prop item |
| `import_fbx` | Import an FBX file as a new scene item |
| `attach_to_bone` | Attach an item to a named skeleton bone |
| `transfer_skin_weights` | Transfer skin weights using a clothing template (default, dress, gloves, shoes, cloak, other) |
| `convert_to_hair` | Convert a mesh item into hair using a hair template (top, base_all, rear, bangs, accessory, brows, upper_lash, lower_lash) |
| `cloth_to_accessory` | Convert a cloth item into an accessory, keeping its current shape by default |
| `conform_cloth` | Conform a cloth item to the body with 1-10 iterations and optional conform values |
| `get_transform` | Read an item's move, rotate and scale values |
| `set_transform` | Set an item's move, rotate and/or scale values |
| `save_project` | Save the current project. `file_path` (or `path`, the same thing) saves under that name; **no path overwrites the open project in place**. Unknown arguments are refused and nothing is saved (a mistyped "save as" used to overwrite the open project). The reply says when it overwrote something |
| `export_obj` | Export the scene, or one item with `item_name`, to OBJ (current pose and materials by default) |
| `offset_mesh` | Move every vertex of an item's mesh by a world offset in cm, keeping skin weights (moves a cloth item; needs that item's OBJ from `export_obj` with `current_pose` false) |
| `get_floor_contact` | Read the current floor-contact settings |
| `set_floor_contact` | Apply floor-contact settings returned by `get_floor_contact` |
| `auto_adjust_foot_height` | Automatically adjust foot height so the avatar stands on the floor |
| `render_viewport` | Render the current viewport to a PNG file |
| `capture_views4` | Save 4 check images (front, side, top, perspective) and put the camera back |
| `get_physics_info` | Show Activate Physics, the soft-cloth meshes/materials and the Soft PhysX property names of a cloth/accessory/hair/avatar item |
| `set_physics_active` | Turn Activate Physics on/off for a whole item (RLPy has no per-material switch) |
| `load_physics_weight_map` | Load a Soft Cloth weight map PNG for one mesh/material (if this fails, load it by hand: Modify > Physics > Weight Map) |
| `get_soft_physics_params` | Read Soft PhysX properties (Mass, Friction, SolverFrequency, Damping, TetherLimit, Drag, Elasticity, Stretch, Bending, Inertia, SoftVsRigidCollisionMargin, SelfCollisionMargin, SoftVsRigidCollision, SelfCollision) |
| `set_soft_physics_params` | Set Soft PhysX properties and read them back |
| `get_physics_collision` | List collision shapes (probed by bone name) with on/off state and value |
| `set_physics_collision` | Turn collision shapes on/off and/or set their value, with read-back |

### MCP Resources

| Resource URI | Description |
|-------------|-------------|
| `cc5://morphs/catalog` | Complete catalog of all morph sliders grouped by category |
| `cc5://avatar/current` | Current avatar state with all active morph values |

## Prerequisites

- **Node.js** 18+ and npm
- **Reallusion Character Creator 5** (CC5)
- **Windows** (CC5 is Windows-only)
- **Blender** 4.5+ (tested with 5.2) **with the CC/iC Blender Tools add-on — required** (step 3 below).
  The goal of this project is to turn 3D models made in Tripo (and similar) into CC5 characters and
  outfits with little hand work; much of that fitting happens in Blender, and every CC5 ⇄ Blender
  round trip (custom shoes, high-heel boots, re-weighted clothes) goes through this add-on.
- **Blender MCP — recommended** ([ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)):
  lets the LLM drive Blender directly next to this server. Install its `addon.py` in Blender
  ("MCP for Blender") and add `{"blender": {"command": "uvx", "args": ["blender-mcp"]}}` to
  `mcpServers`. Background scripts (`blender -b --python ...`) also work without it.

## Quick Start

### 1. Build the MCP Server

```bash
git clone https://github.com/mackatwentytsuru/cc5-mcp-server.git
cd cc5-mcp-server
npm install
npm run build
```

### 2. Install the CC5 Plugin

Run in an **Administrator PowerShell**:

```powershell
powershell -ExecutionPolicy Bypass -File install-plugin.ps1
```

This copies the files of `cc5-plugin/` into CC5's `OpenPlugin\CC5_MCP_Bridge` directory (replacing an older install). Restart CC5 afterwards.

### 3. Install CC/iC Blender Tools in Blender (required)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-blender-addon.ps1
```

Downloads the pinned release of [soupday/cc_blender_tools](https://github.com/soupday/cc_blender_tools)
(Reallusion's own CC/iC Tools add-on), copies it into Blender's user add-on folder as
`cc_blender_tools`, enables it and checks that `bpy.ops.cc3.importer` exists. Use `-Version` for
another tag and `-Blender` when Blender is not under `C:\Program Files\Blender Foundation`.
Do not skip this: without it CC5 exports cannot be read back with their bind pose, and Blender
results cannot be sent to CC5 with the FbxKey (CC5 then asks to "characterize" and replaces the
avatar with a broken `RootNode`).

The round trip used for shoes and high-heel boots:

| Step | Where | How |
|------|-------|-----|
| Export the avatar for Blender | CC5 | `POST /export/fbx {"target_tool": "Blender", "include_current_pose": true}` (same flags as the official CC/iC Blender Pipeline plug-in: FbxKey + json) |
| Import | Blender | `bpy.ops.cc3.importer(param="IMPORT", filepath=..., no_build=True, no_rigify=True)` — do not call `read_factory_settings` first, it unloads the add-on |
| Fit / weight the new mesh, export | Blender | parent to the armature with body weights, then `bpy.ops.cc3.exporter(param="EXPORT_CC3", filepath=...)` |
| Load back | CC5 | `POST /workflow/import_blender {"file_path": ...}` (replaces the avatar — save first) |
| Set the item type | CC5 | `POST /workflow/dialog/table_combo {"window": "Asset Import Status Report", "row_starts": "<mesh>", "column": 1, "text": "Shoes"}`, then press OK |

For high heels: give the avatar a shoe with the wanted High Heels height first, so the feet in the
export are already bent; put the untouched boot on those feet in Blender (never flatten the boot).

### 4. Configure Claude Code

Add to your `~/.claude.json` under `mcpServers` (a ready-made snippet is in `claude-mcp-config.json`):

```json
{
  "cc5": {
    "command": "node",
    "args": ["<path-to-project>/build/index.js"],
    "env": {
      "CC5_BRIDGE_URL": "http://127.0.0.1:5101"
    }
  }
}
```

Replace `<path-to-project>` with the absolute path to this repository.

`exec_python` and the silent Export Head routes are off by default. To use them, see [Security](#security).

### 5. Start the Bridge

**Option A: Automatic (recommended)** -- Launch CC5. The plugin loads automatically from `OpenPlugin/CC5_MCP_Bridge/`. Enable it in Plugin Manager if needed.

**Option B: Manual** -- In CC5, go to Script > Load Python and select `start_bridge.py`.

### 6. Verify Connection

Ask Claude: *"Check if CC5 is connected"* -- it will call `check_cc5_connection` and report the status.

## Usage Examples

### Create and customize a character

> "Create a new avatar and make them athletic with a slightly larger nose"

Claude will call:
1. `create_avatar` -- adds a base avatar
2. `apply_body_preset` with `preset: "athletic"`
3. `adjust_morph` with `morph_id: "Nose_Size"`, `value: 0.6`

### Describe and adjust

> "What does my character look like? Make the jaw wider."

Claude will call:
1. `describe_character` -- reads current morph state
2. `adjust_morph` with `morph_id: "Jaw_Width"`, `value: 0.7`

### Batch modifications

> "Give the character a rounder face with softer features"

Claude will call `adjust_multiple_morphs` with an array of morph adjustments for cheeks, jaw, chin, etc.

### Export for game engine

> "Export this character as FBX to my project folder"

Claude will call `export_fbx` with the specified output path.

The tool reproduces the CC5 "Export FBX (InstaLOD)" dialog. The recommended Unreal (UE5 Skeleton) call is:

```jsonc
{
  "output_path": "character.fbx",   // bare filename -> D:\CC5Export\character.fbx
  "target_tool": "UE5",             // Target Tool Preset: Unreal (UE5 Skeleton)
  "export_motion": true,            // FBX Options: Mesh and Motion
  "sub_d_level": 0,                  // HD Character Subdivision Level: SubD 0
  "embed_textures": true,           // Texture Settings: Embed Textures = ON
  "fps": 30                          // Include Motion: Frame Rate = 30 (Current Animation = All)
}
```

Passing a bare filename (no directory component) exports into `D:\CC5Export` by default — override the folder with the `CC5_EXPORT_DIR` environment variable. Absolute paths are used as-is. Omitting `motion_range` keeps the dialog default "All".

## UI automation without the mouse

Since 2026-10-26 the bridge can apply presets, work the SkinGen editor and read CC5's pop-ups from
a script (`/ui/*` routes, tools in the table above). What was found working on a real CC5: the
`LoadFile` call for presets with a Qt timer that answers the question windows, the Activate Editor
switch, the layer table. The steps to check each piece on a real CC5 are in
[docs/ui-automation-test-steps_ja.md](docs/ui-automation-test-steps_ja.md) (Japanese).

**What is pressed automatically -- only this.**

| Window | Answer |
|--------|--------|
| title `Apply Character Preset` or `Apply Eyelash Elements` | `Apply`; the check box "Restore neutral lash strip" is ticked (`restore_neutral_lash`) |
| "...add a new layer or replace the current layer?" (buttons only Add / Replace / Cancel) | `Replace` or `Add` (`layer_choice`) |
| "...exit SkinGen editing mode?" (buttons only Yes / No / Cancel) | `Yes` or `No` (`exit_answer`) |

Everything else is left alone and reported (with a PNG): delete / overwrite questions, unknown
windows, and **every window that mentions a licence, purchase, login, update, terms, activation,
subscription, payment or trial** (the whole text of the window is checked: labels, buttons, check
boxes, text boxes, group titles; case, accents, invisible characters, words split by tags or `&`, and
Japanese / Korean / Chinese / German / French / Spanish / Russian words are covered; a password field,
a long document or text too long to check also counts). A window we answer must be plain English
(look-alike letters from other scripts mean it is not ours), so a CC5 running in another UI language
will not be answered. While a dialog that needs a person is open, nothing is pressed. Timers stop
themselves and never press the same window more than three times. The text of line edits and text
boxes (mail addresses, keys, passwords) is never returned by `find_ui_widgets`.

**Jobs.** Slow work (apply, editor on/off, layer operations, framed capture) is a job: the route
returns a job id at once and the work goes on inside CC5's Qt event loop in small steps. Poll
`POST /ui/job {"job_id": ...}` (the MCP tools do it for you; `get_ui_job` shows a job later). While a
window is open or CC5 bakes, `/ui/windows`, `/ui/widgets`, `/ui/job` and `/ui/skingen/state` still
answer; **every other bridge command is refused until the job ends** (RLPy is not re-entrant inside
`LoadFile` / the bake; set `CC5_UI_JOB_GUARD=0` to turn that off). One job at a time.

**Routes** (all `POST`, JSON body; see the module docstrings for every field):

| Route | What |
|-------|------|
| `/ui/preset/apply` (job), `/ui/preset/list` | apply preset files / list what is on disk |
| `/ui/skingen/state`, `/ui/skingen/editor` (job), `/ui/skingen/layer` (job) | SkinGen editor |
| `/ui/windows`, `/ui/widgets` | open windows (+ PNG) / widget finder |
| `/ui/capture_crop` (job) | frame, render big, cut a fixed box |
| `/ui/click` (job) | press one named button (or one entry of its drop-down menu) |
| `/ui/job` | state / result of a job |

**From a script:** `scripts/ui_client.py` (Python standard library only) starts a job and polls it, e.g.
`python scripts/ui_client.py apply "C:/.../Rouge.ccSkinGenPreset"`, `... editor off`, `... layer opacity --index 0 --opacity 60`,
`... windows --shots D:/tmp/shots`, `... crop --crop 1230,1610,2190,1930 --out D:/tmp/eyes.png`.
Exit code 2 means a window needs a person.

**Helper modules.** The code lives in `cc5_ui.py` (jobs, windows, the answers), `cc5_uiview.py` (pictures,
widget finder, framed capture), `cc5_skingen.py`, `cc5_content.py`, `cc5_uiclick.py` (one named button),
next to `cc5_api.py`. Copy all of them when you install by hand (`install-plugin.ps1` and `scripts/copy_to_installed.ps1` do); if one is
missing the routes answer with an error that says so and the rest of the bridge keeps working.
`GET /reload` re-reads all of them.

**Limits.** Not run against every CC5 build: widget names come from CC5 on Qt 5.15 / bridge 1.2.0. The
`/ui` routes are local (Host / Origin checks apply) but have no extra token; they are not behind
`CC5_ALLOW_EXEC`. `skingen_layer delete` needs `confirm=true`, which is a guard against accidents and not a
human confirmation. Content still in the cloud is not listed and cannot be applied; downloading
is a person's job (it can bring the Reallusion Hub to the front).

### Pressing one named button (click_ui_button)

Added on 2026-10-30. While the Windows screen is locked, mouse clicks (real or simulated) do nothing, so a
worker could not press Body Wrap's "Save Skeleton" and hand-fixed points were lost when the window closed.
Qt's `QAbstractButton.click()` still works on a locked screen (tried with Headshot's Paste button), so the
bridge can press a button for you: tool `click_ui_button`, route `POST /ui/click` (a job, like the others).

| Argument | Meaning |
|----------|---------|
| `window` (required) | Title of the CC5 window, dialog or dock panel (case-insensitive), or its objectName. Floating tool windows such as Body Wrap show up in `list_cc5_windows include_other=true` |
| `object_name` and / or `text` | The button: exact objectName, and / or exact visible text (case and the `&` shortcut marker are ignored). Find names with `find_ui_widgets` |
| `menu_item` | Exact text of one entry in the button's own drop-down menu (for example "Save Skeleton" under a disk button): that entry is triggered instead of the button |
| `wait_ms` | How long to wait after the click before the picture (default 1000, 200-15000) |
| `screenshot`, `max_width` | PNG of the window and of every open dialog (default true, 900 px) |

**It refuses (and presses nothing) when:**

- the window or button matches nothing, or more than one **visible** thing (hidden buttons never count and are never pressed);
- the button or menu entry is disabled or hidden;
- its text, objectName or tool tip contains one of these words (any case, also with spaces or tags inside the word):
  `point` / `ポイント`, `buy` / `購入` / `purchase`, `delete` / `削除` / `remove`, `license` / `licence` / `ライセンス` / `activate`,
  `upgrade`, `credit` / `クレジット`, `subscribe`, `pay` / `支払` -- or a word of the window safety list above (login, update, terms, trial, ...);
- a window that needs a person (licence, purchase, login, ...) is open;
- a modal window is open and the button is not in it (a person could not press it either);
- the button opens a drop-down menu and no `menu_item` was given (the menu would stay open on a locked screen).

The click runs on CC5's main thread from a Qt timer, so if it opens a modal window (a file dialog, a
question) the job still finishes: the reply says `click_returned: false` and lists that window with its
picture. **Nothing in it is answered.** Look at it and ask the owner when it is not routine. The checks
live in the bridge (`cc5_uiclick.py`), because any local program can call it; the MCP tool only forwards.

### ボタンを 1 つ押す(click_ui_button、日本語)

2026-10-30 に足しました。Windows の画面に鍵がかかっている間は、マウスのクリックが効きません。そのため、Body Wrap の
「Save Skeleton」を押せず、手で直した点が消えました。Qt の `click()` は鍵の間も効く(Headshot の Paste で確認)ので、
ブリッジがボタンを押せるようにしました。道具は `click_ui_button`、ルートは `POST /ui/click`(ジョブ)です。

- **指定のしかた**: `window` に窓・小窓・ドックの題名(大文字小文字は問わない)か objectName。ボタンは `object_name`(完全一致)か
  `text`(見えている文字の完全一致。大文字小文字と `&` は問わない)、または両方。▾ のメニューの中の項目は `menu_item` に項目の文字を書く。
- **断るとき(何も押さない)**: 当たるものがない・見えているものが 2 つ以上ある。隠れている・灰色(無効)のボタンや項目。
  文字・objectName・ツールチップに次の語があるもの: `point`/`ポイント`、`buy`/`購入`/`purchase`、`delete`/`削除`/`remove`、
  `license`/`licence`/`ライセンス`/`activate`、`upgrade`、`credit`/`クレジット`、`subscribe`、`pay`/`支払`(ほかに login・update・
  規約・体験版など、上の窓の安全の語も)。人が決める窓(ライセンス・購入・ログインなど)が開いている間。モーダルの窓が開いていて、
  押すボタンがその中にないとき。▾ のメニューを持つボタンで `menu_item` がないとき。
- **返すもの**: 押したもの、`click_returned`(押した結果の窓が開いたままなら false)、窓の絵、開いている小窓の一覧と絵。
  押した結果に開いた窓には**何も答えません**。絵を見て、決まった手順でないときは本人に聞いてください。

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CC5_BRIDGE_URL` | `http://127.0.0.1:5101` | Full URL of the CC5 bridge HTTP server |
| `CC5_BRIDGE_PORT` | `5101` | Port for the bridge server (set in `cc5-plugin/main.py`) |
| `CC5_DEV_MODE` | `0` | Development helpers in the bridge plugin: `GET /reload` without a token and the full `GET /api` route list. Accepts `1`, `true` or `yes`. Read from the environment CC5 starts from. It does **not** enable code execution |
| `CC5_ALLOW_EXEC` | *(unset)* | Enables `exec_python` (`POST /exec/python`) and the silent Export Head routes (`POST /export/head_mh/silent/*`). Accepts `1`, `true` or `yes`. Read **only by the bridge plugin**, from the environment CC5 was started from; the MCP server does not read it -- see [Security](#security) |
| `CC5_RELOAD_SECRET` | *(empty)* | Auth token for the `/reload` endpoint. If set, requests must include `X-Reload-Token` header |
| `CC5_REQUEST_TIMEOUT_MS` | `30000` | HTTP request timeout in milliseconds (MCP server side) |
| `CC5_ROOT` | `C:\Program Files\Reallusion\Character Creator 5` | CC5 installation path (used for default avatar loading) |
| `CC5_DIALOG_WATCH` | `1` | `0` disables the dialog warning that is prepended to tool results |
| `CC5_DIALOG_WATCH_IGNORE_HUB` | *(unset)* | `1` hides Reallusion Hub-only dialogs from the warning |
| `CC5_EXPORT_DIR` | `D:\CC5Export` | Default output folder for `export_fbx` when given a bare filename (no directory). Read by the bridge plugin. |
| `CC5_UI_JOB_GUARD` | `1` | `0` lets other bridge commands run while a UI job (apply preset, SkinGen editor, framed capture) is running. Read by the bridge plugin |
| `CC5_CONTENT_ROOTS` | `C:/Users/Public/Documents/Reallusion/Reallusion Templates` + `Reallusion Custom` | Folders `list_presets` reads when RLPy cannot list a content folder (path-separator list). Read by the bridge plugin |

## Development

### Build

```bash
npm run build        # Compile TypeScript
npm run dev          # Watch mode (recompiles on change)
```

### Test

```bash
npm test             # Run tests
npm run test:watch   # Watch mode
npm run test:coverage # With coverage report
npm run test:py      # Bridge plugin security tests (Python 3.10+, no CC5 needed)
```

Current suite: 813 Vitest tests in 24 files, plus 345 Python tests (bridge security, route tables, and the UI automation with a fake Qt in `tests/python/fake_qt.py`).

### Hot-Reload the Python Plugin

The bridge supports hot-reloading `cc5_api.py` without restarting CC5. It is off by default: set `CC5_DEV_MODE=1` (or `CC5_RELOAD_SECRET`) in the environment CC5 starts from.

```bash
# Without auth
curl http://127.0.0.1:5101/reload

# With auth (when CC5_RELOAD_SECRET is set)
curl -H "X-Reload-Token: <secret>" http://127.0.0.1:5101/reload
```

After reloading, the server's dispatch table is automatically patched with the updated functions.

### Project Structure

```
cc5-mcp-server/
├── src/                    # MCP Server (TypeScript)
│   ├── index.ts            # Entry point
│   ├── cc5-bridge.ts       # HTTP client for CC5 bridge
│   ├── types.ts            # Type definitions
│   ├── util.ts             # Shared utilities (bridgeCall wrapper)
│   ├── tools/              # MCP tool definitions (24 files, 100 tools total)
│   │   ├── morph.ts        # Morph search, adjust, reset (5 tools)
│   │   ├── scene.ts        # Scene/avatar management, viewport, subdivision (7 tools)
│   │   ├── asset.ts        # Asset loading / FBX export (2 tools)
│   │   ├── actor-mixer.ts  # ActorMIXER PRO mixer assets (1 tool)
│   │   ├── character.ts    # Body presets, character description (2 tools)
│   │   ├── content.ts      # Clothes, hair, accessories, avatar parts, browse (7 tools)
│   │   ├── color.ts        # Eye, hair, lip, skin color setters (4 tools)
│   │   ├── material.ts     # Material info, colors, properties, shader parameters (9 tools)
│   │   ├── camera.ts       # Camera info, focal length, framing, dolly (5 tools)
│   │   ├── light.ts        # Lights, ambient, IBL (9 tools)
│   │   ├── visibility.ts   # Show/hide items, scene objects (2 tools)
│   │   ├── edit.ts         # Undo/redo (2 tools)
│   │   ├── expression.ts   # Expression info, set, reset (3 tools)
│   │   ├── facial-profile.ts # Facial profile detect + convert (2 tools)
│   │   ├── scripting.ts    # Python execution (1 tool)
│   │   ├── metahuman.ts    # MetaHuman export (2 tools)
│   │   ├── dialogs.ts      # list_dialogs (1 tool)
│   │   ├── presets.ts      # apply_preset, list_presets (2 tools)
│   │   ├── skingen.ts      # SkinGen state / editor / layer (3 tools)
│   │   ├── ui-windows.ts   # list_cc5_windows, get_ui_job, find_ui_widgets (3 tools)
│   │   ├── framed-capture.ts # capture_framed_crop (1 tool)
│   │   ├── ui-click.ts     # click_ui_button (1 tool)
│   │   ├── ui-common.ts    # Shared helpers of the UI tools (job waiting, window text)
│   │   └── workflow.ts     # Text-only workflow routes (26 tools)
│   └── resources/
│       └── morphs.ts       # Morph catalog & avatar state resources
├── cc5-plugin/             # CC5 Python plugin
│   ├── main.py             # Plugin entry (initialize_plugin / uninitialize_plugin)
│   ├── server.py           # HTTP bridge server (http.server)
│   ├── cc5_api.py          # RLPy API wrapper
│   ├── cc5_ui.py           # Qt core: jobs, windows, the answers we allow, job guard
│   ├── cc5_uiview.py       # Window pictures, widget finder, framed capture
│   ├── cc5_skingen.py      # SkinGen editor / layers
│   ├── cc5_content.py      # Preset list / apply
│   ├── cc5_uiclick.py      # Press one named button (/ui/click) and its refusals
│   └── config.json         # Plugin configuration
├── scripts/ui_client.py    # Stdlib client for the /ui routes (job polling, window PNGs)
├── tests/                  # Vitest unit tests; tests/python = bridge + UI automation tests
├── start_bridge.py         # Manual bridge startup script
├── install-plugin.ps1      # Plugin installer (requires admin)
└── claude-mcp-config.json  # Claude Code MCP config snippet
```

## API Reference

The bridge exposes one HTTP route per tool. The tables below list the core routes; the complete route table is `GET_ROUTES` / `POST_ROUTES` in `cc5-plugin/server.py` (and `GET /api` returns it when `CC5_DEV_MODE=1`).

### GET Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /health` | Health check; also whether CC5's main thread runs and whether `CC5_ALLOW_EXEC` is on for CC5 | `{"result": {"status": "ok", "service": "cc5-mcp-bridge", "version": "...", "main_thread_blocked": false, "exec_allowed": false, ...}}` |
| `GET /api` | API discovery (all endpoints and required params, dev mode) | `{"result": {"service": "...", "endpoints": {...}}}` |
| `GET /reload` | Hot-reload cc5_api module (needs `CC5_DEV_MODE=1` or `CC5_RELOAD_SECRET`) | `{"result": {"success": true}}` |
| `GET /avatars` | List all scene avatars | `{"result": [{"name": "...", "id": "...", "type": "..."}]}` |
| `GET /avatar/info` | Current avatar details + active morphs | `{"result": {"name": "...", "active_morphs": {...}}}` |
| `GET /morphs/catalog` | Full morph catalog grouped by category | `{"result": {"Category": [{"id": "...", "display_name": "..."}]}}` |
| `GET /facial/profile` | Current avatar's facial-profile detection (read-only) | `{"result": {"profile_type": "CC5MetaHuman", "expression_set_uid": "...", "total_sliders": 379, "heuristic_class": "...", "arkit_capable": true}}` |

### POST Endpoints

| Endpoint | Parameters | Description |
|----------|-----------|-------------|
| `POST /morph/get` | `morph_id` | Get current morph value |
| `POST /morph/set` | `morph_id`, `value` | Set a morph slider (-1.0 to 1.0) |
| `POST /morphs/set` | `morphs` (array of `{id, value}`) | Set multiple morphs at once (-1.0 to 1.0 each) |
| `POST /avatar/create` | *(none)* | Create a default CC3+ avatar |
| `POST /asset/load` | `file_path` | Load a CC5 asset file |
| `POST /export/fbx` | `output_path`, `options` (optional) | Export avatar as FBX |
| `POST /facial/profile/convert` | `target_profile_path`, `dry_run` (default true), `backup_current_to` (optional) | Swap facial profile via LoadProfile of a target `.ccFacialProfile`. `dry_run=true` inspects/validates only |
| `POST /viewport/capture` | `output_path` (optional) | Capture viewport screenshot |
| `POST /subdivision` | `level` (0-2) | Set HD subdivision level |

All responses follow the envelope format: `{"result": ...}` on success, `{"error": "..."}` on failure.

## Security

The bridge is a local HTTP server running inside CC5. It has these protections:

- **Localhost only** -- The bridge server binds exclusively to `127.0.0.1`. The MCP server validates that `CC5_BRIDGE_URL` points to localhost before connecting.
- **Host check (DNS rebinding)** -- Every request must carry `Host: 127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`, with the bridge's own port. A web page that points its own domain at 127.0.0.1 still sends its own domain name, so it gets HTTP 403.
- **No requests from web pages** -- Requests with an `Origin` header, or with a `Sec-Fetch-Site` header other than `none`, get HTTP 403. Browsers add these headers to requests made by web pages (including form posts and `<img>` loads); curl, Python, PowerShell and the MCP server do not send them. The bridge sends no CORS headers.
- **Risky features are off by default** -- see the next section.
- **Path validation** -- Both the TypeScript MCP server and the Python plugin validate file paths to prevent path traversal (`..`) attacks. Only allowed file extensions are accepted for asset loading and export.
- **Reload authentication** -- The `/reload` endpoint supports token-based auth via the `CC5_RELOAD_SECRET` environment variable and `X-Reload-Token` header.
- **Request size limits** -- The bridge enforces a 1 MB maximum request body size.
- **Thread safety** -- All RLPy API calls are serialized through a command queue and executed on CC5's main thread via QTimer.

### Off by default

| Feature | What it does | Turned on by |
|---------|--------------|--------------|
| `exec_python` tool / `POST /exec/python` | Runs any Python code inside CC5 | `CC5_ALLOW_EXEC=1` |
| `POST /export/head_mh/silent/*` (4 routes) | Drives CC5's Export Head dialogs and types the save path with simulated keystrokes, without asking you | `CC5_ALLOW_EXEC=1` |
| `GET /reload` without a token, full `GET /api` route list | Development helpers | `CC5_DEV_MODE=1` |

Neither `CC5_DEV_MODE` nor `CC5_RELOAD_SECRET` enables code execution. While a feature is off, the bridge answers HTTP 403 with a message that says who decides, how to turn it on and off, and not to go around it; the `exec_python` tool shows that message as it is. When the plugin starts, CC5's Python console prints which of these are on, and `GET /health` reports `exec_allowed` (shown by `check_cc5_connection`).

### One switch: CC5_ALLOW_EXEC in CC5's environment

Whether `exec_python` and the silent Export Head routes run is decided **only** by `CC5_ALLOW_EXEC` in the environment Character Creator 5 was started from. The bridge checks it on every call (in `server.py` by action name, and again inside `cc5_api.py`).

The MCP server has **no switch of its own**: the `exec_python` tool always forwards the call and shows the bridge's answer. It used to check its own copy of `CC5_ALLOW_EXEC` too, and when only that copy said no, a worker called `POST /exec/python` on the bridge directly and got past it. Any program on the computer can reach the bridge, so the bridge is the only place where the decision can be enforced. **Calling the bridge directly (or through another route) to get around a refusal is not allowed: ask the owner.**

**Turn it on** -- set it for your Windows user, then quit CC5 and start it again:

```powershell
setx CC5_ALLOW_EXEC 1
```

`setx` only reaches programs started after it. Start CC5 from the Start menu or from a new terminal; a terminal or app that was already open keeps its old environment until it is restarted.

**Turn it off** -- set it to `0` (or delete the variable), then restart CC5:

```powershell
setx CC5_ALLOW_EXEC 0
# or delete it:
[Environment]::SetEnvironmentVariable("CC5_ALLOW_EXEC", $null, "User")
```

A `CC5_ALLOW_EXEC` entry in the MCP server's `env` (from older instructions) is ignored now; you can remove it.

### What turning it on risks

- Any program running on your computer under your account, and anything that can make the LLM call `exec_python` (for example instructions hidden in a file or web page the model reads), can run code inside CC5 with your user's permissions: read and write your files, start programs, use the network.
- The silent Export Head routes send keystrokes to the window in front. If another window comes to the front while they run, the keystrokes go there.
- The Host and Origin checks stop web pages, not other programs on the same computer. Only turn this on for a computer you trust, never make port 5101 reachable from other computers (no port forwarding or proxies), and turn it off when you do not need it.

### Upgrading from 1.1.x

- `exec_python` used to be on by default (through `CC5_DEV_MODE`, which defaulted to `1`). It is now off until you set `CC5_ALLOW_EXEC=1` as described above.
- `CC5_DEV_MODE` now defaults to `0`. Set `CC5_DEV_MODE=1` for CC5 if you use `GET /reload` while working on the plugin.
- Rebuild the MCP server (`npm run build`), reinstall the plugin and restart CC5. `GET /health` reports `"version": "1.2.0"` once the new plugin is running. Note that `install-plugin.ps1` replaces the whole `CC5_MCP_Bridge` folder, so move anything you keep in it first.
- Since 2026-10-30 the MCP server no longer reads `CC5_ALLOW_EXEC` (see [One switch](#one-switch-cc5_allow_exec-in-cc5s-environment)). `GET /health` has `exec_allowed` once the plugin of that date runs (server.py changed, so restart CC5).

## セキュリティ(日本語)

ブリッジは、CC5 の中で動くローカルの HTTP サーバーです。次の守りが入っています。

- **このパソコンの中だけ** -- ブリッジは `127.0.0.1` だけで待ち受けます。MCP サーバーは、localhost 以外を指す `CC5_BRIDGE_URL` を受け付けません。
- **Host の確認(DNS リバインディング対策)** -- Host ヘッダーが `127.0.0.1:<ポート>`・`localhost:<ポート>`・`[::1]:<ポート>`(ブリッジ自身のポート)でないリクエストは、HTTP 403 で断ります。自分のドメインを 127.0.0.1 に向けた Web ページは、自分のドメイン名を送ってくるので、ここで止まります。
- **Web ページからのリクエストを断る** -- `Origin` ヘッダーがある、または `Sec-Fetch-Site` が `none` 以外のリクエストは、HTTP 403 で断ります。ブラウザーは、Web ページが出すリクエスト(フォームの送信や `<img>` の読み込みを含む)にこれらを付けます。curl・Python・PowerShell・MCP サーバーは付けません。CORS のヘッダーも返しません。
- **危ない機能は初期状態で無効** -- 下の表のとおりです。
- パスの検査、`/reload` のトークン認証、1 MB の上限、CC5 のメインスレッドでの実行は、これまでどおりです。

### 初期状態で無効なもの

| 機能 | すること | 有効にする設定 |
|------|---------|----------------|
| `exec_python` ツール / `POST /exec/python` | CC5 の中で、どんな Python コードでも動かす | `CC5_ALLOW_EXEC=1` |
| `POST /export/head_mh/silent/*`(4 つ) | CC5 の Export Head の画面を自動で操作し、保存先をキー入力で打ち込む(確認なし) | `CC5_ALLOW_EXEC=1` |
| トークンなしの `GET /reload`、`GET /api` の全ルート一覧 | 開発用の機能 | `CC5_DEV_MODE=1` |

`CC5_DEV_MODE` や `CC5_RELOAD_SECRET` では、コードの実行は有効になりません。無効のあいだは、ブリッジが HTTP 403 を返し、誰が決めるか・どう切りかえるか・断りを回り道で越えないこと、を知らせます。`exec_python` ツールは、その文をそのまま見せます。プラグインが起動すると、CC5 の Python コンソールにどれが有効かが表示され、`GET /health` の `exec_allowed` にも出ます(`check_cc5_connection` が表示します)。

### 切りかえは 1 つだけ: CC5 の環境の CC5_ALLOW_EXEC

`exec_python` と silent ルートを動かすかどうかは、**CC5 を起動したときの環境の `CC5_ALLOW_EXEC` だけ**で決まります。ブリッジが毎回たしかめます(`server.py` が命令の名前で、`cc5_api.py` の中でももう一度)。

MCP サーバーには**自分の切りかえがありません**。`exec_python` ツールは、いつもブリッジに渡して、ブリッジの答えを見せます。前は MCP サーバーも自分の `CC5_ALLOW_EXEC` を読んでいて、そちらだけが断ったとき、作業役がブリッジの `POST /exec/python` を直接呼んで、断りを越えてしまいました。ブリッジにはこのパソコンのどのプログラムからも届くので、決まりを守らせられるのはブリッジだけです。**断られたときに、ブリッジを直接(または別のルートで)呼んで越えるのは禁止です。本人に聞いてください。**

**有効にする** -- Windows のユーザー環境変数に設定して、CC5 を終了してから起動し直します。

```powershell
setx CC5_ALLOW_EXEC 1
```

`setx` は、このあとに起動したプログラムにだけ効きます。CC5 はスタートメニューか、新しく開いたターミナルから起動してください。前から開いているターミナルやアプリは、再起動するまで古い設定のままです。

**無効に戻す** -- `0` にする(または変数を消す)して、CC5 を再起動します。

```powershell
setx CC5_ALLOW_EXEC 0
# または消す:
[Environment]::SetEnvironmentVariable("CC5_ALLOW_EXEC", $null, "User")
```

MCP サーバーの `env` に前の説明どおり `CC5_ALLOW_EXEC` を書いていても、今は読まれません。消してかまいません。

### 有効にすると何が危ないか

- このパソコンで同じユーザーとして動くプログラムや、LLM に `exec_python` を呼ばせられるもの(たとえば、モデルが読むファイルや Web ページに隠された指示)が、CC5 の中でコードを動かせるようになります。あなたのユーザーの権限でできること(ファイルの読み書き、プログラムの起動、ネットへの通信)は、全部できてしまいます。
- silent ルートは、いちばん前のウィンドウにキー入力を送ります。動いているあいだに別のウィンドウが前に出ると、そちらに入力されます。
- Host と Origin の確認で防げるのは Web ページだけです。同じパソコンの中の別のプログラムは防げません。信頼できるパソコンでだけ有効にし、ポート 5101 をほかのパソコンから届くようにしないでください(ポートの転送やプロキシをしない)。使わないときは無効に戻してください。

### 1.1.x からの更新

- これまでは `CC5_DEV_MODE` の初期値が `1` だったため、`exec_python` が初期状態で有効でした。今は、上のとおり `CC5_ALLOW_EXEC=1` を設定するまで無効です。
- `CC5_DEV_MODE` の初期値は `0` になりました。プラグインの開発で `GET /reload` を使うときは、CC5 用に `CC5_DEV_MODE=1` を設定してください。
- MCP サーバーを作り直し(`npm run build`)、プラグインを入れ直して、CC5 を再起動します。新しいプラグインが動いていれば、`GET /health` が `"version": "1.2.0"` を返します。`install-plugin.ps1` は `CC5_MCP_Bridge` フォルダーを丸ごと入れ替えるので、そこに置いているものは先に移してください。
- 2026-10-30 から、MCP サーバーは `CC5_ALLOW_EXEC` を読みません(上の「切りかえは 1 つだけ」)。この日のプラグインが動くと、`GET /health` に `exec_allowed` が出ます(`server.py` を変えたので、CC5 の再起動が要ります)。

## License

[MIT](LICENSE) © Yuki Tsuruoka

---

Made by Yuki Tsuruoka — stage visuals and live show production, building tools with Claude Code. Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [channel](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)

制作: Yuki Tsuruoka — ステージ映像とライブ演出の制作。Claude Code でツールを作っています。Web: [otolume.com](https://otolume.com) / Instagram: [@tsuru614](https://www.instagram.com/tsuru614/) / YouTube: [チャンネル](https://www.youtube.com/channel/UCYngpwyo7vGBIXBtKhh7z1g)
