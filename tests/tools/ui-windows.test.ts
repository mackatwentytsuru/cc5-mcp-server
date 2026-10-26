/**
 * list_cc5_windows and find_ui_widgets (read-only), plus capture_framed_crop and the shared UI helpers.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerUiWindowTools, formatWidgets, formatJobStatus } from "../../src/tools/ui-windows.js";
import { registerFramedCaptureTools, formatCropResult, fractionProblem } from "../../src/tools/framed-capture.js";
import { describeWindow, pathProblem, windowImages, stillRunningText, runUiJob, refusedContent } from "../../src/tools/ui-common.js";
import { bridgeCallRich } from "../../src/util.js";
import { createMockServer } from "../helpers/mock-server.js";

function makeBridge() {
  return {
    uiWindows: vi.fn(),
    uiWidgets: vi.fn(),
    uiCaptureCrop: vi.fn(),
    uiWaitJob: vi.fn(),
    uiJob: vi.fn(),
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

  it("without a box it shows a preview and how to convert its coordinates", () => {
    const text = formatCropResult({
      success: true, view: "face", full_path: "x.png", render_size: [3600, 3600], preview_size: [1400, 1400], preview_scale: 2.5714,
    });
    expect(text).toContain("scaled-down preview (1400x1400)");
    expect(text).toContain("x 2.5714 = pixels of the full render");
    expect(text).toContain("Measure the part you want");
  });

  it("warns when the box was changed to fit, or the crop cannot be shown", () => {
    const text = formatCropResult(
      { success: true, view: "face", full_path: "x.png", render_size: [3600, 3600], crop_path: "c.png", crop_box: [0, 0, 3600, 100], crop_size: [3600, 100] },
      [0, 0, 4000, 100],
    );
    expect(text).toContain("NOT the same size");
    expect(text).toContain("too large to show here");
  });

  it("checks crop_fraction before the bridge", async () => {
    expect(fractionProblem(undefined)).toBeUndefined();
    expect(fractionProblem([0.1, 0.1, 0.9, 0.9])).toBeUndefined();
    for (const bad of [[0.5, 0, 0.2, 1], [0, 0, 2, 1], [-0.1, 0, 1, 1], [0, 0.5, 1, 0.5]]) {
      expect(fractionProblem(bad)).toContain("crop_fraction must satisfy");
    }
    expect(texts(await call("capture_framed_crop", { crop_fraction: [0.9, 0, 0.1, 1] }))).toContain("crop_fraction must satisfy");
    expect(bridge.uiCaptureCrop).not.toHaveBeenCalled();
  });

  it("refuses the same file for the crop and the full render, and passes the new options", async () => {
    expect(texts(await call("capture_framed_crop", { output_path: "C:/a.png", full_path: "C:/a.png" }))).toContain("different files");
    bridge.uiCaptureCrop.mockResolvedValue({ success: true, job_id: "crop-9" });
    bridge.uiWaitJob.mockResolvedValue({ finished: true, result: { success: true, view: "face", full_path: "f", render_size: [1, 1] } });
    await call("capture_framed_crop", { overwrite: true, avatar_name: "Beyon", size: 3000 });
    expect(bridge.uiCaptureCrop).toHaveBeenCalledWith({ overwrite: true, avatar_name: "Beyon", size: 3000 });
  });

  it("size is capped where Qt can still read the image back", () => {
    const shape = server.tool.mock.calls.find((c: unknown[]) => c[0] === "capture_framed_crop")[2];
    expect(shape.size.safeParse(5601).success).toBe(false);
    expect(shape.size.safeParse(5600).success).toBe(true);
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

  it("windowImages keeps at most three PNGs and says how many it left out", () => {
    const wins = Array.from({ length: 5 }, (_, i) => ({ title: String(i), text: "", buttons: [], png_base64: "X" }));
    const content = windowImages(wins);
    expect(content.filter((c) => c.type === "image")).toHaveLength(3);
    expect(content[3]).toEqual({ type: "text", text: expect.stringContaining("2 more window picture(s)") });
    expect(windowImages(undefined)).toEqual([]);
  });

  it("describeWindow survives a window with missing fields", () => {
    expect(describeWindow({ title: "T" } as never)).toContain("buttons: (none)");
  });

  it("stillRunningText lists the open windows and a lost contact", () => {
    const text = stillRunningText("j1", 60, {
      success: false, error: "lost contact with CC5: socket hang up",
      windows: [{ title: "Baking", text: "wait", buttons: [] }],
    });
    expect(text).toContain("- 'Baking'");
    expect(text).toContain("Last contact failed: lost contact with CC5: socket hang up");
    expect(text).toContain("get_ui_job");
  });

  it("refusedContent separates a busy start from a refusal", () => {
    expect(refusedContent({ success: false, error: "Timeout waiting for CC5 to process command" })[0])
      .toEqual({ type: "text", text: expect.stringContaining("MAY STILL RUN LATER") });
    expect(refusedContent({ success: false, error: "file not found" })[0]).toEqual({ type: "text", text: "Failed: file not found" });
    expect(refusedContent({ success: false })[0]).toEqual({ type: "text", text: expect.stringContaining("refused to start") });
  });

  it("runUiJob turns a lost wait into 'still running' with the job id", async () => {
    bridge.uiWaitJob.mockRejectedValue(new Error("socket hang up"));
    const run = await runUiJob(bridge as never, async () => ({ success: true, job_id: "j7" }), 10);
    expect(run).toEqual({
      jobId: "j7",
      outcome: { finished: false, status: { success: false, error: "lost contact with CC5: socket hang up" } },
    });
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

describe("get_ui_job", () => {
  it("only reads the state when no wait is asked", async () => {
    bridge.uiJob.mockResolvedValue({ success: true, job_id: "preset-3", kind: "preset", state: "running", elapsed_s: 4, windows: [{ title: "Baking", text: "Please wait", buttons: [], progress: true }] });
    const text = texts(await call("get_ui_job", { job_id: "preset-3" }));
    expect(bridge.uiWaitJob).not.toHaveBeenCalled();
    expect(text).toContain("Job preset-3 (preset): running, 4s");
    expect(text).toContain("progress window");
  });

  it("waits when asked and shows the result without pictures", async () => {
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      status: { success: true, job_id: "crop-1", kind: "crop", state: "done", elapsed_s: 12.5, result: { success: true, png_base64: "AAAA", crop_path: "c.png" } },
    });
    const text = texts(await call("get_ui_job", { job_id: "crop-1", wait_seconds: 60 }));
    expect(bridge.uiWaitJob).toHaveBeenCalledWith("crop-1", { timeoutMs: 60_000 });
    expect(text).toContain("Job crop-1 (crop): done, 12.5s");
    expect(text).toContain("(picture omitted)");
    expect(text).not.toContain("AAAA");
  });

  it("shows the windows when the job is still running after the wait", async () => {
    bridge.uiWaitJob.mockResolvedValue({ finished: false, status: { success: true, job_id: "j", kind: "preset", state: "running" } });
    bridge.uiWindows.mockResolvedValue({ success: true, windows: [{ title: "Mystery", text: "?", buttons: ["OK"], png_base64: "UE5H" }] });
    const result = await call("get_ui_job", { job_id: "j", wait_seconds: 5 });
    expect(images(result)).toHaveLength(1);
  });

  it("reports an unknown job and a silent CC5", async () => {
    bridge.uiJob.mockResolvedValue({ success: false, error: "unknown job 'zzz'" });
    expect(texts(await call("get_ui_job", { job_id: "zzz" }))).toBe("Failed: unknown job 'zzz'");
    bridge.uiWaitJob.mockResolvedValue({ finished: false });
    expect(texts(await call("get_ui_job", { job_id: "j", wait_seconds: 5 }))).toContain("no answer from CC5 within 5s");
  });

  it("cuts a very long result", () => {
    const text = formatJobStatus({ success: true, job_id: "j", kind: "k", state: "done", result: { success: true, blob: "x".repeat(9000) } });
    expect(text).toContain("(cut;");
    expect(text.length).toBeLessThan(4000);
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
