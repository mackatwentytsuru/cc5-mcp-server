/**
 * Material and texture control tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerMaterialTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "get_material_info",
    "List all meshes and their materials on the current avatar. Use this to discover mesh and material names before getting or setting colors.",
    {
      avatar_name: z.string().max(256).optional().describe("Avatar name (optional, defaults to first avatar)"),
    },
    async ({ avatar_name }) => bridgeCall(
      () => bridge.getMaterialInfo(avatar_name),
      (info) => {
        const meshes = info.meshes ?? {};
        const meshNames = Object.keys(meshes);
        if (meshNames.length === 0) {
          return "No meshes found on the avatar. The avatar may not have material data, or GetMeshNames() may not be available in this CC5 version.";
        }
        const lines = meshNames.map(mesh => {
          const mats = meshes[mesh];
          return `- ${mesh}: ${mats.length > 0 ? mats.join(", ") : "(no materials)"}`;
        });
        return `Found ${meshNames.length} mesh(es):\n${lines.join("\n")}`;
      },
    )
  );

  server.tool(
    "get_diffuse_color",
    "Get the diffuse (base) color of a specific material. Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
    },
    async ({ mesh_name, material_name }) => bridgeCall(
      () => bridge.getDiffuseColor(mesh_name, material_name),
      (color) => {
        if (color.error) return `Failed: ${color.error}`;
        return `Diffuse color of ${mesh_name}/${material_name}: RGB(${color.r.toFixed(3)}, ${color.g.toFixed(3)}, ${color.b.toFixed(3)})`;
      },
    )
  );

  server.tool(
    "set_diffuse_color",
    "Set the diffuse (base) color of a material. Useful for changing skin tone, clothing color, etc. RGB values are floats 0.0-1.0. Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
      r: z.number().min(0).max(1).describe("Red component (0.0-1.0)"),
      g: z.number().min(0).max(1).describe("Green component (0.0-1.0)"),
      b: z.number().min(0).max(1).describe("Blue component (0.0-1.0)"),
    },
    async ({ mesh_name, material_name, r, g, b }) => bridgeCall(
      () => bridge.setDiffuseColor(mesh_name, material_name, r, g, b),
      (result) => result.success
        ? `Diffuse color of ${result.mesh ?? mesh_name}/${result.material ?? material_name} set to RGB(${r}, ${g}, ${b})`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "get_material_properties",
    "Get opacity, glossiness, and specular values of a material. Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
    },
    async ({ mesh_name, material_name }) => bridgeCall(
      () => bridge.getMaterialProperties(mesh_name, material_name),
      (props) => {
        if (props.error) return `Failed: ${props.error}`;
        const lines = [`Material properties for ${props.mesh}/${props.material}:`];
        if (props.opacity !== undefined) lines.push(`  Opacity: ${props.opacity}`);
        if (props.glossiness !== undefined) lines.push(`  Glossiness: ${props.glossiness}`);
        if (props.specular !== undefined) lines.push(`  Specular: ${props.specular}`);
        return lines.join("\n");
      },
    )
  );

  server.tool(
    "set_material_opacity",
    "Set the opacity of a material (0.0 = transparent, 1.0 = opaque). Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
      opacity: z.number().min(0).max(1).describe("Opacity value (0.0-1.0)"),
    },
    async ({ mesh_name, material_name, opacity }) => bridgeCall(
      () => bridge.setMaterialOpacity(mesh_name, material_name, opacity),
      (result) => result.success
        ? `Opacity of ${result.mesh ?? mesh_name}/${result.material ?? material_name} set to ${result.opacity ?? opacity}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_material_glossiness",
    "Set the glossiness of a material (0.0 = matte, 1.0 = glossy). Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
      glossiness: z.number().min(0).max(1).describe("Glossiness value (0.0-1.0)"),
    },
    async ({ mesh_name, material_name, glossiness }) => bridgeCall(
      () => bridge.setMaterialGlossiness(mesh_name, material_name, glossiness),
      (result) => result.success
        ? `Glossiness of ${result.mesh ?? mesh_name}/${result.material ?? material_name} set to ${result.glossiness ?? glossiness}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_material_specular",
    "Set the specular weight of a material (0.0 = no specular, 1.0 = full specular). Use get_material_info first to find valid mesh and material names.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
      specular: z.number().min(0).max(1).describe("Specular weight (0.0-1.0)"),
    },
    async ({ mesh_name, material_name, specular }) => bridgeCall(
      () => bridge.setMaterialSpecular(mesh_name, material_name, specular),
      (result) => result.success
        ? `Specular of ${result.mesh ?? mesh_name}/${result.material ?? material_name} set to ${result.specular ?? specular}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "get_shader_parameters",
    "Get the Digital Human Shader parameters for a material (skin roughness scales, SSS radius/falloff/IOR, micronormal strength, specular, etc.). Each value is a list of floats. Use get_material_info first for valid mesh/material names, then set_shader_parameter to change one.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
    },
    async ({ mesh_name, material_name }) => bridgeCall(
      () => bridge.getShaderParameters(mesh_name, material_name),
      (result) => {
        if (!result.success) return `Failed: ${result.error}`;
        const params = result.parameters ?? {};
        const names = Object.keys(params);
        if (names.length === 0) return `${result.material ?? material_name}: no shader parameters (shader: ${result.shader ?? "unknown"}).`;
        const lines = names.map(n => `  - ${n} = [${params[n].map(v => v.toFixed(3)).join(", ")}]`);
        return `Shader '${result.shader ?? "?"}' on ${result.mesh ?? mesh_name}/${result.material ?? material_name} (${names.length} params):\n${lines.join("\n")}`;
      },
    )
  );

  server.tool(
    "set_shader_parameter",
    "Set one Digital Human Shader parameter on a material. Examples: 'Micro Roughness Scale' (skin shininess), 'SSS Radius'/'SSS Falloff' (subsurface scatter), 'MicroNormal Strength' (pore detail), '_Specular'. Discover names + current values with get_shader_parameters; the value list length must match the parameter.",
    {
      mesh_name: z.string().max(256).describe("Mesh name (from get_material_info)"),
      material_name: z.string().max(256).describe("Material name (from get_material_info)"),
      parameter_name: z.string().max(128).describe("Shader parameter name (from get_shader_parameters)"),
      values: z.array(z.number()).min(1).max(16).describe("Float value(s); length must match the parameter"),
    },
    async ({ mesh_name, material_name, parameter_name, values }) => bridgeCall(
      () => bridge.setShaderParameter(mesh_name, material_name, parameter_name, values),
      (result) => result.success
        ? `${result.mesh ?? mesh_name}/${result.material ?? material_name} '${result.parameter ?? parameter_name}' set to [${(result.values ?? values).join(", ")}]`
        : `Failed: ${result.error}`,
    )
  );
}
