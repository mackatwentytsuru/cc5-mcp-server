/**
 * Content presets by script: apply_preset (eyelash presets and elements, SkinGen makeup, ...) and
 * list_presets. The bridge answers only the known question windows while it applies; see
 * cc5-plugin/cc5_ui.py (WINDOW_RULES).
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { UiApplyPresetArgs, UiApplyPresetResult, UiPresetListResult } from "../types.js";
import { bridgeCall, bridgeCallRich, textContent, type ToolContent } from "../util.js";
import {
  failureContent,
  openWindowShots,
  pathProblem,
  runUiJob,
  stillRunningText,
  windowNeedsPerson,
  type WaitOptions,
} from "./ui-common.js";

export const PRESET_CATEGORIES = [
  "eyelash_preset",
  "eyelash_element",
  "makeup_eyelash",
  "makeup_eye",
  "makeup_lip",
  "makeup_full",
  "makeup_foundation",
  "makeup_eyebrow",
  "skingen_tools",
  "skin",
  "avatar_preset",
  "hair",
] as const;

const DEFAULT_FILE_SECONDS = 240;

export function formatApplyResult(result: UiApplyPresetResult): string {
  const lines: string[] = [];
  const files = result.files ?? [];
  lines.push(
    result.success
      ? `Applied ${files.length} file(s) to '${result.avatar ?? "the avatar"}'.`
      : `Failed: ${result.error ?? "not every file was applied"}`,
  );
  for (const file of files) {
    const name = file.path.split("/").pop() ?? file.path;
    const parts = [file.ok ? "ok" : "FAILED"];
    if (file.added && file.added.length > 0) parts.push(`added ${file.added.join(", ")}`);
    if (file.removed && file.removed.length > 0) parts.push(`removed ${file.removed.join(", ")}`);
    if (file.watched) parts.push(`items now: ${file.watched.join(", ") || "(none)"}`);
    if (file.error && !file.ok) parts.push(file.error);
    lines.push(`  - ${name}: ${parts.join("; ")}`);
  }
  if (result.skipped && result.skipped.length > 0) lines.push(`Not applied (an earlier file failed): ${result.skipped.join(", ")}`);
  if (result.answered && result.answered.length > 0) {
    lines.push(`Answered windows: ${result.answered.map((a) => `${a.pressed} ('${a.window}')`).join(", ")}`);
  }
  if (result.skingen) {
    lines.push(
      `SkinGen: editor ${result.skingen.editor_active ? "open" : "closed"}; layers: ${result.skingen.layers.join(", ") || "(none)"}`,
    );
  }
  if (result.note) lines.push(`Note: ${result.note}`);
  return lines.join("\n");
}

async function applyContent(
  bridge: CC5Bridge,
  body: UiApplyPresetArgs,
  fileCount: number,
  perFileSeconds: number,
  wait: WaitOptions,
): Promise<ToolContent[]> {
  const waitSeconds = perFileSeconds * fileCount + 30;
  const run = await runUiJob<UiApplyPresetResult>(bridge, () => bridge.uiApplyPreset(body), waitSeconds, wait);
  if ("refused" in run) return failureContent(run.refused.error ?? "the bridge refused to start the job");
  if (!run.outcome.finished) {
    return [
      textContent(stillRunningText(run.jobId, waitSeconds, run.outcome.status?.windows)),
      ...(await openWindowShots(bridge)),
    ];
  }
  const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
  const content: ToolContent[] = [textContent(formatApplyResult(result))];
  const blocked = (result.files ?? []).map((f) => f.blocked_by).find((w) => w);
  if (blocked) {
    content.push(textContent(windowNeedsPerson(blocked)), ...(await openWindowShots(bridge)));
  }
  return content;
}

export function registerPresetTools(server: McpServer, bridge: CC5Bridge, wait: WaitOptions = {}): void {
  server.tool(
    "apply_preset",
    "Apply content preset file(s) to the avatar WITHOUT the mouse: .ccAvatarPreset (eyelash presets), " +
      ".rlEyelashElement (eyelash strips), .ccSkinGenPreset (makeup: lip, eye, eyelash), other .cc*/.rl*/.i* " +
      "content (never .ccProject / .ccAvatar / .fbx). Uses RFileIO.LoadFile with the avatar selected. While it " +
      "runs, ONLY these question windows are answered: 'Apply Character Preset' / 'Apply Eyelash Elements' " +
      "(Apply, with 'Restore neutral lash strip' ticked unless restore_neutral_lash=false), 'add a new layer or " +
      "replace the current layer?' (layer_choice, default replace) and 'exit SkinGen editing mode?' (Yes). " +
      "Any other window (licence, purchase, login, update, terms, delete, overwrite, unknown) is NEVER pressed: " +
      "it is reported with a screenshot and a person decides. A SkinGen preset opens the SkinGen editor, which " +
      "hides hair, hat and the eyelash strips until skingen_editor active=false (bakes ~10 s). Files are applied " +
      "in order and the run stops at the first problem. Reports what was added/removed in the scene. " +
      "Find files with list_presets.",
    {
      file_path: z.string().min(1).max(4096).optional().describe("One preset file (full path)"),
      file_paths: z.array(z.string().min(1).max(4096)).min(1).max(10).optional()
        .describe("Several files, applied in order (e.g. an upper and a lower eyelash element)"),
      avatar_name: z.string().min(1).max(256).optional().describe("Avatar to apply to (default: the first avatar)"),
      layer_choice: z.enum(["replace", "add"]).optional()
        .describe("Answer to 'add a new layer or replace the current layer?' (default replace)"),
      restore_neutral_lash: z.boolean().optional()
        .describe("Tick 'Restore neutral lash strip' in the Apply window (default true)"),
      watch_prefix: z.string().min(1).max(64).optional()
        .describe("List scene items whose name starts with this after each file (e.g. 'Lash_')"),
      timeout_seconds: z.number().int().min(10).max(900).optional()
        .describe(`Seconds to wait per file for CC5 to settle (default ${DEFAULT_FILE_SECONDS})`),
    },
    async (args) => {
      const paths = args.file_paths ?? (args.file_path ? [args.file_path] : []);
      if (paths.length === 0) return { content: failureContent("give file_path or file_paths") };
      for (const path of paths) {
        const problem = pathProblem(path);
        if (problem) return { content: failureContent(`${problem}: ${path}`) };
      }
      const body: UiApplyPresetArgs = { file_paths: paths };
      const answers: NonNullable<UiApplyPresetArgs["answers"]> = {};
      if (args.layer_choice !== undefined) answers.layer_choice = args.layer_choice;
      if (args.restore_neutral_lash !== undefined) answers.restore_neutral_lash = args.restore_neutral_lash;
      if (Object.keys(answers).length > 0) body.answers = answers;
      if (args.avatar_name !== undefined) body.avatar_name = args.avatar_name;
      if (args.watch_prefix !== undefined) body.watch_prefix = args.watch_prefix;
      const perFile = args.timeout_seconds ?? DEFAULT_FILE_SECONDS;
      body.timeout_s = perFile;
      return bridgeCallRich(
        () => applyContent(bridge, body, paths.length, perFile, wait),
        (content) => content,
      );
    },
  );

  server.tool(
    "list_presets",
    "List preset files that are ON DISK in the CC5 content library, by category or '$/...' folder: eyelash " +
      "presets (.ccAvatarPreset) and elements (.rlEyelashElement), makeup (lip/eye/eyelash/full/foundation/" +
      "eyebrow .ccSkinGenPreset), SkinGen tools, skin, avatar presets, hair. Returns name, full path (pass it to " +
      "apply_preset) and folder. Content still in the cloud (not downloaded) is NOT listed; use `names` to check " +
      "which of the wanted presets are missing. `folder` with list_folders=true shows sub-folders to browse.",
    {
      category: z.enum(PRESET_CATEGORIES).optional().describe("Library area (or give folder)"),
      folder: z.string().min(2).max(512).regex(/^\$\//, "must start with '$/'").optional()
        .describe("A content folder such as '$/Makeup/Lip Makeup'"),
      query: z.string().max(128).optional().describe("Keep names containing this text"),
      names: z.array(z.string().min(1).max(128)).max(50).optional()
        .describe("Exact preset names you want; the reply lists the ones that are not on disk"),
      ext: z.string().regex(/^\.[A-Za-z0-9]{1,24}$/, "like .ccSkinGenPreset").optional().describe("Only this extension"),
      recursive: z.boolean().optional().describe("Include sub-folders (default true)"),
      list_folders: z.boolean().optional().describe("Only list the sub-folders of folder/category"),
      limit: z.number().int().min(1).max(1000).optional().describe("Most entries to return (default 200)"),
    },
    async (args) => {
      if (!args.category && !args.folder) return { content: failureContent("give category or folder") };
      return bridgeCall(
        () => bridge.uiListPresets(args),
        (result: UiPresetListResult) => {
          if (!result.success) return `Failed: ${result.error}`;
          if (result.subfolders) return `Sub-folders of ${result.folders?.join(", ")}:\n${result.subfolders.join("\n") || "(none)"}`;
          const lines = (result.presets ?? []).map((p) => `- ${p.name}${p.installed ? "" : " (not on disk)"}  ${p.path}`);
          const head = `${result.total ?? lines.length} preset(s)${result.truncated ? " (list cut off: use query or limit)" : ""}:`;
          const tail = [
            result.missing && result.missing.length > 0 ? `Not on disk (cloud or misspelled): ${result.missing.join(", ")}` : "",
            result.note ?? "",
          ].filter(Boolean);
          return [head, ...lines, ...tail].join("\n");
        },
      );
    },
  );
}
