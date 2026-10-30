/**
 * Unit tests for registerScriptingTools (exec_python).
 *
 * The ONE gate is CC5_ALLOW_EXEC in CC5's environment, checked by the bridge. The MCP tool has no switch
 * of its own: it always forwards the call and shows the bridge's answer (a refusal included).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { registerScriptingTools, EXEC_GATE_NOTE, formatExecResult } from "../../src/tools/scripting.js";
import { createMockServer } from "../helpers/mock-server.js";

type ToolResult = { content: Array<{ type: string; text: string }>; isError?: boolean };

const BRIDGE_REFUSAL =
  "'exec_python' is disabled. It can run arbitrary code or drive CC5's UI without confirmation, so it is off by " +
  "default. Whether it runs is decided ONLY by CC5_ALLOW_EXEC in the environment Character Creator 5 was started " +
  "from; the MCP server has no switch of its own. ... do not try to get around this refusal ...; ask the owner.";

let server: ReturnType<typeof createMockServer>;
let execPython: ReturnType<typeof vi.fn>;

async function callExec(code = "result = 6 * 7"): Promise<ToolResult> {
  const handler = server.getRegisteredTool("exec_python");
  return (await handler({ code })) as ToolResult;
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.stubEnv("CC5_ALLOW_EXEC", undefined);
  server = createMockServer();
  execPython = vi.fn();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerScriptingTools(server as any, { execPython } as any);
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("registerScriptingTools – registration", () => {
  it("registers exactly 1 tool named exec_python", () => {
    expect(server.tool).toHaveBeenCalledTimes(1);
    expect(server.tool).toHaveBeenCalledWith(
      "exec_python",
      expect.any(String),
      expect.any(Object),
      expect.any(Function),
    );
  });

  it("says in its description that only CC5's own CC5_ALLOW_EXEC decides, and not to go around a refusal", () => {
    const description = server.tool.mock.calls[0][1] as string;
    expect(description).toContain(EXEC_GATE_NOTE);
    expect(EXEC_GATE_NOTE).toContain("decided ONLY by CC5_ALLOW_EXEC in the environment Character Creator 5 was started from");
    expect(EXEC_GATE_NOTE).toContain("has no switch of its own");
    expect(EXEC_GATE_NOTE).toContain("ask the owner");
    expect(description).not.toContain("this MCP server's env");
  });
});

describe("exec_python – the bridge is the only gate", () => {
  it("forwards the call even when CC5_ALLOW_EXEC is not set for the MCP server", async () => {
    execPython.mockResolvedValue({ success: true, result: "42" });
    const result = await callExec("result = 6 * 7");
    expect(execPython).toHaveBeenCalledWith("result = 6 * 7");
    expect(result.isError).toBeUndefined();
    expect(result.content[0].text).toBe("Result: 42");
  });

  it.each(["0", "false", "no", "", "1"])("the MCP server's own CC5_ALLOW_EXEC=%j changes nothing", async (value) => {
    vi.stubEnv("CC5_ALLOW_EXEC", value);
    execPython.mockResolvedValue({ success: true, result: "1" });
    expect((await callExec()).content[0].text).toBe("Result: 1");
    expect(execPython).toHaveBeenCalledTimes(1);
  });

  it("shows the bridge's refusal word for word, as an error", async () => {
    execPython.mockResolvedValue({ success: false, error: BRIDGE_REFUSAL });
    const result = await callExec();
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toBe(`Error: ${BRIDGE_REFUSAL}`);
  });

  it("formats captured output and result together", async () => {
    execPython.mockResolvedValue({ success: true, output: "hello\n", result: "7" });
    const text = (await callExec()).content[0].text;
    expect(text).toContain("Output:\nhello");
    expect(text).toContain("Result: 7");
  });

  it("says when the code ran without output", async () => {
    execPython.mockResolvedValue({ success: true });
    expect((await callExec()).content[0].text).toBe("Code executed successfully (no output)");
  });

  it("passes on a Python error reported by CC5, with the output", async () => {
    execPython.mockResolvedValue({ success: false, error: "NameError: x", output: "partial" });
    const result = await callExec();
    expect(result.content[0].text).toBe("Error: NameError: x\nOutput: partial");
    expect(result.isError).toBe(true);
  });

  it("warns that a busy CC5 may still run the code later", () => {
    const result = formatExecResult({ success: false, error: "Timeout waiting for CC5 to process command" });
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("MAY STILL RUN LATER");
  });

  it("turns a lost connection into one readable error", async () => {
    execPython.mockRejectedValue(new Error("connect ECONNREFUSED 127.0.0.1:5101"));
    const result = await callExec();
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain("CC5 bridge error: connect ECONNREFUSED");
  });
});
