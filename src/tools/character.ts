/**
 * High-level character creation tools.
 * These tools provide semantic, natural-language-friendly interfaces
 * for character modification.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

/**
 * Preset body type mappings.
 * Maps descriptive terms to morph combinations.
 */
export const BODY_PRESETS: Record<string, Array<{ morph_id: string; value: number }>> = {
  athletic: [
    { morph_id: "cc embed morphs/embed_full_body6", value: 0.6 },   // Body Muscular A
    { morph_id: "essential body morphs/pack_full_body1", value: 0.1 }, // Body Fat A
    { morph_id: "cc embed morphs/embed_full_body5", value: 0.2 },   // Body Thin
  ],
  muscular: [
    { morph_id: "cc embed morphs/embed_full_body6", value: 0.9 },   // Body Muscular A
    { morph_id: "essential body morphs/pack_full_body1", value: 0.05 }, // Body Fat A
    { morph_id: "cc embed morphs/embed_full_body5", value: 0.1 },   // Body Thin
  ],
  slim: [
    { morph_id: "cc embed morphs/embed_full_body5", value: 0.7 },   // Body Thin
    { morph_id: "essential body morphs/pack_full_body1", value: 0.0 }, // Body Fat A
    { morph_id: "cc embed morphs/embed_full_body6", value: 0.1 },   // Body Muscular A
  ],
  heavy: [
    { morph_id: "essential body morphs/pack_full_body1", value: 0.7 }, // Body Fat A
    { morph_id: "cc embed morphs/embed_full_body5", value: 0.0 },   // Body Thin
    { morph_id: "cc embed morphs/embed_full_body6", value: 0.2 },   // Body Muscular A
  ],
  average: [
    { morph_id: "essential body morphs/pack_full_body1", value: 0.3 }, // Body Fat A
    { morph_id: "cc embed morphs/embed_full_body5", value: 0.3 },   // Body Thin
    { morph_id: "cc embed morphs/embed_full_body6", value: 0.3 },   // Body Muscular A
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
      const scaled = morphs.map(m => ({
        morph_id: m.morph_id,
        value: m.value * intensity,
      }));

      return bridgeCall(
        () => bridge.setMultipleMorphs(scaled),
        (result) => result.success
          ? `Applied '${preset}' body preset at ${Math.round(intensity * 100)}% intensity`
          : `Failed: ${result.error}`,
      );
    }
  );

  server.tool(
    "describe_character",
    "Get a natural language description of the current character's appearance based on active morph values. Useful for understanding what the character looks like before making changes.",
    {},
    async () => bridgeCall(
      () => bridge.getAvatarInfo(),
      (info) => {
        if (!info) return "No avatar in the scene.";

        const morphs = info.active_morphs;
        const descriptions: string[] = [];

        const fat = morphs["essential body morphs/pack_full_body1"] ?? morphs["cc embed morphs/embed_full_body3"] ?? 0;
        const thin = morphs["cc embed morphs/embed_full_body5"] ?? 0;
        const muscular = morphs["cc embed morphs/embed_full_body6"] ?? morphs["essential body morphs/pack_full_body4"] ?? 0;

        if (muscular > 0.5) descriptions.push("muscular build");
        else if (fat > 0.5) descriptions.push("heavy build");
        else if (thin > 0.5) descriptions.push("slim build");
        else descriptions.push("average build");

        const headScale = morphs["cc embed morphs/embed_full_head9"] ?? 0;
        if (headScale > 0.5) descriptions.push("larger head");
        else if (headScale < -0.3) descriptions.push("smaller head");

        const morphCount = Object.keys(morphs).length;
        let text = `Character: ${info.name}\n`;
        text += `Description: ${descriptions.join(", ")}\n`;
        text += `Total active morphs: ${morphCount}\n\nDetailed morph values:\n`;
        for (const [id, value] of Object.entries(morphs)) {
          text += `  ${id}: ${(value * 100).toFixed(0)}%\n`;
        }
        return text;
      },
    )
  );
}
