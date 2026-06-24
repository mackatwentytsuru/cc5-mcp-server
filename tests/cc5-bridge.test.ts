/**
 * Unit tests for CC5Bridge HTTP client.
 * All HTTP calls are mocked via vi.stubGlobal('fetch', ...).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { CC5Bridge } from "../src/cc5-bridge.js";
import type {
  CC5Response,
  CC5Avatar,
  AvatarInfo,
  MorphCatalog,
  OperationResult,
  CreateAvatarResult,
  CaptureResult,
  MaterialInfo,
  DiffuseColor,
  SetDiffuseColorResult,
  CreateActorMixerResult,
} from "../src/types.js";

// ── helpers ──────────────────────────────────────────────────────────────────

function mockFetch<T>(data: CC5Response<T>, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
    })
  );
}

function mockFetchError(message: string): void {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error(message)));
}

function mockFetchHttpError(status: number, body: string): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: () => Promise.reject(new Error("not json")),
      text: () => Promise.resolve(body),
    })
  );
}

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: CC5Bridge;

beforeEach(() => {
  bridge = new CC5Bridge("http://localhost:5101");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── constructor ───────────────────────────────────────────────────────────────

describe("CC5Bridge constructor", () => {
  it("accepts localhost URLs", () => {
    expect(() => new CC5Bridge("http://localhost:9999")).not.toThrow();
  });

  it("accepts 127.0.0.1 URLs", () => {
    expect(() => new CC5Bridge("http://127.0.0.1:5101")).not.toThrow();
  });

  it("accepts ::1 (IPv6 loopback) URLs", () => {
    expect(() => new CC5Bridge("http://[::1]:5101")).not.toThrow();
  });

  it("rejects non-localhost URLs", () => {
    expect(() => new CC5Bridge("http://example.com:9999")).toThrow(
      "CC5_BRIDGE_URL must point to localhost, got: example.com"
    );
  });

  it("rejects remote IP addresses", () => {
    expect(() => new CC5Bridge("http://192.168.1.100:5101")).toThrow(
      "CC5_BRIDGE_URL must point to localhost"
    );
  });

  it("rejects completely invalid URLs", () => {
    expect(() => new CC5Bridge("not-a-url")).toThrow("Invalid CC5_BRIDGE_URL");
  });

  it("falls back to CC5_BRIDGE_URL env variable when localhost", () => {
    const original = process.env.CC5_BRIDGE_URL;
    process.env.CC5_BRIDGE_URL = "http://localhost:1234";
    const b = new CC5Bridge();
    expect((b as unknown as { baseUrl: string }).baseUrl).toBe("http://localhost:1234");
    process.env.CC5_BRIDGE_URL = original;
  });

  it("falls back to default URL when no env var is set", () => {
    const original = process.env.CC5_BRIDGE_URL;
    delete process.env.CC5_BRIDGE_URL;
    const b = new CC5Bridge();
    expect((b as unknown as { baseUrl: string }).baseUrl).toBe("http://127.0.0.1:5101");
    process.env.CC5_BRIDGE_URL = original;
  });

  it("stores the provided base URL", () => {
    const b = new CC5Bridge("http://127.0.0.1:9999");
    expect((b as unknown as { baseUrl: string }).baseUrl).toBe("http://127.0.0.1:9999");
  });
});

// ── healthCheck ───────────────────────────────────────────────────────────────

describe("CC5Bridge.healthCheck", () => {
  it("returns true when the bridge responds successfully", async () => {
    mockFetch<{ status: string }>({ result: { status: "ok" } });
    const result = await bridge.healthCheck();
    expect(result).toBe(true);
  });

  it("returns false when fetch throws a network error", async () => {
    mockFetchError("ECONNREFUSED");
    const result = await bridge.healthCheck();
    expect(result).toBe(false);
  });

  it("returns false when the server returns a non-200 status", async () => {
    mockFetchHttpError(503, "Service Unavailable");
    const result = await bridge.healthCheck();
    expect(result).toBe(false);
  });

  it("returns false when the response contains an error field", async () => {
    mockFetch({ error: "CC5 not ready" });
    const result = await bridge.healthCheck();
    expect(result).toBe(false);
  });

  it("calls GET /health", async () => {
    mockFetch<{ status: string }>({ result: { status: "ok" } });
    await bridge.healthCheck();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/health",
      expect.objectContaining({ method: "GET" })
    );
  });
});

// ── getAvatars ────────────────────────────────────────────────────────────────

describe("CC5Bridge.getAvatars", () => {
  it("returns an array of avatars on success", async () => {
    const avatars: CC5Avatar[] = [
      { id: "a1", name: "Hero", type: "character" },
      { id: "a2", name: "Villain", type: "character" },
    ];
    mockFetch<CC5Avatar[]>({ result: avatars });
    const result = await bridge.getAvatars();
    expect(result).toEqual(avatars);
    expect(result).toHaveLength(2);
  });

  it("returns an empty array when there are no avatars", async () => {
    mockFetch<CC5Avatar[]>({ result: [] });
    const result = await bridge.getAvatars();
    expect(result).toEqual([]);
  });

  it("throws when the bridge returns an error field", async () => {
    mockFetch({ error: "scene not ready" });
    await expect(bridge.getAvatars()).rejects.toThrow("CC5 error: scene not ready");
  });

  it("throws when the HTTP status is not OK", async () => {
    mockFetchHttpError(500, "Internal Server Error");
    await expect(bridge.getAvatars()).rejects.toThrow("CC5 bridge error (500)");
  });

  it("throws on network failure", async () => {
    mockFetchError("fetch failed");
    await expect(bridge.getAvatars()).rejects.toThrow("fetch failed");
  });

  it("calls GET /avatars", async () => {
    mockFetch<CC5Avatar[]>({ result: [] });
    await bridge.getAvatars();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/avatars",
      expect.objectContaining({ method: "GET" })
    );
  });
});

// ── getAvatarInfo ─────────────────────────────────────────────────────────────

describe("CC5Bridge.getAvatarInfo", () => {
  const sampleInfo: AvatarInfo = {
    id: "av1",
    name: "Test Avatar",
    active_morphs: { Fat: 0.3, Muscular: 0.5 },
  };

  it("returns avatar info on success", async () => {
    mockFetch<AvatarInfo>({ result: sampleInfo });
    const result = await bridge.getAvatarInfo();
    expect(result).toEqual(sampleInfo);
  });

  it("returns null when result is null", async () => {
    mockFetch<null>({ result: null });
    const result = await bridge.getAvatarInfo();
    expect(result).toBeNull();
  });

  it("throws when the bridge returns an error field", async () => {
    mockFetch({ error: "no avatar" });
    await expect(bridge.getAvatarInfo()).rejects.toThrow("CC5 error: no avatar");
  });

  it("calls GET /avatar/info", async () => {
    mockFetch<AvatarInfo>({ result: sampleInfo });
    await bridge.getAvatarInfo();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/avatar/info",
      expect.objectContaining({ method: "GET" })
    );
  });
});

// ── getMorphCatalog ───────────────────────────────────────────────────────────

describe("CC5Bridge.getMorphCatalog", () => {
  const catalog: MorphCatalog = {
    Body: [
      { id: "Fat", display_name: "Fat" },
      { id: "Muscular", display_name: "Muscular" },
    ],
    Head: [{ id: "Head Scale", display_name: "Head Scale" }],
  };

  it("returns the morph catalog on success", async () => {
    mockFetch<MorphCatalog>({ result: catalog });
    const result = await bridge.getMorphCatalog();
    expect(result).toEqual(catalog);
    expect(result.Body).toHaveLength(2);
    expect(result.Head).toHaveLength(1);
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(404, "Not Found");
    await expect(bridge.getMorphCatalog()).rejects.toThrow("CC5 bridge error (404)");
  });

  it("calls GET /morphs/catalog", async () => {
    mockFetch<MorphCatalog>({ result: catalog });
    await bridge.getMorphCatalog();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morphs/catalog",
      expect.objectContaining({ method: "GET" })
    );
  });
});

// ── getMorphValue ─────────────────────────────────────────────────────────────

describe("CC5Bridge.getMorphValue", () => {
  it("returns the numeric morph value", async () => {
    mockFetch<number>({ result: 0.75 });
    const result = await bridge.getMorphValue("Fat");
    expect(result).toBe(0.75);
  });

  it("returns 0 when the morph is at zero", async () => {
    mockFetch<number>({ result: 0 });
    const result = await bridge.getMorphValue("Thin");
    expect(result).toBe(0);
  });

  it("returns null when no morph found", async () => {
    mockFetch<null>({ result: null });
    const result = await bridge.getMorphValue("NonExistent");
    expect(result).toBeNull();
  });

  it("sends POST /morph/get with morph_id in body", async () => {
    mockFetch<number>({ result: 0.5 });
    await bridge.getMorphValue("Nose_Size");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morph/get",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ morph_id: "Nose_Size" }),
      })
    );
  });

  it("throws on bridge error", async () => {
    mockFetch({ error: "morph not found" });
    await expect(bridge.getMorphValue("Unknown")).rejects.toThrow("CC5 error: morph not found");
  });
});

// ── setMorph ──────────────────────────────────────────────────────────────────

describe("CC5Bridge.setMorph", () => {
  const successResult: OperationResult = { success: true };
  const failureResult: OperationResult = { success: false, error: "morph locked" };

  it("returns success result when morph is set", async () => {
    mockFetch<OperationResult>({ result: successResult });
    const result = await bridge.setMorph("Fat", 0.5);
    expect(result.success).toBe(true);
  });

  it("returns failure result when CC5 rejects the operation", async () => {
    mockFetch<OperationResult>({ result: failureResult });
    const result = await bridge.setMorph("Fat", 0.5);
    expect(result.success).toBe(false);
    expect(result.error).toBe("morph locked");
  });

  it("sends POST /morph/set with morph_id and value in body", async () => {
    mockFetch<OperationResult>({ result: successResult });
    await bridge.setMorph("Head_Narrow", 0.3);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morph/set",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ morph_id: "Head_Narrow", value: 0.3 }),
      })
    );
  });

  it("throws when HTTP status is not OK", async () => {
    mockFetchHttpError(400, "Bad Request");
    await expect(bridge.setMorph("Fat", 0.5)).rejects.toThrow("CC5 bridge error (400)");
  });

  it("throws on network failure", async () => {
    mockFetchError("network timeout");
    await expect(bridge.setMorph("Fat", 0.5)).rejects.toThrow("network timeout");
  });
});

// ── setMultipleMorphs ─────────────────────────────────────────────────────────

describe("CC5Bridge.setMultipleMorphs", () => {
  it("sends POST /morphs/set with morphs array", async () => {
    const morphs = [
      { id: "Fat", value: 0.3 },
      { id: "Muscular", value: 0.6 },
    ];
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.setMultipleMorphs(morphs);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morphs/set",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ morphs }),
      })
    );
  });

  it("returns success when all morphs are applied", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.setMultipleMorphs([{ id: "Fat", value: 0.5 }]);
    expect(result.success).toBe(true);
  });

  it("handles empty morphs array", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.setMultipleMorphs([]);
    expect(result.success).toBe(true);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ body: JSON.stringify({ morphs: [] }) })
    );
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "server crash");
    await expect(bridge.setMultipleMorphs([{ id: "Fat", value: 0.5 }])).rejects.toThrow(
      "CC5 bridge error (500)"
    );
  });
});

// ── loadAsset ─────────────────────────────────────────────────────────────────

describe("CC5Bridge.loadAsset", () => {
  it("sends POST /asset/load with file_path in body", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.loadAsset("C:/Assets/MyChar.iAvatar");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/asset/load",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ file_path: "C:/Assets/MyChar.iAvatar" }),
      })
    );
  });

  it("returns success on successful load", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.loadAsset("C:/Assets/Character.ccm");
    expect(result.success).toBe(true);
  });

  it("returns failure when CC5 cannot load the asset", async () => {
    mockFetch<OperationResult>({ result: { success: false, error: "file not found" } });
    const result = await bridge.loadAsset("C:/Missing/file.iAvatar");
    expect(result.success).toBe(false);
    expect(result.error).toBe("file not found");
  });

  it("throws on network error", async () => {
    mockFetchError("connection refused");
    await expect(bridge.loadAsset("C:/file.iAvatar")).rejects.toThrow("connection refused");
  });
});

// ── exportFbx ─────────────────────────────────────────────────────────────────

describe("CC5Bridge.exportFbx", () => {
  it("sends POST /export/fbx with output_path and default options=0", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.exportFbx("C:/Export/character.fbx");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/export/fbx",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ output_path: "C:/Export/character.fbx", options: 0 }),
      })
    );
  });

  it("sends custom options value when provided", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.exportFbx("C:/out.fbx", 3);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ body: JSON.stringify({ output_path: "C:/out.fbx", options: 3 }) })
    );
  });

  it("forwards CC5 dialog options (mesh+motion, embed textures, fps, subd) to the body", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.exportFbx("C:/out.fbx", 0, {
      target_tool: "UE5",
      export_motion: true,
      embed_textures: true,
      fps: 30,
      sub_d_level: 0,
    });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          output_path: "C:/out.fbx",
          options: 0,
          target_tool: "UE5",
          sub_d_level: 0,
          embed_textures: true,
          export_motion: true,
          fps: 30,
        }),
      })
    );
  });

  it("forwards motion_range, texture_size, and convert_image_format", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.exportFbx("C:/out.fbx", 0, {
      motion_range: [0, 100],
      texture_size: 2048,
      convert_image_format: true,
    });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          output_path: "C:/out.fbx",
          options: 0,
          motion_range: [0, 100],
          convert_image_format: true,
          texture_size: 2048,
        }),
      })
    );
  });

  it("omits unset optional params from the body", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.exportFbx("C:/out.fbx", 0, { export_motion: false });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ output_path: "C:/out.fbx", options: 0, export_motion: false }),
      })
    );
  });

  it("returns success result on successful export", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.exportFbx("C:/out.fbx");
    expect(result.success).toBe(true);
  });

  it("returns failure when export fails", async () => {
    mockFetch<OperationResult>({ result: { success: false, error: "disk full" } });
    const result = await bridge.exportFbx("C:/out.fbx");
    expect(result.success).toBe(false);
    expect(result.error).toBe("disk full");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "export failed");
    await expect(bridge.exportFbx("C:/out.fbx")).rejects.toThrow("CC5 bridge error (500)");
  });
});

// ── setSubdivisionLevel ───────────────────────────────────────────────────────

describe("CC5Bridge.setSubdivisionLevel", () => {
  it("sends POST /subdivision with level in body", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    await bridge.setSubdivisionLevel(2);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/subdivision",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ level: 2 }),
      })
    );
  });

  it("returns success for level 0 (base mesh)", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.setSubdivisionLevel(0);
    expect(result.success).toBe(true);
  });

  it("returns success for level 1 (medium)", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.setSubdivisionLevel(1);
    expect(result.success).toBe(true);
  });

  it("returns success for level 2 (HD)", async () => {
    mockFetch<OperationResult>({ result: { success: true } });
    const result = await bridge.setSubdivisionLevel(2);
    expect(result.success).toBe(true);
  });

  it("returns failure result when CC5 rejects the level", async () => {
    mockFetch<OperationResult>({ result: { success: false, error: "HD morphs not loaded" } });
    const result = await bridge.setSubdivisionLevel(2);
    expect(result.success).toBe(false);
    expect(result.error).toBe("HD morphs not loaded");
  });

  it("throws on network error", async () => {
    mockFetchError("timeout");
    await expect(bridge.setSubdivisionLevel(1)).rejects.toThrow("timeout");
  });
});

// ── createDefaultAvatar ───────────────────────────────────────────────────────

describe("CC5Bridge.createDefaultAvatar", () => {
  it("returns CreateAvatarResult on success", async () => {
    const created: CreateAvatarResult = { success: true, name: "Default Character" };
    mockFetch<CreateAvatarResult>({ result: created });
    const result = await bridge.createDefaultAvatar();
    expect(result.success).toBe(true);
    expect(result.name).toBe("Default Character");
  });

  it("sends POST /avatar/create with empty body", async () => {
    mockFetch<CreateAvatarResult>({ result: { success: true } });
    await bridge.createDefaultAvatar();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/avatar/create",
      expect.objectContaining({
        method: "POST",
        body: "{}",
      })
    );
  });

  it("sends POST to the correct /avatar/create endpoint", async () => {
    mockFetch<CreateAvatarResult>({ result: { success: true } });
    await bridge.createDefaultAvatar();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/avatar/create",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("does not include any age field in the request body", async () => {
    mockFetch<CreateAvatarResult>({ result: { success: true } });
    await bridge.createDefaultAvatar();
    const callArgs = vi.mocked(fetch).mock.calls[0];
    const body = (callArgs[1] as RequestInit).body as string;
    expect(JSON.parse(body)).not.toHaveProperty("age");
  });

  it("returns failure when CC5 cannot create avatar", async () => {
    mockFetch<CreateAvatarResult>({ result: { success: false, error: "scene locked" } });
    const result = await bridge.createDefaultAvatar();
    expect(result.success).toBe(false);
    expect(result.error).toBe("scene locked");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "CC5 crashed");
    await expect(bridge.createDefaultAvatar()).rejects.toThrow("CC5 bridge error (500)");
  });

  it("throws on network error", async () => {
    mockFetchError("connection refused");
    await expect(bridge.createDefaultAvatar()).rejects.toThrow("connection refused");
  });
});

// ── captureViewport ───────────────────────────────────────────────────────────

describe("CC5Bridge.captureViewport", () => {
  it("returns CaptureResult with path on success", async () => {
    const captured: CaptureResult = { success: true, path: "C:/temp/capture.png" };
    mockFetch<CaptureResult>({ result: captured });
    const result = await bridge.captureViewport("C:/temp/capture.png");
    expect(result.success).toBe(true);
    expect(result.path).toBe("C:/temp/capture.png");
  });

  it("sends POST /viewport/capture with empty body when no path provided", async () => {
    mockFetch<CaptureResult>({ result: { success: true, path: "/tmp/cc5_capture.png" } });
    await bridge.captureViewport();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/viewport/capture",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({}),
      })
    );
  });

  it("sends POST /viewport/capture with provided output path", async () => {
    mockFetch<CaptureResult>({ result: { success: true } });
    await bridge.captureViewport("C:/screenshots/view.png");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/viewport/capture",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ output_path: "C:/screenshots/view.png" }),
      })
    );
  });

  it("returns failure when viewport capture fails", async () => {
    mockFetch<CaptureResult>({ result: { success: false, error: "no render context" } });
    const result = await bridge.captureViewport();
    expect(result.success).toBe(false);
    expect(result.error).toBe("no render context");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "render failed");
    await expect(bridge.captureViewport()).rejects.toThrow("CC5 bridge error (500)");
  });

  it("throws on network error", async () => {
    mockFetchError("timeout");
    await expect(bridge.captureViewport()).rejects.toThrow("timeout");
  });

  it("returns base64 field when bridge provides it", async () => {
    const captured: CaptureResult = { success: true, path: "/tmp/c.png", base64: "abc123" };
    mockFetch<CaptureResult>({ result: captured });
    const result = await bridge.captureViewport();
    expect(result.base64).toBe("abc123");
  });
});

// ── request internals ─────────────────────────────────────────────────────────

describe("CC5Bridge internal request handling", () => {
  it("sends Content-Type: application/json header", async () => {
    mockFetch<CC5Avatar[]>({ result: [] });
    await bridge.getAvatars();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  it("does not include body on GET requests", async () => {
    mockFetch<CC5Avatar[]>({ result: [] });
    await bridge.getAvatars();
    const callArgs = vi.mocked(fetch).mock.calls[0][1] as RequestInit;
    expect(callArgs.body).toBeUndefined();
  });

  it("throws CC5 bridge error with status code when response is not OK", async () => {
    mockFetchHttpError(422, "Unprocessable Entity");
    await expect(bridge.getAvatars()).rejects.toThrow("CC5 bridge error (422): Unprocessable Entity");
  });

  it("throws CC5 error message from response body error field", async () => {
    mockFetch({ error: "RLPy not initialized" });
    await expect(bridge.getAvatarInfo()).rejects.toThrow("CC5 error: RLPy not initialized");
  });

  it("throws when result field is undefined in the response", async () => {
    mockFetch({});
    await expect(bridge.getAvatars()).rejects.toThrow("CC5 bridge returned empty result");
  });
});

// ── searchMorphs ──────────────────────────────────────────────────────────────

describe("CC5Bridge.searchMorphs", () => {
  type SearchResult = Array<{ id: string; display_name: string; category: string }>;

  const sampleResults: SearchResult = [
    { id: "Nose_Size", display_name: "Nose Size", category: "Head" },
    { id: "Nose_Tip_Scale", display_name: "Nose Tip Scale", category: "Head" },
  ];

  it("returns search results on success", async () => {
    mockFetch<SearchResult>({ result: sampleResults });
    const result = await bridge.searchMorphs("nose");
    expect(result).toEqual(sampleResults);
    expect(result).toHaveLength(2);
  });

  it("returns an empty array when no morphs match", async () => {
    mockFetch<SearchResult>({ result: [] });
    const result = await bridge.searchMorphs("xyznonexistent");
    expect(result).toEqual([]);
  });

  it("sends POST /morphs/search with query in body", async () => {
    mockFetch<SearchResult>({ result: [] });
    await bridge.searchMorphs("eye");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morphs/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "eye", category: "" }),
      })
    );
  });

  it("sends category in body when provided", async () => {
    mockFetch<SearchResult>({ result: [] });
    await bridge.searchMorphs("fat", "Body");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/morphs/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "fat", category: "Body" }),
      })
    );
  });

  it("defaults category to empty string when not provided", async () => {
    mockFetch<SearchResult>({ result: [] });
    await bridge.searchMorphs("jaw");
    const callArgs = vi.mocked(fetch).mock.calls[0];
    const body = JSON.parse((callArgs[1] as RequestInit).body as string);
    expect(body.category).toBe("");
  });

  it("throws on bridge error field", async () => {
    mockFetch({ error: "RLPy not ready" });
    await expect(bridge.searchMorphs("test")).rejects.toThrow("CC5 error: RLPy not ready");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "Internal Server Error");
    await expect(bridge.searchMorphs("test")).rejects.toThrow("CC5 bridge error (500)");
  });

  it("throws on network failure", async () => {
    mockFetchError("fetch failed");
    await expect(bridge.searchMorphs("test")).rejects.toThrow("fetch failed");
  });
});

// ── getMaterialInfo ───────────────────────────────────────────────────────────

describe("CC5Bridge.getMaterialInfo", () => {
  const sampleInfo: MaterialInfo = {
    meshes: {
      CC_Base_Body: ["Std_Skin_Body", "Std_Skin_Arm"],
      CC_Base_Eye: ["Std_Eye_R", "Std_Eye_L"],
    },
  };

  it("returns material info on success", async () => {
    mockFetch<MaterialInfo>({ result: sampleInfo });
    const result = await bridge.getMaterialInfo();
    expect(result).toEqual(sampleInfo);
    expect(Object.keys(result.meshes)).toHaveLength(2);
  });

  it("returns an empty object when no meshes exist", async () => {
    mockFetch<MaterialInfo>({ result: { meshes: {} } });
    const result = await bridge.getMaterialInfo();
    expect(result).toEqual({ meshes: {} });
  });

  it("sends POST /material/info with empty body when no avatar_name provided", async () => {
    mockFetch<MaterialInfo>({ result: {} });
    await bridge.getMaterialInfo();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/material/info",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({}),
      })
    );
  });

  it("sends avatar_name in body when provided", async () => {
    mockFetch<MaterialInfo>({ result: sampleInfo });
    await bridge.getMaterialInfo("Hero");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/material/info",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ avatar_name: "Hero" }),
      })
    );
  });

  it("throws on bridge error field", async () => {
    mockFetch({ error: "no avatar selected" });
    await expect(bridge.getMaterialInfo()).rejects.toThrow("CC5 error: no avatar selected");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(503, "Service Unavailable");
    await expect(bridge.getMaterialInfo()).rejects.toThrow("CC5 bridge error (503)");
  });

  it("throws on network failure", async () => {
    mockFetchError("connection refused");
    await expect(bridge.getMaterialInfo()).rejects.toThrow("connection refused");
  });
});

// ── getDiffuseColor ───────────────────────────────────────────────────────────

describe("CC5Bridge.getDiffuseColor", () => {
  const sampleColor: DiffuseColor = { r: 0.8, g: 0.6, b: 0.4 };

  it("returns DiffuseColor on success", async () => {
    mockFetch<DiffuseColor>({ result: sampleColor });
    const result = await bridge.getDiffuseColor("CC_Base_Body", "Std_Skin_Body");
    expect(result).toEqual(sampleColor);
    expect(result.r).toBe(0.8);
    expect(result.g).toBe(0.6);
    expect(result.b).toBe(0.4);
  });

  it("returns DiffuseColor with error field when material not found", async () => {
    const colorWithError: DiffuseColor = { r: 0, g: 0, b: 0, error: "material not found" };
    mockFetch<DiffuseColor>({ result: colorWithError });
    const result = await bridge.getDiffuseColor("Bad_Mesh", "Bad_Mat");
    expect(result.error).toBe("material not found");
  });

  it("sends POST /material/color/get with mesh and material names", async () => {
    mockFetch<DiffuseColor>({ result: sampleColor });
    await bridge.getDiffuseColor("CC_Base_Body", "Std_Skin_Body");
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/material/color/get",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ mesh_name: "CC_Base_Body", material_name: "Std_Skin_Body" }),
      })
    );
  });

  it("throws on bridge error field", async () => {
    mockFetch({ error: "mesh not found" });
    await expect(bridge.getDiffuseColor("Mesh", "Mat")).rejects.toThrow("CC5 error: mesh not found");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(400, "Bad Request");
    await expect(bridge.getDiffuseColor("Mesh", "Mat")).rejects.toThrow("CC5 bridge error (400)");
  });

  it("throws on network failure", async () => {
    mockFetchError("timeout");
    await expect(bridge.getDiffuseColor("Mesh", "Mat")).rejects.toThrow("timeout");
  });
});

// ── setDiffuseColor ───────────────────────────────────────────────────────────

describe("CC5Bridge.setDiffuseColor", () => {
  const successResult: SetDiffuseColorResult = {
    success: true,
    mesh: "CC_Base_Body",
    material: "Std_Skin_Body",
  };

  it("returns SetDiffuseColorResult on success", async () => {
    mockFetch<SetDiffuseColorResult>({ result: successResult });
    const result = await bridge.setDiffuseColor("CC_Base_Body", "Std_Skin_Body", 0.9, 0.7, 0.5);
    expect(result.success).toBe(true);
    expect(result.mesh).toBe("CC_Base_Body");
    expect(result.material).toBe("Std_Skin_Body");
  });

  it("returns failure result when CC5 cannot set the color", async () => {
    const failure: SetDiffuseColorResult = { success: false, error: "material locked" };
    mockFetch<SetDiffuseColorResult>({ result: failure });
    const result = await bridge.setDiffuseColor("Mesh", "Mat", 0.5, 0.5, 0.5);
    expect(result.success).toBe(false);
    expect(result.error).toBe("material locked");
  });

  it("sends POST /material/color/set with all required fields", async () => {
    mockFetch<SetDiffuseColorResult>({ result: successResult });
    await bridge.setDiffuseColor("CC_Base_Body", "Std_Skin_Body", 0.9, 0.7, 0.5);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/material/color/set",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          mesh_name: "CC_Base_Body",
          material_name: "Std_Skin_Body",
          r: 0.9,
          g: 0.7,
          b: 0.5,
        }),
      })
    );
  });

  it("handles boundary RGB values of 0 and 1", async () => {
    mockFetch<SetDiffuseColorResult>({ result: { success: true } });
    const result = await bridge.setDiffuseColor("Mesh", "Mat", 0, 1, 0);
    expect(result.success).toBe(true);
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ mesh_name: "Mesh", material_name: "Mat", r: 0, g: 1, b: 0 }),
      })
    );
  });

  it("throws on bridge error field", async () => {
    mockFetch({ error: "no avatar" });
    await expect(bridge.setDiffuseColor("M", "N", 0, 0, 0)).rejects.toThrow("CC5 error: no avatar");
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "server error");
    await expect(bridge.setDiffuseColor("M", "N", 0, 0, 0)).rejects.toThrow("CC5 bridge error (500)");
  });

  it("throws on network failure", async () => {
    mockFetchError("ECONNREFUSED");
    await expect(bridge.setDiffuseColor("M", "N", 0, 0, 0)).rejects.toThrow("ECONNREFUSED");
  });
});

// ── createActorMixer ──────────────────────────────────────────────────────────

describe("CC5Bridge.createActorMixer", () => {
  const dryRun: CreateActorMixerResult = {
    success: true,
    morph_name: "Camila",
    created: false,
    dry_run: true,
    new_presets: [],
    presets_dir: "C:/Custom/ActorMIXER",
    scheduled: true,
  };

  it("sends POST /actor_mixer/create with confirm_create always present", async () => {
    mockFetch<CreateActorMixerResult>({ result: dryRun });
    await bridge.createActorMixer({ confirm_create: false });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      "http://localhost:5101/actor_mixer/create",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ confirm_create: false }),
      })
    );
  });

  it("includes only provided optional fields in the body", async () => {
    mockFetch<CreateActorMixerResult>({ result: dryRun });
    await bridge.createActorMixer({
      confirm_create: true,
      morph_name: "Hero",
      use_parts_folder: true,
      head_parts: { eyes: false },
    });
    expect(vi.mocked(fetch)).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          confirm_create: true,
          morph_name: "Hero",
          use_parts_folder: true,
          head_parts: { eyes: false },
        }),
      })
    );
  });

  it("returns the dry-run result on success", async () => {
    mockFetch<CreateActorMixerResult>({ result: dryRun });
    const result = await bridge.createActorMixer({ confirm_create: false });
    expect(result.success).toBe(true);
    expect(result.dry_run).toBe(true);
    expect(result.presets_dir).toBe("C:/Custom/ActorMIXER");
  });

  it("returns created result with new_presets on confirmed create", async () => {
    mockFetch<CreateActorMixerResult>({
      result: {
        success: true,
        morph_name: "Camila",
        created: true,
        dry_run: false,
        new_presets: ["C:/Custom/ActorMIXER/Camila.ccMixerPreset"],
        presets_dir: "C:/Custom/ActorMIXER",
      },
    });
    const result = await bridge.createActorMixer({ confirm_create: true });
    expect(result.created).toBe(true);
    expect(result.new_presets).toEqual(["C:/Custom/ActorMIXER/Camila.ccMixerPreset"]);
  });

  it("returns failure when ActorMIXER PRO is unavailable", async () => {
    mockFetch<CreateActorMixerResult>({
      result: { success: false, error: "ActorMIXER PRO required" },
    });
    const result = await bridge.createActorMixer({ confirm_create: false });
    expect(result.success).toBe(false);
    expect(result.error).toBe("ActorMIXER PRO required");
  });

  it("passes through the trial_content flag from the bridge", async () => {
    mockFetch<CreateActorMixerResult>({
      result: { success: false, error: "trial content", trial_content: true },
    });
    const result = await bridge.createActorMixer({ confirm_create: true });
    expect(result.success).toBe(false);
    expect(result.trial_content).toBe(true);
  });

  it("throws on HTTP error", async () => {
    mockFetchHttpError(500, "server error");
    await expect(bridge.createActorMixer({ confirm_create: false })).rejects.toThrow(
      "CC5 bridge error (500)"
    );
  });

  it("throws on network failure", async () => {
    mockFetchError("ECONNREFUSED");
    await expect(bridge.createActorMixer({ confirm_create: true })).rejects.toThrow("ECONNREFUSED");
  });
});
