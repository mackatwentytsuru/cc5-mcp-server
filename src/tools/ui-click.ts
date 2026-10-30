/**
 * click_ui_button: press ONE named button of a CC5 window from inside CC5 (Qt click(), no mouse).
 *
 * Made on 2026-10-30: while the Windows screen is locked, mouse clicks do nothing (a worker could not press
 * Body Wrap's "Save Skeleton" and the owner's hand-fixed points were lost), but Qt's click() still works.
 * What may be pressed is decided by the bridge (cc5-plugin/cc5_uiclick.py), because any local program can
 * call it; this tool only forwards the request and shows the answer, the window picture and the dialogs.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { UiClickArgs, UiClickResult } from "../types.js";
import { bridgeCallRich, pngContent, textContent, type ToolContent } from "../util.js";
import { describeWindow, failureContent, refusedContent, runUiJob, stillRunningText, windowImages, type WaitOptions } from "./ui-common.js";

const DEFAULT_WAIT_MS = 1000;
const EXTRA_WAIT_SECONDS = 60;

const nameField = z.string().min(1).max(256);

function pressedText(result: UiClickResult): string {
  const p = result.pressed ?? {};
  const button = [p.text ? `'${p.text}'` : "(no text)", p.object_name ? `[${p.object_name}]` : ""].filter(Boolean).join(" ");
  return p.menu_item ? `the menu entry '${p.menu_item}' of the button ${button}` : `the button ${button}`;
}

export function formatClickResult(result: UiClickResult): string {
  const lines: string[] = [];
  if (result.success) {
    lines.push(`Pressed ${pressedText(result)} in '${result.window ?? "?"}'.`);
  } else {
    lines.push(`Failed: ${result.error ?? "the click did not happen"}`);
  }
  if (result.note) lines.push(result.note);
  if (result.checked_before !== undefined) {
    lines.push(`Checked before: ${result.checked_before}, after: ${result.checked_after}.`);
  }
  if (result.hidden_skipped) lines.push(`(${result.hidden_skipped} hidden button(s) with the same name were left alone.)`);
  if (result.window_open === false) lines.push("The window closed after the click.");
  if (result.screenshot_error) lines.push(`No picture of the window: ${result.screenshot_error}`);
  const dialogs = result.dialogs ?? [];
  if (result.window !== undefined || dialogs.length > 0) {
    lines.push(dialogs.length === 0
      ? "Open dialogs after the click: none."
      : `Open dialogs after the click (none was answered):\n${dialogs.map((d) => `  - ${describeWindow(d)}`).join("\n")}`);
  }
  return lines.join("\n");
}

export function registerUiClickTools(server: McpServer, bridge: CC5Bridge, wait: WaitOptions = {}): void {
  server.tool(
    "click_ui_button",
    "Press ONE button of a CC5 window, dialog or dock panel from inside CC5 (Qt click(), no mouse), so it " +
      "works while the Windows screen is locked. Name the window (title, case-insensitive, or objectName) and " +
      "the button (object_name and/or exact text; find names with find_ui_widgets, or list_cc5_windows " +
      "include_other=true for floating tool windows such as Body Wrap). For a button with a drop-down menu " +
      "(like the disk button with Load / Save Skeleton) give menu_item to press one entry. CC5 refuses, and " +
      "presses nothing, when: nothing or more than one VISIBLE button matches; the button or entry is disabled " +
      "or hidden; its text, objectName or tool tip mentions points, buy, purchase, delete, remove, licence, " +
      "activate, upgrade, credit, subscribe, pay (or ポイント 購入 削除 ライセンス クレジット 支払), or login / " +
      "update / terms / trial; a licence / purchase / login window is open; a modal window is open and the " +
      "button is not in it. Waits wait_ms, then returns a picture of the window and the dialogs that are open " +
      "(a window the click opened is never answered: look at it, and ask the owner when it is not routine). " +
      "Do not use it to get past a refusal of another tool.",
    {
      window: nameField.describe("Title (case-insensitive) or objectName of the CC5 window, dialog or dock panel"),
      object_name: nameField.optional().describe("Exact objectName of the button"),
      text: nameField.optional().describe("Exact visible text of the button (case and the & marker are ignored)"),
      menu_item: nameField.optional().describe("Exact text of one entry in the button's own drop-down menu (presses that entry, not the button)"),
      wait_ms: z.number().int().min(200).max(15000).optional().describe(`Wait after the click before the picture (default ${DEFAULT_WAIT_MS})`),
      screenshot: z.boolean().optional().describe("Return a PNG of the window and of each open dialog (default true)"),
      max_width: z.number().int().min(200).max(2400).optional().describe("Scale the window PNG down to this width (default 900)"),
    },
    async (args) => {
      if (!args.object_name && !args.text) {
        return { content: failureContent("give object_name or text (or both) of the button to press") };
      }
      const body: UiClickArgs = { ...args };
      const seconds = Math.ceil((args.wait_ms ?? DEFAULT_WAIT_MS) / 1000) + EXTRA_WAIT_SECONDS;
      return bridgeCallRich(async (): Promise<ToolContent[]> => {
        const run = await runUiJob<UiClickResult>(bridge, () => bridge.uiClick(body), seconds, wait);
        if ("refused" in run) return refusedContent(run.refused);
        if (!run.outcome.finished) return [textContent(stillRunningText(run.jobId, seconds, run.outcome.status))];
        const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
        const content: ToolContent[] = [textContent(formatClickResult(result))];
        if (result.png_base64) content.push(pngContent(result.png_base64));
        content.push(...windowImages(result.dialogs));
        return content;
      }, (content) => content);
    },
  );
}
