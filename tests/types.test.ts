/**
 * Type-level and structural tests for the CC5 type definitions.
 * These compile-time checks verify that the types have the expected shapes.
 */

import { describe, it, expect } from "vitest";
import type {
  CC5Avatar,
  MorphEntry,
  MorphCatalog,
  MorphSetRequest,
  AvatarInfo,
  CC5Response,
  OperationResult,
} from "../src/types.js";

// ── CC5Avatar ─────────────────────────────────────────────────────────────────

describe("CC5Avatar type", () => {
  it("accepts a valid avatar object", () => {
    const avatar: CC5Avatar = { id: "a1", name: "Hero", type: "character" };
    expect(avatar.id).toBe("a1");
    expect(avatar.name).toBe("Hero");
    expect(avatar.type).toBe("character");
  });

  it("id, name, type are all strings", () => {
    const avatar: CC5Avatar = { id: "123", name: "Test", type: "npc" };
    expect(typeof avatar.id).toBe("string");
    expect(typeof avatar.name).toBe("string");
    expect(typeof avatar.type).toBe("string");
  });
});

// ── MorphEntry ────────────────────────────────────────────────────────────────

describe("MorphEntry type", () => {
  it("accepts a valid morph entry", () => {
    const entry: MorphEntry = { id: "Fat", display_name: "Fat Body" };
    expect(entry.id).toBe("Fat");
    expect(entry.display_name).toBe("Fat Body");
  });
});

// ── MorphCatalog ──────────────────────────────────────────────────────────────

describe("MorphCatalog type", () => {
  it("accepts a catalog with multiple categories", () => {
    const catalog: MorphCatalog = {
      Body: [
        { id: "Fat", display_name: "Fat" },
        { id: "Muscular", display_name: "Muscular" },
      ],
      Face: [{ id: "Nose_Size", display_name: "Nose Size" }],
    };
    expect(Object.keys(catalog)).toHaveLength(2);
    expect(catalog.Body).toHaveLength(2);
    expect(catalog.Face).toHaveLength(1);
  });

  it("accepts an empty catalog", () => {
    const catalog: MorphCatalog = {};
    expect(Object.keys(catalog)).toHaveLength(0);
  });

  it("is indexable by string category keys", () => {
    const catalog: MorphCatalog = {
      CustomCategory: [{ id: "Custom_Morph", display_name: "Custom Morph" }],
    };
    expect(catalog["CustomCategory"]).toHaveLength(1);
  });
});

// ── MorphSetRequest ───────────────────────────────────────────────────────────

describe("MorphSetRequest type", () => {
  it("accepts id and numeric value", () => {
    const req: MorphSetRequest = { id: "Fat", value: 0.5 };
    expect(req.id).toBe("Fat");
    expect(req.value).toBe(0.5);
  });

  it("accepts value = 0 (minimum boundary)", () => {
    const req: MorphSetRequest = { id: "Thin", value: 0 };
    expect(req.value).toBe(0);
  });

  it("accepts value = 1 (maximum boundary)", () => {
    const req: MorphSetRequest = { id: "Muscular", value: 1 };
    expect(req.value).toBe(1);
  });
});

// ── AvatarInfo ────────────────────────────────────────────────────────────────

describe("AvatarInfo type", () => {
  it("accepts a full avatar info object", () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "MyHero",
      active_morphs: { Fat: 0.3, Muscular: 0.5 },
    };
    expect(info.id).toBe("av1");
    expect(info.name).toBe("MyHero");
    expect(info.active_morphs["Fat"]).toBe(0.3);
  });

  it("accepts empty active_morphs", () => {
    const info: AvatarInfo = { id: "av2", name: "Plain", active_morphs: {} };
    expect(Object.keys(info.active_morphs)).toHaveLength(0);
  });

  it("active_morphs values are numbers", () => {
    const info: AvatarInfo = {
      id: "av1",
      name: "Test",
      active_morphs: { A: 0.1, B: 0.9 },
    };
    for (const v of Object.values(info.active_morphs)) {
      expect(typeof v).toBe("number");
    }
  });
});

// ── CC5Response ───────────────────────────────────────────────────────────────

describe("CC5Response type", () => {
  it("accepts a result-only response", () => {
    const resp: CC5Response<string> = { result: "ok" };
    expect(resp.result).toBe("ok");
    expect(resp.error).toBeUndefined();
  });

  it("accepts an error-only response", () => {
    const resp: CC5Response<string> = { error: "something went wrong" };
    expect(resp.error).toBe("something went wrong");
    expect(resp.result).toBeUndefined();
  });

  it("accepts an empty response (both fields optional)", () => {
    const resp: CC5Response = {};
    expect(resp.result).toBeUndefined();
    expect(resp.error).toBeUndefined();
  });

  it("defaults generic type to unknown when not specified", () => {
    const resp: CC5Response = { result: { anything: true } };
    expect(resp.result).toEqual({ anything: true });
  });
});

// ── OperationResult ───────────────────────────────────────────────────────────

describe("OperationResult type", () => {
  it("accepts a success result", () => {
    const result: OperationResult = { success: true };
    expect(result.success).toBe(true);
  });

  it("accepts a failure result with error message", () => {
    const result: OperationResult = { success: false, error: "morph locked" };
    expect(result.success).toBe(false);
    expect(result.error).toBe("morph locked");
  });

  it("accepts additional arbitrary fields via index signature", () => {
    const result: OperationResult = { success: true, exported_path: "C:/out.fbx", count: 5 };
    expect(result["exported_path"]).toBe("C:/out.fbx");
    expect(result["count"]).toBe(5);
  });

  it("error field is optional on success", () => {
    const result: OperationResult = { success: true };
    expect(result.error).toBeUndefined();
  });
});
