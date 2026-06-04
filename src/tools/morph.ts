/**
 * Morph adjustment tools for CC5.
 * Controls facial features, body shape, and other character morphs.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerMorphTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "search_morphs",
    "Search the morph catalog by keyword. Much faster than downloading the full catalog. Use this to find morph IDs for specific features (e.g., 'nose', 'eye', 'jaw').",
    {
      query: z.string().max(256).describe("Search keyword (e.g., 'nose', 'eye size', 'jaw', 'fat')"),
      category: z.string().max(256).optional().describe("Optional category filter (e.g., 'Body', 'Head')"),
    },
    async ({ query, category }) => bridgeCall(
      () => bridge.searchMorphs(query, category),
      (results) => results.length > 0
        ? `Found ${results.length} morph(s):\n${results.map(r => `- ${r.display_name} (ID: ${r.id})`).join("\n")}`
        : `No morphs found matching '${query}'`,
    )
  );

  server.tool(
    "adjust_morph",
    "Adjust a single morph slider on the current character. Use get_morph_catalog first to discover available morph IDs.",
    {
      morph_id: z.string().describe("The morph slider ID (e.g., 'Fat', 'Head_Narrow', 'Nose_Size')"),
      value: z.number().min(-1).max(1).describe("Morph value between -1.0 and 1.0. Negative values shrink features."),
    },
    async ({ morph_id, value }) => bridgeCall(
      () => bridge.setMorph(morph_id, value),
      (result) => result.success ? `Set morph '${morph_id}' to ${value}` : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "adjust_multiple_morphs",
    "Adjust multiple morph sliders at once. More efficient than calling adjust_morph repeatedly. Use for batch character modifications.",
    {
      morphs: z.array(z.object({
        morph_id: z.string().max(256).describe("Morph slider ID"),
        value: z.number().min(-1).max(1).describe("Value -1.0 to 1.0"),
      })).max(500).describe("Array of morph adjustments (max 500)"),
    },
    async ({ morphs }) => bridgeCall(
      () => bridge.setMultipleMorphs(morphs),
      (result) => result.success ? `Applied ${morphs.length} morph adjustments` : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "get_morph_value",
    "Get the current value of a specific morph slider.",
    {
      morph_id: z.string().describe("The morph slider ID to query"),
    },
    async ({ morph_id }) => bridgeCall(
      () => bridge.getMorphValue(morph_id),
      (value) => value !== null
        ? `Morph '${morph_id}' current value: ${value}`
        : `Could not get morph value for '${morph_id}'`,
    )
  );

  server.tool(
    "reset_morphs",
    "Reset all morph sliders to zero for the current avatar (or a named avatar). Useful for starting fresh with character customization.",
    {
      avatar_name: z.string().max(256).optional().describe("Name of the avatar to reset. Defaults to the first avatar if omitted."),
    },
    async ({ avatar_name }) => bridgeCall(
      () => bridge.resetAllMorphs(avatar_name),
      (result) => result.success
        ? `Reset ${result.reset_count ?? 0} morph(s) to zero`
        : `Failed: ${result.error}`,
    )
  );
}
