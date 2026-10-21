/**
 * Tests for dialog detection: parsing, warning text, caching, the server.tool wrapper
 * and the list_dialogs tool. The PowerShell probe itself is injected (never spawned here).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  parseScan,
  isSensitiveDialog,
  formatDialogWarning,
  DialogWatcher,
  withDialogWatch,
  type DialogInfo,
} from "../src/dialogs.js";
import { registerDialogTools } from "../src/tools/dialogs.js";
import { createMockServer } from "./helpers/mock-server.js";

function dlg(over: Partial<DialogInfo> = {}): DialogInfo {
  return {
    process: "CharacterCreator",
    pid: 1,
    hwnd: 2,
    title: "Open",
    className: "#32770",
    foreground: true,
    hasOwner: true,
    modal: true,
    rect: [0, 0, 100, 100],
    texts: ["File name:"],
    buttons: ["Open", "Cancel"],
    textSource: "win32",
    screenshot: null,
    ...over,
  };
}

describe("parseScan", () => {
  it("parses JSON and strips a BOM", () => {
    const r = parseScan("\uFEFF" + JSON.stringify({ timestamp: "t", dialogs: [dlg()] }));
    expect(r.dialogs).toHaveLength(1);
    expect(r.dialogs[0].title).toBe("Open");
  });
  it("treats a missing dialogs field as empty", () => {
    expect(parseScan('{"timestamp":"t"}').dialogs).toEqual([]);
  });
  it("throws on garbage", () => {
    expect(() => parseScan("not json")).toThrow();
  });
});

describe("isSensitiveDialog", () => {
  it.each([
    ["License Agreement", [], []],
    ["Hub", ["今すぐアップデートしますか"], ["更新"]],
    ["Login", ["Sign in to continue"], []],
    ["Confirm", ["Overwrite existing file?"], ["Yes"]],
    ["確認", ["ファイルを上書きしますか"], []],
    ["購入", [], []],
  ])("flags %s", (title, texts, buttons) => {
    expect(isSensitiveDialog({ title, texts: texts as string[], buttons: buttons as string[] })).toBe(true);
  });
  it("does not flag a plain file-open dialog", () => {
    expect(isSensitiveDialog({ title: "開く", texts: ["ファイル名:"], buttons: ["開く", "キャンセル"] })).toBe(false);
  });
});

describe("formatDialogWarning", () => {
  afterEach(() => {
    delete process.env.CC5_DIALOG_WATCH_IGNORE_HUB;
  });
  it("is null with no dialogs", () => {
    expect(formatDialogWarning([])).toBeNull();
  });
  it("names title, body and buttons for a CC5 dialog", () => {
    const w = formatDialogWarning([dlg({ title: "Unsaved project", texts: ["Save?"], buttons: ["Yes", "No"] })])!;
    expect(w).toContain("⚠ CC5 に小窓");
    expect(w).toContain("Unsaved project");
    expect(w).toContain("Save?");
    expect(w).toContain("Yes | No");
    expect(w).toContain("人が判断");
    expect(w).toContain("勝手に押さない");
  });
  it("uses the info header for Hub-only dialogs", () => {
    const w = formatDialogWarning([dlg({ process: "Reallusion Hub", title: "x" })])!;
    expect(w.startsWith("ℹ Reallusion Hub")).toBe(true);
  });
  it("can ignore Hub dialogs via env", () => {
    process.env.CC5_DIALOG_WATCH_IGNORE_HUB = "1";
    expect(formatDialogWarning([dlg({ process: "Reallusion Hub" })])).toBeNull();
  });
  it("truncates to five entries", () => {
    const w = formatDialogWarning(Array.from({ length: 7 }, (_, i) => dlg({ title: `T${i}` })))!;
    expect(w).toContain("ほか 2 件");
  });
});

describe("DialogWatcher", () => {
  let t = 0;
  const now = () => t;
  beforeEach(() => {
    t = 1000;
  });

  it("caches within the ttl", async () => {
    const scan = vi.fn().mockResolvedValue({ timestamp: "", dialogs: [dlg()] });
    const w = new DialogWatcher(scan, 4000, 3000, now, true);
    expect(await w.getWarning()).toContain("⚠");
    t += 1000;
    await w.getWarning();
    expect(scan).toHaveBeenCalledTimes(1);
    t += 5000;
    await w.getWarning();
    expect(scan).toHaveBeenCalledTimes(2);
  });

  it("never throws when the scan fails, and returns null", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const scan = vi.fn().mockRejectedValue(new Error("boom"));
    const w = new DialogWatcher(scan, 4000, 3000, now, true);
    expect(await w.getWarning()).toBeNull();
    spy.mockRestore();
  });

  it("does not scan when disabled", async () => {
    const scan = vi.fn();
    const w = new DialogWatcher(scan, 4000, 3000, now, false);
    expect(await w.getWarning()).toBeNull();
    expect(scan).not.toHaveBeenCalled();
  });

  it("falls back to the stale cache when a rescan is slow", async () => {
    let first = true;
    const scan = vi.fn().mockImplementation(() =>
      first ? ((first = false), Promise.resolve({ timestamp: "", dialogs: [dlg()] })) : new Promise(() => {}),
    );
    const w = new DialogWatcher(scan, 4000, 20, now, true);
    await w.getWarning();
    t += 10_000;
    expect(await w.getWarning()).toContain("⚠");
  });
});

describe("withDialogWatch", () => {
  it("prepends the warning to every tool result but not to list_dialogs", async () => {
    const server = createMockServer();
    const watcher = new DialogWatcher(vi.fn().mockResolvedValue({ timestamp: "", dialogs: [dlg()] }), 4000, 3000, () => 0, true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    withDialogWatch(server as any, watcher);
    server.tool("undo", "d", {}, async () => ({ content: [{ type: "text", text: "Undo successful" }] }));
    server.tool("list_dialogs", "d", {}, async () => ({ content: [{ type: "text", text: "list" }] }));
    const undo = await server.getRegisteredTool("undo")({});
    expect(undo.content[0].text).toContain("⚠ CC5 に小窓");
    expect(undo.content[1].text).toBe("Undo successful");
    const list = await server.getRegisteredTool("list_dialogs")({});
    expect(list.content).toHaveLength(1);
  });

  it("leaves results untouched when no dialog is open", async () => {
    const server = createMockServer();
    const watcher = new DialogWatcher(vi.fn().mockResolvedValue({ timestamp: "", dialogs: [] }), 4000, 3000, () => 0, true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    withDialogWatch(server as any, watcher);
    server.tool("undo", "d", {}, async () => ({ content: [{ type: "text", text: "ok" }] }));
    const r = await server.getRegisteredTool("undo")({});
    expect(r.content).toEqual([{ type: "text", text: "ok" }]);
  });
});

describe("list_dialogs tool", () => {
  it("registers exactly one tool and there is no click/dismiss tool", () => {
    const server = createMockServer();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    registerDialogTools(server as any);
    expect(server.tool).toHaveBeenCalledTimes(1);
    expect(server.tool.mock.calls[0][0]).toBe("list_dialogs");
  });

  it("reports an empty list", async () => {
    const server = createMockServer();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    registerDialogTools(server as any, undefined, vi.fn().mockResolvedValue({ timestamp: "", dialogs: [] }));
    const r = await server.getRegisteredTool("list_dialogs")({});
    expect(r.content[0].text).toContain("ありません");
  });

  it("lists dialogs and attaches an image from the temp dir only", async () => {
    const png = path.join(os.tmpdir(), `cc5-dlg-test-${process.pid}.png`);
    fs.writeFileSync(png, Buffer.from([0x89, 0x50, 0x4e, 0x47]));
    const server = createMockServer();
    const scan = vi.fn().mockResolvedValue({
      timestamp: "",
      dialogs: [dlg({ screenshot: png }), dlg({ title: "evil", screenshot: "C:\\Windows\\win.ini" })],
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    registerDialogTools(server as any, undefined, scan);
    const r = await server.getRegisteredTool("list_dialogs")({});
    fs.unlinkSync(png);
    expect(r.content[0].text).toContain("開いている小窓: 2件");
    const images = r.content.filter((c) => c.type === "image");
    expect(images).toHaveLength(1);
  });

  it("returns an error text when the scan fails", async () => {
    const server = createMockServer();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    registerDialogTools(server as any, undefined, vi.fn().mockRejectedValue(new Error("nope")));
    const r = await server.getRegisteredTool("list_dialogs")({});
    expect(r.content[0].text).toContain("nope");
  });
});
