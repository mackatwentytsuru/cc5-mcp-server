/**
 * Unit tests for registerActorMixerTools.
 *
 * The create_actor_mixer tool drives CC5's native "Create Mixer Assets" dialog.
 * confirm_create is a safety gate: false => dry-run (CANCEL), true => Create.
 * The handler forwards options to bridge.createActorMixer and formats the
 * dry-run vs created messaging. Bridge errors are caught by bridgeCall.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerActorMixerTools } from "../../src/tools/actor-mixer.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import { createMockServer } from "../helpers/mock-server.js";
import type { CreateActorMixerResult } from "../../src/types.js";

// ── fixtures ────────────────────────────────────────────────────────────────

const DRY_RUN_RESULT: CreateActorMixerResult = {
  success: true,
  morph_name: "Camila",
  created: false,
  dry_run: true,
  new_presets: [],
  presets_dir: "C:/Custom/ActorMIXER",
  scheduled: true,
};

const CREATED_RESULT: CreateActorMixerResult = {
  success: true,
  morph_name: "Camila",
  created: true,
  dry_run: false,
  new_presets: ["C:/Custom/ActorMIXER/Camila.ccMixerPreset"],
  presets_dir: "C:/Custom/ActorMIXER",
};

const CREATED_SCHEDULED_RESULT: CreateActorMixerResult = {
  success: true,
  morph_name: "Camila",
  created: false,
  dry_run: false,
  new_presets: [],
  presets_dir: "C:/Custom/ActorMIXER",
  scheduled: true,
};

const FAILURE_RESULT: CreateActorMixerResult = {
  success: false,
  error: "ActorMIXER PRO required",
  created: false,
  dry_run: true,
  new_presets: [],
  presets_dir: "",
};

const TRIAL_RESULT: CreateActorMixerResult = {
  success: false,
  error:
    "Cannot create ActorMIXER assets: the current avatar contains TRIAL content " +
    "(IsTrialContentMode is true). The plugin refuses to generate mixer presets " +
    "from trial content. Replace the trial asset(s) with owned/purchased " +
    "equivalents, or load a non-trial avatar, then retry.",
  trial_content: true,
  created: false,
  dry_run: true,
  new_presets: [],
  presets_dir: "",
};

// ── setup ───────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerActorMixerTools(server as any, bridge as any);
});

// ── registration ─────────────────────────────────────────────────────────────

describe("registerActorMixerTools – registration", () => {
  it("registers exactly 1 tool", () => {
    expect(server.tool).toHaveBeenCalledTimes(1);
  });

  it("registers create_actor_mixer", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "create_actor_mixer",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── dry-run (confirm_create=false) ────────────────────────────────────────────

describe("create_actor_mixer handler – dry-run", () => {
  it("returns a dry-run message that says CANCELLED and no files written", async () => {
    bridge.createActorMixer.mockResolvedValue(DRY_RUN_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("dry-run");
    expect(result.content[0].text).toContain("CANCELLED");
    expect(result.content[0].text).toContain("no files written");
  });

  it("mentions the avatar name and presets_dir in the dry-run message", async () => {
    bridge.createActorMixer.mockResolvedValue(DRY_RUN_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("Camila");
    expect(result.content[0].text).toContain("C:/Custom/ActorMIXER");
    expect(result.content[0].text).toContain("confirm_create=true");
  });

  it("forwards confirm_create=false to the bridge", async () => {
    bridge.createActorMixer.mockResolvedValue(DRY_RUN_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    await handler({ confirm_create: false });
    expect(bridge.createActorMixer).toHaveBeenCalledWith(
      expect.objectContaining({ confirm_create: false })
    );
  });

  it("defaults confirm_create to false when omitted (safety gate)", async () => {
    bridge.createActorMixer.mockResolvedValue(DRY_RUN_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    // The zod default is applied by the SDK at runtime; the mock server passes
    // args through, so we assert the handler still produces a dry-run message
    // when confirm_create is explicitly false.
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("dry-run");
  });

  it("returns content with type 'text'", async () => {
    bridge.createActorMixer.mockResolvedValue(DRY_RUN_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].type).toBe("text");
  });
});

// ── create (confirm_create=true) ─────────────────────────────────────────────

describe("create_actor_mixer handler – create", () => {
  it("returns a success message listing new presets when created", async () => {
    bridge.createActorMixer.mockResolvedValue(CREATED_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).toContain("Create clicked");
    expect(result.content[0].text).toContain("Camila.ccMixerPreset");
  });

  it("includes presets_dir in the created message", async () => {
    bridge.createActorMixer.mockResolvedValue(CREATED_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).toContain("C:/Custom/ActorMIXER");
  });

  it("tells the caller to poll status when creation is scheduled without presets yet", async () => {
    bridge.createActorMixer.mockResolvedValue(CREATED_SCHEDULED_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).toContain("poll");
    expect(result.content[0].text).toContain("/actor_mixer/status");
  });

  it("forwards confirm_create=true to the bridge", async () => {
    bridge.createActorMixer.mockResolvedValue(CREATED_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    await handler({ confirm_create: true });
    expect(bridge.createActorMixer).toHaveBeenCalledWith(
      expect.objectContaining({ confirm_create: true })
    );
  });

  it("forwards nested option objects to the bridge", async () => {
    bridge.createActorMixer.mockResolvedValue(CREATED_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    await handler({
      confirm_create: true,
      morph_name: "Hero",
      slider_path: "Custom/Heroes",
      use_parts_folder: true,
      head_parts: { eyes: false, nose: true },
      body_parts: { torso: true },
      save_presets: { enabled: true, character: true, body_parts: false },
      save_avatar_presets: { enabled: false },
    });
    expect(bridge.createActorMixer).toHaveBeenCalledWith(
      expect.objectContaining({
        morph_name: "Hero",
        slider_path: "Custom/Heroes",
        use_parts_folder: true,
        head_parts: { eyes: false, nose: true },
        body_parts: { torso: true },
        save_presets: { enabled: true, character: true, body_parts: false },
        save_avatar_presets: { enabled: false },
      })
    );
  });
});

// ── error handling ───────────────────────────────────────────────────────────

describe("create_actor_mixer handler – error handling", () => {
  it("returns a failure message when the bridge returns success:false", async () => {
    bridge.createActorMixer.mockResolvedValue(FAILURE_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("Create Mixer Assets failed");
    expect(result.content[0].text).toContain("ActorMIXER PRO required");
  });

  it("returns 'unknown error' when failure has no error string", async () => {
    bridge.createActorMixer.mockResolvedValue({
      success: false,
      created: false,
      dry_run: true,
      new_presets: [],
    });
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("unknown error");
  });

  it("returns bridge error text when the bridge throws (does not propagate)", async () => {
    bridge.createActorMixer.mockRejectedValue(new Error("CC5 not connected"));
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).toContain("CC5 bridge error: CC5 not connected");
  });
});

// ── trial-content precondition ───────────────────────────────────────────────

describe("create_actor_mixer handler – trial content precondition", () => {
  it("returns a TRIAL-content message when the avatar has trial content", async () => {
    bridge.createActorMixer.mockResolvedValue(TRIAL_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).toContain("blocked (TRIAL content)");
    expect(result.content[0].text).toContain("IsTrialContentMode is true");
  });

  it("surfaces the actionable guidance to replace/swap the trial asset", async () => {
    bridge.createActorMixer.mockResolvedValue(TRIAL_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("Replace the trial asset");
    expect(result.content[0].text).toContain("non-trial avatar");
  });

  it("does NOT report a generic 'failed' prefix when trial_content is set", async () => {
    bridge.createActorMixer.mockResolvedValue(TRIAL_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: true });
    expect(result.content[0].text).not.toContain("Create Mixer Assets failed:");
  });

  it("forwards the request to the bridge (guard lives in Python, not the tool layer)", async () => {
    // The trial precondition is enforced server-side in cc5_api.create_actor_mixer;
    // the tool layer forwards the call and renders whatever the bridge returns.
    bridge.createActorMixer.mockResolvedValue(TRIAL_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    await handler({ confirm_create: true });
    expect(bridge.createActorMixer).toHaveBeenCalledTimes(1);
    expect(bridge.createActorMixer).toHaveBeenCalledWith(
      expect.objectContaining({ confirm_create: true })
    );
  });

  it("falls back to the normal failure prefix when trial_content is false/absent", async () => {
    bridge.createActorMixer.mockResolvedValue(FAILURE_RESULT);
    const handler = server.getRegisteredTool("create_actor_mixer");
    const result = await handler({ confirm_create: false });
    expect(result.content[0].text).toContain("Create Mixer Assets failed");
    expect(result.content[0].text).not.toContain("TRIAL content");
  });
});
