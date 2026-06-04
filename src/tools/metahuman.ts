/**
 * Mesh-to-MetaHuman pipeline helpers for CC5.
 *
 * Automates the Solomon Jagwe workflow chapters 3-1/3-2/4:
 *  - bake_skin_textures: Skin Editor -> Bake at given resolution
 *  - export_head_metahuman: File -> Export -> Export Head -> Mesh to MetaHuman
 */

import path from "node:path";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

const ALLOWED_RESOLUTIONS = [256, 512, 1024, 2048, 4096] as const;

const NULL_BYTE = String.fromCharCode(0);

function validateOutputDir(dir: string): string | null {
  if (dir.includes(NULL_BYTE)) return "Path contains null byte";
  if (dir.includes("..")) return "Path traversal ('..') is not allowed";
  if (!path.isAbsolute(dir)) return "output_dir must be an absolute path";
  return null;
}

function validateCharacterName(name: string): string | null {
  if (!name || !name.trim()) return "character_name must not be empty";
  if (name.length > 128) return "character_name too long (max 128)";
  // Disallow path separators and dangerous chars
  if (/[\\\/:*?"<>|]/.test(name)) {
    return "character_name contains invalid characters";
  }
  return null;
}

export function registerMetaHumanTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "bake_skin_textures",
    "Trigger CC5's Skin Editor / SkinGen 'Bake Textures' workflow. CC5 does not expose a one-shot bake API, so this tool opens the Skin Editor panel and reports whether manual confirmation is required. Used in Mesh-to-MetaHuman prep (Chapter 3-1).",
    {
      resolution: z.union([
        z.literal(256), z.literal(512), z.literal(1024), z.literal(2048), z.literal(4096),
      ]).default(4096).describe("Texture resolution to bake at. 4096 (4K) is recommended for MetaHuman."),
    },
    async ({ resolution }) => bridgeCall(
      () => bridge.bakeSkinTextures(resolution),
      (res) => {
        const parts: string[] = [];
        if (res.success) {
          parts.push(`Skin bake initiated at ${res.resolution}px`);
          if (res.triggered_action) parts.push(`Triggered: ${res.triggered_action}`);
        } else {
          parts.push(`Bake automation failed: ${res.error}`);
        }
        if (res.manual_step_required && res.instructions) {
          parts.push(`Manual step: ${res.instructions}`);
        }
        if (res.notes && res.notes.length) parts.push(`Notes: ${res.notes.join("; ")}`);
        return parts.join("\n");
      },
    ),
  );

  server.tool(
    "export_head_metahuman",
    "Trigger CC5's 'File -> Export -> Export Head -> Mesh to MetaHuman' pipeline (Chapter 4). Opens the relevant menu/dialog; user must confirm output path and gender in the resulting CC5 dialog.",
    {
      output_dir: z.string().describe("Absolute directory where the Mesh-to-MetaHuman files will be written (e.g., 'D:/epic/BYONDEgirls57Stage/Content/Characters/CC5/BEYONZ/')"),
      character_name: z.string().describe("Character name (e.g., 'BEYONZ'). Used as the base file name."),
      gender: z.enum(["Male", "Female"]).default("Female").describe("Character gender - selects 'Mesh to MetaHuman Male' or 'Mesh to MetaHuman Female'."),
    },
    async ({ output_dir, character_name, gender }) => {
      const dirError = validateOutputDir(output_dir);
      if (dirError) return { content: [{ type: "text" as const, text: dirError }] };
      const nameError = validateCharacterName(character_name);
      if (nameError) return { content: [{ type: "text" as const, text: nameError }] };

      return bridgeCall(
        () => bridge.exportHeadMetaHuman(output_dir, character_name, gender),
        (res) => {
          const parts: string[] = [];
          if (res.success) {
            parts.push(`Mesh-to-MetaHuman export initiated for ${character_name} (${gender})`);
            if (res.triggered_action) parts.push(`Triggered: ${res.triggered_action}`);
          } else {
            parts.push(`Export automation failed: ${res.error}`);
          }
          if (res.manual_step_required && res.instructions) {
            parts.push(`Manual step:\n${res.instructions}`);
          }
          if (res.notes && res.notes.length) parts.push(`Notes: ${res.notes.join("; ")}`);
          return parts.join("\n");
        },
      );
    },
  );
}

// Re-export for tests
export const _internal = { ALLOWED_RESOLUTIONS, validateOutputDir, validateCharacterName };
