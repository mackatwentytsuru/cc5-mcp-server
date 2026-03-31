/**
 * Asset loading and export tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";

export function registerAssetTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "load_asset",
    "Load a CC5 asset file into the scene. Supports .iAvatar, .ccm (character), .iClothes (clothing), .iHair (hair), .iProp (prop), and other CC5 formats.",
    {
      file_path: z.string().describe("Absolute path to the CC5 asset file (e.g., 'C:/Assets/MyChar.iAvatar')"),
    },
    async ({ file_path }) => {
      const result = await bridge.loadAsset(file_path);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `Asset loaded: ${file_path}`
            : `Failed to load asset: ${result.error}`,
        }],
      };
    }
  );

  server.tool(
    "export_fbx",
    "Export the current avatar as an FBX file. Use this after completing character adjustments to save the result for game engines or other 3D applications.",
    {
      output_path: z.string().describe("Absolute path for the exported FBX file (e.g., 'C:/Export/character.fbx')"),
    },
    async ({ output_path }) => {
      const result = await bridge.exportFbx(output_path);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `FBX exported to: ${output_path}`
            : `Export failed: ${result.error}`,
        }],
      };
    }
  );
}
