/**
 * Scene and avatar management tools for CC5.
 */

import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

function validateCapturePath(filePath: string): string | null {
  if (filePath.includes("..")) {
    return "Path traversal ('..') is not allowed";
  }
  const normalized = path.resolve(filePath);
  if (!normalized.toLowerCase().endsWith(".png")) {
    return "Output path must end with .png";
  }
  return null;
}

export function registerSceneTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "list_avatars",
    "List all avatars (characters) currently in the CC5 scene.",
    {},
    async () => bridgeCall(
      () => bridge.getAvatars(),
      (avatars) => avatars.length > 0
        ? `Found ${avatars.length} avatar(s):\n${avatars.map(a => `- ${a.name} (ID: ${a.id})`).join("\n")}`
        : "No avatars in the current scene.",
    )
  );

  server.tool(
    "get_avatar_info",
    "Get detailed information about the current avatar, including all non-zero morph values. Useful for understanding the character's current state.",
    {},
    async () => bridgeCall(
      () => bridge.getAvatarInfo(),
      (info) => {
        if (!info) return "No avatar in the scene.";
        const morphCount = Object.keys(info.active_morphs).length;
        let text = `Avatar: ${info.name}\nActive morphs (${morphCount}):\n`;
        for (const [id, value] of Object.entries(info.active_morphs)) {
          text += `  ${id}: ${value}\n`;
        }
        return text;
      },
    )
  );

  server.tool(
    "check_cc5_connection",
    "Check if CC5 is running and the bridge plugin is active.",
    {},
    async () => {
      try {
        const connected = await bridge.healthCheck();
        return {
          content: [{
            type: "text" as const,
            text: connected
              ? "CC5 bridge is connected and ready."
              : "CC5 bridge is NOT responding. Make sure Character Creator 5 is running with the MCP Bridge plugin loaded.",
          }],
        };
      } catch {
        return {
          content: [{
            type: "text" as const,
            text: "CC5 bridge is NOT responding. Make sure Character Creator 5 is running with the MCP Bridge plugin loaded.",
          }],
        };
      }
    }
  );

  server.tool(
    "create_avatar",
    "Create a new default avatar in the CC5 scene. Adds a CC3+ base avatar without clearing the existing scene.",
    {},
    async () => bridgeCall(
      () => bridge.createDefaultAvatar(),
      (result) => result.success
        ? `Created avatar '${result.name ?? "Unknown"}'`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "capture_viewport",
    "Capture a screenshot of the CC5 3D viewport. Returns the image file path. Use this to see the current character appearance.",
    {
      output_path: z.string().optional().describe("Output PNG file path. Defaults to a temp file if omitted."),
    },
    async ({ output_path }) => {
      if (output_path) {
        const pathError = validateCapturePath(output_path);
        if (pathError) {
          return { content: [{ type: "text" as const, text: pathError }] };
        }
      }
      try {
        const result = await bridge.captureViewport(output_path);
        let imgPath = result.path;
        let base64Data = result.base64;

        // Return a clear failure message if the bridge reported an error
        if (!result.success) {
          return { content: [{ type: "text" as const, text: `Failed: ${result.error}` }] };
        }

        // Fallback: if RenderImage succeeded but returned no image data, use Windows screenshot
        if (!base64Data) {
          const fallbackPath = output_path ?? path.join(os.tmpdir(), "cc5_viewport.png");
          try {
            const psCmd = `Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $s=[System.Windows.Forms.Screen]::PrimaryScreen; $b=New-Object System.Drawing.Bitmap($s.Bounds.Width,$s.Bounds.Height); $g=[System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($s.Bounds.Location,[System.Drawing.Point]::Empty,$s.Bounds.Size); $b.Save('${fallbackPath.replace(/\\/g, "/")}'); $g.Dispose(); $b.Dispose()`;
            execSync(`powershell -Command "${psCmd}"`, { timeout: 15000 });
            if (fs.existsSync(fallbackPath)) {
              const data = fs.readFileSync(fallbackPath);
              base64Data = data.toString("base64");
              imgPath = fallbackPath;
            }
          } catch {
            // Fallback also failed
          }
        }

        const content: Array<{ type: "text"; text: string } | { type: "image"; data: string; mimeType: string }> = [];
        if (base64Data) {
          content.push({ type: "image" as const, data: base64Data, mimeType: "image/png" });
          content.push({ type: "text" as const, text: `Viewport captured: ${imgPath ?? "temp file"}` });
        } else {
          content.push({ type: "text" as const, text: "Failed to capture viewport via both RenderImage and screen capture." });
        }
        return { content };
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        return { content: [{ type: "text" as const, text: `CC5 bridge error: ${message}` }] };
      }
    }
  );

  server.tool(
    "set_subdivision_level",
    "Set the HD subdivision level for the current avatar. Level 0 = base mesh, 1 = medium detail, 2 = highest detail (HD morphs).",
    {
      level: z.number().int().min(0).max(2).describe("Subdivision level: 0 (base), 1 (medium), 2 (HD)"),
    },
    async ({ level }) => bridgeCall(
      () => bridge.setSubdivisionLevel(level),
      (result) => result.success ? `Subdivision level set to ${level}` : `Failed: ${result.error}`,
    )
  );
}
