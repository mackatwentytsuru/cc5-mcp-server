# CC5 Plugin → MCP Expansion Roadmap

Goal: drive the user's owned Character Creator 5 plugins/content from Claude Code
(cc5-mcp-server + cc5-agent skill) so common tasks are one tool call.

This roadmap is grounded in a **live RLPy automation audit** run on the actual CC5
5.11 install (2026-06), i.e. what is genuinely scriptable vs UI/Qt-only — not guesses.

## Owned plugins / content (from Reallusion order history)

- **Plugins:** Headshot 3.0, ActorMIXER PRO, SkinGen Premium, HD Face Control (free)
- **Content:** Headshot Morph 1400+ (bonus), HD/Ultimate Morphs, Hair Builder 2 - eGirl
  (+ Extra Material Plus), Short Dress 3, Human/HD Anatomy Set, ActorMIXER CORE Library,
  SkinGen resources

## Live RLPy automation surface (audit results)

| Plugin / system | RLPy surface found | Feasibility |
|---|---|---|
| **Headshot 3** | `RHeadshot`, `RHeadshotOption`, `RHeadshot_CreateHeadFromPhoto`, `RHeadshot_ImportHeadFromObj` | ✅ **Direct MCP** (photo→3D head scriptable) |
| **Morphs** (1400+, Ultimate) | `RIMorphComponent`, `RMorphSliderSetting`, `avatar.GetMorphComponent()` | ✅ Direct MCP (already partly covered by adjust_morph) |
| **Hair Builder 2 / Smart Hair** | `RIHair`, `HairVector`, `EHairType_Bangs/Base/Rear/Top/Accessory`, `avatar.GetHairs()` | ✅ Direct MCP |
| **Face / Expression / Viseme** | `GetFaceComponent`, `GetFacialProfileComponent`, `GetVisemeComponent`, `EFacialProfile_CC5MetaHuman/CC4Extended/...` | ✅ Direct MCP |
| **HD Face Control** | `GetHikEffectorComponent` (HIK facial effectors) | ✅ Direct MCP |
| **SkinGen Premium** | content-folder enums only (`EContentRootFolder_*Makeup`, `ImageLayer`, `EObjectType_ImageLayer`, `EWrinkleLayerType_*`) — no `RSkinGen` class | ⚠️ Partial MCP (content/layer load) + UI for fine editing |
| **ActorMIXER PRO** | `EContentRootFolder_MixerPreset_*` enums only — no RLPy mixer API (native C++ Qt plugin `CCAvatarShaping.dll`) | ❌ No direct API → preset load via MCP; panel driving via in-process Qt automation (see create_actor_mixer) |

## Proposed MCP tools (by priority)

### HIGH — direct RLPy, high value
1. `headshot_create_from_photo(image_path, options)` — RHeadshot_CreateHeadFromPhoto + RHeadshotOption
2. `headshot_import_from_obj(obj_path)` — RHeadshot_ImportHeadFromObj
3. `list_hair` / `apply_hair_element(path, mode=replace|add)` — RIHair / EHairType_*
4. `recolor_hair(...)` / `adjust_hair_morph(...)` — Smart Hair shader + element morph sliders
5. `set_facial_profile(profile)` — EFacialProfile_CC5MetaHuman / CC4Extended / etc.

### MEDIUM
6. `set_viseme(...)` / `face_puppet(...)` — VisemeComponent / FaceComponent
7. `hd_face_effector(...)` — HikEffectorComponent (HD Face Control)
8. `skingen_apply_makeup(layer, content)` — makeup content-folder load (Eye/Lip/Foundation/Full)
9. `skingen_add_image_layer(...)` / `skingen_set_wrinkle(type, weight)` — ImageLayer / EWrinkleLayerType_*

### LOW / UI-bound
10. `load_mixer_preset(path)` — load .ccMixerPreset content (full character / part)
11. ActorMIXER panel automation — reuse the in-process Qt approach from `create_actor_mixer`
    (shiboken2 + QTimer.singleShot); no clean RLPy path exists.

## Next 3 to build (recommended start)

1. **`headshot_create_from_photo`** — biggest capability unlock, fully scriptable.
2. **`apply_hair_element` + `list_hair`** — Hair Builder 2 is owned + heavily used; RIHair is clean.
3. **`set_facial_profile`** — small, high-leverage (switch to CC5 MetaHuman profile etc.).

## Already shipped (this work)

- `create_actor_mixer` — Qt-automation driver for "Create Mixer Assets" (trial guard + confirm gate).
- `export_fbx` — full Export-FBX dialog parity (embed textures, fps, motion, SubD via SetExportLevel,
  CC5_EXPORT_DIR default).

## Implementation notes / guardrails

- RLPy is single-threaded; route all calls through the existing QTimer queue.
- Native Qt plugins (ActorMIXER) need shiboken2 `wrapInstance` + `QTimer.singleShot` to avoid
  blocking the bridge on modal exec loops. Never drive Qt buttons via Windows UIA (no-op).
- Respect trial-content / DRM gates — do not bypass `IsTrialContentMode()` or licensing.
- When researching plugin APIs with sub-agents, keep them **web-only**; do NOT give research
  agents live cc5 MCP access (a research agent once applied a hair element to the live scene).
