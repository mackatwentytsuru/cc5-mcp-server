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
  PhysicsInfoResult,
  PhysicsActivateResult,
  PhysicsWeightMapResult,
  PhysicsParamsResult,
  PhysicsCollisionGetResult,
  PhysicsCollisionSetResult,
  PhysicsMeshEntry,
  PhysicsMaterialTarget,
} from "../types.js";
import { SOFT_PHYSX_PROPERTIES } from "../types.js";

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

// ── Physics (Soft Cloth) helpers ──────────────────────────────────────────────

const physicsTargetFields = {
  mesh_name: z
    .string()
    .min(1)
    .max(256)
    .optional()
    .describe("Soft-cloth mesh name (see get_physics_info); optional when the item has only one"),
  material_name: z
    .string()
    .min(1)
    .max(256)
    .optional()
    .describe("Soft-cloth material name on that mesh; optional when the mesh has only one"),
};

function toPhysicsTarget(value: PhysicsMaterialTarget): PhysicsMaterialTarget {
  const target: PhysicsMaterialTarget = {};
  if (value.mesh_name !== undefined) target.mesh_name = value.mesh_name;
  if (value.material_name !== undefined) target.material_name = value.material_name;
  return target;
}

const SOFT_PHYSX_SET: ReadonlySet<string> = new Set(SOFT_PHYSX_PROPERTIES);

const WEIGHT_MAP_GUI_HINT =
  "If this cannot be done from a script, load it by hand in CC5 (画面で読み込む): select the item, Modify panel > Physics > Weight Map.";

function meshesNote(meshes?: PhysicsMeshEntry[]): string | undefined {
  if (!meshes || meshes.length === 0) return undefined;
  return `Soft-cloth meshes: ${meshes
    .map((m) => `${m.mesh} [${m.materials.join(", ") || "no materials listed"}]`)
    .join("; ")}`;
}

function notesNote(notes?: string[]): string | undefined {
  return notes && notes.length > 0 ? `Notes: ${notes.join(" ")}` : undefined;
}

function physicsLabel(
  result: { name?: string; mesh?: string; material?: string },
  fallback?: string,
): string {
  const item = result.name ?? fallback ?? "item";
  return result.mesh || result.material
    ? `'${item}' mesh '${result.mesh ?? "?"}' material '${result.material ?? "?"}'`
    : `'${item}'`;
}

function physicsFailed(
  result: {
    error?: string;
    matches?: WorkflowItemRef[];
    meshes?: PhysicsMeshEntry[];
    notes?: string[];
  },
  ...extra: Array<string | undefined>
): string {
  return failed(
    result.error,
    matchesNote(result.matches),
    meshesNote(result.meshes),
    ...extra,
    notesNote(result.notes),
  );
}

function shapeText(shape: { enabled: boolean | null; value: number | null } | null): string {
  if (!shape) return "n/a";
  const enabled = shape.enabled === null ? "?" : shape.enabled ? "on" : "off";
  const value = shape.value === null ? "?" : num(shape.value);
  return `${enabled}, value ${value}`;
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
            // Cloth and hair have no visibility getter in RLPy; the bridge sends null for them (10-24).
            const extras = [
              item.visible === true ? "visible" : item.visible === false ? "hidden" : "visibility unknown",
            ];
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
    `Read an item's move (cm), rotate (degrees, Euler X/Y/Z) and scale (percent, 100 = original size) — the same units set_transform takes, so the values can be edited and passed back. ${NO_GUI}`,
    selectorShape({}),
    async ({ item_name, item_id }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfGetTransform(toSelector({ item_name, item_id })),
        (result: WorkflowTransformResult) =>
          result.success
            ? `'${result.name ?? item_name ?? item_id}' move=${vec(result.move)} rotate=${vec(result.rotate)} scale=${vec(result.scale)}` +
              (result.units_warning ? `\nWarning: ${result.units_warning}` : "")
            : failedItem(result),
      );
    },
  );

  server.tool(
    "set_transform",
    `Set an item's move, rotate and/or scale values and return the applied values. ${NO_GUI}`,
    selectorShape({
      move: z.array(z.number()).length(3).optional().describe("[x, y, z] move in cm"),
      rotate: z.array(z.number()).length(3).optional().describe("[x, y, z] rotation in degrees (Euler)"),
      scale: z.array(z.number()).length(3).optional().describe("[x, y, z] scale in percent (100 = original size)"),
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

  // ── Physics (Soft Cloth) ──────────────────────────────────────────────────

  server.tool(
    "get_physics_info",
    `Show an item's Activate Physics state, its soft-cloth meshes/materials and the Soft PhysX property names. Works for cloth, accessory, hair and avatar items (props have no physics component in RLPy). ${NO_GUI}`,
    selectorShape({}),
    async ({ item_name, item_id }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfPhysicsInfo(toSelector({ item_name, item_id })),
        (result: PhysicsInfoResult) => {
          if (!result.success) return physicsFailed(result);
          const state =
            result.activate === null || result.activate === undefined
              ? "unknown"
              : result.activate
                ? "on"
                : "off";
          const lines = [
            `Physics for '${result.name ?? item_name ?? item_id}'${result.kind ? ` (${result.kind})` : ""}: Activate Physics ${state}`,
          ];
          const meshes = result.meshes ?? [];
          if (meshes.length === 0) {
            lines.push(
              "  No soft-cloth meshes yet (load a weight map to make a material soft cloth).",
            );
          } else {
            for (const mesh of meshes) {
              lines.push(
                `  - mesh ${mesh.mesh}: ${mesh.materials.join(", ") || "(no materials listed)"}`,
              );
            }
          }
          if (result.properties && result.properties.length > 0) {
            lines.push(`  Soft PhysX properties: ${result.properties.join(", ")}`);
          }
          if (result.weight_map_import === false) {
            lines.push(`  Weight-map import is not available in this RLPy. ${WEIGHT_MAP_GUI_HINT}`);
          }
          const notes = notesNote(result.notes);
          if (notes) lines.push(`  ${notes}`);
          return lines.join("\n");
        },
      );
    },
  );

  server.tool(
    "set_physics_active",
    `Turn Activate Physics on or off for a cloth, accessory, hair or avatar item. RLPy has one switch per item, not per mesh or material. The value is read back after the change. ${NO_GUI}`,
    selectorShape({
      enable: z.boolean().describe("true turns Activate Physics on, false turns it off"),
    }),
    async ({ item_name, item_id, enable }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () => bridge.wfPhysicsActivate(toSelector({ item_name, item_id }), enable),
        (result: PhysicsActivateResult) =>
          result.success
            ? `Activate Physics for '${result.name ?? item_name ?? item_id}' is now ${(result.activate ?? enable) ? "on" : "off"}${result.verified === false ? " (could not read it back)" : ""}`
            : failedItem(result),
      );
    },
  );

  server.tool(
    "load_physics_weight_map",
    `Load a Soft Cloth weight map PNG for one mesh/material of an item (RLPy SetPhysicsSoftColthWeightMap). ${WEIGHT_MAP_GUI_HINT} ${NO_GUI}`,
    selectorShape({
      ...physicsTargetFields,
      file_path: z.string().min(1).max(4096).describe("Full path of the weight map .png file"),
    }),
    async ({ item_name, item_id, mesh_name, material_name, file_path }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      if (!file_path.toLowerCase().endsWith(".png")) {
        return schemaFailure("file_path must be a .png file.");
      }
      return bridgeCall(
        () =>
          bridge.wfPhysicsLoadWeightMap(
            toSelector({ item_name, item_id }),
            toPhysicsTarget({ mesh_name, material_name }),
            file_path,
          ),
        (result: PhysicsWeightMapResult) => {
          if (!result.success) {
            return physicsFailed(
              result,
              result.gui_only
                ? "This must be done by hand in the CC5 GUI (Modify panel > Physics > Weight Map)."
                : undefined,
            );
          }
          const check =
            result.weight_map_present === true
              ? " (weight map present after loading)"
              : result.weight_map_present === false
                ? " (warning: no weight map reads back)"
                : "";
          const notes = notesNote(result.notes);
          return `Loaded weight map ${result.path ?? file_path} into ${physicsLabel(result, item_name ?? item_id)}${check}${notes ? `. ${notes}` : ""}`;
        },
      );
    },
  );

  server.tool(
    "get_soft_physics_params",
    `Read Soft PhysX properties (${SOFT_PHYSX_PROPERTIES.join(", ")}) of one soft-cloth mesh/material. ${NO_GUI}`,
    selectorShape({
      ...physicsTargetFields,
      names: z
        .array(z.enum(SOFT_PHYSX_PROPERTIES))
        .min(1)
        .optional()
        .describe("Property names to read; omit to read all of them"),
    }),
    async ({ item_name, item_id, mesh_name, material_name, names }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () =>
          bridge.wfPhysicsGetParams(
            toSelector({ item_name, item_id }),
            toPhysicsTarget({ mesh_name, material_name }),
            names,
          ),
        (result: PhysicsParamsResult) => {
          if (!result.success) {
            return physicsFailed(
              result,
              result.allowed ? `Allowed: ${result.allowed.join(", ")}` : undefined,
            );
          }
          const lines = [
            `Soft PhysX for ${physicsLabel(result, item_name ?? item_id)}: ${formatRecord(result.params)}`,
          ];
          if (result.unreadable && Object.keys(result.unreadable).length > 0) {
            lines.push(`  Unreadable: ${Object.keys(result.unreadable).join(", ")}`);
          }
          const notes = notesNote(result.notes);
          if (notes) lines.push(`  ${notes}`);
          return lines.join("\n");
        },
      );
    },
  );

  server.tool(
    "set_soft_physics_params",
    `Set Soft PhysX properties of one soft-cloth mesh/material and read them back. Allowed names: ${SOFT_PHYSX_PROPERTIES.join(", ")}. SoftVsRigidCollision and SelfCollision are switches (true/false or 1/0). ${NO_GUI}`,
    selectorShape({
      ...physicsTargetFields,
      values: z
        .record(z.union([z.number().finite(), z.boolean()]))
        .describe("Property name/value pairs, for example { Mass: 1.5, SelfCollision: true }"),
    }),
    async ({ item_name, item_id, mesh_name, material_name, values }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      const keys = Object.keys(values);
      if (keys.length === 0) return schemaFailure("values must contain at least one property.");
      const unknown = keys.filter((key) => !SOFT_PHYSX_SET.has(key));
      if (unknown.length > 0) {
        return schemaFailure(
          `Unknown Soft PhysX property: ${unknown.join(", ")}. Allowed: ${SOFT_PHYSX_PROPERTIES.join(", ")}`,
        );
      }
      return bridgeCall(
        () =>
          bridge.wfPhysicsSetParams(
            toSelector({ item_name, item_id }),
            toPhysicsTarget({ mesh_name, material_name }),
            values,
          ),
        (result: PhysicsParamsResult) => {
          const change = `${formatRecord(result.before)} -> ${formatRecord(result.after)}`;
          if (!result.success) {
            return physicsFailed(
              result,
              result.before || result.after ? `Values: ${change}` : undefined,
              result.allowed ? `Allowed: ${result.allowed.join(", ")}` : undefined,
            );
          }
          const notes = notesNote(result.notes);
          return `Updated Soft PhysX for ${physicsLabel(result, item_name ?? item_id)}: ${change}${notes ? `. ${notes}` : ""}`;
        },
      );
    },
  );

  server.tool(
    "get_physics_collision",
    `List collision shapes for one soft-cloth mesh/material with their on/off state and value (most likely the margin). RLPy cannot list shapes, so the given names, or every skin bone of the avatar, are probed. ${NO_GUI}`,
    selectorShape({
      ...physicsTargetFields,
      collision_names: z
        .array(z.string().min(1).max(256))
        .min(1)
        .max(500)
        .optional()
        .describe(
          "Collision shape (bone) names to check, for example CC_Base_Spine02; omit to probe all skin bones",
        ),
    }),
    async ({ item_name, item_id, mesh_name, material_name, collision_names }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      return bridgeCall(
        () =>
          bridge.wfPhysicsGetCollision(
            toSelector({ item_name, item_id }),
            toPhysicsTarget({ mesh_name, material_name }),
            collision_names,
          ),
        (result: PhysicsCollisionGetResult) => {
          if (!result.success) return physicsFailed(result);
          const shapes = result.shapes ?? [];
          const lines = [
            `Collision shapes for ${physicsLabel(result, item_name ?? item_id)}: ${shapes.length} found${result.probed !== undefined ? ` (${result.probed} name(s) checked)` : ""}`,
          ];
          for (const shape of shapes) {
            lines.push(`  - ${shape.name}: ${shapeText(shape)}`);
          }
          if (result.unknown && result.unknown.length > 0) {
            lines.push(`  Not found: ${result.unknown.join(", ")}`);
          }
          const notes = notesNote(result.notes);
          if (notes) lines.push(`  ${notes}`);
          return lines.join("\n");
        },
      );
    },
  );

  server.tool(
    "set_physics_collision",
    `Turn collision shapes on/off and/or set their value (most likely the margin) for one soft-cloth mesh/material; every shape is read back. ${NO_GUI}`,
    selectorShape({
      ...physicsTargetFields,
      shapes: z
        .array(
          z.object({
            name: z.string().min(1).max(256).describe("Collision shape (bone) name"),
            enabled: z.boolean().optional().describe("true to use this shape, false to ignore it"),
            value: z.number().finite().optional().describe("New collision value (margin)"),
          }),
        )
        .min(1)
        .max(200)
        .describe("Shapes to change; each needs enabled and/or value"),
    }),
    async ({ item_name, item_id, mesh_name, material_name, shapes }) => {
      const problem = selectorProblem({ item_name, item_id });
      if (problem) return schemaFailure(problem);
      if (shapes.some((shape) => shape.enabled === undefined && shape.value === undefined)) {
        return schemaFailure("Each shape needs enabled and/or value.");
      }
      return bridgeCall(
        () =>
          bridge.wfPhysicsSetCollision(
            toSelector({ item_name, item_id }),
            toPhysicsTarget({ mesh_name, material_name }),
            shapes,
          ),
        (result: PhysicsCollisionSetResult) => {
          const rows = (result.shapes ?? []).map(
            (shape) =>
              `  - ${shape.name}: ${shapeText(shape.before)} -> ${shapeText(shape.after)}${shape.errors ? ` (${shape.errors.join("; ")})` : ""}`,
          );
          if (!result.success) {
            const base = physicsFailed(result);
            return rows.length > 0 ? `${base}\n${rows.join("\n")}` : base;
          }
          const notes = notesNote(result.notes);
          return [
            `Updated collision shapes for ${physicsLabel(result, item_name ?? item_id)}:`,
            ...rows,
            ...(notes ? [`  ${notes}`] : []),
          ].join("\n");
        },
      );
    },
  );
}
