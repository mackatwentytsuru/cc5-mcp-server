---
name: cc5-agent
description: Control Reallusion Character Creator 5 (CC5) via MCP tools — avatar creation, morph adjustment, materials/colors, lights, camera, content, viewport capture, asset loading, FBX/MetaHuman export, and text-only outfit/hair work via workflow tools. Trigger on: CC5, character creator, avatar, morph, character creation, 3D character, body shape, facial features, FBX export, 服, 衣装, outfit, custom clothing, Transfer Skin Weights, Conform, ヒール, 髪の登録.
origin: user-project
---

# CC5 Agent Skill

Programmatically control Character Creator 5 avatars through Claude using the CC5 MCP Server.
Verified against **CC5 5.10.x (CC5.1)** — live-tested, ~56 tools. A **text-only workflow tool set**
lets cheap text models (DeepSeek, GLM) do CC5 work safely without seeing the GUI.

## When to Activate

- User mentions CC5, Character Creator, or avatar creation
- Adjusting morphs (body/face), materials, colors, lights, camera, expressions
- Loading character/content assets, browsing CC5 content, exporting FBX / MetaHuman head
- Capturing viewport screenshots, applying body presets
- Custom clothing / outfit / hair from FBX (服, 衣装, ヒール, 髪の登録), Transfer Skin Weights, Conform

## Mandatory checks

1. After EVERY change in CC5, call `capture_views4`. It saves 4 images: front (X), side (Y),
   top (Z), plus one perspective view. Look at ALL 4 images before the next step.
   Never judge from one view.
2. Take screenshots through MCP while working. In your report, say which image shows what.
3. If your model cannot read images, still take the 4 images, save them, and hand their file
   paths to a vision model (Claude or Gemini) for the verdict. Do not continue past a visual
   decision on your own.
4. Never click Windows dialogs blindly. Never type into Windows Open/Save file-name boxes —
   typing there RENAMES files (a folder was once renamed `cc_body_now` → `beyon_parts_v4.ccProject`).
   Never press anything in the "Reallusion Hub の重要なアップデート" dialog. In the DRM content
   dialog, only press Close — never Buy/Pack.
5. Never call `RFileIO.LoadFile` / `LoadObject` on an FBX. They REPLACE THE WHOLE SCENE.
   Use the workflow `import_fbx` tool only (it diffs the scene and reports the new item).
6. Before risky steps, call `save_project`. If the scene breaks, call `/workflow/open_project`
   to reopen the saved file.

## Model routing

- **DeepSeek / GLM** (`claude-oc`, `claude-glm`): run the MCP workflow tools, run the Blender
  fitting scripts, write drafts and reports.
- **Claude / Gemini**: give the visual verdict on the 4 check images, write the owner-facing
  Japanese text, and make final decisions.
- A text model never decides a visual question alone — it always routes to a vision model.

## Architecture

```
Claude (LLM) <--stdio--> MCP Server (Node.js) <--HTTP:5101--> CC5 Plugin (Python) <--RLPy--> CC5
```

## Launching CC5 for use/testing (IMPORTANT)

The bridge plugin only loads once CC5 is in **3D Creator** mode. On launch CC5 shows a splash
then sometimes a "3D Creator / AI Studio" chooser; until 3D Creator is entered, `http://127.0.0.1:5101`
is down. Use `scripts/launch_cc5_for_test.ps1` (launches + waits for the bridge), or launch
`CharacterCreator.exe` and poll `GET /health` until `{"status":"ok"}` (~30-60s). If stuck on the
chooser, click "3D Creator" (left button). CC5 cannot run truly headless.

## Text-only workflow tools (18)

Every result is short readable text; made for models that cannot see the GUI.
Item addressing: `item_name` OR `item_id` from `list_scene_items` (ids preferred — names repeat).

- `list_scene_items` — list every scene item (name, id, kind, visibility, parent); ids for the rest
- `set_visible` — show/hide one item by name or id
- `remove_item` — remove a clothing/hair/accessory/prop item by name or id
- `import_fbx` — import an FBX into the scene as a new item (the ONLY safe FBX import)
- `attach_to_bone` — attach an item to a named skeleton bone (Pick Parent)
- `transfer_skin_weights` — transfer skin weights, template: default | dress | gloves | shoes | cloak | other
- `convert_to_hair` — convert a mesh to hair, template: top | base_all | rear | bangs | accessory | brows
- `cloth_to_accessory` — convert cloth to an accessory (keep_current_shape=true default) to allow transforms
- `conform_cloth` — conform cloth to the body, 1-10 iterations, optional conform values
- `get_transform` / `set_transform` — read/set an item's move, rotate, scale
- `save_project` — save the project, optionally to a new path
- `export_obj` — export the scene to OBJ (optional current pose, materials)
- `get_floor_contact` / `set_floor_contact` — read/apply floor-contact settings
- `auto_adjust_foot_height` — auto-adjust so the avatar stands on the floor
- `render_viewport` — render the current viewport to a PNG
- `capture_views4` — save 4 check images (front X, side Y, top Z, perspective) of an item or the avatar

Route limits (from the plugin report — expect these, do not "fix" them by clicking):
- `set_transform` may return `needs GUI:` when no API path sticks; then use Blender fitting instead.
- Shoes rule: only ONE shoes item per character; a second Shoes transfer needs `replace: true`.
- `convert_to_hair` has no upper_lash/lower_lash template (no API constant) — CC's built-in lashes
  looked better than custom ones anyway.
- Conform key strings are undocumented; pass `values` to read them back.
- `capture_views4` perspective is a preset view (Home/Focus), not an exact 45°; if the camera
  cannot be restored, a `warning` is included.

## Text-only outfit workflow (custom FBX parts)

1. `list_scene_items` — see what is in the scene; note ids.
2. `import_fbx` — import the part FBX. Never `RFileIO.LoadFile`/`LoadObject` (scene-wiping).
3. `attach_to_bone` — `CC_Base_Head` for hair/hat; a body bone (e.g. `CC_Base_Spine02`) before
   Transfer Skin Weights.
4. `transfer_skin_weights` (clothes) or `convert_to_hair` (hair):
   - Clothes templates: Default (tops, gloves/arms, bloomers), Dress (skirts), Shoes (boots).
   - Hair: `base_all` for hair; `brows` for brows. Join left+right boots into ONE mesh before
     the Shoes transfer (only one shoes item allowed).
5. `conform_cloth` — light conform if needed. Prefer Blender numeric fitting over heavy Conform.
6. `capture_views4` — the 4 check images; look at all 4 (or hand paths to a vision model).
7. `save_project` — save before the next part.

Prerequisites from the fitting pipeline (all learned the hard way):
- Build parts in Blender in the SAME frame as the CC body: export the body as OBJ
  ("Character With Current Pose", Z-up, cm); fit in metres, Z-up, front = -Y; export FBX with
  `axis_forward=-Z, axis_up=Y, apply_unit_scale`, embedded textures.
- Use the T-pose (the CC5 preset) BEFORE converting anything. Weights transfer in the current
  pose — a part made for another pose gets double-posed.
- Cloth has no Transform panel. To move/scale it: `cloth_to_accessory`, `set_transform`,
  then `transfer_skin_weights` again.
- Mirror a good left glove to make the right (x → -x, reverse face winding); the CC body is
  symmetric to within 2 mm.

### Blender numeric fitting (cheaper than CC Conform)

Fit by signed distance to the body (BVH `find_nearest`), not by eye:
pull tight items (corset) to a 3 mm gap; push-only for skirts/boots; smooth the displacement
over mesh edges; export and re-import.

```
blender --background part.blend --python J:/OTOLUME/parts/beyon/cc5_trial3/scripts/v11_fit_part.py
blender --background part.blend --python J:/OTOLUME/parts/beyon/cc5_trial3/scripts/v11_check_part.py
```

- `v11_fit_part.py` — fits the part mesh onto the imported body OBJ by signed distance.
- `v11_check_part.py` — reports remaining distances/gaps so you can verify by numbers.

### Hair extras

- Hide scalp gaps with a hair-coloured "cap" mesh made from the head skin, offset 1.5 mm.
- Fill gaps under the hair with an inner layer: strands shrunk ×0.86 toward the head centre,
  dark green, removed in front of the face.
- Lift the bangs off the eyes.

### High heels (research, not yet tested)

- Official route: fit boots to the FLAT foot, transfer as Shoes, go to T-pose, then
  High Heels > Heel Height until the heel touches the floor.
- Do not move the body up or down by hand. Toes poking through: tilt `CC_Base_L/R_Foot` and
  `ToeBase` at frame 0, or widen the inside of the boot.

### Big anime eyes

- Eye Scale ~150, Eyeball Scale ~400. Keep Eyeball Depth small or the eyeball pokes through
  the closed lid. Eyeball Depth: plus = forward. Eyeball Move: minus = toward the nose.
- Morph values above 100 can only be typed in the GUI; the MCP clamps them to -1..1.
- The DH Eye shader draws the iris as a circle; an oval texture does not make an oval iris.

## Available MCP Tools (~55 core tools)

**Scene/avatar:** check_cc5_connection, list_avatars, get_avatar_info, get_scene_objects,
  create_avatar (NEUTRAL untextured base — see "Realistic faces" below), delete_avatar, describe_character
**Morphs:** get_morph_catalog, search_morphs, adjust_morph, adjust_multiple_morphs,
  get_morph_value, reset_morphs, apply_body_preset
**Materials/color:** get_material_info, get_diffuse_color, set_diffuse_color,
  get_material_properties, set_material_opacity, set_material_glossiness, set_material_specular,
  get_shader_parameters, set_shader_parameter (Digital Human Shader: skin roughness / SSS / micronormal),
  set_eye_color, set_hair_color, set_lip_color,
  set_skin_color (sets ALL body skin materials head/body/arm/leg at once — use this for a
  uniform skin tone instead of set_diffuse_color which only hits one material)
**Lights/camera/expression:** get_lights, get_light_info (color + multiplier + active + cast_shadow
  + darken_shadow_strength + range), set_light_color, set_light_multiplier,
  set_light_active (on/off toggle), set_light_shadow (cast_shadow + darken_strength 0-1),
  get_visual_settings, set_ambient (scene fill color 0-1), set_ibl (HDRI/IBL enable + load),
  get_camera_info, set_camera_focal_length, frame_camera (preset views: face/front/home/all/...),
  get_expression_info, set_expression (set facial sliders by name, weight 0-1), reset_expression
**Content:** list_clothes, list_hair, list_accessories, browse_content, remove_scene_item,
  set_item_visible (these last two FAIL on imported props/accessories — use the workflow
  `set_visible` / `remove_item` tools instead, addressed by id)
**Assets/export:** load_asset, export_fbx, set_subdivision_level, capture_viewport,
  bake_skin_textures, export_head_metahuman
**Edit/advanced:** undo, redo, exec_python (gated by CC5_DEV_MODE/CC5_ALLOW_EXEC)

## Realistic faces — DON'T start from create_avatar (avoids the "mannequin/yokai" trap)

`create_avatar` loads the CC3+ **neutral base**, which has **no skin/eye textures, no eyebrows,
no eyelashes, no hair** — it renders as a pale, **blank-white-eyed mannequin**. Sculpting morphs
on top still looks creepy because the problem is *content, not shape*. For a real human face:
```
delete_avatar                      # clear the neutral mannequin (or any current avatar)
browse_content("character")        # -> CC4 Camila / CC4 Susan (female) / CC4 Kevin — FULLY TEXTURED
load_asset("<...>/CC4 Camila.ccAvatar")   # real skin, brown irises w/ catchlights, brows, lashes
# THEN sculpt cuter: bigger rounder eyes, smaller upturned nose, softer/shorter jaw, fuller cheeks+lips
```
- **Hair / eyebrows:** scalp hair is wearable content (`.ccHair`) — a base CC5 install often has
  **zero hair files**; you cannot add hair without a hair pack (or custom FBX → `convert_to_hair`).
- **"Cute" morph direction** (subtle, stacked): larger/rounder eyes + bigger iris, smaller shorter
  upturned nose, narrower softer jaw + shorter chin, fuller cheeks, fuller lower lip, gentle smile
  via set_expression. Over-sculpting = uncanny; keep offsets small.

## Common Workflows

### Start from scratch (textured — preferred)
```
check_cc5_connection -> delete_avatar -> browse_content("character") -> load_asset("CC4 Camila.ccAvatar")
  -> adjust_multiple_morphs([cute set]) -> set_expression(smile) -> frame_camera("face") -> capture_viewport
```
### Adjust features
```
get_avatar_info  (or search_morphs("jaw"))  -> adjust_multiple_morphs([...]) -> capture_viewport
```
### Browse + load content (CC5.1)
```
browse_content("shoes")  -> returns .ccShoes paths -> load_asset("<...>.ccShoes")
```
Categories: wearables (cloth_upper, cloth_lower, cloth, shoes, accessory_head, accessory_body)
and scene/animation (pose, motion, expression, props, light, camera, character). All returned
paths load via load_asset. `pose`/`motion` may be empty on a base install — an honest empty list.
### Export for game engine / MetaHuman
```
set_subdivision_level(2)   # requires HD: generate via CC5 UI Modify > Subdivide first (RLPy can't)
export_fbx("C:/Export/character.fbx", target_tool="UE5", sub_d_level=1, use_smooth_mesh=true)
export_head_metahuman(output_dir, character_name)   # Mesh-to-MetaHuman head
```

## Lighting workflow

Work light-by-light, not by cranking one light up:
1. `get_lights` to list the rig, `get_light_info` to read each light's full state.
2. `set_light_active(name, false)` to mute a light and see its contribution, then re-enable.
3. `set_light_shadow(name, darken_strength=0.2..0.5)` to soften shadows; `cast_shadow=false`
   to drop a fill light's shadow entirely.
4. `set_light_color` / `set_light_multiplier` for warmth and intensity balance.
5. Environment: `set_ambient(r,g,b)` for the global fill; `set_ibl(image_path, enable)` for HDRI
   mood. Read both with `get_visual_settings`.
Capture between changes (`capture_views4`) to judge the result.

## Facial expressions

`get_expression_info` lists slider names grouped (Brow, Eye, Mouth, ...; ~160 sliders on a CC3+
base). `set_expression([{name, weight}, ...])` keys them — weight is **0.0-1.0**, unknown names
are skipped + reported. A subtle smile = `Mouth_Smile_L/R` + `Cheek_Raise_L/R`. `reset_expression`
zeroes everything. Verify visually.

### Expression profile ruler (official Reallusion course data, 2026-07-12)

CC4 Standard = 60 blendshapes / CC4 Extended = 140 / ExPlus = 63 (= ARKit 52 + 11 tongue) /
CC5 Extended ≈ 160 sliders / CC5 HD = 390 / CC5 MetaHuman = 379 sliders (`CTRL_expressions_*`).
Determine via: (1) `get_expression_info` count, (2) `exec_python` `GetProfileType()` /
`GetExpressionSetUid()`, (3) grep morph-target names in an exported FBX. Sliders ≠ blendshapes.
Full SOPs live in the `cc5-driver` skill; course knowledge base:
`C:\Users\macka\Desktop\cc5 to ue\knowledge\reallusion-courses\INSIGHTS.md`.

## Skin / material detail (Digital Human Shader)

CC skin uses the **Digital Human Shader** with ~56 PBR parameters via
`get_shader_parameters(mesh, material)` / `set_shader_parameter(mesh, material, name, [values])`.
Values are **lists of floats** matching the parameter length (validated server-side). Skin
materials are `Std_Skin_Head/Body/Arm/Leg` on `CC_Base_Body`. Useful: `Micro Roughness Scale`
(~0.4 = realistic), `SSS Radius/Falloff/IOR`, `MicroNormal Strength`, `_Specular`, per-region
roughness scales. Always `get_shader_parameters` first, then set.

## Key facts / constraints

- **Morph value range: -1.0 to 1.0** (negative shrinks; not 0-1).
- **Morph IDs are namespaced** (`cc embed morphs/embed_full_body6`). Always `search_morphs(...)`
  / `get_avatar_info()` first.
- **Colors are floats 0.0-1.0** at the API (RLPy stores 0-255 internally; normalized API-side).
- **Content files are `.cc*` on CC5.1**, not legacy `.i*`. `load_asset` accepts both;
  `browse_content` returns `.cc*` paths.
- **Subdivision/HD:** `set_subdivision_level` only switches existing levels; generating HD is
  CC5 UI-only (`Modify > Subdivide`). Fresh CC3+ char = max level 0.
- **RLPy is NOT thread-safe** — all calls run on CC5's main thread via a QTimer queue.
- **CC5 = Python 3.10 + PySide2**. Bridge on port 5101 (`CC5_BRIDGE_URL` to override).
- **Hot reload:** `GET http://127.0.0.1:5101/reload` reloads cc5_api.py. Edits must be copied to
  `.../Bin64/OpenPlugin/CC5_MCP_Bridge/` first.
- **Path safety:** load/export/capture tools reject `..` and enforce extension rules.
- **Item names repeat** (two `cc_p12_skirt`); always use ids.
- **Known bug — capture breaks after loading cloth:** `RenderImage` can stop creating files right
  after a `.ccCloth` load. Workaround: scene change or `GET /reload`, or a `windows` MCP window
  screenshot. Load clothing LAST after capturing the face.
- **capture_viewport** switches the right panel to the Render tab; prefer window screenshots or
  `capture_views4` / `render_viewport`.
- **Color limitations (verify visually!):** `set_lip_color` needs a DEDICATED lip material (the
  CC3+ base has none — clean error). `set_eye_color` may not visibly change the iris (texture-
  driven); a real change needs a texture swap / SkinGen. Use `set_skin_color` for uniform tone.

## GUI and automation pitfalls

- Never type into Windows Open/Save file-name boxes (renames files). Navigate Open dialogs by
  double-clicking; to save under a new name, copy the file with the shell.
- CC5 Save-As/Export dialogs create a folder with the typed name and wait for a second name.
- The Modify panel layout shifts with scrolling — re-read the panel image before every click.
- Other apps (Chrome, 1Password, WindVoice) can come on top of CC5. Check the foreground window
  before clicking; never click while the owner is using the screen.

## Development

```bash
cd C:\Users\macka\Projects\cc5-mcp-server
npm install && npm run build      # MCP server (TypeScript)
npm test                          # 374 unit tests
curl http://127.0.0.1:5101/health # bridge liveness
# Plugin auto-starts inside CC5 (initialize_plugin); install via install-plugin.ps1 (admin).
```

---

## Changes vs the old skill (5 lines)

1. Added a "Mandatory checks" section near the top (4-image `capture_views4` after every change, MCP screenshots named in the report, vision-model escalation, dialog/DRM safety rules, FBX `RFileIO.LoadFile` ban, `save_project` before risky steps).
2. Added a "Text-only outfit workflow" section: the 18 workflow tools with one-line uses and route limits, the 7-step list_scene_items→import_fbx→attach_to_bone→transfer/convert→conform_cloth→capture_views4→save_project pipeline, plus the Blender `v11_fit_part.py` / `v11_check_part.py` fitting step.
3. Added "Model routing" (DeepSeek/GLM run tools and scripts; Claude/Gemini give the visual verdict and owner-facing Japanese) and folded in all 2026-10-22 outfit lessons (same-frame Blender build, T-pose before transfer, one-shoes rule, cloth→accessory for transforms, hair cap + inner layer, high-heel route, anime-eye values, GUI pitfalls, ids over names).
4. Extended the YAML description triggers (服, 衣装, outfit, custom clothing, Transfer Skin Weights, Conform, ヒール, 髪の登録) and flagged that `set_item_visible`/`remove_scene_item` fail on imported props (use workflow tools).
5. Trimmed and merged the older sections (common workflows, expressions, profile ruler, shader, constraints) to stay under ~320 lines while keeping every still-true fact from the old skill.
