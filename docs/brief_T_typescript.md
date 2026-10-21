# Brief T — TypeScript side (MCP tools) for the workflow routes

Add MCP tools for every route in `docs/contract_workflow_routes.md`.

## Read ONLY these files
- `docs/contract_workflow_routes.md`
- `src/tools/visibility.ts` (the pattern for a tools file)
- `src/util.ts` (`bridgeCall`)
- `src/cc5-bridge.ts`: read it in parts with Grep and Read offset/limit. Learn how a bridge method posts to a route, for example find `setItemVisible` and `removeSceneItem`.
- `src/index.ts`: lines 1–80.
- `tests/tools/scene.test.ts`, as the test pattern (read in parts if long).

## Do
1. **Add the bridge methods.** In `src/cc5-bridge.ts` add one method per route, for example `listSceneItems()`, `wfSetVisible(sel, visible)`, `wfImportFbx(path)` and so on. They follow the existing style: POST JSON, typed result. Put any new result types in `src/types.ts` (append only).
2. **Add the tools file.** Create `src/tools/workflow.ts` with `registerWorkflowTools(server, bridge)`. Tool names:
   - `list_scene_items`, `set_visible`, `remove_item`, `import_fbx`, `attach_to_bone`, `transfer_skin_weights`, `convert_to_hair`, `cloth_to_accessory`, `conform_cloth`
   - `get_transform`, `set_transform`, `save_project`, `export_obj`, `get_floor_contact`, `set_floor_contact`, `auto_adjust_foot_height`, `render_viewport`, `capture_views4`

   For each tool:
   - Declare zod input schemas matching the contract. The item selector is `item_name` (string ≤256, optional) and `item_id` (string ≤64, optional), plus a refine requiring at least one of them. Template enums are as in the contract.
   - Write clear one-line descriptions in English. Say that these tools work without the GUI and are meant for text-only models.
   - In the `capture_views4` description, add: "Always call this after every change and check all 4 images (front X, side Y, top Z, perspective) before moving on."
   - Format results as short readable text, like visibility.ts does.
3. **Register it.** In `src/index.ts`, import and call `registerWorkflowTools(server, bridge)` next to the other register calls.
4. **Test it.** Add `tests/tools/workflow.test.ts`, mocking the bridge like the existing tests. For each tool, test one success and one failure. Also test the item-selector validation (neither name nor id → schema error).
5. **Check it.** Run `npm run build` and `npm test`, and fix until both pass.
6. **Update the README.** Add one line per tool to `README.md` under a new heading "Text-only workflow tools".

## Limits
Touch only:
- `src/cc5-bridge.ts`, `src/types.ts` and `src/index.ts`;
- the new `src/tools/workflow.ts` and `tests/tools/workflow.test.ts`;
- `README.md`.

Do not touch `cc5-plugin/`. Do not commit.
