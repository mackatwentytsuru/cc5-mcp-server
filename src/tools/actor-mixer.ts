/**
 * ActorMIXER PRO "Create Mixer Assets" tool for CC5.
 *
 * Drives CC5's native ActorMIXER PRO dialog (qtCreateMixerSliderAction →
 * CreateMixerSliderDlg) in-process to generate mixer assets (.ccMixerPreset)
 * from the currently open avatar. The dialog runs a modal exec loop on the CC5
 * side, so the Python driver schedules everything via QTimer and returns
 * immediately. `confirm_create` is a hard safety gate: false runs a dry-run
 * (sets every field, then CANCELs — no files written); true clicks Create once.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { CreateActorMixerOptions } from "../types.js";
import { bridgeCall } from "../util.js";

const headPartsShape = z
  .object({
    eyes: z.boolean().optional(),
    forehead: z.boolean().optional(),
    chin: z.boolean().optional(),
    mouth: z.boolean().optional(),
    ears: z.boolean().optional(),
    nose: z.boolean().optional(),
    head_shape: z.boolean().optional(),
  })
  .optional()
  .describe("Head-part checkboxes (default: all true).");

const bodyPartsShape = z
  .object({
    body: z.boolean().optional(),
    torso: z.boolean().optional(),
  })
  .optional()
  .describe("Body-part checkboxes (default: all false).");

const savePresetsShape = z
  .object({
    enabled: z.boolean().optional(),
    character: z.boolean().optional(),
    head: z.boolean().optional(),
    head_parts: z.boolean().optional(),
    body: z.boolean().optional(),
    body_parts: z.boolean().optional(),
  })
  .optional()
  .describe("'Save Presets' groupbox + children (default: enabled; character/head/head_parts/body on).");

const saveAvatarPresetsShape = z
  .object({
    enabled: z.boolean().optional(),
  })
  .optional()
  .describe("'Save Avatar Presets' groupbox (default: disabled).");

export function registerActorMixerTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "create_actor_mixer",
    "Generate ActorMIXER PRO mixer assets (.ccMixerPreset) from the currently open avatar by driving CC5's native 'Create Mixer Assets' dialog. SAFETY: confirm_create defaults to false, which previews the configuration then CANCELs the dialog (dry-run, no files written). Set confirm_create=true to actually create the presets. Requires the ActorMIXER PRO plugin in CC5.",
    {
      morph_name: z.string().optional()
        .describe("Slider/mixer name (qtSliderNameLineEdit). Defaults to the open avatar's name."),
      slider_path: z.string().optional()
        .describe("Optional slider path/category (qtSliderPathLineEdit)."),
      use_parts_folder: z.boolean().optional()
        .describe("Use under-part folder organization (qtUseUnderPartFolderCheckBox). Default false."),
      head_parts: headPartsShape,
      body_parts: bodyPartsShape,
      save_presets: savePresetsShape,
      save_avatar_presets: saveAvatarPresetsShape,
      confirm_create: z.boolean().default(false)
        .describe("Safety gate. false (default) = set fields then CANCEL (dry-run). true = click Create once."),
    },
    async (args) => {
      const opts: CreateActorMixerOptions = args;
      return bridgeCall(
        () => bridge.createActorMixer(opts),
        (result) => {
          if (!result.success) {
            const prefix = result.trial_content ? "Create Mixer Assets blocked (TRIAL content)" : "Create Mixer Assets failed";
            return `${prefix}: ${result.error ?? "unknown error"}`;
          }
          const name = result.morph_name ? ` for '${result.morph_name}'` : "";
          if (result.dry_run) {
            const dir = result.presets_dir ? ` Presets would be written under: ${result.presets_dir}.` : "";
            return `Create Mixer Assets dry-run${name}: dialog configured and CANCELLED (no files written).${dir} Set confirm_create=true to create.`;
          }
          const pollPath = result.poll_endpoint ?? "/actor_mixer/status";
          const presetsLine = result.new_presets && result.new_presets.length
            ? ` New presets: ${result.new_presets.join("; ")}.`
            : ` (Creation scheduled — poll GET ${pollPath} for new_presets.)`;
          const dir = result.presets_dir ? ` Presets dir: ${result.presets_dir}.` : "";
          return `Create Mixer Assets started${name}: Create clicked.${presetsLine}${dir}`;
        },
      );
    }
  );
}
