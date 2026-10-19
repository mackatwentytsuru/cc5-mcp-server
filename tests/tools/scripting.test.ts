/**
 * Unit tests for registerScriptingTools (exec_python).
 * exec_python must be refused unless CC5_ALLOW_EXEC is switched on.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { registerScriptingTools, EXEC_DISABLED_MESSAGE } from "../../src/tools/scripting.js";
import { createMockServer } from "../helpers/mock-server.js";

type ToolResult = { content: Array<{ type: string; text: string }>; isError?: boolean };

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

  it("says in its description that it is off by default", () => {
    const description = server.tool.mock.calls[0][1] as string;
    expect(description).toContain("Off by default");
    expect(description).toContain("CC5_ALLOW_EXEC=1");
  });
});

describe("exec_python – disabled by default", () => {
  it("refuses when CC5_ALLOW_EXEC is not set, without calling the bridge", async () => {
    const result = await callExec();
    expect(execPython).not.toHaveBeenCalled();
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toBe(EXEC_DISABLED_MESSAGE);
  });

  it("tells the user how to enable it", async () => {
    const text = (await callExec()).content[0].text;
    expect(text).toContain("CC5_ALLOW_EXEC=1");
    expect(text).toContain("setx CC5_ALLOW_EXEC 1");
    expect(text).toContain("restart CC5");
  });

  it.each(["0", "false", "no", ""])("refuses when CC5_ALLOW_EXEC=%j", async (value) => {
    vi.stubEnv("CC5_ALLOW_EXEC", value);
    const result = await callExec();
    expect(execPython).not.toHaveBeenCalled();
    expect(result.isError).toBe(true);
  });

  it("ignores CC5_DEV_MODE (dev mode does not enable code execution)", async () => {
    vi.stubEnv("CC5_DEV_MODE", "1");
    const result = await callExec();
    expect(execPython).not.toHaveBeenCalled();
    expect(result.isError).toBe(true);
  });
});

describe("exec_python – enabled with CC5_ALLOW_EXEC", () => {
  it("runs the code when CC5_ALLOW_EXEC=1", async () => {
    vi.stubEnv("CC5_ALLOW_EXEC", "1");
    execPython.mockResolvedValue({ success: true, result: "42" });
    const result = await callExec("result = 6 * 7");
    expect(execPython).toHaveBeenCalledWith("result = 6 * 7");
    expect(result.isError).toBeUndefined();
    expect(result.content[0].text).toBe("Result: 42");
  });

  it.each(["true", "yes", "TRUE"])("also accepts CC5_ALLOW_EXEC=%j", async (value) => {
    vi.stubEnv("CC5_ALLOW_EXEC", value);
    execPython.mockResolvedValue({ success: true });
    const result = await callExec();
    expect(execPython).toHaveBeenCalledTimes(1);
    expect(result.content[0].text).toBe("Code executed successfully (no output)");
  });

  it("reads the flag on every call (no caching at registration time)", async () => {
    execPython.mockResolvedValue({ success: true, result: "1" });
    expect((await callExec()).isError).toBe(true);
    vi.stubEnv("CC5_ALLOW_EXEC", "1");
    expect((await callExec()).content[0].text).toBe("Result: 1");
  });

  it("formats captured output and result together", async () => {
    vi.stubEnv("CC5_ALLOW_EXEC", "1");
    execPython.mockResolvedValue({ success: true, output: "hello\n", result: "7" });
    const text = (await callExec()).content[0].text;
    expect(text).toContain("Output:\nhello");
    expect(text).toContain("Result: 7");
  });

  it("passes on an error reported by CC5", async () => {
    vi.stubEnv("CC5_ALLOW_EXEC", "1");
    execPython.mockResolvedValue({ success: false, error: "NameError: x", output: "partial" });
    const text = (await callExec()).content[0].text;
    expect(text).toBe("Error: NameError: x\nOutput: partial");
  });

  it("passes on a refusal from the CC5 side (plugin without CC5_ALLOW_EXEC)", async () => {
    vi.stubEnv("CC5_ALLOW_EXEC", "1");
    execPython.mockRejectedValue(new Error("CC5 bridge error (403): {\"error\": \"'exec_python' is disabled.\"}"));
    const text = (await callExec()).content[0].text;
    expect(text).toContain("403");
    expect(text).toContain("'exec_python' is disabled.");
  });
});
