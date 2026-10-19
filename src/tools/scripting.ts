/**
 * Python scripting tool for CC5.
 * Allows executing arbitrary RLPy Python code inside CC5.
 *
 * Off by default: the tool refuses to run unless CC5_ALLOW_EXEC=1 is set in this
 * MCP server's environment. The CC5 bridge plugin enforces the same opt-in on its
 * side (CC5_ALLOW_EXEC in the environment CC5 starts from).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall, isEnvFlagEnabled } from "../util.js";

export const EXEC_ENV_FLAG = "CC5_ALLOW_EXEC";

export const EXEC_DISABLED_MESSAGE =
  "exec_python is disabled. It runs arbitrary Python inside Character Creator 5, so it is off by default. " +
  `To enable it, set ${EXEC_ENV_FLAG}=1 in this MCP server's env (for Claude Code: mcpServers.cc5.env in ~/.claude.json) ` +
  `and in the environment CC5 starts from (for example run 'setx ${EXEC_ENV_FLAG} 1', then restart CC5). ` +
  "See the Security section of the README.";

export function registerScriptingTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "exec_python",
    `Execute arbitrary Python code inside CC5's RLPy environment. Off by default: works only when ${EXEC_ENV_FLAG}=1 is set for this MCP server and for CC5. Has access to RLPy module, all cc5_api helper functions, and the running CC5 scene. Use this for operations not covered by other tools. Set a 'result' variable to return a value.`,
    {
      code: z.string().max(10000).describe("Python code to execute. Has access to: RLPy, get_first_avatar(), get_avatars(), get_avatar_info(), get_morph_catalog(), search_morphs(), get_lights(), get_material_info(), capture_viewport(). Set 'result' variable to return a value."),
    },
    async ({ code }) => {
      if (!isEnvFlagEnabled(EXEC_ENV_FLAG)) {
        return { content: [{ type: "text" as const, text: EXEC_DISABLED_MESSAGE }], isError: true };
      }
      return bridgeCall(
        () => bridge.execPython(code),
        (res) => {
          if (!res.success) return `Error: ${res.error}${res.output ? `\nOutput: ${res.output}` : ""}`;
          const parts: string[] = [];
          if (res.output) parts.push(`Output:\n${res.output}`);
          if (res.result) parts.push(`Result: ${res.result}`);
          return parts.length > 0 ? parts.join("\n") : "Code executed successfully (no output)";
        },
      );
    },
  );
}
