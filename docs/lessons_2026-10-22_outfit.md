# Lessons from building a custom outfit in CC5 (2026-10-21/22, ビヨんちゃん)

These lessons go into the cc5-agent skill. Every item was learned the hard way.

## Image check rule (owner order)
- After EVERY change in CC5, check it with 4 images: front (X), side (Y), top (Z), and one more angle (a 45° perspective, or a low front view for shoes and skirts).
- Use `capture_views4`; if it is not available, use `frame_camera` front/left/top plus one extra, with a viewport screenshot each.
- Never judge from the front view only.
- A model that cannot read images still takes the 4 images, saves them, and reports their paths so a vision model (Claude/Gemini) can judge.

## Workflow that works for custom FBX parts
1. Make the parts in Blender in the SAME frame as the CC body:
   - export the body with File > Export > OBJ > "Character With Current Pose", Z-up, cm;
   - fit in metres, Z-up, front = -Y;
   - export FBX with axis_forward=-Z, axis_up=Y, apply_unit_scale, embedded textures.
2. Use the T-pose (the CC5 preset) BEFORE converting anything. Weights are transferred in the current pose, so a part made for another pose gets double-posed.
3. Import FBX as a Prop.
4. Attach it to a bone (Pick Parent): `CC_Base_Head` for hair and hat; any body bone (for example `CC_Base_Spine02`) before Transfer Skin Weights.
5. Choose the type of part:
   - Clothes: Transfer Skin Weights with Default (tops, gloves/arms, bloomers), Dress (skirts) or Shoes (boots).
   - Hair: Create Hair, Brows, Beard, Lashes with the "Base/All" template.
   - Brows: Brows template. Lashes: CC's built-in lashes looked better than custom ones.
6. Only ONE shoes item per character. Join the left and right boots into one mesh before the Shoes transfer. Making a second shoes item asks "replace?".
7. Cloth has no Transform panel. To move or scale it, first Convert to Accessory, then transform it, then Transfer Skin Weights again.
8. Fit problems are cheaper to fix in Blender by numbers than with CC Conform:
   - the signed distance to the body (BVH find_nearest);
   - pull the part onto the body to a gap of 3 mm (tight items: corset), or push-only (skirts, boots);
   - smooth the displacement over the mesh edges;
   - export and re-import.
   - Scripts: `J:/OTOLUME/parts/beyon/cc5_trial3/scripts/v11_fit_part.py` and `v11_check_part.py`.
9. Mirror a good left glove to make the right glove (x → -x, reverse the face winding). The CC body is symmetric to within 2 mm.
10. Hair:
    - Hide scalp gaps with a hair-coloured "cap" mesh made from the head skin (offset 1.5 mm).
    - Fill the gaps under the hair with an inner layer: the strands shrunk ×0.86 toward the head centre, dark green, and removed in front of the face.
    - Lift the bangs off the eyes.
11. High heels (research, not yet tested):
    - Official route: fit the boots to the flat foot, transfer as Shoes, go to T-pose, then High Heels > Heel Height until the heel touches the floor.
    - Do not move the body up or down by hand.
    - Toes poking through: tilt `CC_Base_L/R_Foot` and `ToeBase` at frame 0, or widen the inside of the boot.
12. Big anime eyes:
    - Eye Scale ~150 and Eyeball Scale ~400.
    - Keep Eyeball Depth small, or the eyeball pokes through the closed lid.
    - Eyeball Depth: plus = forward. Eyeball Move: minus = toward the nose.
    - Morph values above 100 can only be typed in the GUI; the MCP clamps them to -1..1.
13. The DH Eye shader draws the iris as a circle. An oval texture does not make an oval iris.

## GUI and automation pitfalls
- **NEVER type into a Windows Open/Save dialog's file-name box with `ui_type`.** It renamed the selected folder (`cc_body_now` → `beyon_parts_v4.ccProject`). In Open dialogs, navigate by double-clicking. To save under a new name, copy the file with the shell.
- CC5 Save-As/Export dialogs create a folder with the typed name and wait for a second name.
- `capture_viewport` switches the right panel to the Render tab. Prefer a window screenshot of the viewport region.
- The Modify panel layout shifts with scrolling. Re-read the panel image before every click; misclicks opened Edit Spring and Create Hair.
- Other apps (Chrome, 1Password, WindVoice) can come on top of CC5. Check the foreground window before clicking, and never click while the owner is using the screen.
- Never press anything on the "Reallusion Hub 重要なアップデート" dialog.
- `set_item_visible` / `remove_scene_item` failed for imported props and accessories ("Item not found"). Use the workflow tools with item ids.
- Item names repeat (two `cc_p12_skirt`). Always use ids.

## Model routing for CC5 work (owner, 10-22)
- DeepSeek (`claude-oc`) and GLM (`claude-glm`): scripts, drafts, MCP tool calls through the text-only workflow tools.
- Claude/Gemini: the visual verdict on the 4 images, Japanese for the owner, and final decisions.

## 10-22 morning (boots / high heels)
- `import_fbx` automation once opened the irreversible "Game Base UVs" convert dialog instead of the Import flow. It was cancelled by hand. Until fixed, the import automation must verify each dialog's title before pressing any button and abort on anything unexpected. Never press Convert in "Game Base UVs".
- High-heel boots modelled in heel pose: rotate `CC_Base_L/R_Foot` X -37 and `ToeBase` X +37 at frame 0. The new route `/workflow/bone/rotation` does this through `skeleton.GetClip(0).GetControl("Layer", bone).GetDataBlock()`, with `Rotation/RotationX` in radians. Then import the boot as a Prop, attach it to the hip, and Transfer Skin Weights with Shoes. Converting a weighted boot back to an accessory binds it to the foot bone, so re-import it instead.
- `foot_auto` (AutoAdjustFootHeight) crushed the heel-posed boots. Reopen the saved project to recover.
- The High Heels dialog's Heel Height on flat feet only moved the shoe.
- The import status can report "did not appear" while the prop still lands seconds later. Re-list the items after about 10 s.

## 10-22 late morning (import fix, stale ids, lift)
- **Stale ids crash CC5.** Item ids change whenever a project is reopened. `_wf_resolve` used to pass an unknown id to `RScene.QueryObjectByID`, and that is an access violation inside CharacterCreator.exe (crashes at 11:02 and 11:28). Fixed: ids are resolved from the current scan only. Rule: call `list_scene_items` again after every reopen or crash.
- **Import automation fixed:**
  - Buttons are clicked only inside dialogs titled "Import Fbx" or "Import Settings". The import aborts if a "Game Base…" or other unexpected dialog is visible.
  - The app-wide event filter is gone.
  - Deferred calls check that the Qt object is still alive.
  - The file dialog is filled through its line edit, then its Open button is pressed.
  - Live-tested twice (skirt and boots): done in about 20 s, no crash.
- **Startup dialogs block everything** after a crash: "Unsaved project data found" (Cancel keeps the saved file), "Load Project" (Replace All + OK) and the DRM list (Close). Clear them before any workflow call.
- **The avatar lifts after shoes and foot posing.** The whole body was 6.80 cm higher than in the 01:35 export. A newly imported prop lands at the unlifted height, so a boot or skirt fitted in Blender ends up 6.8 cm low and the calf pokes through. Before transferring weights, raise the prop by the lift; measure it by comparing the head or hair height of a fresh current-pose OBJ export with the source OBJ.
- `transform/set` used to fail with "RTransform_T expected at most 1 arguments": `RTransform.T()`, `R()` and `S()` are getters. It now writes through `GetControl("Transform").GetDataBlock()` (`Position/PositionX..Z` in cm; `Rotation/RotationX..Z` in degrees, converted to radians). Live-tested: a prop raised by 6.803 cm.
- After a successful import, CC5 stops answering for 10–60 s while it converts. Poll `/workflow/import_fbx/status` with a long timeout and do not fire other routes in the meantime. In the 11:48 run, a trace in %TEMP%/cc5_import_trace.log showed every step.
- Two silent CC5 exits (no APPCRASH entry) happened right after an import began, at 11:37 and 11:45. Both times the bridge had been reloaded several times while the project was still loading. Reload once, only after the project has finished loading.
- **The avatar lift is recomputed every time a Shoes item is transferred**, and it depends on where the shoe sits. A transferred cloth cannot be moved afterwards: there is no Transform data block on cloth. Measured with boots v13c: prop raised 6.803 → lift 9.541; raised 9.541 → lift 8.368. That is roughly linear (lift ≈ 12.455 − 0.428 × offset), so the fixed point is ≈ 8.72. Procedure: import → raise by the guess → attach → transfer Shoes → export the current pose and measure the lift from a body or hair offset → repeat with the solved offset until boot-top-minus-lift equals the authored boot top.
