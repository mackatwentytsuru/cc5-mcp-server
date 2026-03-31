/**
 * Morph adjustment tools for CC5.
 * Controls facial features, body shape, and other character morphs.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";

export function registerMorphTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "adjust_morph",
    "Adjust a single morph slider on the current character. Use get_morph_catalog first to discover available morph IDs.",
    {
      morph_id: z.string().describe("The morph slider ID (e.g., 'Fat', 'Head_Narrow', 'Nose_Size')"),
      value: z.number().min(0).max(1).describe("Morph value between 0.0 (none) and 1.0 (maximum)"),
    },
    async ({ morph_id, value }) => {
      const result = await bridge.setMorph(morph_id, value);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `Set morph '${morph_id}' to ${value}`
            : `Failed: ${result.error}`,
        }],
      };
    }
  );

  server.tool(
    "adjust_multiple_morphs",
    "Adjust multiple morph sliders at once. More efficient than calling adjust_morph repeatedly. Use for batch character modifications.",
    {
      morphs: z.array(z.object({
        id: z.string().describe("Morph slider ID"),
        value: z.number().min(0).max(1).describe("Value 0.0-1.0"),
      })).describe("Array of morph adjustments to apply simultaneously"),
    },
    async ({ morphs }) => {
      const result = await bridge.setMultipleMorphs(morphs);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `Applied ${morphs.length} morph adjustments`
            : `Failed: ${result.error}`,
        }],
      };
    }
  );

  server.tool(
    "get_morph_value",
    "Get the current value of a specific morph slider.",
    {
      morph_id: z.string().describe("The morph slider ID to query"),
    },
    async ({ morph_id }) => {
      const value = await bridge.getMorphValue(morph_id);
      return {
        content: [{
          type: "text" as const,
          text: value !== null
            ? `Morph '${morph_id}' current value: ${value}`
            : `Could not get morph value for '${morph_id}'`,
        }],
      };
    }
  );
}
