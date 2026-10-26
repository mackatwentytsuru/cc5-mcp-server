/**
 * Notice windows from inside CC5 (list_cc5_windows) and find widgets (find_ui_widgets).
 * Both are read-only. They read CC5's own Qt windows through the bridge, so they work when CC5 runs
 * on another machine (an ssh tunnel), where the desktop-based list_dialogs cannot see the screen.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { UiWidgetsResult, UiWindowsResult } from "../types.js";
import { bridgeCall, bridgeCallRich, textContent, type ToolContent } from "../util.js";
import { describeWindow, failureContent, windowImages } from "./ui-common.js";

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
    bits.push(w.visible ? "visible" : "hidden", w.enabled ? "enabled" : "disabled");
    return `- ${bits.join(" ")}  (in: ${w.path || "top level"})`;
  });
  const more = (result.count ?? widgets.length) > widgets.length ? `\n(${result.count} match; raise limit or narrow the filter)` : "";
  return `${widgets.length} widget(s):\n${lines.join("\n")}${more}`;
}

export function registerUiWindowTools(server: McpServer, bridge: CC5Bridge): void {
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
