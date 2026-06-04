/**
 * Python scripting tool for CC5.
 * Allows executing arbitrary RLPy Python code inside CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerScriptingTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "exec_python",
    "Execute arbitrary Python code inside CC5's RLPy environment. Has access to RLPy module, all cc5_api helper functions, and the running CC5 scene. Use this for operations not covered by other tools. Set a 'result' variable to return a value.",
    {
      code: z.string().max(10000).describe("Python code to execute. Has access to: RLPy, get_first_avatar(), get_avatars(), get_avatar_info(), get_morph_catalog(), search_morphs(), get_lights(), get_material_info(), capture_viewport(). Set 'result' variable to return a value."),
    },
    async ({ code }) => bridgeCall(
      () => bridge.execPython(code),
      (res) => {
        if (!res.success) return `Error: ${res.error}${res.output ? `\nOutput: ${res.output}` : ""}`;
        const parts: string[] = [];
        if (res.output) parts.push(`Output:\n${res.output}`);
        if (res.result) parts.push(`Result: ${res.result}`);
        return parts.length > 0 ? parts.join("\n") : "Code executed successfully (no output)";
      },
    )
  );
}
