/**
 * Unit tests for registerCameraTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerCameraTools } from "../../src/tools/camera.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { CameraInfo, FocalLengthResult } from "../../src/types.js";
import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerCameraTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerCameraTools – registration", () => {
  it("registers exactly 2 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(2);
  });

  it("registers get_camera_info", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_camera_info",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_camera_focal_length", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_camera_focal_length",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── get_camera_info ───────────────────────────────────────────────────────────

describe("get_camera_info handler", () => {
  const sampleCameraInfo: CameraInfo = {
    name: "DefaultCamera",
    position: { x: 0.0, y: 100.0, z: 200.0 },
    focal_length: 50,
  };

  it("returns camera name, position, and focal length on success", async () => {
    bridge.getCameraInfo.mockResolvedValue(sampleCameraInfo);
    const handler = server.getRegisteredTool("get_camera_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("DefaultCamera");
    expect(result.content[0].text).toContain("50mm");
  });

  it("includes position coordinates in the response", async () => {
    bridge.getCameraInfo.mockResolvedValue(sampleCameraInfo);
    const handler = server.getRegisteredTool("get_camera_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("0.0");
    expect(result.content[0].text).toContain("100.0");
    expect(result.content[0].text).toContain("200.0");
  });

  it("returns error message when info has error field", async () => {
    const errorInfo: CameraInfo = {
      name: "",
      position: { x: 0, y: 0, z: 0 },
      focal_length: 0,
      error: "No camera",
    };
    bridge.getCameraInfo.mockResolvedValue(errorInfo);
    const handler = server.getRegisteredTool("get_camera_info");
    const result = await handler({});
    expect(result.content[0].text).toBe("Camera error: No camera");
  });

  it("returns content with type 'text'", async () => {
    bridge.getCameraInfo.mockResolvedValue(sampleCameraInfo);
    const handler = server.getRegisteredTool("get_camera_info");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("calls bridge.getCameraInfo with no arguments", async () => {
    bridge.getCameraInfo.mockResolvedValue(sampleCameraInfo);
    const handler = server.getRegisteredTool("get_camera_info");
    await handler({});
    expect(bridge.getCameraInfo).toHaveBeenCalledWith();
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getCameraInfo.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_camera_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});

// ── set_camera_focal_length ───────────────────────────────────────────────────

describe("set_camera_focal_length handler", () => {
  it("returns success message with the focal length on success", async () => {
    const focalResult: FocalLengthResult = { success: true, focal_length: 85 };
    bridge.setCameraFocalLength.mockResolvedValue(focalResult);
    const handler = server.getRegisteredTool("set_camera_focal_length");
    const result = await handler({ focal_length: 85 });
    expect(result.content[0].text).toBe("Camera focal length set to 85mm");
  });

  it("returns failure message when operation fails", async () => {
    const focalResult: FocalLengthResult = { success: false, error: "no camera in scene" };
    bridge.setCameraFocalLength.mockResolvedValue(focalResult);
    const handler = server.getRegisteredTool("set_camera_focal_length");
    const result = await handler({ focal_length: 50 });
    expect(result.content[0].text).toBe("Failed: no camera in scene");
  });

  it("calls bridge.setCameraFocalLength with the focal length value", async () => {
    const focalResult: FocalLengthResult = { success: true, focal_length: 135 };
    bridge.setCameraFocalLength.mockResolvedValue(focalResult);
    const handler = server.getRegisteredTool("set_camera_focal_length");
    await handler({ focal_length: 135 });
    expect(bridge.setCameraFocalLength).toHaveBeenCalledWith(135);
  });

  it("returns content with type 'text'", async () => {
    const focalResult: FocalLengthResult = { success: true, focal_length: 50 };
    bridge.setCameraFocalLength.mockResolvedValue(focalResult);
    const handler = server.getRegisteredTool("set_camera_focal_length");
    const result = await handler({ focal_length: 50 });
    expect(result.content[0].type).toBe("text");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setCameraFocalLength.mockRejectedValue(new Error("connection lost"));
    const handler = server.getRegisteredTool("set_camera_focal_length");
    const result = await handler({ focal_length: 50 });
    expect(result.content[0].text).toContain("CC5 bridge error: connection lost");
    expect(result.content[0].text).toContain("Is CC5 running");
  });

  it("works with wide angle focal length (35mm)", async () => {
    const focalResult: FocalLengthResult = { success: true, focal_length: 35 };
    bridge.setCameraFocalLength.mockResolvedValue(focalResult);
    const handler = server.getRegisteredTool("set_camera_focal_length");
    const result = await handler({ focal_length: 35 });
    expect(result.content[0].text).toBe("Camera focal length set to 35mm");
  });
});
