/**
 * CC5Bridge methods for the /ui/ routes: failure replies come back as results (lenient mode) and
 * uiWaitJob polls a job through "CC5 is busy" replies.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { CC5Bridge } from "../src/cc5-bridge.js";

type Reply = { status: number; body: unknown };

/** fetch stub that answers from a queue of replies; the last one repeats. */
function stubFetch(replies: Reply[]): ReturnType<typeof vi.fn> {
  const queue = [...replies];
  const fn = vi.fn().mockImplementation(async () => {
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: () => Promise.resolve(reply.body),
      text: () => Promise.resolve(typeof reply.body === "string" ? reply.body : JSON.stringify(reply.body)),
    };
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const ok = (result: unknown): Reply => ({ status: 200, body: { result } });
const busy: Reply = { status: 504, body: { error: "Timeout waiting for CC5 to process command" } };

let bridge: CC5Bridge;
const fastWait = { sleep: () => Promise.resolve(), intervalMs: 0 };

beforeEach(() => {
  bridge = new CC5Bridge("http://localhost:5101");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("lenient failure replies", () => {
  it("returns the body of a 400 as the result", async () => {
    stubFetch([{ status: 400, body: { success: false, error: "file not found", path: "x" } }]);
    const reply = await bridge.uiApplyPreset({ file_path: "x" });
    expect(reply).toEqual({ success: false, error: "file not found", path: "x" });
  });

  it("marks a reply that has only an error as a failure", async () => {
    stubFetch([busy]);
    const reply = await bridge.uiWindows();
    expect(reply.success).toBe(false);
    expect(reply.error).toContain("Timeout waiting for CC5");
  });

  it("still throws when the body is not JSON", async () => {
    stubFetch([{ status: 500, body: "<html>oops</html>" }]);
    await expect(bridge.uiSkinGenState()).rejects.toThrow("CC5 bridge error (500)");
  });

  it("ordinary methods keep throwing on a 400", async () => {
    stubFetch([{ status: 400, body: { success: false, error: "nope" } }]);
    await expect(bridge.getAvatars()).rejects.toThrow("CC5 bridge error (400)");
  });
});

describe("request shapes", () => {
  it.each([
    ["uiApplyPreset", () => bridge.uiApplyPreset({ file_path: "a.ccSkinGenPreset" }), "/ui/preset/apply", { file_path: "a.ccSkinGenPreset" }],
    ["uiListPresets", () => bridge.uiListPresets({ category: "makeup_lip" }), "/ui/preset/list", { category: "makeup_lip" }],
    ["uiSkinGenState", () => bridge.uiSkinGenState(), "/ui/skingen/state", {}],
    ["uiSkinGenEditor", () => bridge.uiSkinGenEditor({ active: false }), "/ui/skingen/editor", { active: false }],
    ["uiSkinGenLayer", () => bridge.uiSkinGenLayer({ action: "hide", index: 1 }), "/ui/skingen/layer", { action: "hide", index: 1 }],
    ["uiWindows", () => bridge.uiWindows({ screenshot: true }), "/ui/windows", { screenshot: true }],
    ["uiWidgets", () => bridge.uiWidgets({ object_name: "qtSpinBox" }), "/ui/widgets", { object_name: "qtSpinBox" }],
    ["uiCaptureCrop", () => bridge.uiCaptureCrop({ size: 3600 }), "/ui/capture_crop", { size: 3600 }],
    ["uiJob", () => bridge.uiJob("preset-1"), "/ui/job", { job_id: "preset-1" }],
  ])("%s posts to %s", async (_name, call, path, body) => {
    const fetchFn = stubFetch([ok({ success: true })]);
    await call();
    const [url, options] = fetchFn.mock.calls[0];
    expect(url).toBe(`http://localhost:5101${path}`);
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(body);
  });

  it("uiWindows with no arguments sends an empty body", async () => {
    const fetchFn = stubFetch([ok({ success: true, windows: [] })]);
    await bridge.uiWindows();
    expect(JSON.parse(fetchFn.mock.calls[0][1].body)).toEqual({});
  });
});

describe("uiWaitJob", () => {
  const done = (result: unknown) => ok({ success: true, job_id: "j1", state: "done", result });

  it("returns the result once the job is done", async () => {
    stubFetch([ok({ success: true, state: "running" }), done({ success: true, files: [] })]);
    const outcome = await bridge.uiWaitJob("j1", fastWait);
    expect(outcome.finished).toBe(true);
    expect(outcome.result).toEqual({ success: true, files: [] });
  });

  it("keeps polling through 'CC5 is busy' replies", async () => {
    const fetchFn = stubFetch([busy, busy, ok({ success: true, state: "running" }), busy, done({ success: true })]);
    const outcome = await bridge.uiWaitJob("j1", fastWait);
    expect(outcome.finished).toBe(true);
    expect(fetchFn).toHaveBeenCalledTimes(5);
  });

  it("returns a failed job's result", async () => {
    stubFetch([ok({ success: true, job_id: "j1", state: "failed", result: { success: false, error: "RuntimeError: x" } })]);
    const outcome = await bridge.uiWaitJob("j1", fastWait);
    expect(outcome.finished).toBe(true);
    expect(outcome.result?.error).toBe("RuntimeError: x");
  });

  it("gives up at the timeout and returns the last status with its open windows", async () => {
    const windows = [{ title: "Mystery", text: "?", buttons: ["OK"] }];
    stubFetch([ok({ success: true, state: "running", windows })]);
    let clock = 0;
    const outcome = await bridge.uiWaitJob("j1", {
      timeoutMs: 5_000,
      intervalMs: 1_000,
      sleep: async (ms) => { clock += ms; },
      now: () => clock,
    });
    expect(outcome.finished).toBe(false);
    expect(outcome.status?.windows).toEqual(windows);
  });

  it("reports an unknown job instead of waiting for ever", async () => {
    stubFetch([{ status: 400, body: { success: false, error: "unknown job 'zzz'" } }]);
    const outcome = await bridge.uiWaitJob("zzz", fastWait);
    expect(outcome.finished).toBe(true);
    expect(outcome.result?.success).toBe(false);
    expect(outcome.result?.error).toContain("unknown job");
  });

  it("survives a few network errors, then throws", async () => {
    const fetchFn = vi.fn()
      .mockRejectedValueOnce(new Error("socket hang up"))
      .mockRejectedValueOnce(new Error("socket hang up"))
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ result: { state: "done", result: { success: true } } }), text: () => Promise.resolve("") });
    vi.stubGlobal("fetch", fetchFn);
    expect((await bridge.uiWaitJob("j1", fastWait)).finished).toBe(true);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection refused")));
    await expect(bridge.uiWaitJob("j1", fastWait)).rejects.toThrow("connection refused");
  });
});
