/**
 * SkinGen (Modify > Appearance editor) by script: skingen_state, skingen_editor, skingen_layer.
 * The bridge drives the editor's own widgets (cc5-plugin/cc5_skingen.py). Confirmation windows that
 * CC5 opens (other than "exit SkinGen editing mode?") are never answered here.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type {
  SkinGenEditorResult,
  SkinGenLayer,
  SkinGenLayerArgs,
  SkinGenLayerResult,
  SkinGenState,
} from "../types.js";
import { bridgeCall, bridgeCallRich, textContent, type ToolContent } from "../util.js";
import {
  failureContent,
  openWindowShots,
  refusedContent,
  runUiJob,
  stillRunningText,
  windowNeedsPerson,
  type WaitOptions,
} from "./ui-common.js";

const DEFAULT_SETTLE_SECONDS = 120;
const LAYER_WAIT_SECONDS = 90;

/** How long the tool waits for an editor switch: the bridge waits up to 60 s for the switch, then settles twice. */
export function editorWaitSeconds(timeoutSeconds: number | undefined): number {
  return 60 + 2 * ((timeoutSeconds ?? DEFAULT_SETTLE_SECONDS) + 10) + 30;
}

export function formatLayers(layers: SkinGenLayer[] | undefined): string {
  if (!layers || layers.length === 0) return "  (no layers)";
  return layers
    .map((l) => {
      const flags = [l.visible === false ? "HIDDEN" : l.visible === true ? "visible" : "visibility unknown"];
      if (l.selected) flags.push("selected");
      return `  ${l.index}: ${l.name ?? "(unnamed)"} [${flags.join(", ")}]`;
    })
    .join("\n");
}

export function formatSkinGenState(state: SkinGenState): string {
  if (!state.success) return `Failed: ${state.error}`;
  const head = state.editor_found
    ? `SkinGen editor: ${state.editor_active ? "ON" : "off"}${state.tab ? `, tab ${state.tab}` : ""}`
    : "SkinGen editor switch not found";
  const lines = [head];
  if (state.combos) lines.push(`Selected: ${Object.entries(state.combos).map(([k, v]) => `${k}=${v}`).join(", ")}`);
  lines.push(`Layers (${state.layers?.length ?? 0}):`, formatLayers(state.layers));
  if (state.opacity !== null && state.opacity !== undefined) lines.push(`Opacity of the selected layer: ${state.opacity}`);
  if (state.hint) lines.push(state.hint);
  return lines.join("\n");
}

/** Why the arguments of skingen_layer cannot work, or undefined. Checked before anything is sent. */
export function layerProblem(args: {
  action: string;
  index?: number;
  name?: string;
  opacity?: number;
  scope?: string;
  confirm_delete?: boolean;
}): string | undefined {
  const needsRow = args.action !== "delete" || (args.scope ?? "selected_layer") === "selected_layer";
  if (needsRow && args.index === undefined && !args.name) return "give index or name of the layer";
  if (args.action === "opacity" && args.opacity === undefined) return "opacity (0-100) is required for action opacity";
  if (args.action === "delete" && args.confirm_delete !== true) {
    return "delete needs confirm_delete=true (it cannot be undone from here)";
  }
  return undefined;
}

export function registerSkinGenTools(server: McpServer, bridge: CC5Bridge, wait: WaitOptions = {}): void {
  server.tool(
    "skingen_state",
    "Read the SkinGen editor (Modify > Appearance): whether the editor is on, which tab, the layers (index, " +
      "name, visible / HIDDEN, selected) and the opacity of the selected layer. Read-only. Apply a SkinGen " +
      "preset with apply_preset first; it opens the editor.",
    {},
    async () => bridgeCall(() => bridge.uiSkinGenState(), formatSkinGenState),
  );

  server.tool(
    "skingen_editor",
    "Turn the SkinGen editor on or off. Off BAKES the layers into the textures (~10 s, CC5 is busy) and CC5 asks " +
      "'exit SkinGen editing mode?'; that question is answered Yes (or No with exit_answer) and the tool waits " +
      "until CC5 is quiet. While the editor is on, hair, hat and eyelash strips are hidden, so switch it off " +
      "before a face photo. Any other window that appears is NOT answered: it is reported with a screenshot.",
    {
      active: z.boolean().describe("true = editor on, false = off (bakes)"),
      exit_answer: z.enum(["yes", "no"]).optional().describe("Answer to 'exit SkinGen editing mode?' (default yes)"),
      timeout_seconds: z.number().int().min(10).max(600).optional()
        .describe(`Seconds CC5 may take to settle after the switch changed (default ${DEFAULT_SETTLE_SECONDS})`),
    },
    async ({ active, exit_answer, timeout_seconds }) =>
      bridgeCallRich(async (): Promise<ToolContent[]> => {
        const waitSeconds = editorWaitSeconds(timeout_seconds);
        const run = await runUiJob<SkinGenEditorResult>(
          bridge,
          () => bridge.uiSkinGenEditor({ active, ...(exit_answer ? { exit_answer } : {}), ...(timeout_seconds ? { timeout_s: timeout_seconds } : {}) }),
          waitSeconds,
          wait,
        );
        if ("refused" in run) return refusedContent(run.refused);
        if (!run.outcome.finished) {
          return [textContent(stillRunningText(run.jobId, waitSeconds, run.outcome.status)), ...(await openWindowShots(bridge))];
        }
        const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
        const answered = (result.answered ?? []).map((a) => a.pressed).join(", ");
        const text = result.success
          ? `SkinGen editor is now ${result.editor_active ? "ON" : "off"}${result.changed ? "" : " (it already was)"}.` +
            `${answered ? ` Answered: ${answered}.` : ""}${result.waited_s ? ` Waited ${result.waited_s}s for CC5.` : ""}`
          : `Failed: ${result.error}`;
        const content: ToolContent[] = [textContent(text)];
        if (result.blocked_windows && result.blocked_windows.length > 0) {
          content.push(textContent(`Windows left alone: ${result.blocked_windows.map((b) => `'${b.title}' (${b.why})`).join("; ")}`));
        }
        if (result.blocked_by) content.push(textContent(windowNeedsPerson(result.blocked_by)));
        if (!result.success) content.push(...(await openWindowShots(bridge)));    // see what is on screen
        return content;
      }, (content) => content),
  );

  server.tool(
    "skingen_layer",
    "Work on one SkinGen layer without the mouse: select, show, hide, set opacity (0-100, the box of the " +
      "SELECTED layer; the layer is selected first), or delete. Address the layer by index or by name (names " +
      "must be unique; use skingen_state to see them). delete needs confirm_delete=true and a scope: " +
      "selected_layer (default), current_material or all_material; a confirmation window CC5 opens is NOT " +
      "answered, it is reported with a screenshot for a person. Every call reads the result back and says " +
      "whether CC5 really changed.",
    {
      action: z.enum(["select", "show", "hide", "opacity", "delete"]).describe("What to do"),
      index: z.number().int().min(0).max(500).optional().describe("Layer number (row, from 0)"),
      name: z.string().min(1).max(128).optional().describe("Layer name (when unique)"),
      opacity: z.number().int().min(0).max(100).optional().describe("Opacity 0-100 for action opacity"),
      scope: z.enum(["selected_layer", "current_material", "all_material"]).optional()
        .describe("For delete: Selected Layer (default) / Current Material / All Material"),
      confirm_delete: z.boolean().optional().describe("Must be true for action delete"),
    },
    async (args) => {
      const problem = layerProblem(args);
      if (problem) return { content: failureContent(problem) };
      const body: SkinGenLayerArgs = { action: args.action };
      if (args.index !== undefined) body.index = args.index;
      if (args.name !== undefined) body.name = args.name;
      if (args.opacity !== undefined) body.opacity = args.opacity;
      if (args.scope !== undefined) body.scope = args.scope;
      if (args.confirm_delete === true) body.confirm = true;
      return bridgeCallRich(async (): Promise<ToolContent[]> => {
        const run = await runUiJob<SkinGenLayerResult>(bridge, () => bridge.uiSkinGenLayer(body), LAYER_WAIT_SECONDS, wait);
        if ("refused" in run) return refusedContent(run.refused);
        if (!run.outcome.finished) {
          return [textContent(stillRunningText(run.jobId, LAYER_WAIT_SECONDS, run.outcome.status)), ...(await openWindowShots(bridge))];
        }
        const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
        const content: ToolContent[] = [textContent(formatLayerResult(args.action, result))];
        if (result.blocked_by) content.push(textContent(windowNeedsPerson(result.blocked_by)), ...(await openWindowShots(bridge)));
        return content;
      }, (content) => content);
    },
  );
}

export function formatLayerResult(action: string, result: SkinGenLayerResult): string {
  if (!result.success) {
    const menu = result.menu && result.menu.length > 0 ? ` Menu entries: ${result.menu.join(" | ")}.` : "";
    return `Failed: ${result.error}.${menu}${result.layers ? `\nLayers:\n${formatLayers(result.layers)}` : ""}`;
  }
  const lines: string[] = [];
  if (action === "opacity") {
    lines.push(`Opacity of layer ${String(result.layer)}: ${result.opacity_before} -> ${result.opacity_after} (read back from CC5).`);
  } else if (action === "delete") {
    const unchanged = result.layers_before !== undefined && result.layers_before === result.layers_after;
    lines.push(`Deleted (${result.scope}): ${result.layers_before} -> ${result.layers_after} layer(s).` +
      (unchanged ? " The count did not change (normal for current/all material when nothing was left); check skingen_state." : ""));
  } else {
    lines.push(`${action} done.`);
  }
  lines.push("Layers now:", formatLayers(result.layers));
  return lines.join("\n");
}
