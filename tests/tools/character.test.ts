/**
 * Unit tests for registerCharacterTools.
 * Covers apply_body_preset (BODY_PRESETS data, intensity scaling) and
 * describe_character (body description logic).
 * Tool handlers use bridgeCall, so bridge errors become content text.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerCharacterTools, BODY_PRESETS } from "../../src/tools/character.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { AvatarInfo } from "../../src/types.js";

import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerCharacterTools(server as any, bridge as any);
});

// ── BODY_PRESETS direct tests ─────────────────────────────────────────────────

describe("BODY_PRESETS constant", () => {
  it("exports BODY_PRESETS with exactly 5 presets", () => {
    expect(Object.keys(BODY_PRESETS)).toHaveLength(5);
  });

  it("includes all expected preset names", () => {
    expect(BODY_PRESETS).toHaveProperty("athletic");
    expect(BODY_PRESETS).toHaveProperty("muscular");
    expect(BODY_PRESETS).toHaveProperty("slim");
    expect(BODY_PRESETS).toHaveProperty("heavy");
    expect(BODY_PRESETS).toHaveProperty("average");
  });

  it("each preset has exactly 3 morphs (Muscular, Fat, Thin)", () => {
    for (const [preset, morphs] of Object.entries(BODY_PRESETS)) {
      expect(morphs).toHaveLength(3);
      const ids = morphs.map((m) => m.morph_id);
      expect(ids).toContain("cc embed morphs/embed_full_body6");
      expect(ids).toContain("essential body morphs/pack_full_body1");
      expect(ids).toContain("cc embed morphs/embed_full_body5");
      void preset; // suppress lint
    }
  });

  it("all preset morph values are in the valid range [0, 1]", () => {
    for (const morphs of Object.values(BODY_PRESETS)) {
      for (const m of morphs) {
        expect(m.value).toBeGreaterThanOrEqual(0);
        expect(m.value).toBeLessThanOrEqual(1);
      }
    }
  });

  it("athletic preset: Muscular is the dominant morph", () => {
    const muscular = BODY_PRESETS.athletic.find((m) => m.morph_id === "cc embed morphs/embed_full_body6")!;
    const fat = BODY_PRESETS.athletic.find((m) => m.morph_id === "essential body morphs/pack_full_body1")!;
    const thin = BODY_PRESETS.athletic.find((m) => m.morph_id === "cc embed morphs/embed_full_body5")!;
    expect(muscular.value).toBeGreaterThan(fat.value);
    expect(muscular.value).toBeGreaterThan(thin.value);
  });

  it("muscular preset: Muscular value > 0.8", () => {
    const muscular = BODY_PRESETS.muscular.find((m) => m.morph_id === "cc embed morphs/embed_full_body6")!;
    expect(muscular.value).toBeGreaterThan(0.8);
  });

  it("slim preset: Thin is the dominant morph", () => {
    const thin = BODY_PRESETS.slim.find((m) => m.morph_id === "cc embed morphs/embed_full_body5")!;
    const fat = BODY_PRESETS.slim.find((m) => m.morph_id === "essential body morphs/pack_full_body1")!;
    expect(thin.value).toBeGreaterThan(fat.value);
  });

  it("heavy preset: Fat is the dominant morph", () => {
    const fat = BODY_PRESETS.heavy.find((m) => m.morph_id === "essential body morphs/pack_full_body1")!;
    const thin = BODY_PRESETS.heavy.find((m) => m.morph_id === "cc embed morphs/embed_full_body5")!;
    expect(fat.value).toBeGreaterThan(thin.value);
  });

  it("average preset: all morph values are equal", () => {
    const values = BODY_PRESETS.average.map((m) => m.value);
    const allEqual = values.every((v) => v === values[0]);
    expect(allEqual).toBe(true);
  });
});

// ── registration ──────────────────────────────────────────────────────────────

describe("registerCharacterTools – registration", () => {
  it("registers exactly 2 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(2);
  });

  it("registers apply_body_preset", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "apply_body_preset",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers describe_character", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "describe_character",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── apply_body_preset handler ─────────────────────────────────────────────────

describe("apply_body_preset handler – preset values and scaling", () => {
  it("applies 'athletic' preset at full intensity", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    const result = await handler({ preset: "athletic", intensity: 1.0 });
    expect(result.content[0].text).toBe("Applied 'athletic' body preset at 100% intensity");

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    const muscular = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body6");
    const fat = call.find((m) => m.morph_id === "essential body morphs/pack_full_body1");
    const thin = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body5");
    expect(muscular?.value).toBeCloseTo(0.6);
    expect(fat?.value).toBeCloseTo(0.1);
    expect(thin?.value).toBeCloseTo(0.2);
  });

  it("applies 'muscular' preset at full intensity", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "muscular", intensity: 1.0 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    const muscular = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body6");
    expect(muscular?.value).toBeCloseTo(0.9);
  });

  it("applies 'slim' preset at full intensity", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "slim", intensity: 1.0 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    const thin = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body5");
    const fat = call.find((m) => m.morph_id === "essential body morphs/pack_full_body1");
    expect(thin?.value).toBeCloseTo(0.7);
    expect(fat?.value).toBeCloseTo(0.0);
  });

  it("applies 'heavy' preset at full intensity", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "heavy", intensity: 1.0 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    const fat = call.find((m) => m.morph_id === "essential body morphs/pack_full_body1");
    expect(fat?.value).toBeCloseTo(0.7);
  });

  it("applies 'average' preset at full intensity", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "average", intensity: 1.0 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    for (const m of call) {
      expect(m.value).toBeCloseTo(0.3);
    }
  });

  it("scales morph values by intensity = 0.5", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    const result = await handler({ preset: "athletic", intensity: 0.5 });
    expect(result.content[0].text).toContain("50% intensity");

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    const muscular = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body6");
    // athletic Muscular = 0.6 * 0.5 = 0.3
    expect(muscular?.value).toBeCloseTo(0.3);
  });

  it("scales morph values to 0 at intensity = 0", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "muscular", intensity: 0 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    for (const m of call) {
      expect(m.value).toBe(0);
    }
  });

  it("returns intensity as percentage (75% example)", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    const result = await handler({ preset: "slim", intensity: 0.75 });
    expect(result.content[0].text).toContain("75% intensity");
  });

  it("returns failure message when setMultipleMorphs returns failure", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("apply_body_preset");
    const result = await handler({ preset: "athletic", intensity: 1.0 });
    expect(result.content[0].text).toBe("Failed: operation failed");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setMultipleMorphs.mockRejectedValue(new Error("bridge crash"));
    const handler = server.getRegisteredTool("apply_body_preset");
    const result = await handler({ preset: "slim", intensity: 1.0 });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge crash");
  });

  it("passes scaled morphs array to bridge, not originals", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "athletic", intensity: 0.5 });

    const call = bridge.setMultipleMorphs.mock.calls[0][0] as Array<{ morph_id: string; value: number }>;
    // Original athletic values should NOT appear unmutated
    const muscular = call.find((m) => m.morph_id === "cc embed morphs/embed_full_body6");
    expect(muscular?.value).not.toBeCloseTo(0.6); // original unscaled
  });

  it("does not mutate the BODY_PRESETS values when scaling", async () => {
    const originalMuscularValue = BODY_PRESETS.athletic.find((m) => m.morph_id === "cc embed morphs/embed_full_body6")!.value;
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("apply_body_preset");
    await handler({ preset: "athletic", intensity: 0.5 });
    const afterMuscularValue = BODY_PRESETS.athletic.find((m) => m.morph_id === "cc embed morphs/embed_full_body6")!.value;
    expect(afterMuscularValue).toBe(originalMuscularValue);
  });
});

// ── describe_character ────────────────────────────────────────────────────────

describe("describe_character handler", () => {
  it("shows no-avatar message when getAvatarInfo returns null", async () => {
    bridge.getAvatarInfo.mockResolvedValue(null);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toBe("No avatar in the scene.");
  });

  it("includes character name in the description", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "MyHero",
      active_morphs: { "essential body morphs/pack_full_body1": 0.3, "cc embed morphs/embed_full_body6": 0.3, "cc embed morphs/embed_full_body5": 0.3 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("MyHero");
  });

  it("describes 'muscular build' when Muscular > 0.5", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Fighter",
      active_morphs: { "cc embed morphs/embed_full_body6": 0.8, "essential body morphs/pack_full_body1": 0.1, "cc embed morphs/embed_full_body5": 0.0 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("muscular build");
  });

  it("describes 'heavy build' when Fat > 0.5 and Muscular <= 0.5", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "BigGuy",
      active_morphs: { "essential body morphs/pack_full_body1": 0.7, "cc embed morphs/embed_full_body6": 0.0, "cc embed morphs/embed_full_body5": 0.0 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("heavy build");
  });

  it("describes 'slim build' when Thin > 0.5 and others <= 0.5", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Slim",
      active_morphs: { "cc embed morphs/embed_full_body5": 0.7, "essential body morphs/pack_full_body1": 0.0, "cc embed morphs/embed_full_body6": 0.0 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("slim build");
  });

  it("describes 'average build' when no morph dominates", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Average",
      active_morphs: { "essential body morphs/pack_full_body1": 0.3, "cc embed morphs/embed_full_body6": 0.3, "cc embed morphs/embed_full_body5": 0.3 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("average build");
  });

  it("describes 'average build' when active_morphs is empty (all morph defaults to 0)", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Default",
      active_morphs: {},
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("average build");
  });

  it("notes 'larger head' when Head Scale > 0.5", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "BigHead",
      active_morphs: { "cc embed morphs/embed_full_head9": 0.8 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("larger head");
  });

  it("notes 'smaller head' when Head Scale < -0.3", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "SmallHead",
      active_morphs: { "cc embed morphs/embed_full_head9": -0.5 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("smaller head");
  });

  it("does not note head size when Head Scale is absent", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Normal",
      active_morphs: { Fat: 0.1 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).not.toContain("head");
  });

  it("shows total active morph count", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Detailed",
      active_morphs: { "essential body morphs/pack_full_body1": 0.3, "cc embed morphs/embed_full_body6": 0.5, "cc embed morphs/embed_full_body5": 0.1, "cc embed morphs/embed_full_head9": 0.2 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("Total active morphs: 4");
  });

  it("shows morph values as percentages in the detailed section", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Hero",
      active_morphs: { "essential body morphs/pack_full_body1": 0.5 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    // 0.5 * 100 = 50%
    expect(result.content[0].text).toContain("50%");
  });

  it("Muscular takes precedence over Fat in build description", async () => {
    // Both Muscular and Fat > 0.5, but Muscular is checked first in the source
    const info: AvatarInfo = {
      id: "av1",
      name: "BothHigh",
      active_morphs: { "cc embed morphs/embed_full_body6": 0.8, "essential body morphs/pack_full_body1": 0.7 },
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("muscular build");
    expect(result.content[0].text).not.toContain("heavy build");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getAvatarInfo.mockRejectedValue(new Error("timeout"));
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: timeout");
  });

  it("description prefix is 'Character: <name>'", async () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "KungFuKid",
      active_morphs: {},
    };
    bridge.getAvatarInfo.mockResolvedValue(info);
    const handler = server.getRegisteredTool("describe_character");
    const result = await handler({});
    expect(result.content[0].text).toContain("Character: KungFuKid");
  });
});
