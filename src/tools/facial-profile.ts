/**
 * Facial expression-profile tools for CC5.
 *
 *  - get_facial_profile: detect the current avatar's expression profile
 *    (RLPy GetProfileType + GetExpressionSetUid + slider-count breakdown).
 *  - convert_facial_profile: swap the active facial profile by LoadProfile of a
 *    target .ccFacialProfile asset. dry_run by default (safe / no scene change).
 *    RLPy has no direct profile-type / one-click-ExPlus-upgrade API.
 */

import path from "node:path";
import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

const NULL_BYTE = String.fromCharCode(0);

function validateProfilePath(p: string): string | null {
  if (!p) return null; // empty is allowed (inspection-only dry run)
  if (p.includes(NULL_BYTE)) return "Path contains null byte";
  if (p.includes("..")) return "Path traversal ('..') is not allowed";
  if (!path.isAbsolute(p)) return "Path must be absolute";
  return null;
}

export function registerFacialProfileTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "get_facial_profile",
    "Detect the current avatar's facial expression profile (read-only). Returns the authoritative RLPy profile type (CC5MetaHuman/CC4Extended/CC4Standard/Traditional), the expression-set UID, a per-category slider-count breakdown, and a heuristic ExPlus/HD/MetaHuman/Traditional class plus ARKit-capability. Use this for Phase-0 profile judgement before a Route-B UE export.",
    {},
    async () => bridgeCall(
      () => bridge.getFacialProfile(),
      (info) => {
        if (!info.success) return `Failed: ${info.error}`;
        const lines: string[] = [];
        lines.push(`Avatar: ${info.avatar ?? "?"}`);
        lines.push(`Profile type: ${info.profile_type ?? "?"} (id ${info.profile_type_id ?? "?"})`);
        lines.push(`Expression-set UID: ${info.expression_set_uid ?? "?"}`);
        lines.push(`Heuristic class: ${info.heuristic_class ?? "?"}`);
        lines.push(`Total sliders: ${info.total_sliders ?? 0} across ${info.category_count ?? 0} categories`);
        lines.push(`ARKit-capable: ${info.arkit_capable ? "yes" : "no"}`);
        const counts = info.category_slider_counts ?? {};
        const cats = Object.keys(counts);
        if (cats.length) {
          lines.push("Categories:");
          for (const c of cats) lines.push(`  - ${c}: ${counts[c]}`);
        }
        return lines.join("\n");
      },
    ),
  );

  server.tool(
    "convert_facial_profile",
    "Swap the current avatar's facial profile by LOADING a target .ccFacialProfile asset (RLPy RIFacialProfileComponent.LoadProfile). NOTE: RLPy exposes no direct profile-type conversion nor the F8 'Corrective enable' one-click ExPlus upgrade — a pre-built target profile file is required. dry_run defaults to TRUE (inspects + validates only, no scene change). Recommended usage is a temporary switch before export then convert back to a backup to restore the original: (1) backup_current_to saves the current profile, (2) export_fbx, (3) convert back to the backup.",
    {
      target_profile_path: z.string().max(1024).default("").describe("Absolute path to a target .ccFacialProfile asset to load. Required when dry_run=false."),
      dry_run: z.boolean().default(true).describe("TRUE (default): inspect + validate only, no scene change. FALSE: actually LoadProfile (modifies the avatar)."),
      backup_current_to: z.string().max(1024).default("").describe("Absolute path to SaveProfile the current profile to before loading (enables restore). Optional."),
    },
    async ({ target_profile_path, dry_run, backup_current_to }) => {
      const targetErr = validateProfilePath(target_profile_path);
      if (targetErr) return { content: [{ type: "text" as const, text: `target_profile_path: ${targetErr}` }] };
      const backupErr = validateProfilePath(backup_current_to);
      if (backupErr) return { content: [{ type: "text" as const, text: `backup_current_to: ${backupErr}` }] };

      return bridgeCall(
        () => bridge.convertFacialProfile({ target_profile_path, dry_run, backup_current_to }),
        (res) => {
          if (!res.success) return `Failed: ${res.error}`;
          const lines: string[] = [];
          if (res.dry_run) {
            const cur = res.current_profile ?? {};
            lines.push("DRY RUN (no scene change).");
            lines.push(`Current: ${cur.profile_type ?? "?"} / UID ${cur.expression_set_uid ?? "?"} / ${cur.total_sliders ?? 0} sliders`);
            lines.push(`Target: ${res.target_profile_path || "(none)"} — valid: ${res.target_path_valid ? "yes" : "no"}`);
            if (res.path_error) lines.push(`Path error: ${res.path_error}`);
          } else {
            const before = res.before ?? {};
            const after = res.after ?? {};
            lines.push(`Applied. Before: ${before.profile_type ?? "?"} (${before.total_sliders ?? 0}) -> After: ${after.profile_type ?? "?"} (${after.total_sliders ?? 0})`);
            if (res.backup_saved_to) lines.push(`Backup saved to: ${res.backup_saved_to}`);
          }
          if (res.notes && res.notes.length) lines.push(`Notes: ${res.notes.join(" | ")}`);
          return lines.join("\n");
        },
      );
    },
  );
}

// Re-export for tests
export const _internal = { validateProfilePath };
