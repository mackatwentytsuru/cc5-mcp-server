---
name: cc5-ui-automation
description: Apply Character Creator 5 presets (eyelash presets and strips, SkinGen makeup such as lipstick and eyeshadow), work the SkinGen editor (layers, visibility, opacity, bake), notice CC5 pop-up windows, press one named button of a CC5 window (also while the screen is locked, e.g. Body Wrap's Save Skeleton), and shoot equal-size comparison crops, all through the cc5 MCP without the mouse. Trigger on: SkinGen, makeup, lipstick, lip, eyeshadow, eyelash, preset, apply preset, layer opacity, bake, pop-up, popup, dialog, window, click button, press button, locked screen, Save Skeleton, click_ui_button, メイク, 口紅, まつげ, 型, プリセット, ポップアップ, 小窓, 濃さ, ボタンを押す, 画面の鍵.
origin: user-project
---

# CC5 UI automation (no mouse)

Use this when the work in Character Creator 5 is "apply a preset / look at a window / change a SkinGen
layer". Everything goes through the cc5 MCP tools below (or `scripts/ui_client.py` for loops). Read the
`cc5-agent` skill first for the general rules (look at images, one change then check, ids over names).

## The safety rules (not negotiable)

1. **Only three windows are ever answered by the tools**: `Apply Character Preset` / `Apply Eyelash Elements`
   (Apply), "add a new layer or replace the current layer?" (Replace, or Add with `layer_choice`),
   "exit SkinGen editing mode?" (Yes, or No). That is the whole list.
2. **Any window about a licence, purchase, login, update, terms, activation, subscription, payment or trial is
   never pressed**, and while one is open the tools press nothing. Delete / overwrite / unknown windows are
   not answered either. When a tool says "a window is waiting for a person": stop, look at the picture it
   returned (or `list_cc5_windows`), tell the owner in Japanese what it says, and wait. Never press it by
   hand-made scripts, never type into it.
3. Do not add answers to `WINDOW_RULES` (cc5_ui.py) without the owner's OK. Widening a title or a text match is
   how a wrong window gets pressed.
4. `click_ui_button` presses ONE button you name. CC5 refuses (and presses nothing) any button or menu entry whose
   text, objectName or tool tip mentions points / ポイント, buy / 購入 / purchase, delete / 削除 / remove, license /
   licence / ライセンス / activate, upgrade, credit / クレジット, subscribe, pay / 支払 (and login, update, terms, trial,
   ...); hidden, disabled or ambiguous buttons; anything while a licence / purchase / login window is open; anything
   outside an open modal window. **A refusal is final**: never get around it (another route, `exec_python`, the
   bridge directly, a different name for the same button). Tell the owner and wait. Do not edit `DENY_WORDS`
   (cc5_uiclick.py) without the owner's OK. A window the click opens is not answered: look at its picture and ask
   the owner unless the next step is routine (e.g. a file name you were told to use).
5. `exec_python` runs only when `CC5_ALLOW_EXEC=1` is set in the environment CC5 was started from. That is the only
   switch (the MCP server has none). When it is refused, do not call `POST /exec/python` on the bridge directly or
   look for another way in: ask the owner.

## Tools

| Need | Tool |
|------|------|
| What presets are on disk? | `list_presets` (category `makeup_lip`, `makeup_eye`, `makeup_eyelash`, `eyelash_preset`, `eyelash_element`, ...; `names` shows the missing ones) |
| Apply one or several | `apply_preset` (`file_paths` in order; `watch_prefix` e.g. `Lash_`; `layer_choice`; `restore_neutral_lash`) |
| SkinGen editor | `skingen_state` (read), `skingen_editor active=true/false`, `skingen_layer action=select/show/hide/opacity/delete` |
| What is on screen? | `list_cc5_windows` (text + PNG of each window), `get_ui_job` (a job that said "Still running") |
| Name of a widget | `find_ui_widgets` (read-only) |
| Same-size comparison shots | `capture_framed_crop` (preset view, big render, fixed box) |
| Press one named button (works on a locked screen) | `click_ui_button` (`window`, `object_name` and/or `text`, `menu_item` for a ▾ menu, `wait_ms`) |

`apply_preset`, `skingen_editor`, `skingen_layer`, `capture_framed_crop` and `click_ui_button` run as a job inside CC5. The tool
waits for it. While it runs, other bridge commands are refused ("was NOT run"); only the read-only tools work.
If a start request timed out, do **not** send it again: look first (`list_cc5_windows`, `skingen_state`).

## Recipes

**Eyelash options** (strips are Cloth items `Lash_Up_*` / `Lash_Low_*`, not the SkinGen lash texture):
`list_presets category=eyelash_preset` -> `apply_preset file_path=<preset> watch_prefix=Lash_` -> shoot with
`capture_framed_crop` (hide hair and hat first with `set_visible`; show them again after) -> next preset.
Strips can also be applied one by one: `apply_preset file_paths=[<Upper>.rlEyelashElement, <Lower>.rlEyelashElement]`.

**Lipstick / makeup options** (SkinGen presets):
1. `apply_preset file_path=<Lip Makeup>/Rouge.ccSkinGenPreset` (a second preset asks add-or-replace; the default
   Replace keeps ONE lip layer). It opens the SkinGen editor, which **hides hair, hat and the eyelash strips**.
2. `skingen_state` to see the layers.
3. Tune: `skingen_layer action=opacity index=0 opacity=60` (selects the layer first; opacity is the box of the
   SELECTED layer), `action=hide/show`.
4. `skingen_editor active=false` **before every face shot**: it bakes (~10 s), answers the exit question and waits
   until CC5 is quiet. Shooting before the bake ended gives a picture without the makeup.
5. `capture_framed_crop` with the same box for every option.

**Equal-size crops.** `dolly_camera`'s step size changed mid-session (15 cm, then 42 cm), so options shot with
different dolly counts had different sizes. Call `capture_framed_crop` once without `crop` (it returns a preview
and `preview_scale`), measure the box on the preview (x `preview_scale` = render pixels), then pass the same
`crop` for every option. It refuses to crop a window screenshot (RenderImage failed) because the scale would be wrong.

**Pressing a button on a locked screen** (金剛 locks itself after ~20 minutes; mouse clicks then do nothing, Qt's
`click()` still works):
1. Find the window: `list_cc5_windows include_other=true` (floating tool windows such as Body Wrap only show with
   `include_other`). Find the button: `find_ui_widgets ancestor=<window objectName> class_name=QToolButton` (or
   `text_contains=...`). Icon buttons have no text: use `object_name`.
2. `click_ui_button window="Body Wrap" object_name=<name>`; for an entry of a ▾ menu add `menu_item="Save Skeleton"`
   (a ▾ button without `menu_item` is refused and the reply lists its entries).
3. Read the reply: `click_returned: false` + a dialog in the list means the click opened a window (often a file
   dialog). Nothing in it was pressed.
4. A file dialog it opens (untested for Save Skeleton): the way that worked on 10-22 is
   `POST /workflow/dialog/native {"enable": false}` BEFORE the click (CC5's own Qt file dialog), then
   `POST /workflow/dialog/file_fill {"path": "<new file>", "save": true}`, then `{"enable": true}` again.
   Save under a NEW name; never overwrite the owner's files.

**Seeing a pop-up.** After any failure or "Still running": `list_cc5_windows`. Progress windows (Baking, Please
wait, Mipmap, Loading) go away by themselves; question windows need the owner. Check `check_cc5_connection`
(`main_thread_blocked`) too.

## Facts and pitfalls (learned 2026-10-26)

- Presets go on with `RFileIO.LoadFile(path)` with the avatar SELECTED (the tools do that). `.ccAvatarPreset`,
  `.rlEyelashElement` and `.ccSkinGenPreset` work; `.ccProject` / `.ccAvatar` / FBX are refused on purpose.
- SkinGen layer eye button: **checked = hidden**. Layer widgets are rebuilt on every selection, so tools wait
  between steps; do not click by hand while a job runs.
- The opacity box is `qtBlendOpacityHorizontalSliderEx > qtSpinBox` (0-100). It had never been tried on a real
  CC5 when written: read back `opacity_after` and look at the picture.
- `/workflow/save` (tool `save_project`): `file_path` or `path` = save as; no path = **overwrites the open project**.
  Unknown arguments are refused. Save under a new name before risky work.
- After a fresh CC5 start the Head/Body shaping sliders can be missing until `Help > Refresh Sliders`
  (`POST /workflow/menu/trigger {"path": "Help > Refresh Sliders"}`).
- Content in the cloud is not on disk: `list_presets` does not show it and nothing can apply it. Downloading it
  by double-click can bring the Reallusion Hub to the front, so the next clicks land on the Hub: one item at a time,
  by the owner.
- Items that show as trial (captures turn into window grabs): Help > Activate Purchased Items, OK on "Finished".
- `exec/python` replies carry values as text (repr): use `ast.literal_eval`.
- A 504 "Timeout waiting for CC5" means CC5's main thread is busy (bake, a window). The request stays queued
  and may run later.

## From a script

`python scripts/ui_client.py apply|editor|layer|windows|presets|crop ...` starts the job and polls it (stdlib only,
`CC5_BRIDGE_URL` may be an ssh tunnel). Exit code 2 = a window needs a person (its PNG is saved with `--shots`).
Import `run_job(path, body)` and `post(path, body)` from it for your own loops (lineup sheets).

## Extending

- New widget? `find_ui_widgets` first; add the objectName to `cc5-plugin/cc5_skingen.py` (or a new module with
  a `ROUTES` table, registered in `cc5_api._UI_MODULES`), write the fake-Qt test in `tests/python/`, then the MCP tool.
- A one-off press of a named button needs no new code: `click_ui_button`. Its checks are in `cc5-plugin/cc5_uiclick.py`
  (tests: `tests/python/test_ui_click.py`).
- Test steps for a real CC5 and what is still unverified: `docs/ui-automation-test-steps_ja.md`.
