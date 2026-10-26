/**
 * skingen_state, skingen_editor, skingen_layer: arguments are checked before the bridge is called,
 * results are read back to the model, and windows that need a person come with a screenshot.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  registerSkinGenTools,
  formatLayers,
  formatSkinGenState,
  formatLayerResult,
  layerProblem,
} from "../../src/tools/skingen.js";
import { createMockServer } from "../helpers/mock-server.js";

function makeBridge() {
  return {
    uiSkinGenState: vi.fn(),
    uiSkinGenEditor: vi.fn(),
    uiSkinGenLayer: vi.fn(),
    uiWaitJob: vi.fn(),
    uiWindows: vi.fn(),
  };
}

let bridge: ReturnType<typeof makeBridge>;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = makeBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerSkinGenTools(server as any, bridge as any);
});

const call = (tool: string, args: Record<string, unknown>) => server.getRegisteredTool(tool)(args);
const texts = (result: { content: Array<{ type: string; text?: string }> }) =>
  result.content.filter((c) => c.type === "text").map((c) => c.text).join("\n");

const LAYERS = [
  { index: 0, name: "Lips", visible: true, selected: false },
  { index: 1, name: "Eyeshadow", visible: false, selected: true },
];

describe("skingen_state", () => {
  it("shows the editor, layers and opacity", async () => {
    bridge.uiSkinGenState.mockResolvedValue({
      success: true, editor_found: true, editor_active: true, tab: "makeup", layers: LAYERS, opacity: 60, combos: { material: "Head" },
    });
    const text = texts(await call("skingen_state", {}));
    expect(text).toContain("SkinGen editor: ON, tab makeup");
    expect(text).toContain("Selected: material=Head");
    expect(text).toContain("0: Lips [visible]");
    expect(text).toContain("1: Eyeshadow [HIDDEN, selected]");
    expect(text).toContain("Opacity of the selected layer: 60");
  });

  it("explains a missing editor", () => {
    expect(formatSkinGenState({ success: true, editor_found: false, layers: [], hint: "Apply a SkinGen preset." }))
      .toContain("switch not found");
    expect(formatLayers([])).toBe("  (no layers)");
    expect(formatSkinGenState({ success: false, error: "x" })).toBe("Failed: x");
  });
});

describe("skingen_editor", () => {
  it("turns the editor off and tells what was answered", async () => {
    bridge.uiSkinGenEditor.mockResolvedValue({ success: true, job_id: "e-1" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: true, changed: true, editor_active: false, waited_s: 14.2, answered: [{ rule: "skingen_exit", pressed: "yes", window: "SkinGen" }] },
    });
    const text = texts(await call("skingen_editor", { active: false, exit_answer: "yes", timeout_seconds: 90 }));
    expect(bridge.uiSkinGenEditor).toHaveBeenCalledWith({ active: false, exit_answer: "yes", timeout_s: 90 });
    expect(bridge.uiWaitJob).toHaveBeenCalledWith("e-1", expect.objectContaining({ timeoutMs: 150_000 }));
    expect(text).toContain("SkinGen editor is now off.");
    expect(text).toContain("Answered: yes.");
    expect(text).toContain("Waited 14.2s");
  });

  it("says when nothing had to change", async () => {
    bridge.uiSkinGenEditor.mockResolvedValue({ success: true, job_id: "e-2" });
    bridge.uiWaitJob.mockResolvedValue({ finished: true, result: { success: true, changed: false, editor_active: true } });
    expect(texts(await call("skingen_editor", { active: true }))).toContain("(it already was)");
  });

  it("a window that needs a person is shown with a screenshot", async () => {
    bridge.uiSkinGenEditor.mockResolvedValue({ success: true, job_id: "e-3" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: false, error: "a window needs a person: 'Save'", blocked_by: { title: "Save", text: "Save changes?", buttons: ["Yes", "No"] } },
    });
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [{ title: "Save", text: "Save changes?", buttons: ["Yes", "No"], png_base64: "UE5H" }] });
    const result = await call("skingen_editor", { active: false });
    expect(texts(result)).toContain("Failed: a window needs a person");
    expect(texts(result)).toContain("Save changes?");
    expect(result.content.some((c: { type: string }) => c.type === "image")).toBe(true);
  });

  it("a refusal from the bridge and a still-running job", async () => {
    bridge.uiSkinGenEditor.mockResolvedValueOnce({ success: false, error: "the Activate Editor switch was not found" });
    expect(texts(await call("skingen_editor", { active: false }))).toContain("switch was not found");
    bridge.uiSkinGenEditor.mockResolvedValueOnce({ success: true, job_id: "e-4" });
    bridge.uiWaitJob.mockResolvedValueOnce({ finished: false, status: { success: true, state: "running", windows: [] } });
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [] });
    expect(texts(await call("skingen_editor", { active: false }))).toContain("Still running after 150s");
  });
});

describe("layerProblem", () => {
  it.each([
    [{ action: "hide" }, "give index or name"],
    [{ action: "opacity", index: 0 }, "opacity (0-100) is required"],
    [{ action: "delete", index: 0 }, "confirm_delete=true"],
    [{ action: "delete", index: 0, confirm_delete: false }, "confirm_delete=true"],
    [{ action: "delete", scope: "selected_layer", confirm_delete: true }, "give index or name"],
  ])("%j -> %s", (args, expected) => {
    expect(layerProblem(args)).toContain(expected);
  });

  it.each([
    [{ action: "hide", name: "Lips" }],
    [{ action: "opacity", index: 1, opacity: 0 }],
    [{ action: "delete", scope: "all_material", confirm_delete: true }],
    [{ action: "delete", scope: "current_material", confirm_delete: true }],
    [{ action: "delete", index: 2, confirm_delete: true }],
  ])("%j is fine", (args) => {
    expect(layerProblem(args)).toBeUndefined();
  });
});

describe("skingen_layer", () => {
  it("does not call the bridge with bad arguments", async () => {
    expect(texts(await call("skingen_layer", { action: "delete", index: 0 }))).toContain("confirm_delete=true");
    expect(texts(await call("skingen_layer", { action: "opacity", name: "Lips" }))).toContain("opacity (0-100)");
    expect(bridge.uiSkinGenLayer).not.toHaveBeenCalled();
  });

  it("limits opacity to 0-100 whole numbers", () => {
    const shape = server.tool.mock.calls.find((c: unknown[]) => c[0] === "skingen_layer")[2];
    expect(shape.opacity.safeParse(101).success).toBe(false);
    expect(shape.opacity.safeParse(12.5).success).toBe(false);
    expect(shape.opacity.safeParse(0).success).toBe(true);
    expect(shape.action.safeParse("explode").success).toBe(false);
  });

  it("sets opacity and reports the read-back", async () => {
    bridge.uiSkinGenLayer.mockResolvedValue({ success: true, job_id: "l-1" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: true, layer: 1, opacity_before: 100, opacity_after: 35, layers: LAYERS },
    });
    const text = texts(await call("skingen_layer", { action: "opacity", name: "Eyeshadow", opacity: 35 }));
    expect(bridge.uiSkinGenLayer).toHaveBeenCalledWith({ action: "opacity", name: "Eyeshadow", opacity: 35 });
    expect(text).toContain("Opacity of layer 1: 100 -> 35 (read back from CC5).");
    expect(text).toContain("Layers now:");
  });

  it("passes confirm to the bridge for delete", async () => {
    bridge.uiSkinGenLayer.mockResolvedValue({ success: true, job_id: "l-2" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: true, scope: "selected_layer", layers_before: 2, layers_after: 1, layers: [LAYERS[0]] },
    });
    const text = texts(await call("skingen_layer", { action: "delete", index: 1, confirm_delete: true }));
    expect(bridge.uiSkinGenLayer).toHaveBeenCalledWith({ action: "delete", index: 1, confirm: true });
    expect(text).toContain("Deleted (selected_layer): 2 -> 1 layer(s).");
  });

  it("a confirmation window is reported, not answered", async () => {
    bridge.uiSkinGenLayer.mockResolvedValue({ success: true, job_id: "l-3" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: false, error: "a window needs a person: 'Delete'", blocked_by: { title: "Delete", text: "Delete the layer?", buttons: ["Yes", "No"] } },
    });
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [{ title: "Delete", text: "Delete the layer?", buttons: ["Yes", "No"], png_base64: "UE5H" }] });
    const result = await call("skingen_layer", { action: "delete", index: 0, confirm_delete: true });
    expect(texts(result)).toContain("waiting for a person");
    expect(result.content.some((c: { type: string }) => c.type === "image")).toBe(true);
  });

  it("failure text includes the menu entries and layers", () => {
    const text = formatLayerResult("delete", { success: false, error: "no delete menu entry", menu: ["Selected Layer", "All Material"], layers: LAYERS });
    expect(text).toContain("Menu entries: Selected Layer | All Material.");
    expect(text).toContain("1: Eyeshadow");
  });

  it("show / hide / select say what they did", () => {
    expect(formatLayerResult("hide", { success: true, layers: LAYERS })).toContain("hide done.");
  });
});
