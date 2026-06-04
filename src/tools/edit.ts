/**
 * Undo/Redo tools for CC5.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerEditTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "undo",
    "Undo the last action in CC5. Use this to revert the most recent change.",
    {},
    async () => bridgeCall(
      () => bridge.undo(),
      (result) => result.success ? "Undo successful" : `Undo failed: ${result.error}`,
    )
  );

  server.tool(
    "redo",
    "Redo the last undone action in CC5. Use this to reapply a previously undone change.",
    {},
    async () => bridgeCall(
      () => bridge.redo(),
      (result) => result.success ? "Redo successful" : `Redo failed: ${result.error}`,
    )
  );
}
