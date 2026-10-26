/**
 * list_cc5_windows and find_ui_widgets (read-only), plus capture_framed_crop and the shared UI helpers.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerUiWindowTools, formatWidgets } from "../../src/tools/ui-windows.js";
import { registerFramedCaptureTools, formatCropResult } from "../../src/tools/framed-capture.js";
import { describeWindow, pathProblem, windowImages, stillRunningText, runUiJob } from "../../src/tools/ui-common.js";
import { bridgeCallRich } from "../../src/util.js";
import { createMockServer } from "../helpers/mock-server.js";

function makeBridge() {
  return {
    uiWindows: vi.fn(),
    uiWidgets: vi.fn(),
    uiCaptureCrop: vi.fn(),
    uiWaitJob: vi.fn(),
  };
}

let bridge: ReturnType<typeof makeBridge>;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = makeBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerUiWindowTools(server as any, bridge as any);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerFramedCaptureTools(server as any, bridge as any);
});

const call = (tool: string, args: Record<string, unknown>) => server.getRegisteredTool(tool)(args);
const texts = (result: { content: Array<{ type: string; text?: string }> }) =>
  result.content.filter((c) => c.type === "text").map((c) => c.text).join("\n");
const images = (result: { content: Array<{ type: string }> }) => result.content.filter((c) => c.type === "image");

describe("list_cc5_windows", () => {
  it("says so when nothing is open", async () => {
    bridge.uiWindows.mockResolvedValue({ success: true, count: 0, windows: [] });
    expect(texts(await call("list_cc5_windows", {}))).toBe("No pop-up windows are open in CC5.");
    expect(bridge.uiWindows).toHaveBeenCalledWith({ screenshot: true });
  });

  it("describes each window, flags the ones for a person, and returns the PNGs", async () => {
    bridge.uiWindows.mockResolvedValue({
      success: true,
      windows: [
        { title: "Apply Character Preset", text: "Apply?", buttons: ["Apply", "Cancel"], answerable_as: "apply_preset", png_base64: "AAAA" },
        { title: "License", text: "Your license has expired", buttons: ["OK"], needs_human: "license", png_base64: "BBBB" },
        { title: "Baking", text: "Please wait", buttons: [], progress: true },
      ],
    });
    const result = await call("list_cc5_windows", { screenshot: true, target: "main", max_width: 600 });
    const text = texts(result);
    expect(bridge.uiWindows).toHaveBeenCalledWith({ screenshot: true, target: "main", max_width: 600 });
    expect(text).toContain("3 window(s) open in CC5");
    expect(text).toContain("known question (apply_preset)");
    expect(text).toContain("人が判断: mentions 'license'");
    expect(text).toContain("progress window");
    expect(images(result)).toHaveLength(2);
  });

  it("returns the main window picture when asked", async () => {
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [], main_window: { title: "Character Creator 5", png_base64: "CCCC" } });
    const result = await call("list_cc5_windows", { target: "main" });
    expect(texts(result)).toContain("Main window: Character Creator 5");
    expect(images(result)).toHaveLength(1);
  });

  it("can skip screenshots and shows failures", async () => {
    bridge.uiWindows.mockResolvedValue({ success: false, error: "no Qt application" });
    expect(texts(await call("list_cc5_windows", { screenshot: false }))).toBe("Failed: no Qt application");
    expect(bridge.uiWindows).toHaveBeenCalledWith({ screenshot: false });
  });
});

describe("find_ui_widgets", () => {
  it("needs a filter", async () => {
    expect(texts(await call("find_ui_widgets", { visible_only: false }))).toContain("give object_name");
    expect(bridge.uiWidgets).not.toHaveBeenCalled();
  });

  it("lists matches with their state and parent chain", async () => {
    bridge.uiWidgets.mockResolvedValue({
      success: true,
      count: 3,
      shown: 1,
      widgets: [{ object_name: "qtSpinBox", class: "QSpinBox", visible: true, enabled: true, value: 40, path: "qtBlendOpacityHorizontalSliderEx < MixSubstancePanel" }],
    });
    const text = texts(await call("find_ui_widgets", { object_name: "qtSpinBox" }));
    expect(text).toContain("qtSpinBox <QSpinBox> value=40 visible enabled");
    expect(text).toContain("(in: qtBlendOpacityHorizontalSliderEx < MixSubstancePanel)");
    expect(text).toContain("3 match");
  });

  it("formats empty and failed answers", () => {
    expect(formatWidgets({ success: true, widgets: [] })).toBe("No widget matches.");
    expect(formatWidgets({ success: false, error: "boom" })).toBe("Failed: boom");
    expect(formatWidgets({
      success: true,
      widgets: [{ object_name: "", class: "QCheckBox", visible: false, enabled: false, text: "Activate Editor", checked: true, current_text: "x", path: "" }],
    })).toContain("(no name) <QCheckBox> text='Activate Editor' current='x' checked=true hidden disabled  (in: top level)");
  });
});

describe("capture_framed_crop", () => {
  it("renders, cuts and returns the crop as an image", async () => {
    bridge.uiCaptureCrop.mockResolvedValue({ success: true, job_id: "crop-1" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: { success: true, view: "face", full_path: "D:/t/full.png", render_size: [3600, 3600], crop_path: "D:/t/crop.png", crop_box: [1230, 1610, 2190, 1930], crop_size: [960, 320], png_base64: "UE5H" },
    });
    const result = await call("capture_framed_crop", { crop: [1230, 1610, 2190, 1930], output_path: "D:/t/crop.png" });
    expect(bridge.uiCaptureCrop).toHaveBeenCalledWith({ crop: [1230, 1610, 2190, 1930], output_path: "D:/t/crop.png" });
    const text = texts(result);
    expect(text).toContain("Rendered the 'face' view at 3600x3600 px");
    expect(text).toContain("Cut box 1230, 1610, 2190, 1930 (960x320 px)");
    expect(text).toContain("on the machine CC5 runs on");
    expect(images(result)).toHaveLength(1);
  });

  it("without a box it tells how to measure one", () => {
    expect(formatCropResult({ success: true, view: "face", full_path: "x.png", render_size: [3600, 3600] })).toContain("measure the part you want");
  });

  it("refuses both boxes, bad paths and non-png paths before the bridge", async () => {
    expect(texts(await call("capture_framed_crop", { crop: [0, 0, 1, 1], crop_fraction: [0, 0, 1, 1] }))).toContain("not both");
    expect(texts(await call("capture_framed_crop", { output_path: "C:/a/../b.png" }))).toContain("traversal");
    expect(texts(await call("capture_framed_crop", { full_path: "C:/a/b.jpg" }))).toContain(".png");
    expect(bridge.uiCaptureCrop).not.toHaveBeenCalled();
  });

  it("schema: size and box shape", () => {
    const shape = server.tool.mock.calls.find((c: unknown[]) => c[0] === "capture_framed_crop")[2];
    expect(shape.size.safeParse(100).success).toBe(false);
    expect(shape.size.safeParse(3600).success).toBe(true);
    expect(shape.crop.safeParse([1, 2, 3]).success).toBe(false);
    expect(shape.view.safeParse("dolly").success).toBe(false);
  });

  it("shows failures and refusals", async () => {
    bridge.uiCaptureCrop.mockResolvedValueOnce({ success: false, error: "another UI job is still running" });
    expect(texts(await call("capture_framed_crop", {}))).toContain("another UI job is still running");
    bridge.uiCaptureCrop.mockResolvedValueOnce({ success: true, job_id: "crop-2" });
    bridge.uiWaitJob.mockResolvedValueOnce({ finished: true, result: { success: false, error: "RenderImage failed" } });
    const result = await call("capture_framed_crop", {});
    expect(texts(result)).toBe("Failed: RenderImage failed");
    expect(images(result)).toHaveLength(0);
    bridge.uiCaptureCrop.mockResolvedValueOnce({ success: true, job_id: "crop-3" });
    bridge.uiWaitJob.mockResolvedValueOnce({ finished: false, status: { success: true, state: "running" } });
    expect(texts(await call("capture_framed_crop", {}))).toContain("Still running after 180s");
  });
});

describe("ui-common helpers", () => {
  it("pathProblem catches traversal and null bytes only", () => {
    expect(pathProblem("C:\\a\\..\\b")).toContain("traversal");
    expect(pathProblem("a/b\0c")).toContain("null byte");
    expect(pathProblem("C:/ok/file..name.png")).toBeUndefined();
    expect(pathProblem("C:/ok/file.png")).toBeUndefined();
  });

  it("describeWindow lists check boxes and flags", () => {
    const text = describeWindow({
      title: "", text: "t".repeat(300), buttons: [], checkboxes: [{ text: "Restore neutral lash strip", checked: true }], blocked_reason: "no 'replace' button",
    });
    expect(text.startsWith("'(no title)'")).toBe(true);
    expect(text).toContain("buttons: (none)");
    expect(text).toContain("Restore neutral lash strip=on");
    expect(text).toContain("not answered: no 'replace' button");
    expect(text.length).toBeLessThan(400);
  });

  it("windowImages keeps at most three PNGs", () => {
    const wins = Array.from({ length: 5 }, (_, i) => ({ title: String(i), text: "", buttons: [], png_base64: "X" }));
    expect(windowImages(wins)).toHaveLength(3);
    expect(windowImages(undefined)).toEqual([]);
  });

  it("stillRunningText lists the open windows", () => {
    expect(stillRunningText("j1", 60, [{ title: "Baking", text: "wait", buttons: [] }])).toContain("- 'Baking'");
  });

  it("runUiJob stops at a refusal and passes the timeout to the wait", async () => {
    const refused = await runUiJob(bridge as never, async () => ({ success: false, error: "busy" }), 10);
    expect(refused).toEqual({ refused: { success: false, error: "busy" } });
    bridge.uiWaitJob.mockResolvedValue({ finished: true, result: { success: true } });
    const run = await runUiJob(bridge as never, async () => ({ success: true, job_id: "j9" }), 10, { intervalMs: 5 });
    expect(run).toMatchObject({ jobId: "j9" });
    expect(bridge.uiWaitJob).toHaveBeenCalledWith("j9", { timeoutMs: 10_000, intervalMs: 5 });
  });
});

describe("bridgeCallRich", () => {
  it("returns the formatter's blocks, awaiting it", async () => {
    const result = await bridgeCallRich(() => Promise.resolve(2), async (n) => [{ type: "text", text: `n=${n}` }]);
    expect(result.content).toEqual([{ type: "text", text: "n=2" }]);
  });

  it("turns a rejection into one readable text block", async () => {
    const result = await bridgeCallRich(() => Promise.reject(new Error("tunnel down")), () => []);
    expect(result.content[0]).toEqual({ type: "text", text: expect.stringContaining("CC5 bridge error: tunnel down") });
  });

  it("turns a formatter failure into the same text block", async () => {
    const result = await bridgeCallRich(() => Promise.resolve(1), () => { throw new Error("bad format"); });
    expect(result.content[0]).toEqual({ type: "text", text: expect.stringContaining("bad format") });
  });
});
