/**
 * Expression control tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerExpressionTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "get_expression_info",
    "Get available facial expression groups and slider names for the current avatar. Use this to discover expression controls before adjusting facial animations.",
    {},
    async () => bridgeCall(
      () => bridge.getExpressionInfo(),
      (info) => {
        const groups = Object.keys(info);
        if (groups.length === 0) return "No expression data available.";
        let text = `Expression groups (${groups.length}):\n`;
        for (const group of groups) {
          const names = info[group];
          text += `\n${group} (${names.length}):\n`;
          text += names.map(n => `  - ${n}`).join("\n") + "\n";
        }
        return text;
      },
    )
  );

  server.tool(
    "set_expression",
    "Set one or more facial expression sliders by name (weights 0.0-1.0; e.g. a smile or raised brow). Use get_expression_info first to discover valid slider names. Unknown names are skipped and reported.",
    {
      expressions: z.array(z.object({
        name: z.string().max(128).describe("Expression slider name, e.g. 'Brow_Raise_Inner_L'"),
        weight: z.number().min(0).max(1).describe("Strength 0.0-1.0"),
      })).min(1).max(400).describe("List of expression sliders to set"),
    },
    async ({ expressions }) => bridgeCall(
      () => bridge.setExpression(expressions),
      (result) => {
        if (!result.success) {
          const skipped = result.skipped?.length ? ` (skipped: ${result.skipped.join(", ")})` : "";
          return `Failed: ${result.error}${skipped}`;
        }
        const applied = result.applied ?? [];
        const lines = applied.map(a => `  - ${a.name} = ${a.weight}`);
        const skipped = result.skipped?.length ? `\nSkipped (unknown): ${result.skipped.join(", ")}` : "";
        return `Set ${applied.length} expression slider(s):\n${lines.join("\n")}${skipped}`;
      },
    )
  );

  server.tool(
    "reset_expression",
    "Reset all facial expression sliders to 0 (neutral face). Use after set_expression to clear an expression.",
    {},
    async () => bridgeCall(
      () => bridge.resetExpression(),
      (result) => result.success
        ? `Reset ${result.reset_count ?? 0} expression slider(s) to neutral.`
        : `Failed: ${result.error}`,
    )
  );
}
