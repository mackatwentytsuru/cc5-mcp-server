/**
 * Unit tests for registerEditTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerEditTools } from "../../src/tools/edit.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerEditTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerEditTools – registration", () => {
  it("registers exactly 2 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(2);
  });

  it("registers undo", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "undo",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers redo", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "redo",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── undo ──────────────────────────────────────────────────────────────────────

describe("undo handler", () => {
  it("returns success message when undo succeeds", async () => {
    bridge.undo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("undo");
    const result = await handler({});
    expect(result.content[0].text).toBe("Undo successful");
  });

  it("returns failure message when undo returns failure result", async () => {
    bridge.undo.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("undo");
    const result = await handler({});
    expect(result.content[0].text).toBe("Undo failed: operation failed");
  });

  it("calls bridge.undo with no arguments", async () => {
    bridge.undo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("undo");
    await handler({});
    expect(bridge.undo).toHaveBeenCalledWith();
  });

  it("returns content with type 'text'", async () => {
    bridge.undo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("undo");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("returns bridge error text when bridge.undo throws (does not propagate)", async () => {
    bridge.undo.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("undo");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});

// ── redo ──────────────────────────────────────────────────────────────────────

describe("redo handler", () => {
  it("returns success message when redo succeeds", async () => {
    bridge.redo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("redo");
    const result = await handler({});
    expect(result.content[0].text).toBe("Redo successful");
  });

  it("returns failure message when redo returns failure result", async () => {
    bridge.redo.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("redo");
    const result = await handler({});
    expect(result.content[0].text).toBe("Redo failed: operation failed");
  });

  it("calls bridge.redo with no arguments", async () => {
    bridge.redo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("redo");
    await handler({});
    expect(bridge.redo).toHaveBeenCalledWith();
  });

  it("returns content with type 'text'", async () => {
    bridge.redo.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("redo");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("returns bridge error text when bridge.redo throws (does not propagate)", async () => {
    bridge.redo.mockRejectedValue(new Error("network error"));
    const handler = server.getRegisteredTool("redo");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: network error");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});
