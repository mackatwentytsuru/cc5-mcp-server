---
name: cc5-headshot-face-match
description: Character Creator 5 の Headshot 3 で、お手本の顔画像とそっくりな 3D の頭を作り、モーフを測りながら自動で近づける手順。CC5 の AI Image Generator で正面・横顔・体を作って APPLY IMAGES で Headshot に渡し、型を選んで生成し、正面と真横を撮って MediaPipe の目印と横顔の輪郭で比率を測り、差が減る向きにモーフを1つずつ動かす。Use when the user wants a CC5 / Headshot 3 head that matches a reference image, or asks to make the face look like the reference, tune face morphs toward a photo, or rebuild a head with Headshot 3.
---

# CC5 Headshot 3: make a head match a reference image

Character Creator 5 + Headshot 3 + this repository's MCP bridge (HTTP 127.0.0.1:5101).

## 0. Rules
- Operate CC5 through the `cc5` MCP tools / bridge HTTP. Do not type into Windows file dialogs: put images on the clipboard (PowerShell `-STA`, `[System.Windows.Forms.Clipboard]::SetImage`) and press Ctrl+V on the Headshot photo slot.
- Never press purchase / trial (Buy, Pack), Hub update, or "Game Base UVs" Convert buttons. List dialogs with `list_dialogs` and ask the user.
- AI Image Generator spends points (shown next to the button, e.g. front 30 / side 30 / body 15). Confirm with the user first.
- If bought content shows as trial (watermark, export refused, or captures turn into a screenshot of the whole CC5 window), run **Help > Activate Purchased Items** and press **OK** on "Activate Purchased Items Finished.", then reload the bridge. `capture_viewport` now reports `fallback: "window_screenshot"` with a warning when this happens.
- Delete the per-step measurement images after a run; keep the JSON, logs and the sheets you show the user.

## 1. Make the reference images with CC5's AI Image Generator
- Images made elsewhere, or even CC5 images pasted back from a file, can make Headshot stop with **"Failed to detect facial landmarks in the reference image."** Images handed over with **APPLY IMAGES** from the AI Image Generator went through.
- After that error appears once, the same CC5 session may keep failing even with good images. Restart CC5 (close without saving only if the user says the scene is not needed).
- Steps (Headshot 3 panel → AI Image Generator):
  1. **Front → Modify**: put the reference front image in Photo Resource. Check **Enhance Image** and **Remove Hair / Eyebrow / Eyelash** (leave makeup so cheek color and lip color stay). GENERATE IMAGE.
  2. **Side → Generate**: the generated front is the source. GENERATE IMAGE (true left-facing profile).
  3. **Body**: set Gender to **Female** if needed (the default is Male), pick a body shape. GENERATE IMAGE.
  4. **APPLY IMAGES** → the Generate Character dialog receives front, side and body.
- Results are saved under `C:/Users/Public/Documents/Reallusion/Reallusion Custom/Media/Texture/ImageGen/`.
- Editing lashes out with external image editors tended to change the eye and eyelid shape. Prefer the generator's Remove Eyelash.

## 2. Generate in Headshot 3
- The Headshot 3 window can open off-screen; move it on-screen with a window tool.
- In Generate Character → HEAD, pick options per tab that match the reference (face shape, forehead, mid face / lips, chin, eyes, nose, ears). Each applies a `*_preset` morph at 0.5. Screenshot all tabs and check the selections.
- BODY: Create by Photo with the body image; set Female again if needed.
- GENERATE. A "Save stream …" progress window means it is working. Save a copy right after.
- A body made from a photo gives a **CC3_Base_Plus** base. If the target engine expects CC5 HD facial curves, convert the facial profile to CC5 HD before export.

## 3. Measure and tune

### 3-0. Match the reference's camera and lighting first
- CC5's Preview Camera cannot be moved or re-lensed by scripts (no Transform control; CC5 cannot create cameras). From the `face` view, `dolly_camera` (bridge `/camera/dolly`, a wheel message to the viewport; the user's mouse does not move) moves it 15 cm per notch along the view axis. Compare face-landmark overlap against the reference at several distances to estimate the reference's camera distance.
- Capture the side with the SAME camera by rotating the avatar −90°; measure.py's `--scale render` divides side lengths by the front IPD, which is only valid with one camera.
- Try lighting presets (`Stage/Atmosphere/*.iAtm` via load_asset) and pick the one whose skin color, brightness and shading are closest to the reference (let the user decide). Save the project first: loading a preset replaces the scene lights.

Scripts are in `scripts/`. Run them with a Python that has `mediapipe opencv-python pillow numpy`.
Download the MediaPipe face model once:
`curl -L -o scripts/hs3_fit/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`

```
set REF_FRONT=<reference front image>
set REF_SIDE=<reference side image, facing left>
set FIT_WORK=<work folder>
python scripts/fit_step.py step00 <avatar name from list_scene_items>
```
- `fit_step.py` captures the front (face camera, straight on) and the side (the `left` preset at 6000 px, cropped to the head, which keeps perspective low), measures ratios with `hs3_fit/measure.py` (unit = distance between the pupils), and prints the difference table and a **total**. It also writes aligned overlays (`fit/<name>_cmp.jpg`, `fit/<name>_side_zoom.jpg`).
- Close-up perspective cameras exaggerate the nose in profile, so compare the side only from the `left` preset view (the script does this).
- Manual hints (direction differs per head; move one or two sliders and re-measure):
  - full under-chin → lower Baby Face / Rounded Chin presets, Neck Double Chin −, Chin Depth A +
  - deep nose root / short bridge → Nose Ridge Upper Depth +, Nose Ridge Upper Height +, Brow Depth −, Brow Ridge Depth −, Forehead Lower Depth −
  - nose tip too far out → Nose Depth −; smaller nose → Nose Scale −, Nostril Scale −
  - low skull top → Skull Height +; outer eye corners → Eye Angle +; cheek width → Cheek Scale +
- **Automatic tuning**: `python scripts/auto_tune.py 0.15 1`, then `python scripts/auto_tune.py 0.1 2`. It moves each morph by ±step and keeps a change only if the total drops by at least 1.5. Log: `fit/auto_tune.log`. Edit the `MORPHS` list for your head. In the first real use the total went 283 → 148.
- Always check by eye afterwards: `python scripts/shots6.py <name> <avatar name>` (front, 30°, 45°, side, from above, from below). Do not judge from the front only.
- Save a new project copy at each milestone and record the morph ids and values in a JSON file.
