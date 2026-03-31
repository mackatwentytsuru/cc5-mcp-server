/**
 * High-level character creation tools.
 * These tools provide semantic, natural-language-friendly interfaces
 * for character modification.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";

/**
 * Preset body type mappings.
 * Maps descriptive terms to morph combinations.
 */
const BODY_PRESETS: Record<string, Array<{ id: string; value: number }>> = {
  athletic: [
    { id: "Muscular", value: 0.6 },
    { id: "Fat", value: 0.1 },
    { id: "Thin", value: 0.2 },
  ],
  muscular: [
    { id: "Muscular", value: 0.9 },
    { id: "Fat", value: 0.05 },
    { id: "Thin", value: 0.1 },
  ],
  slim: [
    { id: "Thin", value: 0.7 },
    { id: "Fat", value: 0.0 },
    { id: "Muscular", value: 0.1 },
  ],
  heavy: [
    { id: "Fat", value: 0.7 },
    { id: "Thin", value: 0.0 },
    { id: "Muscular", value: 0.2 },
  ],
  average: [
    { id: "Fat", value: 0.3 },
    { id: "Thin", value: 0.3 },
    { id: "Muscular", value: 0.3 },
  ],
};

export function registerCharacterTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "apply_body_preset",
    "Apply a predefined body type to the current character. Available presets: athletic, muscular, slim, heavy, average.",
    {
      preset: z.enum(["athletic", "muscular", "slim", "heavy", "average"])
        .describe("Body type preset name"),
      intensity: z.number().min(0).max(1).default(1.0)
        .describe("How strongly to apply the preset (0.0-1.0). Default 1.0"),
    },
    async ({ preset, intensity }) => {
      const morphs = BODY_PRESETS[preset];
      if (!morphs) {
        return {
          content: [{ type: "text" as const, text: `Unknown preset: ${preset}` }],
        };
      }

      const scaled = morphs.map(m => ({
        id: m.id,
        value: m.value * intensity,
      }));

      const result = await bridge.setMultipleMorphs(scaled);
      return {
        content: [{
          type: "text" as const,
          text: result.success
            ? `Applied '${preset}' body preset at ${Math.round(intensity * 100)}% intensity`
            : `Failed: ${result.error}`,
        }],
      };
    }
  );

  server.tool(
    "describe_character",
    "Get a natural language description of the current character's appearance based on active morph values. Useful for understanding what the character looks like before making changes.",
    {},
    async () => {
      const info = await bridge.getAvatarInfo();
      if (!info) {
        return {
          content: [{ type: "text" as const, text: "No avatar in the scene." }],
        };
      }

      const morphs = info.active_morphs;
      const descriptions: string[] = [];

      // Body analysis
      const fat = morphs["Fat"] ?? 0;
      const thin = morphs["Thin"] ?? 0;
      const muscular = morphs["Muscular"] ?? 0;

      if (muscular > 0.5) descriptions.push("muscular build");
      else if (fat > 0.5) descriptions.push("heavy build");
      else if (thin > 0.5) descriptions.push("slim build");
      else descriptions.push("average build");

      // Head
      const headScale = morphs["Head Scale"] ?? 0;
      if (headScale > 0.5) descriptions.push("larger head");
      else if (headScale < -0.3) descriptions.push("smaller head");

      const morphCount = Object.keys(morphs).length;
      let text = `Character: ${info.name}\n`;
      text += `Description: ${descriptions.join(", ")}\n`;
      text += `Total active morphs: ${morphCount}\n`;
      text += `\nDetailed morph values:\n`;
      for (const [id, value] of Object.entries(morphs)) {
        text += `  ${id}: ${(value * 100).toFixed(0)}%\n`;
      }

      return { content: [{ type: "text" as const, text }] };
    }
  );
}
