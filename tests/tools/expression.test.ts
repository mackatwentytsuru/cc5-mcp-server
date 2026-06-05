/**
 * Unit tests for registerExpressionTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerExpressionTools } from "../../src/tools/expression.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { ExpressionInfo, ExpressionSetResult, ExpressionResetResult } from "../../src/types.js";
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
  it("registers exactly 3 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(3);
  });

  it("registers get_expression_info", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_expression_info",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_expression", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_expression",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers reset_expression", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "reset_expression",
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

// ── set_expression ────────────────────────────────────────────────────────────

describe("set_expression handler", () => {
  it("reports applied sliders on success", async () => {
    const r: ExpressionSetResult = {
      success: true,
      applied: [{ name: "Brow_Raise_Inner_L", weight: 0.8 }],
      skipped: [],
    };
    bridge.setExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("set_expression");
    const result = await handler({ expressions: [{ name: "Brow_Raise_Inner_L", weight: 0.8 }] });
    expect(result.content[0].text).toContain("Set 1 expression slider(s)");
    expect(result.content[0].text).toContain("Brow_Raise_Inner_L = 0.8");
  });

  it("reports skipped unknown names", async () => {
    const r: ExpressionSetResult = {
      success: true,
      applied: [{ name: "Smile_L", weight: 1 }],
      skipped: ["Bogus"],
    };
    bridge.setExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("set_expression");
    const result = await handler({ expressions: [{ name: "Smile_L", weight: 1 }, { name: "Bogus", weight: 1 }] });
    expect(result.content[0].text).toContain("Skipped (unknown): Bogus");
  });

  it("returns failure message when nothing valid was set", async () => {
    const r: ExpressionSetResult = { success: false, error: "No valid expression names", skipped: ["Nope"] };
    bridge.setExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("set_expression");
    const result = await handler({ expressions: [{ name: "Nope", weight: 1 }] });
    expect(result.content[0].text).toContain("Failed: No valid expression names");
    expect(result.content[0].text).toContain("skipped: Nope");
  });

  it("calls bridge.setExpression with the expression list", async () => {
    const r: ExpressionSetResult = { success: true, applied: [{ name: "Smile_L", weight: 0.5 }], skipped: [] };
    bridge.setExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("set_expression");
    await handler({ expressions: [{ name: "Smile_L", weight: 0.5 }] });
    expect(bridge.setExpression).toHaveBeenCalledWith([{ name: "Smile_L", weight: 0.5 }]);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setExpression.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("set_expression");
    const result = await handler({ expressions: [{ name: "Smile_L", weight: 1 }] });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});

// ── reset_expression ──────────────────────────────────────────────────────────

describe("reset_expression handler", () => {
  it("reports the number of sliders reset", async () => {
    const r: ExpressionResetResult = { success: true, reset_count: 128 };
    bridge.resetExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("reset_expression");
    const result = await handler({});
    expect(result.content[0].text).toBe("Reset 128 expression slider(s) to neutral.");
  });

  it("returns failure message when no avatar", async () => {
    const r: ExpressionResetResult = { success: false, error: "No avatar" };
    bridge.resetExpression.mockResolvedValue(r);
    const handler = server.getRegisteredTool("reset_expression");
    const result = await handler({});
    expect(result.content[0].text).toBe("Failed: No avatar");
  });

  it("calls bridge.resetExpression with no arguments", async () => {
    bridge.resetExpression.mockResolvedValue({ success: true, reset_count: 0 });
    const handler = server.getRegisteredTool("reset_expression");
    await handler({});
    expect(bridge.resetExpression).toHaveBeenCalledWith();
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.resetExpression.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("reset_expression");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});
