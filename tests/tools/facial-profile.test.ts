/**
 * Unit tests for registerFacialProfileTools.
 *
 * get_facial_profile is read-only (detects the avatar's expression profile).
 * convert_facial_profile swaps the profile via LoadProfile and defaults to
 * dry_run=true (safety). Path validation (absolute, no traversal) lives in the
 * tool layer; the LoadProfile execution + RLPy limitation live in Python.
 * Bridge errors are caught by bridgeCall and become content text.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { registerFacialProfileTools, _internal } from "../../src/tools/facial-profile.js";
import { createMockBridge } from "../helpers/mock-bridge.js";
import type { MockBridge } from "../helpers/mock-bridge.js";
import { createMockServer } from "../helpers/mock-server.js";
import type { FacialProfileInfo, ConvertFacialProfileResult } from "../../src/types.js";

// ── fixtures ──────────────────────────────────────────────────────────────────

const PROFILE_OK: FacialProfileInfo = {
  success: true,
  avatar: "CC3_Base_Plus",
  profile_type_id: 1,
  profile_type: "CC5MetaHuman",
  expression_set_uid: "CC5 MetaHuman",
  category_slider_counts: { Brows: 8, Jaw: 14 },
  total_sliders: 379,
  category_count: 19,
  heuristic_class: "CC5 MetaHuman (HD)",
  arkit_capable: true,
};

const CONVERT_DRY: ConvertFacialProfileResult = {
  success: true,
  dry_run: true,
  applied: false,
  current_profile: { profile_type: "CC5MetaHuman", expression_set_uid: "CC5 MetaHuman", total_sliders: 379 },
  target_profile_path: "",
  target_path_valid: false,
  path_error: null,
  notes: ["RLPy has no direct profile-type / ExPlus-upgrade API; this LOADS a target .ccFacialProfile."],
};

const CONVERT_APPLIED: ConvertFacialProfileResult = {
  success: true,
  dry_run: false,
  applied: true,
  before: { profile_type: "CC5MetaHuman", total_sliders: 379 },
  after: { profile_type: "Traditional", total_sliders: 60 },
  backup_saved_to: "D:/tmp/backup.ccFacialProfile",
  target_profile_path: "D:/profiles/explus.ccFacialProfile",
};

// ── setup ─────────────────────────────────────────────────────────────────────

let bridge: MockBridge;
let server: ReturnType<typeof createMockServer>;

beforeEach(() => {
  bridge = createMockBridge();
  server = createMockServer();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  registerFacialProfileTools(server as any, bridge as any);
});

// ── registration ──────────────────────────────────────────────────────────────

describe("registerFacialProfileTools – registration", () => {
  it("registers exactly 2 tools", () => {
    expect(server.tool).toHaveBeenCalledTimes(2);
  });

  it("registers get_facial_profile", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "get_facial_profile", expect.any(String), expect.any(Object), expect.any(Function),
    );
  });

  it("registers convert_facial_profile", () => {
    expect(server.tool).toHaveBeenCalledWith(
      "convert_facial_profile", expect.any(String), expect.any(Object), expect.any(Function),
    );
  });
});

// ── get_facial_profile ──────────────────────────────────────────────────────────

describe("get_facial_profile handler", () => {
  it("formats the profile type, UID, slider count and heuristic class", async () => {
    bridge.getFacialProfile.mockResolvedValue(PROFILE_OK);
    const handler = server.getRegisteredTool("get_facial_profile");
    const result = await handler({});
    const text = result.content[0].text;
    expect(text).toContain("CC5MetaHuman");
    expect(text).toContain("CC5 MetaHuman");
    expect(text).toContain("379");
    expect(text).toContain("CC5 MetaHuman (HD)");
    expect(text).toContain("ARKit-capable: yes");
  });

  it("returns a Failed message when the bridge reports success:false", async () => {
    bridge.getFacialProfile.mockResolvedValue({ success: false, error: "No avatar" });
    const handler = server.getRegisteredTool("get_facial_profile");
    const result = await handler({});
    expect(result.content[0].text).toContain("Failed: No avatar");
  });

  it("returns bridge error text when the bridge throws (does not propagate)", async () => {
    bridge.getFacialProfile.mockRejectedValue(new Error("CC5 not connected"));
    const handler = server.getRegisteredTool("get_facial_profile");
    const result = await handler({});
    expect(result.content[0].text).toContain("CC5 bridge error: CC5 not connected");
  });
});

// ── convert_facial_profile – dry run ────────────────────────────────────────────

describe("convert_facial_profile handler – dry run", () => {
  it("renders a DRY RUN message with the current profile", async () => {
    bridge.convertFacialProfile.mockResolvedValue(CONVERT_DRY);
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "", dry_run: true, backup_current_to: "" });
    expect(result.content[0].text).toContain("DRY RUN");
    expect(result.content[0].text).toContain("CC5MetaHuman");
  });

  it("forwards dry_run=true to the bridge", async () => {
    bridge.convertFacialProfile.mockResolvedValue(CONVERT_DRY);
    const handler = server.getRegisteredTool("convert_facial_profile");
    await handler({ target_profile_path: "", dry_run: true, backup_current_to: "" });
    expect(bridge.convertFacialProfile).toHaveBeenCalledWith(
      expect.objectContaining({ dry_run: true }),
    );
  });

  it("rejects a relative target path before calling the bridge", async () => {
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "relative/foo.ccFacialProfile", dry_run: true });
    expect(result.content[0].text).toContain("must be absolute");
    expect(bridge.convertFacialProfile).not.toHaveBeenCalled();
  });

  it("rejects a path-traversal target before calling the bridge", async () => {
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "D:/../secret.ccFacialProfile", dry_run: true });
    expect(result.content[0].text).toContain("traversal");
    expect(bridge.convertFacialProfile).not.toHaveBeenCalled();
  });

  it("rejects a relative backup path before calling the bridge", async () => {
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "", dry_run: true, backup_current_to: "rel/backup.ccFacialProfile" });
    expect(result.content[0].text).toContain("backup_current_to");
    expect(bridge.convertFacialProfile).not.toHaveBeenCalled();
  });
});

// ── convert_facial_profile – applied ────────────────────────────────────────────

describe("convert_facial_profile handler – applied", () => {
  it("renders an Applied before/after message and the backup path", async () => {
    bridge.convertFacialProfile.mockResolvedValue(CONVERT_APPLIED);
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "D:/profiles/explus.ccFacialProfile", dry_run: false });
    const text = result.content[0].text;
    expect(text).toContain("Applied");
    expect(text).toContain("CC5MetaHuman");
    expect(text).toContain("Traditional");
    expect(text).toContain("D:/tmp/backup.ccFacialProfile");
  });

  it("returns a Failed message when the bridge reports success:false", async () => {
    bridge.convertFacialProfile.mockResolvedValue({ success: false, error: "LoadProfile failed" });
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "D:/profiles/explus.ccFacialProfile", dry_run: false });
    expect(result.content[0].text).toContain("Failed: LoadProfile failed");
  });

  it("returns bridge error text when the bridge throws", async () => {
    bridge.convertFacialProfile.mockRejectedValue(new Error("timeout"));
    const handler = server.getRegisteredTool("convert_facial_profile");
    const result = await handler({ target_profile_path: "D:/profiles/explus.ccFacialProfile", dry_run: false });
    expect(result.content[0].text).toContain("CC5 bridge error: timeout");
  });
});

// ── validateProfilePath unit ────────────────────────────────────────────────────

describe("_internal.validateProfilePath", () => {
  it("allows an empty path (inspection-only dry run)", () => {
    expect(_internal.validateProfilePath("")).toBeNull();
  });

  it("allows an absolute path", () => {
    expect(_internal.validateProfilePath("D:/profiles/explus.ccFacialProfile")).toBeNull();
  });

  it("rejects a relative path", () => {
    expect(_internal.validateProfilePath("profiles/explus.ccFacialProfile")).toContain("absolute");
  });

  it("rejects a traversal path", () => {
    expect(_internal.validateProfilePath("D:/../x")).toContain("traversal");
  });

  it("rejects a null byte", () => {
    expect(_internal.validateProfilePath(`D:/x${String.fromCharCode(0)}.ccFacialProfile`)).toContain("null byte");
  });
});
