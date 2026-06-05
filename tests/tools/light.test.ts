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
  it("registers exactly 9 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(9);
  });

  it("registers get_visual_settings", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_visual_settings",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_ambient", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_ambient",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_ibl", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_ibl",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_light_active", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_light_active",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_light_shadow", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_light_shadow",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
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

// ── set_light_active ──────────────────────────────────────────────────────────

describe("set_light_active handler", () => {
  it("reports the light turned on", async () => {
    bridge.setLightActive.mockResolvedValue({ success: true, light: "KeyLight", active: true });
    const handler = server.getRegisteredTool("set_light_active");
    const result = await handler({ light_name: "KeyLight", active: true });
    expect(result.content[0].text).toBe("Light 'KeyLight' turned on");
  });

  it("reports the light turned off", async () => {
    bridge.setLightActive.mockResolvedValue({ success: true, light: "FillLight", active: false });
    const handler = server.getRegisteredTool("set_light_active");
    const result = await handler({ light_name: "FillLight", active: false });
    expect(result.content[0].text).toBe("Light 'FillLight' turned off");
  });

  it("returns failure message when light is not found", async () => {
    bridge.setLightActive.mockResolvedValue({ success: false, error: "Light not found: Nope" });
    const handler = server.getRegisteredTool("set_light_active");
    const result = await handler({ light_name: "Nope", active: true });
    expect(result.content[0].text).toBe("Failed: Light not found: Nope");
  });

  it("calls bridge.setLightActive with the correct arguments", async () => {
    bridge.setLightActive.mockResolvedValue({ success: true, light: "BackLight", active: false });
    const handler = server.getRegisteredTool("set_light_active");
    await handler({ light_name: "BackLight", active: false });
    expect(bridge.setLightActive).toHaveBeenCalledWith("BackLight", false);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setLightActive.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("set_light_active");
    const result = await handler({ light_name: "KeyLight", active: true });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});

// ── set_light_shadow ──────────────────────────────────────────────────────────

describe("set_light_shadow handler", () => {
  it("reports cast-shadow toggle", async () => {
    bridge.setLightShadow.mockResolvedValue({ success: true, light: "KeyLight", cast_shadow: false });
    const handler = server.getRegisteredTool("set_light_shadow");
    const result = await handler({ light_name: "KeyLight", cast_shadow: false });
    expect(result.content[0].text).toBe("Light 'KeyLight' shadow updated: cast shadow off");
  });

  it("reports darkness change", async () => {
    bridge.setLightShadow.mockResolvedValue({ success: true, light: "KeyLight", darken_shadow_strength: 0.4 });
    const handler = server.getRegisteredTool("set_light_shadow");
    const result = await handler({ light_name: "KeyLight", darken_strength: 0.4 });
    expect(result.content[0].text).toBe("Light 'KeyLight' shadow updated: darkness 0.4");
  });

  it("passes undefined args through as null to the bridge", async () => {
    bridge.setLightShadow.mockResolvedValue({ success: true, light: "KeyLight", cast_shadow: true });
    const handler = server.getRegisteredTool("set_light_shadow");
    await handler({ light_name: "KeyLight", cast_shadow: true });
    expect(bridge.setLightShadow).toHaveBeenCalledWith("KeyLight", true, null);
  });

  it("returns failure message on bridge-side validation error", async () => {
    bridge.setLightShadow.mockResolvedValue({ success: false, error: "Provide cast_shadow and/or darken_strength" });
    const handler = server.getRegisteredTool("set_light_shadow");
    const result = await handler({ light_name: "KeyLight" });
    expect(result.content[0].text).toBe("Failed: Provide cast_shadow and/or darken_strength");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setLightShadow.mockRejectedValue(new Error("network error"));
    const handler = server.getRegisteredTool("set_light_shadow");
    const result = await handler({ light_name: "KeyLight", darken_strength: 0.2 });
    expect(result.content[0].text).toContain("CC5 bridge error: network error");
  });
});

// ── get_visual_settings ───────────────────────────────────────────────────────

describe("get_visual_settings handler", () => {
  it("reports ambient color and IBL state", async () => {
    bridge.getVisualSettings.mockResolvedValue({ success: true, ambient: { r: 0.1, g: 0.2, b: 0.3 }, ibl_enabled: true });
    const handler = server.getRegisteredTool("get_visual_settings");
    const result = await handler({});
    expect(result.content[0].text).toContain("Ambient: RGB(0.100, 0.200, 0.300)");
    expect(result.content[0].text).toContain("IBL: on");
  });

  it("returns failure message when unavailable", async () => {
    bridge.getVisualSettings.mockResolvedValue({ success: false, error: "Visual settings not available" });
    const handler = server.getRegisteredTool("get_visual_settings");
    const result = await handler({});
    expect(result.content[0].text).toBe("Failed: Visual settings not available");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getVisualSettings.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_visual_settings");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});

// ── set_ambient ───────────────────────────────────────────────────────────────

describe("set_ambient handler", () => {
  it("reports the applied ambient color", async () => {
    bridge.setAmbient.mockResolvedValue({ success: true, ambient: { r: 0.5, g: 0.25, b: 0.1 } });
    const handler = server.getRegisteredTool("set_ambient");
    const result = await handler({ r: 0.5, g: 0.25, b: 0.1 });
    expect(result.content[0].text).toContain("Ambient color set to RGB(0.500, 0.250, 0.100)");
  });

  it("calls bridge.setAmbient with the rgb values", async () => {
    bridge.setAmbient.mockResolvedValue({ success: true, ambient: { r: 0, g: 0, b: 0 } });
    const handler = server.getRegisteredTool("set_ambient");
    await handler({ r: 0.2, g: 0.3, b: 0.4 });
    expect(bridge.setAmbient).toHaveBeenCalledWith(0.2, 0.3, 0.4);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setAmbient.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("set_ambient");
    const result = await handler({ r: 0.5, g: 0.5, b: 0.5 });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});

// ── set_ibl ───────────────────────────────────────────────────────────────────

describe("set_ibl handler", () => {
  it("reports IBL enabled with loaded image", async () => {
    bridge.setIbl.mockResolvedValue({ success: true, ibl_enabled: true, loaded_image: "C:/env/studio.hdr" });
    const handler = server.getRegisteredTool("set_ibl");
    const result = await handler({ image_path: "C:/env/studio.hdr", enable: true });
    expect(result.content[0].text).toBe("IBL enabled (loaded C:/env/studio.hdr)");
  });

  it("reports IBL disabled (toggle only, no image)", async () => {
    bridge.setIbl.mockResolvedValue({ success: true, ibl_enabled: false, loaded_image: null });
    const handler = server.getRegisteredTool("set_ibl");
    const result = await handler({ enable: false });
    expect(result.content[0].text).toBe("IBL disabled");
  });

  it("passes empty string when image_path omitted", async () => {
    bridge.setIbl.mockResolvedValue({ success: true, ibl_enabled: true });
    const handler = server.getRegisteredTool("set_ibl");
    await handler({ enable: true });
    expect(bridge.setIbl).toHaveBeenCalledWith("", true);
  });

  it("returns failure message on bad image path", async () => {
    bridge.setIbl.mockResolvedValue({ success: false, error: "IBL image not found: x.hdr" });
    const handler = server.getRegisteredTool("set_ibl");
    const result = await handler({ image_path: "x.hdr", enable: true });
    expect(result.content[0].text).toBe("Failed: IBL image not found: x.hdr");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setIbl.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("set_ibl");
    const result = await handler({ enable: true });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});
