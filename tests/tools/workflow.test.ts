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
];

describe("registerWorkflowTools – registration", () => {
  it("registers exactly 18 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(18);
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
