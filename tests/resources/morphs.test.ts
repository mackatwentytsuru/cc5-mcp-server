/**
 * Unit tests for registerMorphResources.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { registerMorphResources } from "../../src/resources/morphs.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { MorphCatalog, AvatarInfo } from "../../src/types.js";

// ── mock server ───────────────────────────────────────────────────────────────

type ResourceHandler = (uri: URL) => Promise<{
  contents: Array<{ uri: string; mimeType: string; text: string }>;
}>;

interface CapturedResource {
  name: string;
  uri: string;
  handler: ResourceHandler;
}

function createMockServer() {
  const registered: CapturedResource[] = [];
  const resourceSpy = vi.fn((...args: unknown[]) => {
    const name = args[0] as string;
    const uri = args[1] as string;
    const handler = args[args.length - 1] as ResourceHandler;
    registered.push({ name, uri, handler });
  });
  return {
    resource: resourceSpy,
    getRegisteredResource: (name: string): ResourceHandler => {
      const entry = registered.find((r) => r.name === name);
      if (!entry) throw new Error(`Resource '${name}' was not registered`);
      return entry.handler;
    },
    getRegisteredResources: () => registered,
  };
}

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerMorphResources(server as any, bridge as any);
});

// ── registration ──────────────────────────────────────────────────────────────

describe("registerMorphResources – registration", () => {
  it("registers exactly 2 resources", () => {
    expect(server.resource).toHaveBeenCalledTimes(2);
  });

  it("registers morph-catalog with cc5://morphs/catalog URI", () => {
    const resources = server.getRegisteredResources();
    const catalog = resources.find((r) => r.name === "morph-catalog");
    expect(catalog).toBeDefined();
    expect(catalog?.uri).toBe("cc5://morphs/catalog");
  });

  it("registers avatar-state with cc5://avatar/current URI", () => {
    const resources = server.getRegisteredResources();
    const avatarState = resources.find((r) => r.name === "avatar-state");
    expect(avatarState).toBeDefined();
    expect(avatarState?.uri).toBe("cc5://avatar/current");
  });
});

// ── morph-catalog resource ─────────────────────────────────────────────────────

describe("morph-catalog resource handler", () => {
  const catalog: MorphCatalog = {
    Body: [
      { id: "Fat", display_name: "Fat" },
      { id: "Muscular", display_name: "Muscular" },
    ],
    Face: [{ id: "Nose_Size", display_name: "Nose Size" }],
  };

  const uri = new URL("cc5://morphs/catalog");

  it("returns the morph catalog as formatted JSON", async () => {
    bridge.getMorphCatalog.mockResolvedValue(catalog);
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    const parsed = JSON.parse(result.contents[0].text);
    expect(parsed).toEqual(catalog);
  });

  it("returns application/json mimeType", async () => {
    bridge.getMorphCatalog.mockResolvedValue(catalog);
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    expect(result.contents[0].mimeType).toBe("application/json");
  });

  it("returns the request URI in the contents uri field", async () => {
    bridge.getMorphCatalog.mockResolvedValue(catalog);
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    expect(result.contents[0].uri).toBe(uri.href);
  });

  it("returns error JSON when bridge throws", async () => {
    bridge.getMorphCatalog.mockRejectedValue(new Error("CC5 offline"));
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    const parsed = JSON.parse(result.contents[0].text);
    expect(parsed.error).toBeTruthy();
    expect(parsed.hint).toBeTruthy();
  });

  it("error response still returns application/json mimeType", async () => {
    bridge.getMorphCatalog.mockRejectedValue(new Error("CC5 offline"));
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    expect(result.contents[0].mimeType).toBe("application/json");
  });

  it("returns pretty-printed JSON (contains newlines)", async () => {
    bridge.getMorphCatalog.mockResolvedValue(catalog);
    const handler = server.getRegisteredResource("morph-catalog");
    const result = await handler(uri);
    expect(result.contents[0].text).toContain("\n");
  });
});

// ── avatar-state resource ──────────────────────────────────────────────────────

describe("avatar-state resource handler", () => {
  const sampleInfo: AvatarInfo = {
    id: "av1",
    name: "MyHero",
    active_morphs: { Fat: 0.3, Muscular: 0.5 },
  };

  const uri = new URL("cc5://avatar/current");

  it("returns avatar info as formatted JSON", async () => {
    bridge.getAvatarInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    const parsed = JSON.parse(result.contents[0].text);
    expect(parsed).toEqual(sampleInfo);
  });

  it("returns application/json mimeType", async () => {
    bridge.getAvatarInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    expect(result.contents[0].mimeType).toBe("application/json");
  });

  it("returns the request URI in the contents uri field", async () => {
    bridge.getAvatarInfo.mockResolvedValue(sampleInfo);
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    expect(result.contents[0].uri).toBe(uri.href);
  });

  it("returns null info as JSON null when no avatar is present", async () => {
    bridge.getAvatarInfo.mockResolvedValue(null);
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    const parsed = JSON.parse(result.contents[0].text);
    expect(parsed).toBeNull();
  });

  it("returns error JSON when bridge throws", async () => {
    bridge.getAvatarInfo.mockRejectedValue(new Error("bridge unavailable"));
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    const parsed = JSON.parse(result.contents[0].text);
    expect(parsed.error).toBeTruthy();
  });

  it("error response contains contents array with one item", async () => {
    bridge.getAvatarInfo.mockRejectedValue(new Error("fail"));
    const handler = server.getRegisteredResource("avatar-state");
    const result = await handler(uri);
    expect(result.contents).toHaveLength(1);
  });
});
