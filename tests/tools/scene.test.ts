/**
 * Unit tests for registerSceneTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses.
 * The check_cc5_connection handler has its own try/catch with specific behavior.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerSceneTools } from "../../src/tools/scene.js";
import {
  createMockBridge,
  SUCCESS,
  FAILURE,
  CREATE_SUCCESS,
  CAPTURE_SUCCESS,
} from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { CC5Avatar, AvatarInfo, CreateAvatarResult, CaptureResult } from "../../src/types.js";

import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerSceneTools(server as any, bridge as any);
});

// ── registration ──────────────────────────────────────────────────────────────

describe("registerSceneTools – registration", () => {
  it("registers exactly 6 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(6);
  });

  it("registers list_avatars", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "list_avatars",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers get_avatar_info", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_avatar_info",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers check_cc5_connection", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "check_cc5_connection",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers create_avatar", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "create_avatar",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers capture_viewport", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "capture_viewport",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_subdivision_level", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_subdivision_level",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── list_avatars ──────────────────────────────────────────────────────────────

describe("list_avatars handler", () => {
  it("lists avatars with names and IDs", async () => {
    const avatars: CC5Avatar[] = [
      { id: "a1", name: "Hero", type: "character" },
      { id: "a2", name: "Villain", type: "character" },
    ];
    bridge.getAvatars.mockResolvedValue(avatars);
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].text).toContain("Found 2 avatar(s)");
    expect(result.content[0].text).toContain("Hero");
    expect(result.content[0].text).toContain("a1");
    expect(result.content[0].text).toContain("Villain");
    expect(result.content[0].text).toContain("a2");
  });

  it("shows empty scene message when no avatars exist", async () => {
    bridge.getAvatars.mockResolvedValue([]);
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].text).toBe("No avatars in the current scene.");
  });

  it("handles a single avatar correctly", async () => {
    bridge.getAvatars.mockResolvedValue([{ id: "solo", name: "Solo", type: "character" }]);
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].text).toContain("Found 1 avatar(s)");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getAvatars.mockRejectedValue(new Error("connection refused"));
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: connection refused");
  });

  it("returns content with type 'text'", async () => {
    bridge.getAvatars.mockResolvedValue([]);
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("formats avatar list with dash prefix per avatar", async () => {
    const avatars: CC5Avatar[] = [
      { id: "x1", name: "Alpha", type: "character" },
    ];
    bridge.getAvatars.mockResolvedValue(avatars);
    const handler = server.getRegisteredTool("list_avatars");
    const result = await handler({});
    expect(result.content[0].text).toContain("- Alpha (ID: x1)");
  });
});

// ── get_avatar_info ───────────────────────────────────────────────────────────

describe("get_avatar_info handler", () => {
  const sampleInfo: AvatarInfo = {
    id: "av1",
    name: "TestHero",
    active_morphs: { Fat: 0.3, Muscular: 0.5, Thin: 0.1 },
  };

  it("shows avatar name and active morph count", async () => {
    bridge.getAvatarInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_avatar_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("TestHero");
    expect(result.content[0].text).toContain("Active morphs (3)");
  });

  it("lists each morph and its value", async () => {
    bridge.getAvatarInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_avatar_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("Fat");
    expect(result.content[0].text).toContain("0.3");
    expect(result.content[0].text).toContain("Muscular");
    expect(result.content[0].text).toContain("0.5");
  });

  it("shows no-avatar message when info is null", async () => {
    bridge.getAvatarInfo.mockResolvedValue(null);
    const handler = server.getRegisteredTool("get_avatar_info");
    const result = await handler({});
    expect(result.content[0].text).toBe("No avatar in the scene.");
  });

  it("shows zero active morphs correctly", async () => {
    bridge.getAvatarInfo.mockResolvedValue({
      id: "av2",
      name: "Plain",
      active_morphs: {},
    });
    const handler = server.getRegisteredTool("get_avatar_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("Active morphs (0)");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getAvatarInfo.mockRejectedValue(new Error("not connected"));
    const handler = server.getRegisteredTool("get_avatar_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: not connected");
  });
});

// ── check_cc5_connection ──────────────────────────────────────────────────────

describe("check_cc5_connection handler", () => {
  it("returns connected message when bridge is healthy", async () => {
    bridge.healthCheck.mockResolvedValue(true);
    const handler = server.getRegisteredTool("check_cc5_connection");
    const result = await handler({});
    expect(result.content[0].text).toContain("connected and ready");
  });

  it("returns not-responding message when healthCheck returns false", async () => {
    bridge.healthCheck.mockResolvedValue(false);
    const handler = server.getRegisteredTool("check_cc5_connection");
    const result = await handler({});
    expect(result.content[0].text).toContain("NOT responding");
    expect(result.content[0].text).toContain("Character Creator 5");
  });

  it("returns not-responding message when healthCheck throws", async () => {
    bridge.healthCheck.mockRejectedValue(new Error("ECONNREFUSED"));
    const handler = server.getRegisteredTool("check_cc5_connection");
    const result = await handler({});
    expect(result.content[0].text).toContain("NOT responding");
  });

  it("calls bridge.healthCheck once per invocation", async () => {
    bridge.healthCheck.mockResolvedValue(true);
    const handler = server.getRegisteredTool("check_cc5_connection");
    await handler({});
    expect(bridge.healthCheck).toHaveBeenCalledTimes(1);
  });

  it("returns content with type 'text'", async () => {
    bridge.healthCheck.mockResolvedValue(true);
    const handler = server.getRegisteredTool("check_cc5_connection");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });
});

// ── create_avatar ─────────────────────────────────────────────────────────────

describe("create_avatar handler", () => {
  it("returns success message with avatar name on success", async () => {
    bridge.createDefaultAvatar.mockResolvedValue(CREATE_SUCCESS);
    const handler = server.getRegisteredTool("create_avatar");
    const result = await handler({});
    expect(result.content[0].text).toContain("Created avatar");
    expect(result.content[0].text).toContain("Default Character");
  });

  it("uses 'Unknown' as name when result.name is undefined", async () => {
    const noName: CreateAvatarResult = { success: true };
    bridge.createDefaultAvatar.mockResolvedValue(noName);
    const handler = server.getRegisteredTool("create_avatar");
    const result = await handler({});
    expect(result.content[0].text).toContain("Unknown");
  });

  it("returns failure message when operation fails", async () => {
    const failed: CreateAvatarResult = { success: false, error: "scene is locked" };
    bridge.createDefaultAvatar.mockResolvedValue(failed);
    const handler = server.getRegisteredTool("create_avatar");
    const result = await handler({});
    expect(result.content[0].text).toBe("Failed: scene is locked");
  });

  it("calls bridge.createDefaultAvatar with no arguments", async () => {
    bridge.createDefaultAvatar.mockResolvedValue(CREATE_SUCCESS);
    const handler = server.getRegisteredTool("create_avatar");
    await handler({});
    expect(bridge.createDefaultAvatar).toHaveBeenCalledWith();
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.createDefaultAvatar.mockRejectedValue(new Error("CC5 not running"));
    const handler = server.getRegisteredTool("create_avatar");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: CC5 not running");
  });

  it("returns content with type 'text'", async () => {
    bridge.createDefaultAvatar.mockResolvedValue(CREATE_SUCCESS);
    const handler = server.getRegisteredTool("create_avatar");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });
});

// ── capture_viewport ──────────────────────────────────────────────────────────

describe("capture_viewport handler", () => {
  it("returns success message with capture path when path is provided", async () => {
    bridge.captureViewport.mockResolvedValue(CAPTURE_SUCCESS);
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({ output_path: "C:/temp/capture.png" });
    // Handler returns [image, text] when bridge supplies base64 data
    expect(result.content[0].type).toBe("image");
    expect(result.content[1].text).toContain("Viewport captured:");
    expect(result.content[1].text).toContain("C:/temp/capture.png");
  });

  it("returns success message with result.path when no output_path arg given", async () => {
    const captured: CaptureResult = { success: true, path: "/tmp/cc5_snap.png", base64: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" };
    bridge.captureViewport.mockResolvedValue(captured);
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({});
    // Handler returns [image, text] when bridge supplies base64 data
    expect(result.content[0].type).toBe("image");
    expect(result.content[1].text).toContain("Viewport captured:");
    expect(result.content[1].text).toContain("/tmp/cc5_snap.png");
  });

  it("returns failure message when capture operation fails", async () => {
    const failed: CaptureResult = { success: false, error: "no render context" };
    bridge.captureViewport.mockResolvedValue(failed);
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({});
    expect(result.content[0].text).toBe("Failed: no render context");
  });

  it("rejects path containing '..'", async () => {
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({ output_path: "C:/safe/../../../etc/evil.png" });
    expect(result.content[0].text).toContain("Path traversal");
    expect(bridge.captureViewport).not.toHaveBeenCalled();
  });

  it("rejects non-.png extension", async () => {
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({ output_path: "C:/out/frame.jpg" });
    expect(result.content[0].text).toContain(".png");
    expect(bridge.captureViewport).not.toHaveBeenCalled();
  });

  it("calls bridge.captureViewport with the output path", async () => {
    bridge.captureViewport.mockResolvedValue(CAPTURE_SUCCESS);
    const handler = server.getRegisteredTool("capture_viewport");
    await handler({ output_path: "C:/temp/capture.png" });
    expect(bridge.captureViewport).toHaveBeenCalledWith("C:/temp/capture.png", undefined, undefined);
  });

  it("calls bridge.captureViewport with undefined when no path given", async () => {
    const captured: CaptureResult = { success: true, path: "/tmp/snap.png" };
    bridge.captureViewport.mockResolvedValue(captured);
    const handler = server.getRegisteredTool("capture_viewport");
    await handler({});
    expect(bridge.captureViewport).toHaveBeenCalledWith(undefined, undefined, undefined);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.captureViewport.mockRejectedValue(new Error("render failed"));
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: render failed");
  });

  it("returns image content followed by text content on success", async () => {
    bridge.captureViewport.mockResolvedValue(CAPTURE_SUCCESS);
    const handler = server.getRegisteredTool("capture_viewport");
    const result = await handler({ output_path: "C:/temp/capture.png" });
    expect(result.content[0].type).toBe("image");
    expect(result.content[1].type).toBe("text");
  });
});

// ── set_subdivision_level ─────────────────────────────────────────────────────

describe("set_subdivision_level handler", () => {
  it("returns success message with the level on success", async () => {
    bridge.setSubdivisionLevel.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("set_subdivision_level");
    const result = await handler({ level: 2 });
    expect(result.content[0].text).toBe("Subdivision level set to 2");
  });

  it("returns failure message when operation returns failure", async () => {
    bridge.setSubdivisionLevel.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("set_subdivision_level");
    const result = await handler({ level: 1 });
    expect(result.content[0].text).toBe("Failed: operation failed");
  });

  it("calls bridge.setSubdivisionLevel with the level", async () => {
    bridge.setSubdivisionLevel.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("set_subdivision_level");
    await handler({ level: 0 });
    expect(bridge.setSubdivisionLevel).toHaveBeenCalledWith(0);
  });

  it("works for level 0 (base mesh)", async () => {
    bridge.setSubdivisionLevel.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("set_subdivision_level");
    const result = await handler({ level: 0 });
    expect(result.content[0].text).toBe("Subdivision level set to 0");
  });

  it("works for level 1 (medium)", async () => {
    bridge.setSubdivisionLevel.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("set_subdivision_level");
    const result = await handler({ level: 1 });
    expect(result.content[0].text).toBe("Subdivision level set to 1");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setSubdivisionLevel.mockRejectedValue(new Error("CC5 crashed"));
    const handler = server.getRegisteredTool("set_subdivision_level");
    const result = await handler({ level: 2 });
    expect(result.content[0].text).toContain("CC5 bridge error: CC5 crashed");
  });
});
