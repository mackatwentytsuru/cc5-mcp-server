/**
 * Expression control tools for CC5.
 */

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
}
