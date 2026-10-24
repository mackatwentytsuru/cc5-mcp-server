/**
 * Unit tests for the avatar-part tools in registerContentTools (list_avatar_parts,
 * remove_avatar_part). HD brows are avatar parts, not hairs, so list_hair misses them.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerContentTools } from "../../src/tools/content.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import type { AvatarPartsResult, RemoveAvatarPartResult } from "../../src/types.js";
import { createMockServer } from "../helpers/mock-server.js";

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerContentTools(server as any, bridge as any);
});

describe("list_avatar_parts handler", () => {
  const sample: AvatarPartsResult = {
    success: true,
    avatar: "CC3_Base_Plus",
    parts: [
      { type: "Brow", name: "Female_Petite", id: 1, removable: true },
      { type: "Eyelash", name: "Lash_Up_Wavy", id: 2, removable: false },
    ],
  };

  it("is registered", () => {
    expect(server.tool).toHaveBeenCalledWith("list_avatar_parts", expect.any(String), expect.any(Object), expect.any(Function));
  });

  it("lists each part with its type and whether it can be removed", async () => {
    bridge.listAvatarParts.mockResolvedValue(sample);
    const text = (await server.getRegisteredTool("list_avatar_parts")({})).content[0].text;
    expect(text).toContain("CC3_Base_Plus");
    expect(text).toContain("- Brow: Female_Petite (removable)");
    expect(text).toContain("- Eyelash: Lash_Up_Wavy");
    expect(text).not.toContain("Lash_Up_Wavy (removable)");
  });

  it("returns the failure message", async () => {
    bridge.listAvatarParts.mockResolvedValue({ success: false, error: "No avatar in scene" });
    const text = (await server.getRegisteredTool("list_avatar_parts")({})).content[0].text;
    expect(text).toBe("Failed: No avatar in scene");
  });
});

describe("remove_avatar_part handler", () => {
  it("is registered", () => {
    expect(server.tool).toHaveBeenCalledWith("remove_avatar_part", expect.any(String), expect.any(Object), expect.any(Function));
  });

  it("removes all brows by type and reports what was removed", async () => {
    const removed: RemoveAvatarPartResult = {
      success: true, removed: [{ type: "Brow", name: "Female_Petite" }], remaining_face_hair: [],
    };
    bridge.removeAvatarPart.mockResolvedValue(removed);
    const text = (await server.getRegisteredTool("remove_avatar_part")({ type: "Brow" })).content[0].text;
    expect(bridge.removeAvatarPart).toHaveBeenCalledWith(undefined, "Brow");
    expect(text).toBe("Removed: Brow Female_Petite");
  });

  it("only accepts Brow or Beard as the type", () => {
    const call = server.tool.mock.calls.find((c: unknown[]) => c[0] === "remove_avatar_part");
    expect(call[2].type.safeParse("Eyelash").success).toBe(false);
    expect(call[2].type.safeParse("Beard").success).toBe(true);
  });

  it("returns the failure message from the bridge", async () => {
    bridge.removeAvatarPart.mockResolvedValue({ success: false, error: "Only Brow, Beard parts can be removed" });
    const text = (await server.getRegisteredTool("remove_avatar_part")({ name: "Lash_Up_Wavy" })).content[0].text;
    expect(text).toBe("Failed: Only Brow, Beard parts can be removed");
  });
});
