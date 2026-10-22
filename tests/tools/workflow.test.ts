/**
 * Unit tests for registerWorkflowTools.
 * The bridge is mocked like the other tool tests; the MCP server is the shared
 * mock server. The item-selector refine is tested through the exported schema
 * and through the handler guard (the SDK only advertises raw shapes).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  registerWorkflowTools,
  itemSelectorSchema,
  optionalTargetSchema,
} from "../../src/tools/workflow.js";
import { createMockServer } from "../helpers/mock-server.js";

// ── mock bridge ───────────────────────────────────────────────────────────────

function createWorkflowBridge() {
  return {
    listSceneItems: vi.fn(),
    wfSetVisible: vi.fn(),
    wfRemoveItem: vi.fn(),
    wfImportFbx: vi.fn(),
    wfAttachToBone: vi.fn(),
    wfTransferSkinWeights: vi.fn(),
    wfConvertToHair: vi.fn(),
    wfClothToAccessory: vi.fn(),
    wfConformCloth: vi.fn(),
    wfGetTransform: vi.fn(),
    wfSetTransform: vi.fn(),
    wfSaveProject: vi.fn(),
    wfExportObj: vi.fn(),
    wfGetFloorContact: vi.fn(),
    wfSetFloorContact: vi.fn(),
    wfAutoAdjustFootHeight: vi.fn(),
    wfRenderViewport: vi.fn(),
    wfCaptureViews4: vi.fn(),
    wfPhysicsInfo: vi.fn(),
    wfPhysicsActivate: vi.fn(),
    wfPhysicsLoadWeightMap: vi.fn(),
    wfPhysicsGetParams: vi.fn(),
    wfPhysicsSetParams: vi.fn(),
    wfPhysicsGetCollision: vi.fn(),
    wfPhysicsSetCollision: vi.fn(),
  };
}

type WorkflowBridge = ReturnType<typeof createWorkflowBridge>;

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: WorkflowBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createWorkflowBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerWorkflowTools(server as any, bridge as any);
});

/** Call a registered tool handler directly, as the SDK does after validation. */
async function call(tool: string, args: Record<string, unknown>) {
  return server.getRegisteredTool(tool)(args);
}

function descriptionOf(tool: string): string {
  const registration = server.tool.mock.calls.find((entry: unknown[]) => entry[0] === tool);
  if (!registration) throw new Error(`Tool '${tool}' was not registered`);
  return registration[1] as string;
}

// ── registration ──────────────────────────────────────────────────────────────

const TOOL_NAMES = [
  "list_scene_items",
  "set_visible",
  "remove_item",
  "import_fbx",
  "attach_to_bone",
  "transfer_skin_weights",
  "convert_to_hair",
  "cloth_to_accessory",
  "conform_cloth",
  "get_transform",
  "set_transform",
  "save_project",
  "export_obj",
  "get_floor_contact",
  "set_floor_contact",
  "auto_adjust_foot_height",
  "render_viewport",
  "capture_views4",
  "get_physics_info",
  "set_physics_active",
  "load_physics_weight_map",
  "get_soft_physics_params",
  "set_soft_physics_params",
  "get_physics_collision",
  "set_physics_collision",
];

describe("registerWorkflowTools – registration", () => {
  it("registers exactly 25 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(25);
  });

  it.each(TOOL_NAMES)("registers %s", (name) => {
    const registered = server.tool.mock.calls.map((entry: unknown[]) => entry[0]);
    expect(registered).toContain(name);
  });

  it("says every tool works without the GUI for text-only models", () => {
    for (const name of TOOL_NAMES) {
      expect(descriptionOf(name)).toContain(
        "Works without the GUI and is meant for text-only models.",
      );
    }
  });

  it("puts the 4-image review rule in capture_views4", () => {
    expect(descriptionOf("capture_views4")).toContain(
      "Always call this after every change and check all 4 images (front X, side Y, top Z, perspective) before moving on.",
    );
  });
});

// ── success and failure per tool ──────────────────────────────────────────────

interface ToolCase {
  tool: string;
  args: Record<string, unknown>;
  method: keyof WorkflowBridge;
  expectedArgs: unknown[];
  success: Record<string, unknown>;
  successContains: string[];
}

const ITEM = { name: "Jacket", id: "i1", kind: "cloth" };
const TRANSFORM = {
  success: true,
  name: "Jacket",
  move: [1, 2.5, -3],
  rotate: [0, 45, 0],
  scale: [1, 1, 1],
};

const CASES: ToolCase[] = [
  {
    tool: "list_scene_items",
    args: {},
    method: "listSceneItems",
    expectedArgs: [],
    success: {
      success: true,
      items: [
        { name: "Jacket", id: "i1", kind: "cloth", visible: true, parent: "Hero", cloth_type: "top" },
      ],
    },
    successContains: ["Found 1 item(s)", "Jacket", "id: i1", "visible", "parent: Hero", "cloth: top"],
  },
  {
    tool: "set_visible",
    args: { item_name: "Jacket", visible: false },
    method: "wfSetVisible",
    expectedArgs: [{ item_name: "Jacket" }, false],
    success: { success: true, name: "Jacket", id: "i1", visible: false },
    successContains: ["Item 'Jacket'", "id: i1", "is now hidden"],
  },
  {
    tool: "remove_item",
    args: { item_name: "Jacket" },
    method: "wfRemoveItem",
    expectedArgs: [{ item_name: "Jacket" }],
    success: { success: true, removed: ITEM },
    successContains: ["Removed 'Jacket'", "id: i1", "kind: cloth"],
  },
  {
    tool: "import_fbx",
    args: { file_path: "C:/assets/shoes.fbx" },
    method: "wfImportFbx",
    expectedArgs: ["C:/assets/shoes.fbx"],
    success: { success: true, item: ITEM },
    successContains: ["Imported 'Jacket'", "id: i1"],
  },
  {
    tool: "attach_to_bone",
    args: { item_name: "Jacket", bone_name: "CC_Base_Hip" },
    method: "wfAttachToBone",
    expectedArgs: [{ item_name: "Jacket" }, "CC_Base_Hip"],
    success: { success: true, name: "Jacket", bone: "CC_Base_Hip" },
    successContains: ["Attached 'Jacket' to bone 'CC_Base_Hip'"],
  },
  {
    tool: "transfer_skin_weights",
    args: { item_id: "i1", template: "dress" },
    method: "wfTransferSkinWeights",
    expectedArgs: [{ item_id: "i1" }, "dress"],
    success: { success: true, name: "Jacket", template: "dress", kind_after: "cloth" },
    successContains: ["Transferred skin weights to 'Jacket'", "template: dress", "kind now cloth"],
  },
  {
    tool: "convert_to_hair",
    args: { item_name: "Cap", template: "bangs" },
    method: "wfConvertToHair",
    expectedArgs: [{ item_name: "Cap" }, "bangs"],
    success: { success: true, name: "Cap", template: "bangs" },
    successContains: ["Converted 'Cap' to hair", "template: bangs"],
  },
  {
    tool: "cloth_to_accessory",
    args: { item_name: "Jacket" },
    method: "wfClothToAccessory",
    expectedArgs: [{ item_name: "Jacket" }, true],
    success: { success: true, name: "Jacket" },
    successContains: ["Converted 'Jacket' to an accessory"],
  },
  {
    tool: "conform_cloth",
    args: { item_name: "Jacket", iterations: 3, values: { chest: 0.5 } },
    method: "wfConformCloth",
    expectedArgs: [{ item_name: "Jacket" }, 3, { chest: 0.5 }],
    success: { success: true, name: "Jacket", before: { chest: 0.25 }, after: { chest: 0.6 } },
    successContains: ["Conformed 'Jacket'", "chest=0.25 -> chest=0.6"],
  },
  {
    tool: "get_transform",
    args: { item_name: "Jacket" },
    method: "wfGetTransform",
    expectedArgs: [{ item_name: "Jacket" }],
    success: TRANSFORM,
    successContains: ["'Jacket'", "move=(1, 2.5, -3)", "rotate=(0, 45, 0)", "scale=(1, 1, 1)"],
  },
  {
    tool: "set_transform",
    args: { item_name: "Jacket", move: [1, 2.5, -3] },
    method: "wfSetTransform",
    expectedArgs: [{ item_name: "Jacket" }, { move: [1, 2.5, -3] }],
    success: TRANSFORM,
    successContains: ["Updated 'Jacket'", "move=(1, 2.5, -3)"],
  },
  {
    tool: "save_project",
    args: {},
    method: "wfSaveProject",
    expectedArgs: [undefined],
    success: { success: true, path: "C:/work/hero.ccProject" },
    successContains: ["Saved project to C:/work/hero.ccProject"],
  },
  {
    tool: "export_obj",
    args: { file_path: "C:/work/hero.obj" },
    method: "wfExportObj",
    expectedArgs: ["C:/work/hero.obj", true, true],
    success: { success: true, path: "C:/work/hero.obj", bytes: 2048 },
    successContains: ["Exported OBJ to C:/work/hero.obj", "2048 bytes"],
  },
  {
    tool: "get_floor_contact",
    args: {},
    method: "wfGetFloorContact",
    expectedArgs: [],
    success: { success: true, value: { enabled: true, offset: 0.5 } },
    successContains: ["Floor contact:", "enabled", "0.5"],
  },
  {
    tool: "set_floor_contact",
    args: { value: { enabled: true } },
    method: "wfSetFloorContact",
    expectedArgs: [{ enabled: true }],
    success: { success: true },
    successContains: ["Floor contact settings applied."],
  },
  {
    tool: "auto_adjust_foot_height",
    args: {},
    method: "wfAutoAdjustFootHeight",
    expectedArgs: [],
    success: { success: true },
    successContains: ["Foot height adjusted automatically."],
  },
  {
    tool: "render_viewport",
    args: { file_path: "C:/work/view.png" },
    method: "wfRenderViewport",
    expectedArgs: ["C:/work/view.png"],
    success: { success: true, path: "C:/work/view.png" },
    successContains: ["Rendered viewport to C:/work/view.png"],
  },
  {
    tool: "capture_views4",
    args: { folder: "C:/work/shots", prefix: "hero" },
    method: "wfCaptureViews4",
    expectedArgs: ["C:/work/shots", "hero", undefined],
    success: { success: true, files: ["front.png", "side.png", "top.png", "persp.png"] },
    successContains: [
      "Saved 4 check view(s)",
      "front (X): front.png",
      "side (Y): side.png",
      "top (Z): top.png",
      "perspective: persp.png",
    ],
  },
  {
    tool: "get_physics_info",
    args: { item_name: "Skirt" },
    method: "wfPhysicsInfo",
    expectedArgs: [{ item_name: "Skirt" }],
    success: {
      success: true,
      name: "Skirt",
      kind: "cloth",
      activate: true,
      meshes: [{ mesh: "Skirt", materials: ["Skirt_Mat"] }],
      properties: ["Mass", "Friction"],
      weight_map_import: true,
    },
    successContains: [
      "Physics for 'Skirt' (cloth): Activate Physics on",
      "mesh Skirt: Skirt_Mat",
      "Soft PhysX properties: Mass, Friction",
    ],
  },
  {
    tool: "set_physics_active",
    args: { item_name: "Skirt", enable: false },
    method: "wfPhysicsActivate",
    expectedArgs: [{ item_name: "Skirt" }, false],
    success: { success: true, name: "Skirt", activate: false, verified: true },
    successContains: ["Activate Physics for 'Skirt' is now off"],
  },
  {
    tool: "load_physics_weight_map",
    args: {
      item_name: "Skirt",
      mesh_name: "Skirt",
      material_name: "Skirt_Mat",
      file_path: "C:/maps/skirt.png",
    },
    method: "wfPhysicsLoadWeightMap",
    expectedArgs: [
      { item_name: "Skirt" },
      { mesh_name: "Skirt", material_name: "Skirt_Mat" },
      "C:/maps/skirt.png",
    ],
    success: {
      success: true,
      name: "Skirt",
      mesh: "Skirt",
      material: "Skirt_Mat",
      path: "C:/maps/skirt.png",
      weight_map_present: true,
    },
    successContains: [
      "Loaded weight map C:/maps/skirt.png into 'Skirt' mesh 'Skirt' material 'Skirt_Mat'",
      "weight map present after loading",
    ],
  },
  {
    tool: "get_soft_physics_params",
    args: { item_name: "Skirt", names: ["Mass", "Friction"] },
    method: "wfPhysicsGetParams",
    expectedArgs: [{ item_name: "Skirt" }, {}, ["Mass", "Friction"]],
    success: {
      success: true,
      name: "Skirt",
      mesh: "Skirt",
      material: "Skirt_Mat",
      params: { Mass: 1.5, Friction: 0.25 },
    },
    successContains: [
      "Soft PhysX for 'Skirt' mesh 'Skirt' material 'Skirt_Mat'",
      "Mass=1.5",
      "Friction=0.25",
    ],
  },
  {
    tool: "set_soft_physics_params",
    args: {
      item_name: "Skirt",
      material_name: "Skirt_Mat",
      values: { Mass: 2, SelfCollision: true },
    },
    method: "wfPhysicsSetParams",
    expectedArgs: [
      { item_name: "Skirt" },
      { material_name: "Skirt_Mat" },
      { Mass: 2, SelfCollision: true },
    ],
    success: {
      success: true,
      name: "Skirt",
      mesh: "Skirt",
      material: "Skirt_Mat",
      before: { Mass: 1, SelfCollision: 0 },
      after: { Mass: 2, SelfCollision: 1 },
    },
    successContains: [
      "Updated Soft PhysX for 'Skirt'",
      "Mass=1, SelfCollision=0 -> Mass=2, SelfCollision=1",
    ],
  },
  {
    tool: "get_physics_collision",
    args: { item_name: "Skirt", collision_names: ["CC_Base_Hip", "Nope"] },
    method: "wfPhysicsGetCollision",
    expectedArgs: [{ item_name: "Skirt" }, {}, ["CC_Base_Hip", "Nope"]],
    success: {
      success: true,
      name: "Skirt",
      mesh: "Skirt",
      material: "Skirt_Mat",
      shapes: [{ name: "CC_Base_Hip", enabled: true, value: 0.5 }],
      probed: 2,
      unknown: ["Nope"],
    },
    successContains: [
      "1 found (2 name(s) checked)",
      "CC_Base_Hip: on, value 0.5",
      "Not found: Nope",
    ],
  },
  {
    tool: "set_physics_collision",
    args: { item_name: "Skirt", shapes: [{ name: "CC_Base_Hip", enabled: false, value: 1 }] },
    method: "wfPhysicsSetCollision",
    expectedArgs: [
      { item_name: "Skirt" },
      {},
      [{ name: "CC_Base_Hip", enabled: false, value: 1 }],
    ],
    success: {
      success: true,
      name: "Skirt",
      mesh: "Skirt",
      material: "Skirt_Mat",
      shapes: [
        {
          name: "CC_Base_Hip",
          before: { name: "CC_Base_Hip", enabled: true, value: 0.5 },
          after: { name: "CC_Base_Hip", enabled: false, value: 1 },
        },
      ],
    },
    successContains: [
      "Updated collision shapes for 'Skirt'",
      "CC_Base_Hip: on, value 0.5 -> off, value 1",
    ],
  },
];

describe("workflow tools – success", () => {
  it.each(CASES)("$tool formats a successful result", async (testCase) => {
    bridge[testCase.method].mockResolvedValue(testCase.success);

    const result = await call(testCase.tool, testCase.args);

    expect(bridge[testCase.method]).toHaveBeenCalledWith(...testCase.expectedArgs);
    for (const expected of testCase.successContains) {
      expect(result.content[0].text).toContain(expected);
    }
  });
});

describe("workflow tools – failure", () => {
  it.each(CASES)("$tool reports a failure", async (testCase) => {
    bridge[testCase.method].mockResolvedValue({ success: false, error: "boom" });

    const result = await call(testCase.tool, testCase.args);

    expect(result.content[0].text).toBe("Failed: boom");
  });

  it("attach_to_bone lists bone candidates for an unknown bone", async () => {
    bridge.wfAttachToBone.mockResolvedValue({
      success: false,
      error: "unknown bone",
      bones: ["CC_Base_Hip", "CC_Base_Waist"],
    });

    const result = await call("attach_to_bone", { item_name: "Jacket", bone_name: "Hip" });

    expect(result.content[0].text).toContain("Failed: unknown bone");
    expect(result.content[0].text).toContain("CC_Base_Hip");
    expect(result.content[0].text).toContain("CC_Base_Waist");
  });

  it("reports ambiguous names with the matching items", async () => {
    bridge.wfRemoveItem.mockResolvedValue({
      success: false,
      error: "ambiguous name",
      matches: [
        { name: "Jacket", id: "i1", kind: "cloth" },
        { name: "Jacket", id: "i2", kind: "prop" },
      ],
    });

    const result = await call("remove_item", { item_name: "Jacket" });

    expect(result.content[0].text).toContain("Failed: ambiguous name");
    expect(result.content[0].text).toContain("i1");
    expect(result.content[0].text).toContain("i2");
  });

  it("turns a bridge exception into a readable error", async () => {
    bridge.wfSaveProject.mockRejectedValue(new Error("connection refused"));

    const result = await call("save_project", {});

    expect(result.content[0].text).toContain("CC5 bridge error: connection refused");
  });
});

// ── item-selector validation ──────────────────────────────────────────────────

const SELECTOR_TOOLS: Array<{ tool: string; extra: Record<string, unknown> }> = [
  { tool: "set_visible", extra: { visible: true } },
  { tool: "remove_item", extra: {} },
  { tool: "attach_to_bone", extra: { bone_name: "CC_Base_Hip" } },
  { tool: "transfer_skin_weights", extra: { template: "default" } },
  { tool: "convert_to_hair", extra: { template: "top" } },
  { tool: "cloth_to_accessory", extra: {} },
  { tool: "conform_cloth", extra: {} },
  { tool: "get_transform", extra: {} },
  { tool: "set_transform", extra: { move: [0, 0, 0] } },
  { tool: "get_physics_info", extra: {} },
  { tool: "set_physics_active", extra: { enable: true } },
  { tool: "load_physics_weight_map", extra: { file_path: "C:/maps/w.png" } },
  { tool: "get_soft_physics_params", extra: {} },
  { tool: "set_soft_physics_params", extra: { values: { Mass: 1 } } },
  { tool: "get_physics_collision", extra: {} },
  { tool: "set_physics_collision", extra: { shapes: [{ name: "CC_Base_Hip", enabled: true }] } },
];

describe("item-selector validation", () => {
  it("rejects a selector with neither name nor id", () => {
    const parsed = itemSelectorSchema.safeParse({});

    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(parsed.error.issues.some((i) => i.message.includes("Provide at least one"))).toBe(true);
    }
  });

  it("accepts item_name only", () => {
    expect(itemSelectorSchema.safeParse({ item_name: "Jacket" }).success).toBe(true);
  });

  it("accepts item_id only", () => {
    expect(itemSelectorSchema.safeParse({ item_id: "i1" }).success).toBe(true);
  });

  it("rejects an item_name longer than 256 characters", () => {
    expect(itemSelectorSchema.safeParse({ item_name: "x".repeat(257) }).success).toBe(false);
  });

  it("rejects an item_id longer than 64 characters", () => {
    expect(itemSelectorSchema.safeParse({ item_id: "x".repeat(65) }).success).toBe(false);
  });

  it.each(SELECTOR_TOOLS)("$tool rejects a missing selector before calling the bridge", async ({ tool, extra }) => {
    const result = await call(tool, extra);

    expect(result.content[0].text).toBe(
      "Failed: Provide at least one of item_name or item_id.",
    );
    expect(result.isError).toBe(true);
    for (const method of Object.keys(bridge) as Array<keyof WorkflowBridge>) {
      expect(bridge[method]).not.toHaveBeenCalled();
    }
  });
});

describe("capture_views4 target validation", () => {
  it("allows no target", () => {
    expect(optionalTargetSchema.safeParse(undefined).success).toBe(true);
  });

  it("accepts a target with a name or id", () => {
    expect(optionalTargetSchema.safeParse({ item_name: "Jacket" }).success).toBe(true);
    expect(optionalTargetSchema.safeParse({ item_id: "i1" }).success).toBe(true);
  });

  it("rejects an empty target object", () => {
    expect(optionalTargetSchema.safeParse({}).success).toBe(false);
  });

  it("passes a target through to the bridge", async () => {
    bridge.wfCaptureViews4.mockResolvedValue({ success: true, files: [] });

    await call("capture_views4", {
      folder: "C:/shots",
      prefix: "hero",
      target: { item_name: "Jacket" },
    });

    expect(bridge.wfCaptureViews4).toHaveBeenCalledWith("C:/shots", "hero", {
      item_name: "Jacket",
    });
  });
});

// ── defaults ──────────────────────────────────────────────────────────────────

describe("workflow tools – defaults", () => {
  it("uses 1 conform iteration when iterations is omitted", async () => {
    bridge.wfConformCloth.mockResolvedValue({ success: true, name: "Jacket" });

    await call("conform_cloth", { item_name: "Jacket" });

    expect(bridge.wfConformCloth).toHaveBeenCalledWith({ item_name: "Jacket" }, 1, undefined);
  });

  it("keeps the current shape by default when converting cloth to accessory", async () => {
    bridge.wfClothToAccessory.mockResolvedValue({ success: true, name: "Jacket" });

    await call("cloth_to_accessory", { item_name: "Jacket" });

    expect(bridge.wfClothToAccessory).toHaveBeenCalledWith({ item_name: "Jacket" }, true);
  });

  it("exports the current pose with materials by default", async () => {
    bridge.wfExportObj.mockResolvedValue({ success: true, path: "C:/work/hero.obj", bytes: 1 });

    await call("export_obj", { file_path: "C:/work/hero.obj" });

    expect(bridge.wfExportObj).toHaveBeenCalledWith("C:/work/hero.obj", true, true);
  });
});

// ── physics (Soft Cloth) specifics ────────────────────────────────────────────

describe("physics tools", () => {
  it("set_soft_physics_params rejects unknown property names before calling the bridge", async () => {
    const result = await call("set_soft_physics_params", {
      item_name: "Skirt",
      values: { Mass: 1, Wobble: 3 },
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Unknown Soft PhysX property: Wobble");
    expect(result.content[0].text).toContain("TetherLimit");
    expect(bridge.wfPhysicsSetParams).not.toHaveBeenCalled();
  });

  it("set_soft_physics_params rejects an empty values object", async () => {
    const result = await call("set_soft_physics_params", { item_name: "Skirt", values: {} });

    expect(result.isError).toBe(true);
    expect(bridge.wfPhysicsSetParams).not.toHaveBeenCalled();
  });

  it("set_soft_physics_params shows before/after when the read-back differs", async () => {
    bridge.wfPhysicsSetParams.mockResolvedValue({
      success: false,
      error: "read-back differs for Mass",
      before: { Mass: 1 },
      after: { Mass: 1 },
    });

    const result = await call("set_soft_physics_params", {
      item_name: "Skirt",
      values: { Mass: 5 },
    });

    expect(result.content[0].text).toContain("Failed: read-back differs for Mass");
    expect(result.content[0].text).toContain("Values: Mass=1 -> Mass=1");
  });

  it("load_physics_weight_map rejects a non-PNG path", async () => {
    const result = await call("load_physics_weight_map", {
      item_name: "Skirt",
      file_path: "C:/maps/skirt.jpg",
    });

    expect(result.isError).toBe(true);
    expect(bridge.wfPhysicsLoadWeightMap).not.toHaveBeenCalled();
  });

  it("load_physics_weight_map tells the user to use the CC5 GUI when it is GUI-only", async () => {
    bridge.wfPhysicsLoadWeightMap.mockResolvedValue({
      success: false,
      gui_only: true,
      error: "SetPhysicsSoftColthWeightMap failed: boom",
    });

    const result = await call("load_physics_weight_map", {
      item_name: "Skirt",
      file_path: "C:/maps/skirt.png",
    });

    expect(result.content[0].text).toContain("Failed: SetPhysicsSoftColthWeightMap failed: boom");
    expect(result.content[0].text).toContain("Modify panel > Physics > Weight Map");
  });

  it("describes the GUI fallback for weight maps", () => {
    expect(descriptionOf("load_physics_weight_map")).toContain("画面で読み込む");
  });

  it("lists the soft-cloth meshes when the mesh name is missing", async () => {
    bridge.wfPhysicsGetParams.mockResolvedValue({
      success: false,
      error: "mesh_name is required (the item has several soft-cloth meshes)",
      meshes: [
        { mesh: "Top", materials: ["Top_Mat"] },
        { mesh: "Skirt", materials: ["Skirt_A", "Skirt_B"] },
      ],
    });

    const result = await call("get_soft_physics_params", { item_name: "Dress" });

    expect(result.content[0].text).toContain("mesh_name is required");
    expect(result.content[0].text).toContain("Top [Top_Mat]");
    expect(result.content[0].text).toContain("Skirt [Skirt_A, Skirt_B]");
  });

  it("set_physics_collision rejects a shape with neither enabled nor value", async () => {
    const result = await call("set_physics_collision", {
      item_name: "Skirt",
      shapes: [{ name: "CC_Base_Hip" }],
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("Each shape needs enabled and/or value.");
    expect(bridge.wfPhysicsSetCollision).not.toHaveBeenCalled();
  });

  it("set_physics_collision lists per-shape problems on failure", async () => {
    bridge.wfPhysicsSetCollision.mockResolvedValue({
      success: false,
      error: "CC_Base_Hip: enabled reads back as true",
      shapes: [
        {
          name: "CC_Base_Hip",
          before: { name: "CC_Base_Hip", enabled: true, value: 0.5 },
          after: { name: "CC_Base_Hip", enabled: true, value: 0.5 },
          errors: ["enabled reads back as true"],
        },
      ],
    });

    const result = await call("set_physics_collision", {
      item_name: "Skirt",
      shapes: [{ name: "CC_Base_Hip", enabled: false }],
    });

    expect(result.content[0].text).toContain("Failed: CC_Base_Hip: enabled reads back as true");
    expect(result.content[0].text).toContain("on, value 0.5 -> on, value 0.5");
  });

  it("get_physics_info reports an unknown Activate Physics state", async () => {
    bridge.wfPhysicsInfo.mockResolvedValue({
      success: true,
      name: "Cape",
      activate: null,
      meshes: [],
      weight_map_import: false,
    });

    const result = await call("get_physics_info", { item_name: "Cape" });

    expect(result.content[0].text).toContain("Activate Physics unknown");
    expect(result.content[0].text).toContain("No soft-cloth meshes yet");
    expect(result.content[0].text).toContain("Weight-map import is not available");
  });
});
