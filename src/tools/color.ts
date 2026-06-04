/**
 * Convenience color shortcut tools for CC5.
 * Provides easy-to-use tools for setting eye, hair, and lip colors
 * without needing to know specific mesh/material names.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerColorTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "set_eye_color",
    "Set the eye color of the current avatar. RGB values are floats 0.0-1.0. This is a convenience shortcut that automatically finds the eye materials.",
    {
      r: z.number().min(0).max(1).describe("Red component (0.0-1.0)"),
      g: z.number().min(0).max(1).describe("Green component (0.0-1.0)"),
      b: z.number().min(0).max(1).describe("Blue component (0.0-1.0)"),
    },
    async ({ r, g, b }) => bridgeCall(
      () => bridge.setEyeColor(r, g, b),
      (result) => result.success
        ? `Eye color set to RGB(${r}, ${g}, ${b}). Applied to: ${result.applied_to?.join(", ") ?? "eye materials"}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_hair_color",
    "Set the hair color of the current avatar. RGB values are floats 0.0-1.0. This is a convenience shortcut that automatically finds all hair materials.",
    {
      r: z.number().min(0).max(1).describe("Red component (0.0-1.0)"),
      g: z.number().min(0).max(1).describe("Green component (0.0-1.0)"),
      b: z.number().min(0).max(1).describe("Blue component (0.0-1.0)"),
    },
    async ({ r, g, b }) => bridgeCall(
      () => bridge.setHairColor(r, g, b),
      (result) => result.success
        ? `Hair color set to RGB(${r}, ${g}, ${b}). Applied to: ${result.applied_to?.join(", ") ?? "hair materials"}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "set_lip_color",
    "Set the lip/mouth color of the current avatar. RGB values are floats 0.0-1.0. This is a convenience shortcut that targets lip and mouth materials. Note: may also affect surrounding skin if no separate lip material exists.",
    {
      r: z.number().min(0).max(1).describe("Red component (0.0-1.0)"),
      g: z.number().min(0).max(1).describe("Green component (0.0-1.0)"),
      b: z.number().min(0).max(1).describe("Blue component (0.0-1.0)"),
    },
    async ({ r, g, b }) => bridgeCall(
      () => bridge.setLipColor(r, g, b),
      (result) => result.success
        ? `Lip color set to RGB(${r}, ${g}, ${b}). Applied to: ${result.applied_to?.join(", ") ?? "lip materials"}`
        : `Failed: ${result.error}`,
    )
  );
}
