/**
 * Unit tests for registerMorphTools.
 * Tool handlers use bridgeCall, so bridge errors become content text responses
 * rather than thrown exceptions.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerMorphTools } from "../../src/tools/morph.js";
import { createMockBridge, SUCCESS, FAILURE } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";

import { createMockServer } from "../helpers/mock-server.js";

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerMorphTools(server as any, bridge as any);
});

// ── tool registration ─────────────────────────────────────────────────────────

describe("registerMorphTools – registration", () => {
  it("registers exactly 5 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(5);
  });

  it("registers adjust_morph", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "adjust_morph",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers adjust_multiple_morphs", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "adjust_multiple_morphs",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });

  it("registers get_morph_value", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_morph_value",
      expect.any(String),
      expect.any(Object),
      expect.any(Function)
    );
  });
});

// ── search_morphs ─────────────────────────────────────────────────────────────

describe("search_morphs handler", () => {
  const sampleResults = [
    { id: "Nose_Size", display_name: "Nose Size", category: "Head" },
    { id: "Nose_Tip_Scale", display_name: "Nose Tip Scale", category: "Head" },
  ];

  it("returns found morphs with display names and IDs", async () => {
    bridge.searchMorphs.mockResolvedValue(sampleResults);
    const handler = server.getRegisteredTool("search_morphs");
    const result = await handler({ query: "nose" });
    expect(result.content[0].text).toContain("Found 2 morph(s)");
    expect(result.content[0].text).toContain("Nose Size");
    expect(result.content[0].text).toContain("ID: Nose_Size");
  });

  it("returns not-found message when results array is empty", async () => {
    bridge.searchMorphs.mockResolvedValue([]);
    const handler = server.getRegisteredTool("search_morphs");
    const result = await handler({ query: "xyznonexistent" });
    expect(result.content[0].text).toBe("No morphs found matching 'xyznonexistent'");
  });

  it("calls bridge.searchMorphs with query and optional category", async () => {
    bridge.searchMorphs.mockResolvedValue(sampleResults);
    const handler = server.getRegisteredTool("search_morphs");
    await handler({ query: "nose", category: "Head" });
    expect(bridge.searchMorphs).toHaveBeenCalledWith("nose", "Head");
  });

  it("calls bridge.searchMorphs with query only when category is omitted", async () => {
    bridge.searchMorphs.mockResolvedValue([]);
    const handler = server.getRegisteredTool("search_morphs");
    await handler({ query: "eye" });
    expect(bridge.searchMorphs).toHaveBeenCalledWith("eye", undefined);
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.searchMorphs.mockRejectedValue(new Error("bridge unreachable"));
    const handler = server.getRegisteredTool("search_morphs");
    const result = await handler({ query: "fat" });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge unreachable");
    expect(result.content[0].text).toContain("Is CC5 running");
  });

  it("returns content with type 'text'", async () => {
    bridge.searchMorphs.mockResolvedValue(sampleResults);
    const handler = server.getRegisteredTool("search_morphs");
    const result = await handler({ query: "nose" });
    expect(result.content[0].type).toBe("text");
  });

  it("lists all returned morphs in the output", async () => {
    const manyResults = [
      { id: "Eye_Wide_L", display_name: "Eye Wide L", category: "Head" },
      { id: "Eye_Wide_R", display_name: "Eye Wide R", category: "Head" },
      { id: "Eye_Squint_L", display_name: "Eye Squint L", category: "Head" },
    ];
    bridge.searchMorphs.mockResolvedValue(manyResults);
    const handler = server.getRegisteredTool("search_morphs");
    const result = await handler({ query: "eye" });
    expect(result.content[0].text).toContain("Found 3 morph(s)");
    expect(result.content[0].text).toContain("Eye Wide L");
    expect(result.content[0].text).toContain("Eye Wide R");
    expect(result.content[0].text).toContain("Eye Squint L");
  });
});

// ── adjust_morph ──────────────────────────────────────────────────────────────

describe("adjust_morph handler", () => {
  it("returns success message when setMorph succeeds", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Fat", value: 0.5 });
    expect(result.content[0].text).toBe("Set morph 'Fat' to 0.5");
  });

  it("returns failure message when setMorph returns failure result", async () => {
    bridge.setMorph.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Thin", value: 0.3 });
    expect(result.content[0].text).toBe("Failed: operation failed");
  });

  it("calls bridge.setMorph with the correct morph_id and value", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    await handler({ morph_id: "Head_Narrow", value: 0.7 });
    expect(bridge.setMorph).toHaveBeenCalledWith("Head_Narrow", 0.7);
  });

  it("includes morph_id and value in the success message", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Nose_Size", value: 1.0 });
    expect(result.content[0].text).toContain("Nose_Size");
    expect(result.content[0].text).toContain("1");
  });

  it("returns content with type 'text'", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Fat", value: 0.0 });
    expect(result.content[0].type).toBe("text");
  });

  it("returns bridge error text when bridge.setMorph throws (does not propagate)", async () => {
    bridge.setMorph.mockRejectedValue(new Error("bridge down"));
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Fat", value: 0.5 });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge down");
    expect(result.content[0].text).toContain("Is CC5 running");
  });

  it("works with value = 0 (minimum boundary)", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Fat", value: 0 });
    expect(result.content[0].text).toContain("0");
  });

  it("works with value = 1 (maximum boundary)", async () => {
    bridge.setMorph.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_morph");
    const result = await handler({ morph_id: "Fat", value: 1 });
    expect(result.content[0].text).toContain("1");
  });
});

// ── adjust_multiple_morphs ────────────────────────────────────────────────────

describe("adjust_multiple_morphs handler", () => {
  const morphs = [
    { morph_id: "Fat", value: 0.3 },
    { morph_id: "Muscular", value: 0.6 },
    { morph_id: "Thin", value: 0.1 },
  ];

  it("returns success message with morph count when all succeed", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    const result = await handler({ morphs });
    expect(result.content[0].text).toBe("Applied 3 morph adjustments");
  });

  it("returns failure message when setMultipleMorphs returns failure", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(FAILURE);
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    const result = await handler({ morphs });
    expect(result.content[0].text).toBe("Failed: operation failed");
  });

  it("calls bridge.setMultipleMorphs with the exact morphs array", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    await handler({ morphs });
    expect(bridge.setMultipleMorphs).toHaveBeenCalledWith(morphs);
  });

  it("handles a single morph in the array", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    const result = await handler({ morphs: [{ morph_id: "Fat", value: 0.5 }] });
    expect(result.content[0].text).toBe("Applied 1 morph adjustments");
  });

  it("handles empty morphs array", async () => {
    bridge.setMultipleMorphs.mockResolvedValue(SUCCESS);
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    const result = await handler({ morphs: [] });
    expect(result.content[0].text).toBe("Applied 0 morph adjustments");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.setMultipleMorphs.mockRejectedValue(new Error("network error"));
    const handler = server.getRegisteredTool("adjust_multiple_morphs");
    const result = await handler({ morphs });
    expect(result.content[0].text).toContain("CC5 bridge error: network error");
  });
});

// ── get_morph_value ───────────────────────────────────────────────────────────

describe("get_morph_value handler", () => {
  it("returns the morph value when found", async () => {
    bridge.getMorphValue.mockResolvedValue(0.75);
    const handler = server.getRegisteredTool("get_morph_value");
    const result = await handler({ morph_id: "Fat" });
    expect(result.content[0].text).toBe("Morph 'Fat' current value: 0.75");
  });

  it("returns not-found message when getMorphValue returns null", async () => {
    bridge.getMorphValue.mockResolvedValue(null);
    const handler = server.getRegisteredTool("get_morph_value");
    const result = await handler({ morph_id: "NonExistent" });
    expect(result.content[0].text).toBe("Could not get morph value for 'NonExistent'");
  });

  it("returns the morph value when it is 0 (not null)", async () => {
    bridge.getMorphValue.mockResolvedValue(0);
    const handler = server.getRegisteredTool("get_morph_value");
    const result = await handler({ morph_id: "Thin" });
    // 0 !== null, so it should show the value
    expect(result.content[0].text).toBe("Morph 'Thin' current value: 0");
  });

  it("calls bridge.getMorphValue with the morph_id", async () => {
    bridge.getMorphValue.mockResolvedValue(0.5);
    const handler = server.getRegisteredTool("get_morph_value");
    await handler({ morph_id: "Muscular" });
    expect(bridge.getMorphValue).toHaveBeenCalledWith("Muscular");
  });

  it("returns bridge error text when bridge throws (does not propagate)", async () => {
    bridge.getMorphValue.mockRejectedValue(new Error("bridge error"));
    const handler = server.getRegisteredTool("get_morph_value");
    const result = await handler({ morph_id: "Fat" });
    expect(result.content[0].text).toContain("CC5 bridge error: bridge error");
  });
});
