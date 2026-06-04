/**
 * Unit tests for registerExpressionTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerExpressionTools } from "../../src/tools/expression.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { ExpressionInfo } from "../../src/types.js";
import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerExpressionTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerExpressionTools – registration", () => {
  it("registers exactly 1 tool", () => {
    expect(server.tool).toHaveBeenCalledTimes(1);
  });

  it("registers get_expression_info", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_expression_info",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── get_expression_info ───────────────────────────────────────────────────────

describe("get_expression_info handler", () => {
  it("returns group count and expression names on success", async () => {
    const info: ExpressionInfo = {
      Smile: ["Happy", "Grin"],
      Sad: ["Frown", "Sulk"],
    };
    bridge.getExpressionInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("Expression groups (2)");
    expect(result.content[0].text).toContain("Smile");
    expect(result.content[0].text).toContain("Happy");
    expect(result.content[0].text).toContain("Sad");
  });

  it("lists individual expression names under their group", async () => {
    const info: ExpressionInfo = {
      Eyes: ["Blink", "Squint", "Wide"],
    };
    bridge.getExpressionInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("- Blink");
    expect(result.content[0].text).toContain("- Squint");
    expect(result.content[0].text).toContain("- Wide");
  });

  it("returns no-data message when expression info is empty", async () => {
    const info: ExpressionInfo = {};
    bridge.getExpressionInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].text).toBe("No expression data available.");
  });

  it("returns content with type 'text'", async () => {
    const info: ExpressionInfo = { Smile: ["Happy"] };
    bridge.getExpressionInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("calls bridge.getExpressionInfo with no arguments", async () => {
    bridge.getExpressionInfo.mockResolvedValue({});
    const handler = server.getRegisteredTool("get_expression_info");
    await handler({});
    expect(bridge.getExpressionInfo).toHaveBeenCalledWith();
  });

  it("handles a single group with multiple expressions", async () => {
    const info: ExpressionInfo = {
      Mouth: ["Open", "Smile", "Pucker", "Teeth"],
    };
    bridge.getExpressionInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("Expression groups (1)");
    expect(result.content[0].text).toContain("Mouth (4)");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getExpressionInfo.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_expression_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});
