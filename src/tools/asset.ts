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
  if (!ALLOWED_ASSET_EXTENSIONS.has(ext)) {
    return `Disallowed file extension: ${ext}. Allowed: ${[...ALLOWED_ASSET_EXTENSIONS].join(", ")}`;
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
    "Export the current avatar as an FBX file with optional Mesh-to-MetaHuman friendly settings. Use this after completing character adjustments to save the result for game engines (UE5/Unity) or 3D applications.",
    {
      output_path: z.string().describe("Absolute path for the exported FBX file (e.g., 'C:/Export/character.fbx')"),
      target_tool: z.enum(["UE5", "Default", "Maya", "Unity", "Unreal"]).optional()
        .describe("Target tool preset. 'UE5'/'Unreal' applies Unreal-friendly flags (Y-up, UE bone axis)."),
      sub_d_level: z.number().int().min(0).max(2).optional()
        .describe("HD subdivision level applied before export (0/1/2). Higher = smoother mesh."),
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
