/**
 * click_ui_button: forwards to /ui/click, waits for the job, shows the result, the window picture and the
 * dialogs. What may be pressed is decided by the bridge (tests/python/test_ui_click.py).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerUiClickTools, formatClickResult } from "../../src/tools/ui-click.js";
import { createMockServer } from "../helpers/mock-server.js";

function makeBridge() {
  return { uiClick: vi.fn(), uiWaitJob: vi.fn() };
}

let bridge: ReturnType<typeof makeBridge>;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = makeBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerUiClickTools(server as any, bridge as any);
});

const call = (args: Record<string, unknown>) => server.getRegisteredTool("click_ui_button")(args);
const texts = (result: { content: Array<{ type: string; text?: string }> }) =>
  result.content.filter((c) => c.type === "text").map((c) => c.text).join("\n");
const images = (result: { content: Array<{ type: string }> }) => result.content.filter((c) => c.type === "image");
const schema = () => server.tool.mock.calls.find((c: unknown[]) => c[0] === "click_ui_button")[2];

describe("click_ui_button – registration", () => {
  it("registers one tool whose description names the refusals", () => {
    expect(server.tool).toHaveBeenCalledTimes(1);
    const description = server.tool.mock.calls[0][1] as string;
    for (const word of ["locked", "points", "purchase", "delete", "licence", "activate", "upgrade", "credit",
      "subscribe", "pay", "ポイント", "購入", "削除", "ライセンス", "クレジット", "支払", "modal", "menu_item"]) {
      expect(description).toContain(word);
    }
  });

  it("schema: window is required, names are bounded, wait_ms is 200-15000", () => {
    const shape = schema();
    expect(shape.window.safeParse("").success).toBe(false);
    expect(shape.window.safeParse("Body Wrap").success).toBe(true);
    expect(shape.text.safeParse("x".repeat(257)).success).toBe(false);
    expect(shape.wait_ms.safeParse(100).success).toBe(false);
    expect(shape.wait_ms.safeParse(15001).success).toBe(false);
    expect(shape.wait_ms.safeParse(2000).success).toBe(true);
  });
});

describe("click_ui_button – calls", () => {
  it("needs object_name or text before anything is sent", async () => {
    expect(texts(await call({ window: "Body Wrap" }))).toContain("give object_name or text");
    expect(bridge.uiClick).not.toHaveBeenCalled();
  });

  it("presses, waits for the job and returns the text, the window picture and the dialog pictures", async () => {
    bridge.uiClick.mockResolvedValue({ success: true, job_id: "click-1" });
    bridge.uiWaitJob.mockResolvedValue({
      finished: true,
      result: {
        success: true, window: "Body Wrap", click_returned: false,
        pressed: { text: "", object_name: "qtSkeletonFileButton", menu_item: "Save Skeleton" },
        note: "the click has not returned yet: CC5 is showing a window it opened (see dialogs)",
        window_open: true, png_base64: "V0lO",
        dialogs: [{ title: "Save Skeleton", text: "File name?", buttons: ["Save", "Cancel"], png_base64: "RElB" }],
      },
    });
    const args = { window: "Body Wrap", object_name: "qtSkeletonFileButton", menu_item: "Save Skeleton", wait_ms: 1500 };
    const result = await call(args);
    expect(bridge.uiClick).toHaveBeenCalledWith(args);
    expect(bridge.uiWaitJob).toHaveBeenCalledWith("click-1", { timeoutMs: 62_000 });
    const text = texts(result);
    expect(text).toContain("Pressed the menu entry 'Save Skeleton' of the button (no text) [qtSkeletonFileButton] in 'Body Wrap'.");
    expect(text).toContain("has not returned yet");
    expect(text).toContain("Open dialogs after the click (none was answered):");
    expect(text).toContain("- 'Save Skeleton': File name? | buttons: Save | Cancel");
    expect(images(result)).toEqual([
      { type: "image", data: "V0lO", mimeType: "image/png" },
      { type: "image", data: "RElB", mimeType: "image/png" },
    ]);
  });

  it("shows CC5's refusal as it is (nothing was pressed)", async () => {
    bridge.uiClick.mockResolvedValue({
      success: false,
      error: "refused: the button 'Generate Wrap Points' [qtGen] mentions 'point'. ... Ask the owner",
    });
    const text = texts(await call({ window: "Body Wrap", text: "Generate Wrap Points" }));
    expect(text).toBe("Failed: refused: the button 'Generate Wrap Points' [qtGen] mentions 'point'. ... Ask the owner");
    expect(bridge.uiWaitJob).not.toHaveBeenCalled();
  });

  it("reports a job that failed inside CC5 and a job that is still running", async () => {
    bridge.uiClick.mockResolvedValue({ success: true, job_id: "click-2" });
    bridge.uiWaitJob.mockResolvedValueOnce({
      finished: true,
      result: { success: false, error: "the button 'Paste' [qtPaste] is disabled (greyed out)" },
    });
    const failed = await call({ window: "Headshot", text: "Paste" });
    expect(texts(failed)).toBe("Failed: the button 'Paste' [qtPaste] is disabled (greyed out)");
    expect(images(failed)).toHaveLength(0);
    bridge.uiWaitJob.mockResolvedValueOnce({ finished: false, status: { success: true, state: "running" } });
    expect(texts(await call({ window: "Headshot", text: "Paste" }))).toContain("Still running after 61s (job click-2)");
  });

  it("turns a lost bridge into one readable text", async () => {
    bridge.uiClick.mockRejectedValue(new Error("tunnel down"));
    expect(texts(await call({ window: "Headshot", text: "Paste" }))).toContain("CC5 bridge error: tunnel down");
  });
});

describe("formatClickResult", () => {
  it("toggle state, hidden duplicates, a closed window and a missing picture", () => {
    const text = formatClickResult({
      success: true, window: "Modify", pressed: { text: "Show Mesh", object_name: "qtShowMesh" },
      checked_before: false, checked_after: true, hidden_skipped: 2, window_open: false,
      screenshot_error: "grab returned an empty image", dialogs: [],
    });
    expect(text).toContain("Pressed the button 'Show Mesh' [qtShowMesh] in 'Modify'.");
    expect(text).toContain("Checked before: false, after: true.");
    expect(text).toContain("2 hidden button(s)");
    expect(text).toContain("The window closed after the click.");
    expect(text).toContain("No picture of the window: grab returned an empty image");
    expect(text).toContain("Open dialogs after the click: none.");
  });

  it("a failure without details", () => {
    expect(formatClickResult({ success: false })).toBe("Failed: the click did not happen");
  });
});
