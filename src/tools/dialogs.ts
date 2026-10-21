/**
 * list_dialogs: show the pop-up windows currently open in CC5 / Reallusion Hub.
 * Read-only. Works while CC5's main thread is blocked.
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { describeDialog, scanDialogs, type DialogWatcher, type ScanFn } from "../dialogs.js";

const MAX_IMAGE_BYTES = 2 * 1024 * 1024;

export function registerDialogTools(server: McpServer, watcher?: DialogWatcher, scan: ScanFn = scanDialogs) {
  server.tool(
    "list_dialogs",
    "List the dialogs / pop-up windows currently open in Character Creator 5 and Reallusion Hub " +
      "(title, body text, button labels, process, foreground) and optionally capture an image of each. " +
      "Works even when CC5's main thread is blocked by a modal dialog (so other tools hang). " +
      "READ-ONLY: this server has no tool that clicks dialogs; agreements, purchases, logins, updates, " +
      "deletes and overwrites must be decided by a human. Report what you see and ask.",
    { screenshot: z.boolean().optional().describe("Also capture a PNG of each dialog (default true)") },
    async (args: { screenshot?: boolean }) => {
      const wantShot = args?.screenshot !== false;
      try {
        const result = await scan(wantShot);
        watcher?.update(result.dialogs);
        if (result.dialogs.length === 0) {
          return { content: [{ type: "text" as const, text: "CC5 / Reallusion Hub に開いている小窓はありません。" }] };
        }
        const content: Array<{ type: "text"; text: string } | { type: "image"; data: string; mimeType: string }> = [];
        const lines = result.dialogs.map(
          (d, i) => `${i + 1}. ${describeDialog(d)}${d.screenshot ? `\n   画像: ${d.screenshot}` : ""}`,
        );
        content.push({ type: "text" as const, text: `開いている小窓: ${result.dialogs.length}件\n${lines.join("\n")}` });
        const tmpRoot = path.resolve(os.tmpdir()).toLowerCase();
        for (const d of result.dialogs) {
          if (!d.screenshot) continue;
          const resolved = path.resolve(d.screenshot);
          // Only read files the probe wrote into the temp dir.
          if (!resolved.toLowerCase().startsWith(tmpRoot)) continue;
          try {
            if (fs.statSync(resolved).size > MAX_IMAGE_BYTES) continue;
            content.push({ type: "image" as const, data: fs.readFileSync(resolved).toString("base64"), mimeType: "image/png" });
          } catch {
            /* screenshot is best-effort */
          }
        }
        return { content };
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { content: [{ type: "text" as const, text: `小窓の検出に失敗しました: ${message}` }] };
      }
    },
  );
}
