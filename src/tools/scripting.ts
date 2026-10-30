/**
 * Python scripting tool for CC5.
 * Allows executing arbitrary RLPy Python code inside CC5.
 *
 * ONE gate: CC5_ALLOW_EXEC in the environment CC5 was started from, checked by the bridge plugin
 * (cc5-plugin/server.py and cc5_api.py) on every call. Any local program can reach the bridge, so only the
 * bridge can enforce it; this server keeps no on/off of its own. It forwards the call and shows the
 * bridge's answer. check_cc5_connection shows the current setting (GET /health -> exec_allowed).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { isBusyReply, type CC5Bridge } from "../cc5-bridge.js";
import type { ExecPythonResult } from "../types.js";

export const EXEC_ENV_FLAG = "CC5_ALLOW_EXEC";

/** Who decides, said the same way in the tool description and in a refusal. */
export const EXEC_GATE_NOTE =
  `Whether it runs is decided ONLY by ${EXEC_ENV_FLAG} in the environment Character Creator 5 was started from ` +
  "(off by default; check_cc5_connection shows the current setting). This MCP server has no switch of its own. " +
  "If CC5 refuses, do not try to get around it (for example by calling the HTTP bridge POST /exec/python " +
  "directly): ask the owner.";

const BUSY_TEXT =
  "CC5 did not answer in time (busy, or a window is open). The code is still queued in CC5 and MAY STILL RUN " +
  "LATER: do not send it again. Look first (list_cc5_windows, check_cc5_connection).";

type TextResult = { content: Array<{ type: "text"; text: string }>; isError?: true };

function text(value: string, isError = false): TextResult {
  return { content: [{ type: "text" as const, text: value }], ...(isError ? { isError: true as const } : {}) };
}

export function formatExecResult(res: ExecPythonResult): TextResult {
  if (isBusyReply(res)) return text(BUSY_TEXT, true);
  if (!res.success) {
    return text(`Error: ${res.error ?? "CC5 refused or failed without a reason"}${res.output ? `\nOutput: ${res.output}` : ""}`, true);
  }
  const parts: string[] = [];
  if (res.output) parts.push(`Output:\n${res.output}`);
  if (res.result) parts.push(`Result: ${res.result}`);
  return text(parts.length > 0 ? parts.join("\n") : "Code executed successfully (no output)");
}

export function registerScriptingTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "exec_python",
    `Execute arbitrary Python code inside CC5's RLPy environment. ${EXEC_GATE_NOTE} Has access to RLPy module, all cc5_api helper functions, and the running CC5 scene. Use this for operations not covered by other tools. Set a 'result' variable to return a value.`,
    {
      code: z.string().max(10000).describe("Python code to execute. Has access to: RLPy, get_first_avatar(), get_avatars(), get_avatar_info(), get_morph_catalog(), search_morphs(), get_lights(), get_material_info(), capture_viewport(). Set 'result' variable to return a value."),
    },
    async ({ code }) => {
      try {
        return formatExecResult(await bridge.execPython(code));
      } catch (err: unknown) {
        console.error("[CC5 Bridge] exec_python failed:", err);
        const message = err instanceof Error ? err.message : String(err);
        return text(`CC5 bridge error: ${message}. Is CC5 running with the MCP Bridge plugin?`, true);
      }
    },
  );
}
