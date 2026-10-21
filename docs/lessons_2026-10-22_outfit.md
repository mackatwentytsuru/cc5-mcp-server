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
