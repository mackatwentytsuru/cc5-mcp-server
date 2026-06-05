/**
 * Light control tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerLightTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "get_lights",
    "List all lights in the CC5 scene. Returns light names, IDs, and types (spot, point, directional).",
    {},
    async () => bridgeCall(
      () => bridge.getLights(),
      (lights) => {
        if (lights.length === 0) return "No lights in the scene.";
        const lines = lights.map(l => `- ${l.name} (type: ${l.type}, ID: ${l.id})`);
        return `Found ${lights.length} light(s):\n${lines.join("\n")}`;
      },
    )
  );

  server.tool(
    "set_light_color",
    "Set the color of a light by name. RGB values are floats from 0.0 to 1.0. Use get_lights first to find available light names.",
    {
      light_name: z.string().max(256).describe("Name of the light to modify"),
      r: z.number().min(0).max(1).describe("Red component (0.0-1.0)"),
      g: z.number().min(0).max(1).describe("Green component (0.0-1.0)"),
      b: z.number().min(0).max(1).describe("Blue component (0.0-1.0)"),
    },
    async ({ light_name, r, g, b }) => bridgeCall(
      () => bridge.setLightColor(light_name, r, g, b),
      (result) => result.success
        ? `Light '${result.light ?? light_name}' color set to RGB(${r}, ${g}, ${b})`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "get_light_info",
    "Get detailed info (color + multiplier) for a named light. Use get_lights first to find available light names.",
    {
      light_name: z.string().max(256).describe("Name of the light to query"),
    },
    async ({ light_name }) => bridgeCall(
      () => bridge.getLightInfo(light_name),
      (info) => {
        if (info.error) return `Failed: ${info.error}`;
        const parts = [`Light '${info.name}' (${info.type})`];
        if (info.color) {
          parts.push(`Color: RGB(${info.color.r.toFixed(3)}, ${info.color.g.toFixed(3)}, ${info.color.b.toFixed(3)})`);
        }
        if (info.multiplier !== null && info.multiplier !== undefined) {
          parts.push(`Multiplier: ${info.multiplier}`);
        }
        if (info.active !== null && info.active !== undefined) {
          parts.push(`Active: ${info.active ? "on" : "off"}`);
        }
        if (info.cast_shadow !== null && info.cast_shadow !== undefined) {
          parts.push(`Cast shadow: ${info.cast_shadow ? "yes" : "no"}`);
        }
        if (info.darken_shadow_strength !== null && info.darken_shadow_strength !== undefined) {
          parts.push(`Shadow darkness: ${info.darken_shadow_strength.toFixed(3)}`);
        }
        if (info.range !== null && info.range !== undefined) {
          parts.push(`Range: ${info.range}`);
        }
        return parts.join("\n");
      },
    )
  );

  server.tool(
    "set_light_multiplier",
    "Set the intensity multiplier of a light by name. Higher values = brighter. Use get_lights first to find available light names.",
    {
      light_name: z.string().max(256).describe("Name of the light to modify"),
      multiplier: z.number().min(0).describe("Intensity multiplier (>= 0)"),
    },
    async ({ light_name, multiplier }) => bridgeCall(
      () => bridge.setLightMultiplier(light_name, multiplier),
      (result) => result.success
        ? `Light '${result.light ?? light_name}' multiplier set to ${result.multiplier ?? multiplier}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_light_active",
    "Turn a light on or off by name. Use this to shape a scene by toggling key/fill/rim lights (CC5 lighting workflow). Use get_lights first to find available light names.",
    {
      light_name: z.string().max(256).describe("Name of the light to toggle"),
      active: z.boolean().describe("true = on, false = off"),
    },
    async ({ light_name, active }) => bridgeCall(
      () => bridge.setLightActive(light_name, active),
      (result) => result.success
        ? `Light '${result.light ?? light_name}' turned ${(result.active ?? active) ? "on" : "off"}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_light_shadow",
    "Control a light's shadows: toggle shadow casting and/or set shadow darkness (0.0-1.0; lower = softer/lighter shadows). Provide at least one of cast_shadow / darken_strength. Use get_lights first to find available light names.",
    {
      light_name: z.string().max(256).describe("Name of the light to modify"),
      cast_shadow: z.boolean().optional().describe("Enable/disable shadow casting"),
      darken_strength: z.number().min(0).max(1).optional().describe("Shadow darkness 0.0-1.0 (lower = softer)"),
    },
    async ({ light_name, cast_shadow, darken_strength }) => bridgeCall(
      () => bridge.setLightShadow(
        light_name,
        cast_shadow === undefined ? null : cast_shadow,
        darken_strength === undefined ? null : darken_strength,
      ),
      (result) => {
        if (!result.success) return `Failed: ${result.error}`;
        const bits: string[] = [];
        if (result.cast_shadow !== undefined) bits.push(`cast shadow ${result.cast_shadow ? "on" : "off"}`);
        if (result.darken_shadow_strength !== undefined) bits.push(`darkness ${result.darken_shadow_strength}`);
        return `Light '${result.light ?? light_name}' shadow updated${bits.length ? `: ${bits.join(", ")}` : ""}`;
      },
    )
  );
}
