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
}
