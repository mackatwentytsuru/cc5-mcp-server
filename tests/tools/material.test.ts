/**
 * Unit tests for registerMaterialTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerMaterialTools } from "../../src/tools/material.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { MaterialInfo, DiffuseColor, SetDiffuseColorResult, ShaderParameters, SetShaderParameterResult } from "../../src/types.js";

import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerMaterialTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerMaterialTools – registration", () => {
  it("registers exactly 9 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(9);
  });

  it("registers get_shader_parameters", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_shader_parameters",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_shader_parameter", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_shader_parameter",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers get_material_info", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_material_info",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers get_diffuse_color", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_diffuse_color",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers set_diffuse_color", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "set_diffuse_color",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── get_material_info ─────────────────────────────────────────────────────────

describe("get_material_info handler", () => {
  const sampleInfo: MaterialInfo = {
    meshes: {
      CC_Base_Body: ["Std_Skin_Body", "Std_Skin_Arm"],
      CC_Base_Eye: ["Std_Eye_R", "Std_Eye_L"],
    },
  };

  it("returns mesh and material names on success", async () => {
    bridge.getMaterialInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({ avatar_name: undefined });
    expect(result.content[0].text).toContain("Found 2 mesh(es)");
    expect(result.content[0].text).toContain("CC_Base_Body");
    expect(result.content[0].text).toContain("Std_Skin_Body");
  });

  it("formats materials as comma-separated list under each mesh", async () => {
    bridge.getMaterialInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC_Base_Body: Std_Skin_Body, Std_Skin_Arm");
  });

  it("reports '(no materials)' for a mesh with an empty materials array", async () => {
    const emptyMaterials: MaterialInfo = { meshes: { CC_Base_Body: [] } };
    bridge.getMaterialInfo.mockResolvedValue(emptyMaterials);
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("(no materials)");
  });

  it("returns the no-meshes message when result is an empty object", async () => {
    bridge.getMaterialInfo.mockResolvedValue({ meshes: {} });
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("No meshes found on the avatar");
  });

  it("passes avatar_name to bridge.getMaterialInfo", async () => {
    bridge.getMaterialInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_material_info");
    await handler({ avatar_name: "Hero" });
    expect(bridge.getMaterialInfo).toHaveBeenCalledWith("Hero");
  });

  it("passes undefined when avatar_name is omitted", async () => {
    bridge.getMaterialInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_material_info");
    await handler({});
    expect(bridge.getMaterialInfo).toHaveBeenCalledWith(undefined);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getMaterialInfo.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });

  it("returns content with type 'text'", async () => {
    bridge.getMaterialInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredTool("get_material_info");
    const result = await handler({});
    expect(result.content[0].type).toBe("text");
  });
});

// ── get_diffuse_color ─────────────────────────────────────────────────────────

describe("get_diffuse_color handler", () => {
  const sampleColor: DiffuseColor = { r: 0.8, g: 0.6, b: 0.4 };

  it("returns RGB values for the named mesh and material", async () => {
    bridge.getDiffuseColor.mockResolvedValue(sampleColor);
    const handler = server.getRegisteredTool("get_diffuse_color");
    const result = await handler({ mesh_name: "CC_Base_Body", material_name: "Std_Skin_Body" });
    expect(result.content[0].text).toContain("CC_Base_Body/Std_Skin_Body");
    expect(result.content[0].text).toContain("RGB(");
  });

  it("formats RGB values to 3 decimal places", async () => {
    bridge.getDiffuseColor.mockResolvedValue({ r: 0.1234, g: 0.5678, b: 0.9 });
    const handler = server.getRegisteredTool("get_diffuse_color");
    const result = await handler({ mesh_name: "Mesh", material_name: "Mat" });
    expect(result.content[0].text).toContain("0.123");
    expect(result.content[0].text).toContain("0.568");
    expect(result.content[0].text).toContain("0.900");
  });

  it("returns failure message when response contains an error field", async () => {
    const colorWithError: DiffuseColor = { r: 0, g: 0, b: 0, error: "mesh not found" };
    bridge.getDiffuseColor.mockResolvedValue(colorWithError);
    const handler = server.getRegisteredTool("get_diffuse_color");
    const result = await handler({ mesh_name: "Bad_Mesh", material_name: "Mat" });
    expect(result.content[0].text).toBe("Failed: mesh not found");
  });

  it("calls bridge.getDiffuseColor with mesh_name and material_name", async () => {
    bridge.getDiffuseColor.mockResolvedValue(sampleColor);
    const handler = server.getRegisteredTool("get_diffuse_color");
    await handler({ mesh_name: "CC_Base_Body", material_name: "Std_Skin_Body" });
    expect(bridge.getDiffuseColor).toHaveBeenCalledWith("CC_Base_Body", "Std_Skin_Body");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getDiffuseColor.mockRejectedValue(new Error("timeout"));
    const handler = server.getRegisteredTool("get_diffuse_color");
    const result = await handler({ mesh_name: "Mesh", material_name: "Mat" });
    expect(result.content[0].text).toContain("CC5 bridge error: timeout");
  });

  it("handles RGB values of exactly 0 and 1 (boundary values)", async () => {
    bridge.getDiffuseColor.mockResolvedValue({ r: 0, g: 1, b: 0.5 });
    const handler = server.getRegisteredTool("get_diffuse_color");
    const result = await handler({ mesh_name: "Mesh", material_name: "Mat" });
    expect(result.content[0].text).toContain("RGB(0.000, 1.000, 0.500)");
  });
});

// ── set_diffuse_color ─────────────────────────────────────────────────────────

describe("set_diffuse_color handler", () => {
  const successResult: SetDiffuseColorResult = {
    success: true,
    mesh: "CC_Base_Body",
    material: "Std_Skin_Body",
  };

  it("returns success message with mesh and material names from result", async () => {
    bridge.setDiffuseColor.mockResolvedValue(successResult);
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "CC_Base_Body",
      material_name: "Std_Skin_Body",
      r: 0.9,
      g: 0.7,
      b: 0.5,
    });
    expect(result.content[0].text).toContain("CC_Base_Body/Std_Skin_Body");
    expect(result.content[0].text).toContain("RGB(0.9, 0.7, 0.5)");
  });

  it("falls back to input mesh_name when result.mesh is undefined", async () => {
    const noMeshResult: SetDiffuseColorResult = { success: true };
    bridge.setDiffuseColor.mockResolvedValue(noMeshResult);
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "FallbackMesh",
      material_name: "FallbackMat",
      r: 0.1,
      g: 0.2,
      b: 0.3,
    });
    expect(result.content[0].text).toContain("FallbackMesh/FallbackMat");
  });

  it("returns failure message when result.success is false", async () => {
    bridge.setDiffuseColor.mockResolvedValue(FAILURE as SetDiffuseColorResult);
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "Mesh",
      material_name: "Mat",
      r: 0.5,
      g: 0.5,
      b: 0.5,
    });
    expect(result.content[0].text).toBe("Failed: operation failed");
  });

  it("calls bridge.setDiffuseColor with correct arguments", async () => {
    bridge.setDiffuseColor.mockResolvedValue(successResult);
    const handler = server.getRegisteredTool("set_diffuse_color");
    await handler({
      mesh_name: "CC_Base_Body",
      material_name: "Std_Skin_Body",
      r: 0.9,
      g: 0.7,
      b: 0.5,
    });
    expect(bridge.setDiffuseColor).toHaveBeenCalledWith(
      "CC_Base_Body",
      "Std_Skin_Body",
      0.9,
      0.7,
      0.5
    );
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setDiffuseColor.mockRejectedValue(new Error("CC5 not responding"));
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "Mesh",
      material_name: "Mat",
      r: 0,
      g: 0,
      b: 0,
    });
    expect(result.content[0].text).toContain("CC5 bridge error: CC5 not responding");
  });

  it("handles RGB boundary values 0 and 1", async () => {
    bridge.setDiffuseColor.mockResolvedValue({ success: true });
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "Mesh",
      material_name: "Mat",
      r: 0,
      g: 1,
      b: 0,
    });
    expect(result.content[0].text).toContain("RGB(0, 1, 0)");
  });

  it("returns content with type 'text'", async () => {
    bridge.setDiffuseColor.mockResolvedValue(successResult);
    const handler = server.getRegisteredTool("set_diffuse_color");
    const result = await handler({
      mesh_name: "Mesh",
      material_name: "Mat",
      r: 0.5,
      g: 0.5,
      b: 0.5,
    });
    expect(result.content[0].type).toBe("text");
  });
});

// ── get_shader_parameters ─────────────────────────────────────────────────────

describe("get_shader_parameters handler", () => {
  it("lists shader name and parameters on success", async () => {
    const r: ShaderParameters = {
      success: true,
      mesh: "CC_Base_Body",
      material: "Std_Skin_Head",
      shader: "Digital_Human Head",
      parameters: { "Micro Roughness Scale": [0.05], "SSS Radius": [1.5] },
    };
    bridge.getShaderParameters.mockResolvedValue(r);
    const handler = server.getRegisteredTool("get_shader_parameters");
    const result = await handler({ mesh_name: "CC_Base_Body", material_name: "Std_Skin_Head" });
    expect(result.content[0].text).toContain("Digital_Human Head");
    expect(result.content[0].text).toContain("Micro Roughness Scale = [0.050]");
    expect(result.content[0].text).toContain("SSS Radius = [1.500]");
  });

  it("reports when there are no shader parameters", async () => {
    const r: ShaderParameters = { success: true, material: "Std_Tongue", shader: "Pbr", parameters: {} };
    bridge.getShaderParameters.mockResolvedValue(r);
    const handler = server.getRegisteredTool("get_shader_parameters");
    const result = await handler({ mesh_name: "CC_Base_Body", material_name: "Std_Tongue" });
    expect(result.content[0].text).toContain("no shader parameters");
  });

  it("returns failure message when material not found", async () => {
    bridge.getShaderParameters.mockResolvedValue({ success: false, error: "Material not found: X" });
    const handler = server.getRegisteredTool("get_shader_parameters");
    const result = await handler({ mesh_name: "M", material_name: "X" });
    expect(result.content[0].text).toBe("Failed: Material not found: X");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getShaderParameters.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("get_shader_parameters");
    const result = await handler({ mesh_name: "M", material_name: "Mat" });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});

// ── set_shader_parameter ──────────────────────────────────────────────────────

describe("set_shader_parameter handler", () => {
  it("reports the applied value on success", async () => {
    const r: SetShaderParameterResult = {
      success: true,
      mesh: "CC_Base_Body",
      material: "Std_Skin_Head",
      parameter: "Micro Roughness Scale",
      values: [0.3],
    };
    bridge.setShaderParameter.mockResolvedValue(r);
    const handler = server.getRegisteredTool("set_shader_parameter");
    const result = await handler({
      mesh_name: "CC_Base_Body",
      material_name: "Std_Skin_Head",
      parameter_name: "Micro Roughness Scale",
      values: [0.3],
    });
    expect(result.content[0].text).toContain("'Micro Roughness Scale' set to [0.3]");
  });

  it("returns failure on unknown parameter / arity mismatch", async () => {
    bridge.setShaderParameter.mockResolvedValue({ success: false, error: "Unknown shader parameter: Bogus" });
    const handler = server.getRegisteredTool("set_shader_parameter");
    const result = await handler({
      mesh_name: "CC_Base_Body",
      material_name: "Std_Skin_Head",
      parameter_name: "Bogus",
      values: [1],
    });
    expect(result.content[0].text).toBe("Failed: Unknown shader parameter: Bogus");
  });

  it("calls bridge.setShaderParameter with correct arguments", async () => {
    bridge.setShaderParameter.mockResolvedValue({ success: true, values: [1.5] });
    const handler = server.getRegisteredTool("set_shader_parameter");
    await handler({
      mesh_name: "CC_Base_Body",
      material_name: "Std_Skin_Head",
      parameter_name: "SSS Radius",
      values: [1.5],
    });
    expect(bridge.setShaderParameter).toHaveBeenCalledWith("CC_Base_Body", "Std_Skin_Head", "SSS Radius", [1.5]);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setShaderParameter.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("set_shader_parameter");
    const result = await handler({
      mesh_name: "M",
      material_name: "Mat",
      parameter_name: "SSS Radius",
      values: [1.5],
    });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
  });
});
