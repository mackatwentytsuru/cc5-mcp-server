/**
 * apply_preset and list_presets: argument checks before anything is sent, the job flow, and what
 * the reply tells the model (answered windows, windows that need a person, screenshots).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerPresetTools, formatApplyResult, PRESET_CATEGORIES } from "../../src/tools/presets.js";
import { createMockServer } from "../helpers/mock-server.js";
import type { UiApplyPresetResult } from "../../src/types.js";

function makeBridge() {
  return {
    uiApplyPreset: vi.fn(),
    uiWaitJob: vi.fn(),
    uiWindows: vi.fn(),
    uiListPresets: vi.fn(),
  };
}

let bridge: ReturnType<typeof makeBridge>;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = makeBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerPresetTools(server as any, bridge as any);
});

const call = (tool: string, args: Record<string, unknown>) => server.getRegisteredTool(tool)(args);
const texts = (result: { content: Array<{ type: string; text?: string }> }) =>
  result.content.filter((c) => c.type === "text").map((c) => c.text).join("\n");

function schemaOf(tool: string): Record<string, { safeParse: (v: unknown) => { success: boolean } }> {
  const entry = server.tool.mock.calls.find((c: unknown[]) => c[0] === tool);
  return entry[2];
}

const LIP = "C:/lib/Makeup/Lip Makeup/Rouge.ccSkinGenPreset";

describe("registration", () => {
  it("registers both tools with descriptions that state the safety rule", () => {
    for (const name of ["apply_preset", "list_presets"]) {
      expect(server.tool).toHaveBeenCalledWith(name, expect.any(String), expect.any(Object), expect.any(Function));
    }
    const description = server.tool.mock.calls.find((c: unknown[]) => c[0] === "apply_preset")[1] as string;
    expect(description).toContain("NEVER pressed");
    expect(description).toContain("licence");
  });

  it("offers the same categories as the bridge", () => {
    expect(PRESET_CATEGORIES).toContain("makeup_lip");
    expect(schemaOf("list_presets").category.safeParse("makeup_lip").success).toBe(true);
    expect(schemaOf("list_presets").category.safeParse("everything").success).toBe(false);
  });
});

describe("apply_preset arguments", () => {
  it("needs a file", async () => {
    expect(texts(await call("apply_preset", {}))).toContain("give file_path or file_paths");
    expect(bridge.uiApplyPreset).not.toHaveBeenCalled();
  });

  it("refuses path traversal before the bridge", async () => {
    const result = await call("apply_preset", { file_path: "C:/lib/../secret/x.ccSkinGenPreset" });
    expect(texts(result)).toContain("traversal");
    expect(bridge.uiApplyPreset).not.toHaveBeenCalled();
  });

  it("limits the number of files and rejects an unknown answer", () => {
    const schema = schemaOf("apply_preset");
    expect(schema.file_paths.safeParse(Array(11).fill("a.ccAvatarPreset")).success).toBe(false);
    expect(schema.layer_choice.safeParse("cancel").success).toBe(false);
    expect(schema.layer_choice.safeParse("add").success).toBe(true);
  });
});

describe("apply_preset job flow", () => {
  const success: UiApplyPresetResult = {
    success: true,
    avatar: "Beyon",
    files: [{ path: LIP, ok: true, added: [], removed: [], settled: true }],
    answered: [{ rule: "layer_choice", pressed: "replace", window: "SkinGen" }],
    skingen: { editor_active: true, layers: ["Lips"] },
    note: "The SkinGen editor is open.",
  };

  it("sends the body, waits for the job and reports what was answered", async () => {
    bridge.uiApplyPreset.mockResolvedValue({ success: true, job_id: "preset-1" });
    bridge.uiWaitJob.mockResolvedValue({ finished: true, result: success });
    const result = await call("apply_preset", {
      file_path: LIP, layer_choice: "add", restore_neutral_lash: false, watch_prefix: "Lash_", timeout_seconds: 100,
    });
    expect(bridge.uiApplyPreset).toHaveBeenCalledWith({
      file_paths: [LIP],
      answers: { layer_choice: "add", restore_neutral_lash: false },
      watch_prefix: "Lash_",
      timeout_s: 100,
    });
    expect(bridge.uiWaitJob).toHaveBeenCalledWith("preset-1", expect.objectContaining({ timeoutMs: 130_000 }));
    const text = texts(result);
    expect(text).toContain("Applied 1 file(s) to 'Beyon'");
    expect(text).toContain("Answered windows: replace ('SkinGen')");
    expect(text).toContain("SkinGen: editor open; layers: Lips");
    expect(text).toContain("Note: The SkinGen editor is open.");
  });

  it("keeps defaults out of the body", async () => {
    bridge.uiApplyPreset.mockResolvedValue({ success: true, job_id: "preset-2" });
    bridge.uiWaitJob.mockResolvedValue({ finished: true, result: success });
    await call("apply_preset", { file_paths: [LIP, LIP] });
    const body = bridge.uiApplyPreset.mock.calls[0][0];
    expect(body.answers).toBeUndefined();
    expect(body.timeout_s).toBe(240);
    expect(bridge.uiWaitJob.mock.calls[0][1].timeoutMs).toBe((240 * 2 + 30) * 1000);
  });

  it("shows the bridge's refusal", async () => {
    bridge.uiApplyPreset.mockResolvedValue({ success: false, error: "another UI job is still running: crop-3 (crop)" });
    expect(texts(await call("apply_preset", { file_path: LIP }))).toBe("Failed: another UI job is still running: crop-3 (crop)");
    expect(bridge.uiWaitJob).not.toHaveBeenCalled();
  });

  it("a window that needs a person comes back with its screenshot", async () => {
    bridge.uiApplyPreset.mockResolvedValue({ success: true, job_id: "preset-3" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: {
        success: false,
        error: "a window needs a person",
        files: [{ path: LIP, ok: false, error: "x", blocked_by: { title: "License", text: "expired", buttons: ["OK"], needs_human: "license" } }],
      },
    });
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [{ title: "License", text: "expired", buttons: ["OK"], png_base64: "UE5H" }] });
    const result = await call("apply_preset", { file_path: LIP });
    const text = texts(result);
    expect(text).toContain("Failed: a window needs a person");
    expect(text).toContain("waiting for a person");
    expect(text).toContain("人が判断");
    expect(result.content.some((c: { type: string }) => c.type === "image")).toBe(true);
    expect(bridge.uiWindows).toHaveBeenCalledWith({ screenshot: true, max_width: 800 });
  });

  it("a job that is still running says so and shows the windows", async () => {
    bridge.uiApplyPreset.mockResolvedValue({ success: true, job_id: "preset-4" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: false,
      status: { success: true, state: "running", windows: [{ title: "Baking", text: "Please wait", buttons: [], progress: true }] },
    });
    bridge.uiWindows.mockRejectedValue(new Error("busy"));
    const text = texts(await call("apply_preset", { file_path: LIP }));
    expect(text).toContain("Still running after");
    expect(text).toContain("preset-4");
    expect(text).toContain("progress window");
  });

  it("a bridge error becomes a readable message", async () => {
    bridge.uiApplyPreset.mockRejectedValue(new Error("connect ECONNREFUSED"));
    expect(texts(await call("apply_preset", { file_path: LIP }))).toContain("CC5 bridge error: connect ECONNREFUSED");
  });
});

describe("formatApplyResult", () => {
  it("lists added, removed and watched items per file and the skipped ones", () => {
    const text = formatApplyResult({
      success: false,
      error: "LoadFile reported an error",
      files: [
        { path: "C:/a/Curled.ccAvatarPreset", ok: true, added: ["Cloth:Lash_Up_Curled"], removed: ["Cloth:Lash_Up_Old"], watched: ["Lash_Up_Curled"] },
        { path: "C:/a/Bad.ccAvatarPreset", ok: false, error: "LoadFile reported an error" },
      ],
      skipped: ["C:/a/Later.ccAvatarPreset"],
    });
    expect(text).toContain("Curled.ccAvatarPreset: ok; added Cloth:Lash_Up_Curled; removed Cloth:Lash_Up_Old; items now: Lash_Up_Curled");
    expect(text).toContain("Bad.ccAvatarPreset: FAILED; LoadFile reported an error");
    expect(text).toContain("Not applied (an earlier file failed): C:/a/Later.ccAvatarPreset");
  });
});

describe("list_presets", () => {
  it("needs a category or a folder", async () => {
    expect(texts(await call("list_presets", {}))).toContain("give category or folder");
    expect(bridge.uiListPresets).not.toHaveBeenCalled();
  });

  it("lists presets with their paths and the missing names", async () => {
    bridge.uiListPresets.mockResolvedValue({
      success: true,
      total: 2,
      presets: [
        { name: "Nature", path: "C:/lib/Nature.ccSkinGenPreset", folder: "$/Makeup/Lip Makeup", ext: ".ccSkinGenPreset", installed: true },
        { name: "Rouge", path: "C:/lib/Rouge.ccSkinGenPreset", folder: "$/Makeup/Lip Makeup", ext: ".ccSkinGenPreset", installed: false },
      ],
      missing: ["French Rose"],
      truncated: false,
      note: "Only content on disk is listed.",
    });
    const text = texts(await call("list_presets", { category: "makeup_lip", names: ["Nature", "French Rose"] }));
    expect(text).toContain("2 preset(s):");
    expect(text).toContain("- Nature  C:/lib/Nature.ccSkinGenPreset");
    expect(text).toContain("- Rouge (not on disk)");
    expect(text).toContain("Not on disk (cloud or misspelled): French Rose");
  });

  it("lists sub-folders and failures", async () => {
    bridge.uiListPresets.mockResolvedValueOnce({ success: true, folders: ["$/Makeup"], subfolders: ["$/Makeup/Lip Makeup"] });
    expect(texts(await call("list_presets", { folder: "$/Makeup", list_folders: true }))).toContain("$/Makeup/Lip Makeup");
    bridge.uiListPresets.mockResolvedValueOnce({ success: false, error: "folder must be a content path" });
    expect(texts(await call("list_presets", { folder: "$/x" }))).toBe("Failed: folder must be a content path");
  });

  it("flags a cut-off list", async () => {
    bridge.uiListPresets.mockResolvedValue({ success: true, total: 900, presets: [], truncated: true });
    expect(texts(await call("list_presets", { category: "skin" }))).toContain("list cut off");
  });

  it("only takes '$/' folders and plain extensions", () => {
    const schema = schemaOf("list_presets");
    expect(schema.folder.safeParse("C:/Windows").success).toBe(false);
    expect(schema.folder.safeParse("$/Makeup").success).toBe(true);
    expect(schema.ext.safeParse(".ccSkinGenPreset").success).toBe(true);
    expect(schema.ext.safeParse("ccSkinGenPreset").success).toBe(false);
  });
});
