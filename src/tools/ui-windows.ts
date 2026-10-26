/**
 * Notice windows from inside CC5 (list_cc5_windows) and find widgets (find_ui_widgets).
 * Both are read-only. They read CC5's own Qt windows through the bridge, so they work when CC5 runs
 * on another machine (an ssh tunnel), where the desktop-based list_dialogs cannot see the screen.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { UiJobStatus, UiWidgetsResult, UiWindowsResult } from "../types.js";
import { bridgeCall, bridgeCallRich, textContent, type ToolContent } from "../util.js";
import { describeWindow, failureContent, openWindowShots, windowImages, type WaitOptions } from "./ui-common.js";

const RESULT_CHARS = 3500;

export function formatWidgets(result: UiWidgetsResult): string {
  if (!result.success) return `Failed: ${result.error}`;
  const widgets = result.widgets ?? [];
  if (widgets.length === 0) return "No widget matches.";
  const lines = widgets.map((w) => {
    const bits = [`${w.object_name || "(no name)"} <${w.class}>`];
    if (w.text !== undefined) bits.push(`text='${w.text}'`);
    if (w.current_text !== undefined) bits.push(`current='${w.current_text}'`);
    if (w.value !== undefined) bits.push(`value=${w.value}`);
    if (w.checked !== undefined) bits.push(`checked=${w.checked}`);
    if (w.text_hidden) bits.push("(typed text is never shown)");
    bits.push(w.visible ? "visible" : "hidden", w.enabled ? "enabled" : "disabled");
    return `- ${bits.join(" ")}  (in: ${w.path || "top level"})`;
  });
  const more = (result.count ?? widgets.length) > widgets.length ? `\n(${result.count} match; raise limit or narrow the filter)` : "";
  return `${widgets.length} widget(s):\n${lines.join("\n")}${more}`;
}

/** A job status as text: state, then the result as compact JSON (pictures left out). */
export function formatJobStatus(status: UiJobStatus): string {
  if (!status.success && !status.state) return `Failed: ${status.error ?? "unknown job"}`;
  const head = `Job ${status.job_id} (${status.kind}): ${status.state}${status.elapsed_s !== undefined ? `, ${status.elapsed_s}s` : ""}`;
  if (status.state === "queued" || status.state === "running") {
    const open = (status.windows ?? []).map((w) => `  - ${describeWindow(w)}`).join("\n");
    return `${head}${open ? `\nOpen windows:\n${open}` : ""}`;
  }
  const json = JSON.stringify(status.result, (key, value) => (key === "png_base64" ? "(picture omitted)" : value), 1) ?? "null";
  const cut = json.length > RESULT_CHARS ? `${json.slice(0, RESULT_CHARS)}\n... (cut; ${json.length} characters)` : json;
  return `${head}\nResult:\n${cut}`;
}

export function registerUiWindowTools(server: McpServer, bridge: CC5Bridge, wait: WaitOptions = {}): void {
  server.tool(
    "list_cc5_windows",
    "Look at the pop-up / question windows CC5 has open RIGHT NOW, from inside CC5 (Qt): title, text, buttons, " +
      "check boxes, and whether it is a progress window (baking: wait), a known question that apply_preset / " +
      "skingen_editor would answer, or a window that needs a person (licence, purchase, login, update, terms). " +
      "screenshot=true (default) also returns a PNG of each window (QWidget.grab), and target=main adds the main " +
      "window. Read-only: nothing is pressed. Works while a modal question is open, and when CC5 runs on another " +
      "machine behind a tunnel. Complements list_dialogs (which reads the desktop with Windows APIs).",
    {
      screenshot: z.boolean().optional().describe("Return a PNG of each window (default true)"),
      target: z.enum(["dialogs", "main"]).optional().describe("'main' also returns the main window (default dialogs only)"),
      max_width: z.number().int().min(200).max(2400).optional().describe("Scale PNGs down to this width (default 900)"),
      include_other: z.boolean().optional().describe("Also list floating tool windows that are not dialogs"),
    },
    async ({ screenshot, target, max_width, include_other }) =>
      bridgeCallRich(
        () => bridge.uiWindows({
          screenshot: screenshot !== false,
          ...(target ? { target } : {}),
          ...(max_width ? { max_width } : {}),
          ...(include_other ? { include_other } : {}),
        }),
        (result: UiWindowsResult): ToolContent[] => {
          if (!result.success) return failureContent(result.error ?? "could not read the windows");
          const windows = result.windows ?? [];
          const lines = windows.map((w, i) => `${i + 1}. ${describeWindow(w)}`);
          const head = windows.length === 0
            ? "No pop-up windows are open in CC5."
            : `${windows.length} window(s) open in CC5:\n${lines.join("\n")}`;
          const content: ToolContent[] = [textContent(head), ...windowImages(windows)];
          if (result.main_window?.title) content.push(textContent(`Main window: ${result.main_window.title}`));
          if (result.main_window?.png_base64) content.push({ type: "image", data: result.main_window.png_base64, mimeType: "image/png" });
          return content;
        },
      ),
  );

  server.tool(
    "get_ui_job",
    "Look at (or wait for) a UI job that apply_preset, skingen_editor, skingen_layer or capture_framed_crop " +
      "started in CC5. Those tools wait for their job themselves; use this when one said 'Still running' or " +
      "lost contact, with the job id it printed. wait_seconds=0 only reads the state; a larger value waits " +
      "for the job to finish. The job runs on inside CC5 either way. Read-only.",
    {
      job_id: z.string().min(1).max(64).describe("The job id, e.g. 'preset-3'"),
      wait_seconds: z.number().int().min(0).max(900).optional().describe("Seconds to wait for it to finish (default 0)"),
    },
    async ({ job_id, wait_seconds }) =>
      bridgeCallRich(async (): Promise<ToolContent[]> => {
        if (!wait_seconds) return [textContent(formatJobStatus(await bridge.uiJob(job_id)))];
        const outcome = await bridge.uiWaitJob(job_id, { timeoutMs: wait_seconds * 1000, ...wait });
        const status = outcome.status;
        if (!status) return [textContent(`Job ${job_id}: no answer from CC5 within ${wait_seconds}s`)];
        const content = [textContent(formatJobStatus(status))];
        if (!outcome.finished) content.push(...(await openWindowShots(bridge)));
        return content;
      }, (content) => content),
  );

  server.tool(
    "find_ui_widgets",
    "Find widgets of CC5's own interface by objectName / class / text (read-only; for building new " +
      "automation). Returns each match's name, class, text, value, checked state and parent chain. Needs at " +
      "least one of object_name (exact), name_contains, class_name, text_contains. Hidden widgets are skipped " +
      "unless visible_only=false (the Modify panel counts as hidden while the Render tab is in front). " +
      "Known SkinGen names: qtModeSwitchPushButton, qtFeatureTableWidget, qtEnableToolButton, " +
      "qtBlendOpacityHorizontalSliderEx, qtSpinBox, qtDeleteToolButton.",
    {
      object_name: z.string().min(1).max(128).optional().describe("Exact objectName"),
      name_contains: z.string().min(1).max(128).optional().describe("Part of the objectName"),
      class_name: z.string().min(1).max(128).optional().describe("Qt class, e.g. QSpinBox"),
      text_contains: z.string().min(1).max(128).optional().describe("Part of the widget text"),
      ancestor: z.string().min(1).max(128).optional().describe("objectName or class of a parent"),
      visible_only: z.boolean().optional().describe("Skip hidden widgets (default true)"),
      limit: z.number().int().min(1).max(200).optional().describe("Most widgets to return (default 50)"),
    },
    async (args) => {
      if (!args.object_name && !args.name_contains && !args.class_name && !args.text_contains) {
        return { content: failureContent("give object_name, name_contains, class_name or text_contains") };
      }
      return bridgeCall(() => bridge.uiWidgets(args), formatWidgets);
    },
  );
}
