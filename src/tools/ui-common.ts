/**
 * Shared helpers for the UI-automation tools (apply_preset, skingen_*, list_cc5_windows, ...):
 * running a bridge job to the end, and describing the windows CC5 has open.
 */

import { isBusyReply, type CC5Bridge } from "../cc5-bridge.js";
import type { OperationResult, UiJobOutcome, UiJobStart, UiJobStatus, UiWindowInfo } from "../types.js";
import { pngContent, textContent, type ToolContent } from "../util.js";

const MAX_SHOTS = 3;
const SHOT_WIDTH = 800;

/** How a job tool ends: the bridge refused to start it, or it ran (maybe not to the end). */
export type JobRun<T extends OperationResult> =
  | { refused: UiJobStart }
  | { jobId: string; outcome: UiJobOutcome<T> };

/** What to tell the model when the bridge did not start a job. */
export function refusedContent(refused: UiJobStart): ToolContent[] {
  if (isBusyReply(refused)) {
    return [
      textContent(
        "The start request timed out because CC5 was busy (baking, or a window is waiting). It stays queued in CC5 " +
          "and MAY STILL RUN LATER: do not send it again. Look first with list_cc5_windows and skingen_state / " +
          "list_scene_items, then decide.",
      ),
    ];
  }
  return failureContent(refused.error ?? "the bridge refused to start the job");
}

export interface WaitOptions {
  intervalMs?: number;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
}

/** Start a job and wait for it. timeoutSeconds is how long this call waits; the job itself keeps going. */
export async function runUiJob<T extends OperationResult>(
  bridge: CC5Bridge,
  start: () => Promise<UiJobStart>,
  timeoutSeconds: number,
  wait: WaitOptions = {},
): Promise<JobRun<T>> {
  const reply = await start();
  if (!reply.success || !reply.job_id) return { refused: reply };
  try {
    const outcome = await bridge.uiWaitJob<T>(reply.job_id, { timeoutMs: timeoutSeconds * 1000, ...wait });
    return { jobId: reply.job_id, outcome };
  } catch (err) {
    // The job runs on in CC5; only our contact with it was lost.
    const error = `lost contact with CC5: ${err instanceof Error ? err.message : String(err)}`;
    return { jobId: reply.job_id, outcome: { finished: false, status: { success: false, error } } };
  }
}

export function describeWindow(w: UiWindowInfo): string {
  const buttonList = w.buttons ?? [];
  const bodyText = w.text ?? "";
  const flags: string[] = [];
  if (w.needs_human) flags.push(`人が判断: mentions '${w.needs_human}'`);
  if (w.progress) flags.push("progress window: wait, it goes away by itself");
  if (w.answerable_as) flags.push(`known question (${w.answerable_as})`);
  if (w.blocked_reason) flags.push(`not answered: ${w.blocked_reason}`);
  const buttons = buttonList.length > 0 ? buttonList.join(" | ") : "(none)";
  const boxes = w.checkboxes && w.checkboxes.length > 0
    ? ` | check boxes: ${w.checkboxes.map((c) => `${c.text}=${c.checked ? "on" : "off"}`).join(", ")}`
    : "";
  const tail = flags.length > 0 ? ` [${flags.join("; ")}]` : "";
  return `'${w.title || "(no title)"}': ${bodyText.slice(0, 200)} | buttons: ${buttons}${boxes}${tail}`;
}

/** The text a tool shows when a window needs a person. */
export function windowNeedsPerson(w: UiWindowInfo): string {
  return `⚠ A window is waiting for a person (not answered on purpose): ${describeWindow(w)}`;
}

export function windowImages(windows: UiWindowInfo[] | undefined): ToolContent[] {
  const shots = (windows ?? []).filter((w) => w.png_base64);
  const content: ToolContent[] = shots.slice(0, MAX_SHOTS).map((w) => pngContent(w.png_base64 as string));
  if (shots.length > MAX_SHOTS) {
    content.push(textContent(`(${shots.length - MAX_SHOTS} more window picture(s) not shown; the list above describes every window)`));
  }
  return content;
}

/** Best effort: PNGs of the windows that are open now (nothing when CC5 cannot answer). */
export async function openWindowShots(bridge: CC5Bridge): Promise<ToolContent[]> {
  try {
    const reply = await bridge.uiWindows({ screenshot: true, max_width: SHOT_WIDTH });
    return reply.success ? windowImages(reply.windows) : [];
  } catch {
    return [];
  }
}

/** The text for a job that did not finish while we waited (status is the last thing heard from CC5). */
export function stillRunningText(jobId: string, seconds: number, status: UiJobStatus | undefined): string {
  const open = (status?.windows ?? []).map((w) => `  - ${describeWindow(w)}`).join("\n");
  const lost = status && status.success === false && status.error ? `\nLast contact failed: ${status.error}` : "";
  return (
    `Still running after ${seconds}s (job ${jobId}). It keeps running in CC5; CC5 may be baking or a window may ` +
    `be waiting.${lost}${open ? `\nOpen windows:\n${open}` : ""}\nCall get_ui_job with this job id to wait for ` +
    "the result, and list_cc5_windows to look at the windows."
  );
}

/** Reject a path with a traversal or a null byte before it reaches the bridge. */
export function pathProblem(path: string): string | undefined {
  if (path.includes("\0")) return "Path contains a null byte";
  if (path.replace(/\\/g, "/").split("/").includes("..")) return "Path traversal ('..') is not allowed";
  return undefined;
}

export function failureContent(message: string): ToolContent[] {
  return [textContent(`Failed: ${message}`)];
}
