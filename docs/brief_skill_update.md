# Task: rewrite the cc5-agent skill so cheap text models (DeepSeek, GLM) can run CC5 work safely

Read:
1. `C:/Users/macka/.claude/skills/cc5-agent/SKILL.md`: the current skill, 198 lines. Keep everything in it that is still true.
2. `C:/Users/macka/Projects/cc5-mcp-server/docs/lessons_2026-10-22_outfit.md`: the new lessons. All of them must go in.
3. `C:/Users/macka/Projects/cc5-mcp-server/src/tools/workflow.ts`: the new text-only workflow MCP tools. List each tool with a one-line use.
4. `C:/Users/macka/Projects/cc5-mcp-server/docs/report_P.md`: what each workflow route really does, and its limits.

Write the new skill to `C:/Users/macka/Projects/cc5-mcp-server/docs/SKILL_cc5-agent_draft.md`. Do not edit the real skill file.

Requirements:
- Keep the YAML front matter (name, description). Extend the description so it also triggers on: "服", "衣装", "Transfer Skin Weights", "Conform", "ヒール", "髪の登録", "outfit", "custom clothing".
- **Put a "Mandatory checks" section near the top. Its rules:**
  1. After EVERY change in CC5, call `capture_views4`: front (X), side (Y), top (Z), plus one perspective view. Look at all 4 images before the next step. Never judge from one view.
  2. Take screenshots through MCP while working, and say in the report which image shows what.
  3. If your model cannot read images, still take the 4 images, save them, and hand their file paths to a vision model (Claude or Gemini) for the verdict. Do not continue past a visual decision on your own.
  4. Never click Windows dialogs blindly. Never type into Windows Open/Save file-name boxes, which renames files. Never press anything in the "Reallusion Hub の重要なアップデート" dialog. Never press Buy/Pack in the DRM content dialog; only Close.
  5. Never call `RFileIO.LoadFile` / `LoadObject` on an FBX. They replace the whole scene. Use the workflow `import_fbx` tool only.
  6. Before risky steps, call `save_project`. If the scene breaks, call `/workflow/open_project` to reopen the saved file.
- Add a "Text-only outfit workflow" section as numbered steps that use the workflow tools:
  1. `list_scene_items`
  2. `import_fbx`
  3. `attach_to_bone`
  4. `transfer_skin_weights` or `convert_to_hair`
  5. `conform_cloth`
  6. `capture_views4`
  7. `save_project`
  Also add the Blender fitting step: `v11_fit_part.py` / `v11_check_part.py`, with their command lines from the lessons file.
- Add "Model routing": DeepSeek/GLM run the tools and the scripts; Claude/Gemini give the visual verdict and write the owner-facing Japanese.
- Keep it under about 320 lines. Use clear, plain English, with short sentences and bullet lists.
- At the end, list in 5 lines what you changed compared with the old skill.
