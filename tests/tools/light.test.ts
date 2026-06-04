/**
 * Unit tests for registerLightTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerLightTools } from "../../src/tools/light.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { LightInfo, LightColorResult } from "../../src/types.js";
import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerLightTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerLightTools – registration", () => {
  it("registers exactly 4 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(4);
  });

  it("registers get_lights", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_lights",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_light_color", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_light_color",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── get_lights ────────────────────────────────────────────────────────────────

describe("get_lights handler", () => {
  it("returns no lights message when scene is empty", async () => {
    bridge.getLights.mockResolvedValue([]);
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].text).toBe("No lights in the scene.");
  });

  it("returns light count and details for a single light", async () => {
    const lights: LightInfo[] = [
      { name: "KeyLight", id: 1, type: "SpotLight" },
    ];
    bridge.getLights.mockResolvedValue(lights);
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].text).toContain("Found 1 light(s)");
    expect(result.content[0].text).toContain("KeyLight");
    expect(result.content[0].text).toContain("SpotLight");
    expect(result.content[0].text).toContain("1");
  });

  it("returns all lights for multiple lights", async () => {
    const lights: LightInfo[] = [
      { name: "KeyLight", id: 1, type: "SpotLight" },
      { name: "FillLight", id: 2, type: "PointLight" },
      { name: "BackLight", id: 3, type: "DirectionalLight" },
    ];
    bridge.getLights.mockResolvedValue(lights);
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].text).toContain("Found 3 light(s)");
    expect(result.content[0].text).toContain("KeyLight");
    expect(result.content[0].text).toContain("FillLight");
    expect(result.content[0].text).toContain("BackLight");
  });

  it("formats each light with name, type, and id", async () => {
    const lights: LightInfo[] = [
      { name: "Sun", id: 42, type: "DirectionalLight" },
    ];
    bridge.getLights.mockResolvedValue(lights);
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].text).toContain("- Sun (type: DirectionalLight, ID: 42)");
  });

  it("returns content with type 'text'", async () => {
    bridge.getLights.mockResolvedValue([]);
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });

  it("calls bridge.getLights with no arguments", async () => {
    bridge.getLights.mockResolvedValue([]);
    const handler = server.getRegisteredTool("get_lights");
    await handler({});
    expect(bridge.getLights).toHaveBeenCalledWith();
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getLights.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_lights");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});

// ── set_light_color ───────────────────────────────────────────────────────────

describe("set_light_color handler", () => {
  it("returns success message with light name when color is set", async () => {
    const colorResult: LightColorResult = { success: true, light: "KeyLight" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    const result = await handler({ light_name: "KeyLight", r: 1.0, g: 0.8, b: 0.6 });
    expect(result.content[0].text).toBe("Light 'KeyLight' color set to RGB(1, 0.8, 0.6)");
  });

  it("returns failure message when light is not found", async () => {
    const colorResult: LightColorResult = { success: false, error: "Light not found: MissingLight" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    const result = await handler({ light_name: "MissingLight", r: 1.0, g: 0.0, b: 0.0 });
    expect(result.content[0].text).toBe("Failed: Light not found: MissingLight");
  });

  it("calls bridge.setLightColor with the correct arguments", async () => {
    const colorResult: LightColorResult = { success: true, light: "FillLight" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    await handler({ light_name: "FillLight", r: 0.5, g: 0.5, b: 1.0 });
    expect(bridge.setLightColor).toHaveBeenCalledWith("FillLight", 0.5, 0.5, 1.0);
  });

  it("returns content with type 'text'", async () => {
    const colorResult: LightColorResult = { success: true, light: "KeyLight" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    const result = await handler({ light_name: "KeyLight", r: 1.0, g: 1.0, b: 1.0 });
    expect(result.content[0].type).toBe("text");
  });

  it("works with black color (all zeros)", async () => {
    const colorResult: LightColorResult = { success: true, light: "BackLight" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    const result = await handler({ light_name: "BackLight", r: 0.0, g: 0.0, b: 0.0 });
    expect(result.content[0].text).toContain("BackLight");
    expect(bridge.setLightColor).toHaveBeenCalledWith("BackLight", 0.0, 0.0, 0.0);
  });

  it("works with white color (all ones)", async () => {
    const colorResult: LightColorResult = { success: true, light: "Sun" };
    bridge.setLightColor.mockResolvedValue(colorResult);
    const handler = server.getRegisteredTool("set_light_color");
    await handler({ light_name: "Sun", r: 1.0, g: 1.0, b: 1.0 });
    expect(bridge.setLightColor).toHaveBeenCalledWith("Sun", 1.0, 1.0, 1.0);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setLightColor.mockRejectedValue(new Error("network error"));
    const handler = server.getRegisteredTool("set_light_color");
    const result = await handler({ light_name: "KeyLight", r: 1.0, g: 0.0, b: 0.0 });
    expect(result.content[0].text).toContain("CC5 bridge error: network error");
    expect(result.content[0].text).toContain("Is CC5 running");
  });
});
