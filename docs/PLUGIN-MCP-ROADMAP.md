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
- **Never probe an unknown RLPy signature by calling it with `None` / wrong-arity args.**
  A SWIG null-reference error can be caught as a Python exception yet still leave the C++ side
  corrupt, crashing CC5 seconds later. Read `docs/rlpy-api-reference.md` first.
  See [headshot3-findings.md](headshot3-findings.md) §2 for two measured crashes.
- A modal dialog in CC5 blocks the main-thread QTimer queue, so `exec_python` silently stalls
  while the bridge still reports "connected". Watch for dialogs when calls appear to hang.

## 小窓(ダイアログ)の検出 (2026-10-21)

CC5 のモーダルな小窓が主のスレッドを止めると、ブリッジは生きているのに何も実行されない。
これを人が見逃さないための仕組み。

- `list_dialogs` ツール: CC5(CharacterCreator.exe)と Reallusion Hub の、いま開いている小窓の題名・本文・ボタン・
  プロセス・前面かどうか(と画像)を返す。`scripts/list-dialogs.ps1`(EnumWindows + UI Automation)を使うので、
  **CC5 の主のスレッドが止まっていても動く**(ブリッジを通らない)。
- 自動の注意: どの MCP ツールの結果にも、小窓があれば先頭に `⚠ CC5 に小窓が出ています ...` が付く(4 秒キャッシュ)。
  規約・購入・ログイン・更新・削除・上書きらしい小窓には「人が判断」と付く。
- **小窓を押す道具は作らない**(読むだけ)。押すかどうかは人が決める。
- 切る: `CC5_DIALOG_WATCH=0` / Hub だけ隠す: `CC5_DIALOG_WATCH_IGNORE_HUB=1`。
- 限界: Qt 製の小窓(Hub のお知らせなど)は本文・ボタンが取れないことがある(題名は取れる)。
  画像は Windows が描画できた時だけ(別の画面や後ろにある窓は、他のアプリを写さないよう画像なしにする)。

## Related docs

- **[headshot3-findings.md](headshot3-findings.md)** — Headshot 3 automation research (2026-07-20).
  Which Headshot API to use (`RLPy2.Headshot3`, not `RLPy.RHeadshot`), measured enum values,
  UE5 FBX export flags and why each is required, plus dev-workflow pitfalls
  (repo vs. Program Files copy, actual hot-reload scope, modal-dialog stalls).
