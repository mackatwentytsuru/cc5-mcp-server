/**
 * capture_framed_crop: render the framed view big, then cut a fixed box.
 *
 * dolly_camera's step size changed mid-session (15 cm, then 42 cm a notch), so options shot with
 * different dolly counts were different sizes. Framing with a preset and cutting the same box out of
 * a big render keeps every option at the same scale.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import type { UiCaptureCropArgs, UiCaptureCropResult } from "../types.js";
import { bridgeCallRich, pngContent, textContent, type ToolContent } from "../util.js";
import { failureContent, pathProblem, refusedContent, runUiJob, stillRunningText, type WaitOptions } from "./ui-common.js";

const WAIT_SECONDS = 180;           // a 3600 px render takes several seconds
const MAX_SIZE = 5600;              // Qt 5.15 cannot read back larger images

const box4 = z.array(z.number()).length(4);

function pngPathProblem(path: string | undefined): string | undefined {
  if (path === undefined) return undefined;
  return pathProblem(path) ?? (path.toLowerCase().endsWith(".png") ? undefined : "path must end with .png");
}

/** Why a crop_fraction cannot work (it must be an ordered box inside 0-1), or undefined. */
export function fractionProblem(box: number[] | undefined): string | undefined {
  if (!box) return undefined;
  const [x0, y0, x1, y1] = box;
  return 0 <= x0 && x0 < x1 && x1 <= 1 && 0 <= y0 && y0 < y1 && y1 <= 1
    ? undefined
    : "crop_fraction must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1";
}

export function formatCropResult(result: UiCaptureCropResult, asked?: number[]): string {
  if (!result.success) return `Failed: ${result.error}`;
  const lines = [`Rendered the '${result.view}' view at ${result.render_size?.join("x")} px: ${result.full_path}`];
  if (result.crop_path) {
    lines.push(`Cut box ${result.crop_box?.join(", ")} (${result.crop_size?.join("x")} px): ${result.crop_path}`);
    if (asked && result.crop_box && asked.some((v, i) => Math.round(v) !== result.crop_box?.[i])) {
      lines.push(`Warning: the box was changed to fit the render (asked ${asked.join(", ")}), so this crop is NOT the same size as one with the asked box.`);
    }
    if (!result.png_base64) lines.push(result.note ?? "The crop is too large to show here; open the file.");
  } else {
    const scale = result.preview_scale ? `; coordinates on this preview x ${result.preview_scale} = pixels of the full render` : "";
    lines.push(`No crop box was given: the picture is a scaled-down preview (${result.preview_size?.join("x") ?? "?"})${scale}. ` +
      "Measure the part you want on it, then pass crop (render pixels) or crop_fraction.");
  }
  if (result.warning) lines.push(`Warning: ${result.warning}`);
  lines.push("These paths are on the machine CC5 runs on.");
  return lines.join("\n");
}

export function registerFramedCaptureTools(server: McpServer, bridge: CC5Bridge, wait: WaitOptions = {}): void {
  server.tool(
    "capture_framed_crop",
    "Frame the camera with a PRESET view (default 'face'), render it BIG (default 3600x3600) and cut a fixed " +
      "box out of it, the same way every time, so crops of different options (eyelashes, lipsticks, ...) are the " +
      "same scale. Use this instead of dolly_camera when comparing options: the dolly step size can change " +
      "during a session (15 cm, then 42 cm). Measure the box once: call without crop to get the full render " +
      "path, look at it, then reuse the same crop (pixels of the render) or crop_fraction (0-1) for every " +
      "option. Returns the crop as an image. If CC5's RenderImage fails the capture is a window screenshot and " +
      "the call fails instead of returning a crop of the wrong scale.",
    {
      view: z.enum(["face", "front", "back", "left", "right", "top", "bottom", "home", "all", "focus"]).optional()
        .describe("Preset view (default face)"),
      size: z.number().int().min(256).max(MAX_SIZE).optional().describe(`Render size in pixels, square (default 3600, max ${MAX_SIZE})`),
      crop: box4.optional().describe("[x0, y0, x1, y1] in pixels of the render"),
      crop_fraction: box4.optional().describe("[x0, y0, x1, y1] as fractions 0-1 of the render"),
      output_path: z.string().min(1).max(4096).optional().describe("PNG path for the crop (on the CC5 machine; default: a new temp file)"),
      full_path: z.string().min(1).max(4096).optional().describe("PNG path for the full render (on the CC5 machine; default: a new temp file)"),
      avatar_name: z.string().min(1).max(256).optional().describe("Avatar to select before framing (default: the first)"),
      overwrite: z.boolean().optional().describe("Replace output_path / full_path when the file exists (default: refuse)"),
      settle_ms: z.number().int().min(0).max(10000).optional().describe("Wait after framing before rendering (default 800)"),
    },
    async (args) => {
      const problem = pngPathProblem(args.output_path) ?? pngPathProblem(args.full_path) ?? fractionProblem(args.crop_fraction);
      if (problem) return { content: failureContent(problem) };
      if (args.crop && args.crop_fraction) return { content: failureContent("give crop or crop_fraction, not both") };
      if (args.output_path && args.output_path === args.full_path) {
        return { content: failureContent("output_path and full_path must be different files") };
      }
      const body: UiCaptureCropArgs = { ...args };
      return bridgeCallRich(async (): Promise<ToolContent[]> => {
        const run = await runUiJob<UiCaptureCropResult>(bridge, () => bridge.uiCaptureCrop(body), WAIT_SECONDS, wait);
        if ("refused" in run) return refusedContent(run.refused);
        if (!run.outcome.finished) return [textContent(stillRunningText(run.jobId, WAIT_SECONDS, run.outcome.status))];
        const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
        const content: ToolContent[] = [textContent(formatCropResult(result, args.crop))];
        if (result.success && result.png_base64) content.push(pngContent(result.png_base64));
        return content;
      }, (content) => content);
    },
  );
}
