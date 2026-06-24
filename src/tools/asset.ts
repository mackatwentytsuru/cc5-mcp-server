/**
 * Asset loading and export tools for CC5.
 */

import path from "node:path";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

const ALLOWED_ASSET_EXTENSIONS = new Set([
  ".iavatar", ".ccavatar", ".ccproject", ".ccm",
  ".iclothes", ".ihair", ".iprop", ".ccfbx",
  ".iclothing", ".ishoe", ".iaccessory", ".ibody", ".iskin",
]);

function validateAssetPath(filePath: string): string | null {
  if (filePath.includes("..")) {
    return "Path traversal ('..') is not allowed";
  }
  const normalized = path.resolve(filePath);
  const ext = path.extname(normalized).toLowerCase();
  // Accept the explicit allowlist OR any CC5.1 / iClone content family (.cc*/.i*) —
  // browse_content returns .cc* content files (e.g. .ccShoes) that load_asset accepts.
  if (!ALLOWED_ASSET_EXTENSIONS.has(ext) && !ext.startsWith(".cc") && !ext.startsWith(".i")) {
    return `Disallowed file extension: ${ext}`;
  }
  return null;
}

function validateExportPath(filePath: string): string | null {
  if (filePath.includes("..")) {
    return "Path traversal ('..') is not allowed";
  }
  const normalized = path.resolve(filePath);
  const ext = path.extname(normalized).toLowerCase();
  if (ext !== ".fbx") {
    return `Export path must end with .fbx, got: ${ext}`;
  }
  return null;
}

export function registerAssetTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "load_asset",
    "Load a CC5 asset file into the scene. Supports .iAvatar, .ccm (character), .iClothes (clothing), .iHair (hair), .iProp (prop), and other CC5 formats.",
    {
      file_path: z.string().describe("Absolute path to the CC5 asset file (e.g., 'C:/Assets/MyChar.iAvatar')"),
    },
    async ({ file_path }) => {
      const pathError = validateAssetPath(file_path);
      if (pathError) {
        return { content: [{ type: "text" as const, text: pathError }] };
      }
      return bridgeCall(
        () => bridge.loadAsset(file_path),
        (result) => result.success ? `Asset loaded: ${file_path}` : `Failed to load asset: ${result.error}`,
      );
    }
  );

  server.tool(
    "export_fbx",
    "Export the current avatar as an FBX file, mirroring the CC5 'Export FBX' dialog (target tool preset, mesh+motion, subdivision, embed textures, frame rate). A bare filename (no directory) exports into D:\\CC5Export (override via the CC5_EXPORT_DIR env var). Recommended Unreal call: target_tool='UE5', export_motion=true, embed_textures=true, fps=30, sub_d_level=0.",
    {
      output_path: z.string().describe("Path for the exported FBX file. A bare filename (e.g. 'character.fbx') exports into D:\\CC5Export; an absolute path (e.g. 'C:/Export/character.fbx') is used as-is."),
      target_tool: z.enum(["UE5", "Default", "Maya", "Unity", "Unreal"]).optional()
        .describe("Target Tool Preset. 'UE5'/'Unreal' applies Unreal-friendly flags (Y-up, UE bone axis)."),
      sub_d_level: z.number().int().min(0).max(2).optional()
        .describe("HD Character Subdivision Level (0/1/2). Applied via SetExportLevel (no scene mutation). Higher = smoother mesh."),
      include_current_pose: z.boolean().optional()
        .describe("If true, keep current pose (do NOT force T-pose on motion first frame)."),
      delete_hidden_faces: z.boolean().optional()
        .describe("If true, removes hidden mesh faces from the exported FBX (EExportFbxOptions_RemoveHiddenMesh)."),
      use_smooth_mesh: z.boolean().optional()
        .describe("If true, uses CC5's 'Use Smooth Mesh' option (RExportFbxSetting.EnableBakeSubdivision). Emulated via sub_d_level if unavailable."),
      remove_eyelash: z.boolean().optional()
        .describe("If true, removes eyelash mesh (EExportFbxOptions_RemoveEyelash). Recommended for MetaHuman."),
      remove_tearline_occlusion: z.boolean().optional()
        .describe("If true, removes tear line + occlusion mesh (EExportFbxOptions_RemoveTearLineAndOcclusion). Recommended for MetaHuman."),
      embed_textures: z.boolean().optional()
        .describe("Texture Settings 'Embed Textures': bundle textures into the FBX. Recommended for Unreal."),
      export_motion: z.boolean().optional()
        .describe("FBX Options: true = 'Mesh and Motion' (default), false = 'Mesh' (mesh only)."),
      fps: z.number().int().positive().optional()
        .describe("Include Motion 'Frame Rate' (e.g. 30). Maps to RLPy.RFps.Fps{n}; unsupported values are skipped with a note."),
      motion_range: z.tuple([z.number().int(), z.number().int()]).optional()
        .describe("Include Motion frame range [start, end]. Omit for 'All' (the dialog default)."),
      convert_image_format: z.boolean().optional()
        .describe("Texture Settings 'Convert Image Format' (TIF -> PNG)."),
      texture_size: z.number().int().min(0).optional()
        .describe("Texture Settings 'Max Texture Size' in pixels (0 = original)."),
      options: z.number().int().optional()
        .describe("Raw EExportFbxOptions bitmask (advanced; usually leave 0)."),
    },
    async (args) => {
      const { output_path, options, ...extra } = args;
      const pathError = validateExportPath(output_path);
      if (pathError) {
        return { content: [{ type: "text" as const, text: pathError }] };
      }
      return bridgeCall(
        () => bridge.exportFbx(output_path, options ?? 0, extra as import("../types.js").ExportFbxOptions),
        (result) => {
          if (!result.success) return `Export failed: ${result.error}${result.notes ? `\nNotes: ${result.notes.join("; ")}` : ""}`;
          const notes = result.notes && result.notes.length ? `\nNotes: ${result.notes.join("; ")}` : "";
          return `FBX exported to: ${output_path} (target=${result.target_tool ?? "default"})${notes}`;
        },
      );
    }
  );
}
