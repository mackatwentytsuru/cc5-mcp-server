/**
 * Scene and avatar management tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";

export function registerSceneTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "list_avatars",
    "List all avatars (characters) currently in the CC5 scene.",
    {},
    async () => {
      const avatars = await bridge.getAvatars();
      return {
        content: [{
          type: "text" as const,
          text: avatars.length > 0
            ? `Found ${avatars.length} avatar(s):\n${avatars.map(a => `- ${a.name} (ID: ${a.id})`).join("\n")}`
            : "No avatars in the current scene.",
        }],
      };
    }
  );

  server.tool(
    "get_avatar_info",
    "Get detailed information about the current avatar, including all non-zero morph values. Useful for understanding the character's current state.",
    {},
    async () => {
      const info = await bridge.getAvatarInfo();
      if (!info) {
        return {
          content: [{ type: "text" as const, text: "No avatar in the scene." }],
        };
      }

      const morphCount = Object.keys(info.active_morphs).length;
      let text = `Avatar: ${info.name}\n`;
      text += `Active morphs (${morphCount}):\n`;
      for (const [id, value] of Object.entries(info.active_morphs)) {
        text += `  ${id}: ${value}\n`;
      }
      return { content: [{ type: "text" as const, text }] };
    }
  );

  server.tool(
    "check_cc5_connection",
    "Check if CC5 is running and the bridge plugin is active.",
    {},
    async () => {
      const connected = await bridge.healthCheck();
      return {
        content: [{
          type: "text" as const,
          text: connected
            ? "CC5 bridge is connected and ready."
            : "CC5 bridge is NOT responding. Make sure Character Creator 5 is running with the MCP Bridge plugin loaded.",
        }],
      };
    }
  );

  server.tool(
    "set_subdivision_level",
    "Set the HD subdivision level for the current avatar. Level 0 = base mesh, 1 = medium detail, 2 = highest detail (HD morphs).",
    {
      level: z.number().int().min(0).max(2).describe("Subdivision level: 0 (base), 1 (medium), 2 (HD)"),
    },
    async ({ level }) => {
      const result = await bridge.setSubdivisionLevel(level);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `Subdivision level set to ${level}`
            : `Failed: ${result.error}`,
        }],
      };
    }
  );
}
