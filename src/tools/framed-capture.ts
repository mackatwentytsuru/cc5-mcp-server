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
import { failureContent, pathProblem, runUiJob, stillRunningText, type WaitOptions } from "./ui-common.js";

const WAIT_SECONDS = 180;           // a 3600 px render takes several seconds

const box4 = z.array(z.number()).length(4);

function pngPathProblem(path: string | undefined): string | undefined {
  if (path === undefined) return undefined;
  return pathProblem(path) ?? (path.toLowerCase().endsWith(".png") ? undefined : "path must end with .png");
}

export function formatCropResult(result: UiCaptureCropResult): string {
  if (!result.success) return `Failed: ${result.error}`;
  const lines = [`Rendered the '${result.view}' view at ${result.render_size?.join("x")} px: ${result.full_path}`];
  if (result.crop_path) {
    lines.push(`Cut box ${result.crop_box?.join(", ")} (${result.crop_size?.join("x")} px): ${result.crop_path}`);
  } else {
    lines.push("No crop box was given: measure the part you want on the full render, then pass crop (pixels) or crop_fraction.");
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
      size: z.number().int().min(256).max(8192).optional().describe("Render size in pixels, square (default 3600)"),
      crop: box4.optional().describe("[x0, y0, x1, y1] in pixels of the render"),
      crop_fraction: box4.optional().describe("[x0, y0, x1, y1] as fractions 0-1 of the render"),
      output_path: z.string().min(1).max(4096).optional().describe("PNG path for the crop (on the CC5 machine)"),
      full_path: z.string().min(1).max(4096).optional().describe("PNG path for the full render (on the CC5 machine)"),
      settle_ms: z.number().int().min(0).max(10000).optional().describe("Wait after framing before rendering (default 800)"),
    },
    async (args) => {
      const problem = pngPathProblem(args.output_path) ?? pngPathProblem(args.full_path);
      if (problem) return { content: failureContent(problem) };
      if (args.crop && args.crop_fraction) return { content: failureContent("give crop or crop_fraction, not both") };
      const body: UiCaptureCropArgs = {};
      for (const key of ["view", "size", "crop", "crop_fraction", "output_path", "full_path", "settle_ms"] as const) {
        if (args[key] !== undefined) (body as Record<string, unknown>)[key] = args[key];
      }
      return bridgeCallRich(async (): Promise<ToolContent[]> => {
        const run = await runUiJob<UiCaptureCropResult>(bridge, () => bridge.uiCaptureCrop(body), WAIT_SECONDS, wait);
        if ("refused" in run) return failureContent(run.refused.error ?? "the bridge refused to start the job");
        if (!run.outcome.finished) return [textContent(stillRunningText(run.jobId, WAIT_SECONDS, run.outcome.status?.windows))];
        const result = run.outcome.result ?? { success: false, error: "the job returned nothing" };
        const content: ToolContent[] = [textContent(formatCropResult(result))];
        if (result.success && result.png_base64) content.push(pngContent(result.png_base64));
        return content;
      }, (content) => content);
    },
  );
}
