/**
 * Text-only workflow tools for CC5.
 *
 * One tool per route in docs/contract_workflow_routes.md. These tools are meant
 * for models that cannot look at the GUI: every result is short readable text,
 * and capture_views4 gives 4 images that can be checked after each change.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";
import type {
  WorkflowItemRef,
  WorkflowItemSelector,
  WorkflowItem,
  WorkflowListItemsResult,
  WorkflowSetVisibleResult,
  WorkflowRemoveItemResult,
  WorkflowImportFbxResult,
  WorkflowAttachResult,
  WorkflowTransferWeightsResult,
  WorkflowConvertHairResult,
  WorkflowClothToAccessoryResult,
  WorkflowConformResult,
  WorkflowTransformResult,
  WorkflowSaveResult,
  WorkflowExportObjResult,
  WorkflowFloorContactResult,
  WorkflowSimpleResult,
  WorkflowRenderResult,
  WorkflowViews4Result,
} from "../types.js";

// ── Shared item selector ──────────────────────────────────────────────────────

const itemSelectorFields = {
  item_name: z
    .string()
    .max(256)
    .optional()
    .describe("Item name from list_scene_items (optional when item_id is given)"),
  item_id: z
    .string()
    .max(64)
    .optional()
    .describe("Item id from list_scene_items (optional when item_name is given)"),
};

type SelectorArgs = { item_name?: string; item_id?: string };

function hasItemSelector(value: SelectorArgs): boolean {
  return value.item_name !== undefined || value.item_id !== undefined;
}

const SELECTOR_MESSAGE = "Provide at least one of item_name or item_id.";

/**
 * Item selector schema with the "at least one" refine.
 *
 * The MCP SDK only advertises plain object shapes to clients, so the tools are
 * registered with the raw selector fields and run this refined schema in their
 * handlers as well. Clients therefore see every field, and a selector with
 * neither name nor id is rejected before the bridge is called.
 */
export const itemSelectorSchema = z
  .object(itemSelectorFields)
  .refine(hasItemSelector, { message: SELECTOR_MESSAGE, path: ["item_name"] });

/** An optional nested item selector (used by capture_views4). */
export const optionalTargetSchema = z
  .object(itemSelectorFields)
  .refine(hasItemSelector, { message: SELECTOR_MESSAGE, path: ["item_name"] })
  .optional();

function selectorProblem(value: SelectorArgs): string | undefined {
  const parsed = itemSelectorSchema.safeParse(value);
  if (parsed.success) return undefined;
  return parsed.error.issues[0]?.message ?? SELECTOR_MESSAGE;
}

function schemaFailure(message: string) {
  return {
    content: [{ type: "text" as const, text: `Failed: ${message}` }],
    isError: true,
  };
}

/** Raw shape for a tool that takes an item selector plus extra fields. */
function selectorShape<T extends z.ZodRawShape>(extra: T): T & typeof itemSelectorFields {
  return { ...itemSelectorFields, ...extra };
}

function toSelector(value: SelectorArgs): WorkflowItemSelector {
  const selector: WorkflowItemSelector = {};
  if (value.item_name !== undefined) selector.item_name = value.item_name;
  if (value.item_id !== undefined) selector.item_id = value.item_id;
  return selector;
}

// ── Result formatting ─────────────────────────────────────────────────────────

const NO_GUI = "Works without the GUI and is meant for text-only models.";

function num(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)));
}

function vec(values?: number[]): string {
  return values ? `(${values.map(num).join(", ")})` : "n/a";
}

function formatRecord(record?: Record<string, unknown>): string {
  if (record === undefined) return "n/a";
  const parts = Object.entries(record).map(
    ([key, value]) => `${key}=${typeof value === "number" ? num(value) : JSON.stringify(value)}`,
  );
  return parts.length > 0 ? parts.join(", ") : "(empty)";
}

function formatItemRef(item: WorkflowItemRef): string {
  return `'${item.name}' (id: ${item.id}, kind: ${item.kind})`;
}

function matchesNote(matches?: WorkflowItemRef[]): string | undefined {
  if (!matches || matches.length === 0) return undefined;
  return `Matches: ${matches.map((m) => `${m.name} (id: ${m.id}, ${m.kind})`).join(", ")}`;
}

function failed(error?: string, ...details: Array<string | undefined>): string {
  const extra = details.filter((d): d is string => Boolean(d)).join(" ");
  const base = `Failed: ${error ?? "unknown error"}`;
  return extra ? `${base}. ${extra}` : base;
}

function failedItem(result: { error?: string; matches?: WorkflowItemRef[] }): string {
  return failed(result.error, matchesNote(result.matches));
}

// ── Tools ─────────────────────────────────────────────────────────────────────

export function registerWorkflowTools(server: McpServer, bridge: CC5Bridge): void {
  server.tool(
    "list_scene_items",
    `List every scene item with name, id, kind, visibility and parent; these ids are used by the other workflow tools. ${NO_GUI}`,
    {},
    async () =>
      bridgeCall(
        () => bridge.listSceneItems(),
        (result: WorkflowListItemsResult) => {
          if (!result.success) return failed(result.error);
          const items: WorkflowItem[] = result.items ?? [];
          if (items.length === 0) return "Scene has no items.";
          const lines = [`Found ${items.length} item(s):`];
          for (const item of items) {
            const extras = [item.visible ? "visible" : "hidden"];
            if (item.parent) extras.push(`parent: ${item.parent}`);
            if (item.cloth_type) extras.push(`cloth: ${item.cloth_type}`);
            if (item.hair_type) extras.push(`hair: ${item.hair_type}`);
            lines.push(`  - ${item.name} (id: ${item.id}, ${item.kind}; ${extras.join(", ")})`);
          }
          return lines.join("\n");
        },
      ),
  );

  server.tool(
    "set_visible",
    `Show or hide one scene item by name or id. ${NO_GUI}`,
    selectorShape({
      visible: z.boolean().describe("true to show the item, false to hide it"),
    }),
    async ({ item_name, item_id, visible }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfSetVisible(toSelector({ item_name, item_id }), visible),
        (result: WorkflowSetVisibleResult) =>
          result.success
            ? `Item '${result.name ?? item_name ?? item_id}'${result.id ? ` (id: ${result.id})` : ""} is now ${result.visible ? "visible" : "hidden"}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "remove_item",
    `Remove one clothing, hair, accessory or prop item by name or id. ${NO_GUI}`,
    selectorShape({}),
    async ({ item_name, item_id }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfRemoveItem(toSelector({ item_name, item_id })),
        (result: WorkflowRemoveItemResult) =>
          result.success && result.removed
            ? `Removed ${formatItemRef(result.removed)}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "import_fbx",
    `Import an FBX file into the scene as a new item. ${NO_GUI}`,
    {
      file_path: z.string().min(1).max(4096).describe("Full path of the .fbx file to import"),
    },
    async ({ file_path }) =>
      bridgeCall(
        () => bridge.wfImportFbx(file_path),
        (result: WorkflowImportFbxResult) =>
          result.success && result.item
            ? `Imported ${formatItemRef(result.item)}`
            : failed(result.error),
      ),
  );

  server.tool(
    "attach_to_bone",
    `Attach an item to a named skeleton bone. ${NO_GUI}`,
    selectorShape({
      bone_name: z.string().min(1).max(256).describe("Bone name, for example CC_Base_Hip"),
    }),
    async ({ item_name, item_id, bone_name }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfAttachToBone(toSelector({ item_name, item_id }), bone_name),
        (result: WorkflowAttachResult) =>
          result.success
            ? `Attached '${result.name ?? item_name ?? item_id}' to bone '${result.bone ?? bone_name}'`
            : failed(
                result.error,
                matchesNote(result.matches),
                result.bones && result.bones.length > 0
                  ? `Bone candidates: ${result.bones.join(", ")}`
                  : undefined,
              ),
      );
    },
  );

  server.tool(
    "transfer_skin_weights",
    `Transfer skin weights to an item using a clothing template. ${NO_GUI}`,
    selectorShape({
      template: z
        .enum(["default", "dress", "gloves", "shoes", "cloak", "other"])
        .describe("Weight template to use"),
    }),
    async ({ item_name, item_id, template }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfTransferSkinWeights(toSelector({ item_name, item_id }), template),
        (result: WorkflowTransferWeightsResult) =>
          result.success
            ? `Transferred skin weights to '${result.name ?? item_name ?? item_id}' (template: ${result.template ?? template}${result.kind_after ? `; kind now ${result.kind_after}` : ""})`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "convert_to_hair",
    `Convert a mesh item into hair using a hair template. ${NO_GUI}`,
    selectorShape({
      template: z
        .enum(["top", "base_all", "rear", "bangs", "accessory", "brows", "upper_lash", "lower_lash"])
        .describe("Hair template to use"),
    }),
    async ({ item_name, item_id, template }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfConvertToHair(toSelector({ item_name, item_id }), template),
        (result: WorkflowConvertHairResult) =>
          result.success
            ? `Converted '${result.name ?? item_name ?? item_id}' to hair (template: ${result.template ?? template})`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "cloth_to_accessory",
    `Convert a cloth item into an accessory, optionally keeping its current shape. ${NO_GUI}`,
    selectorShape({
      keep_current_shape: z
        .boolean()
        .default(true)
        .describe("true keeps the current shape, false lets CC5 rebuild it"),
    }),
    async ({ item_name, item_id, keep_current_shape }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () =>
          bridge.wfClothToAccessory(
            toSelector({ item_name, item_id }),
            keep_current_shape ?? true,
          ),
        (result: WorkflowClothToAccessoryResult) =>
          result.success
            ? `Converted '${result.name ?? item_name ?? item_id}' to an accessory`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "conform_cloth",
    `Conform a cloth item to the body with 1-10 iterations and optional conform values. ${NO_GUI}`,
    selectorShape({
      iterations: z
        .number()
        .int()
        .min(1)
        .max(10)
        .default(1)
        .describe("Number of conform iterations (1-10)"),
      values: z
        .record(z.number())
        .optional()
        .describe("Optional conform key/value pairs, for example { chest: 0.5 }"),
    }),
    async ({ item_name, item_id, iterations, values }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfConformCloth(toSelector({ item_name, item_id }), iterations ?? 1, values),
        (result: WorkflowConformResult) =>
          result.success
            ? `Conformed '${result.name ?? item_name ?? item_id}': ${formatRecord(result.before)} -> ${formatRecord(result.after)}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "get_transform",
    `Read an item's move, rotate and scale values. ${NO_GUI}`,
    selectorShape({}),
    async ({ item_name, item_id }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfGetTransform(toSelector({ item_name, item_id })),
        (result: WorkflowTransformResult) =>
          result.success
            ? `'${result.name ?? item_name ?? item_id}' move=${vec(result.move)} rotate=${vec(result.rotate)} scale=${vec(result.scale)}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "set_transform",
    `Set an item's move, rotate and/or scale values and return the applied values. ${NO_GUI}`,
    selectorShape({
      move: z.array(z.number()).length(3).optional().describe("[x, y, z] move values"),
      rotate: z.array(z.number()).length(3).optional().describe("[x, y, z] rotation values"),
      scale: z.array(z.number()).length(3).optional().describe("[x, y, z] scale values"),
    }),
    async ({ item_name, item_id, move, rotate, scale }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfSetTransform(toSelector({ item_name, item_id }), { move, rotate, scale }),
        (result: WorkflowTransformResult) =>
          result.success
            ? `Updated '${result.name ?? item_name ?? item_id}': move=${vec(result.move)} rotate=${vec(result.rotate)} scale=${vec(result.scale)}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "save_project",
    `Save the current CC5 project, optionally to a new path. ${NO_GUI}`,
    {
      file_path: z
        .string()
        .min(1)
        .max(4096)
        .optional()
        .describe("Optional project path; omit to save in place"),
    },
    async ({ file_path }) =>
      bridgeCall(
        () => bridge.wfSaveProject(file_path),
        (result: WorkflowSaveResult) =>
          result.success
            ? `Saved project to ${result.path ?? file_path ?? "(current path)"}`
            : failed(result.error),
      ),
  );

  server.tool(
    "export_obj",
    `Export the scene to an OBJ file with optional current pose and materials. ${NO_GUI}`,
    {
      file_path: z.string().min(1).max(4096).describe("Full path of the .obj file to write"),
      current_pose: z
        .boolean()
        .default(true)
        .describe("true exports the current pose, false exports the rest pose"),
      with_materials: z.boolean().default(true).describe("true writes .mtl materials"),
    },
    async ({ file_path, current_pose, with_materials }) =>
      bridgeCall(
        () => bridge.wfExportObj(file_path, current_pose ?? true, with_materials ?? true),
        (result: WorkflowExportObjResult) =>
          result.success
            ? `Exported OBJ to ${result.path ?? file_path}${result.bytes !== undefined ? ` (${result.bytes} bytes)` : ""}`
            : failed(result.error),
      ),
  );

  server.tool(
    "get_floor_contact",
    `Read the current floor-contact settings. ${NO_GUI}`,
    {},
    async () =>
      bridgeCall(
        () => bridge.wfGetFloorContact(),
        (result: WorkflowFloorContactResult) =>
          result.success
            ? `Floor contact: ${JSON.stringify(result.value)}`
            : failed(result.error),
      ),
  );

  server.tool(
    "set_floor_contact",
    `Apply floor-contact settings previously returned by get_floor_contact. ${NO_GUI}`,
    {
      value: z
        .record(z.unknown())
        .describe("Floor-contact value object, exactly as returned by get_floor_contact"),
    },
    async ({ value }) =>
      bridgeCall(
        () => bridge.wfSetFloorContact(value),
        (result: WorkflowSimpleResult) =>
          result.success ? "Floor contact settings applied." : failed(result.error),
      ),
  );

  server.tool(
    "auto_adjust_foot_height",
    `Automatically adjust foot height so the avatar stands on the floor. ${NO_GUI}`,
    {},
    async () =>
      bridgeCall(
        () => bridge.wfAutoAdjustFootHeight(),
        (result: WorkflowSimpleResult) =>
          result.success ? "Foot height adjusted automatically." : failed(result.error),
      ),
  );

  server.tool(
    "render_viewport",
    `Render the current viewport to a PNG file. ${NO_GUI}`,
    {
      file_path: z.string().min(1).max(4096).describe("Full path of the .png file to write"),
    },
    async ({ file_path }) =>
      bridgeCall(
        () => bridge.wfRenderViewport(file_path),
        (result: WorkflowRenderResult) =>
          result.success
            ? `Rendered viewport to ${result.path ?? file_path}`
            : failed(result.error),
      ),
  );

  server.tool(
    "capture_views4",
    `Save 4 check images (front, side, top, perspective) of the target item or the whole avatar. ${NO_GUI} Always call this after every change and check all 4 images (front X, side Y, top Z, perspective) before moving on.`,
    {
      folder: z.string().min(1).max(4096).describe("Folder where the 4 PNG files are saved"),
      prefix: z.string().min(1).max(128).describe("Filename prefix for the 4 images"),
      target: optionalTargetSchema.describe(
        "Optional item to frame; omit to frame the whole avatar",
      ),
    },
    async ({ folder, prefix, target }) =>
      bridgeCall(
        () => bridge.wfCaptureViews4(folder, prefix, target ? toSelector(target) : undefined),
        (result: WorkflowViews4Result) => {
          if (!result.success) return failed(result.error);
          const files = result.files ?? [];
          const labels = ["front (X)", "side (Y)", "top (Z)", "perspective"];
          const lines = [`Saved ${files.length} check view(s):`];
          files.forEach((file, index) => {
            lines.push(`  ${labels[index] ?? `view ${index + 1}`}: ${file}`);
          });
          return lines.join("\n");
        },
      ),
  );
}
