/**
 * Pop-up / dialog detection for CC5 and Reallusion Hub.
 *
 * A modal dialog in CC5 blocks the plugin's main-thread QTimer queue, so the HTTP bridge
 * still answers /health but nothing executes. This module asks Windows directly (via
 * scripts/list-dialogs.ps1: EnumWindows + UI Automation), so it works while CC5 is stuck.
 *
 * It is READ-ONLY. There is deliberately no tool that clicks a dialog: agreements,
 * purchases, logins, updates, deletes and overwrites must be decided by a human.
 */

import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export interface DialogInfo {
  process: string;
  pid: number;
  hwnd: number;
  title: string;
  className: string;
  foreground: boolean;
  hasOwner: boolean;
  modal: boolean;
  rect: number[];
  texts: string[];
  buttons: string[];
  textSource: string;
  screenshot: string | null;
}

export interface DialogScan {
  timestamp: string;
  dialogs: DialogInfo[];
}

export type ScanFn = (screenshot: boolean) => Promise<DialogScan>;

const SCRIPT_PATH = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "scripts",
  "list-dialogs.ps1",
);
const SCAN_TIMEOUT_MS = 8_000;

/** Run the PowerShell probe. Rejects on non-Windows, timeout or bad output. */
export const scanDialogs: ScanFn = (screenshot) =>
  new Promise((resolve, reject) => {
    if (process.platform !== "win32") {
      reject(new Error("dialog detection is only available on Windows"));
      return;
    }
    const args = ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", SCRIPT_PATH];
    if (screenshot) args.push("-Screenshot");
    execFile(
      "powershell.exe",
      args,
      { timeout: SCAN_TIMEOUT_MS, windowsHide: true, maxBuffer: 4 * 1024 * 1024, encoding: "utf8" },
      (err, stdout) => {
        if (err) {
          reject(err);
          return;
        }
        try {
          resolve(parseScan(stdout));
        } catch (e) {
          reject(e);
        }
      },
    );
  });

export function parseScan(stdout: string): DialogScan {
  const parsed = JSON.parse(stdout.replace(/^﻿/, "").trim()) as Partial<DialogScan>;
  const dialogs = Array.isArray(parsed.dialogs) ? parsed.dialogs : [];
  return { timestamp: String(parsed.timestamp ?? ""), dialogs };
}

// Dialogs a human must decide. Matched against title + body text + button labels.
const SENSITIVE_PATTERNS: RegExp[] = [
  /licen[sc]e/i, /agreement/i, /\beula\b/i, /terms/i, /privacy/i,
  /purchase/i, /\bbuy\b/i, /checkout/i, /payment/i, /\border\b/i,
  /log\s?in/i, /sign[\s-]?in/i, /password/i, /account/i, /activate/i,
  /update/i, /upgrade/i, /install/i,
  /delete/i, /overwrite/i, /replace/i, /unsaved/i,
  /規約/, /同意/, /ライセンス/, /購入/, /支払/, /ログイン/, /サインイン/, /パスワード/,
  /アカウント/, /アクティベ/, /更新/, /アップデート/, /アップグレード/, /インストール/,
  /削除/, /上書き/, /置き換え/, /保存されていない/, /未保存/,
];

export function isSensitiveDialog(d: Pick<DialogInfo, "title" | "texts" | "buttons">): boolean {
  const haystack = [d.title, ...d.texts, ...d.buttons].join("\n");
  return SENSITIVE_PATTERNS.some((re) => re.test(haystack));
}

function clip(s: string, n: number): string {
  const one = s.replace(/\s+/g, " ").trim();
  return one.length > n ? `${one.slice(0, n - 1)}…` : one;
}

function isHub(d: DialogInfo): boolean {
  return /hub/i.test(d.process);
}

export function describeDialog(d: DialogInfo): string {
  const body = clip(d.texts.join(" / "), 160);
  const buttons = d.buttons.length > 0 ? `ボタン: ${d.buttons.slice(0, 6).join(" | ")}` : "ボタン: (取得できず)";
  const flags = [
    d.foreground ? "前面" : null,
    d.modal ? "モーダル" : null,
    isSensitiveDialog(d) ? "規約・購入・ログイン・更新・削除・上書きなどの恐れ: 人が判断" : null,
  ].filter(Boolean);
  return `[${d.process}] 「${clip(d.title, 80) || "(題名なし)"}」${body ? ` / ${body}` : ""} / ${buttons}${flags.length ? ` (${flags.join(", ")})` : ""}`;
}

/** Warning header for tool results, or null when nothing is open. */
export function formatDialogWarning(dialogs: DialogInfo[]): string | null {
  if (dialogs.length === 0) return null;
  const ignoreHub = process.env.CC5_DIALOG_WATCH_IGNORE_HUB === "1";
  const shown = dialogs.filter((d) => !(ignoreHub && isHub(d)));
  if (shown.length === 0) return null;
  const cc5 = shown.filter((d) => !isHub(d));
  const lines = shown.slice(0, 5).map((d) => `  - ${describeDialog(d)}`);
  const head = cc5.length > 0
    ? `⚠ CC5 に小窓が出ています (${shown.length}件)。CC5 が止まっている/操作が実行されない可能性があります。先に人に確かめてください。ボタンを勝手に押さないでください。`
    : `ℹ Reallusion Hub に小窓が出ています (${shown.length}件)。人に確かめてください。ボタンを勝手に押さないでください。`;
  const more = shown.length > 5 ? `\n  ...ほか ${shown.length - 5} 件 (list_dialogs で全件)` : "";
  return `${head}\n${lines.join("\n")}${more}\n  詳しくは list_dialogs ツール (画像つき)。`;
}

/** Caches scans so that every tool call does not spawn PowerShell. Never throws. */
export class DialogWatcher {
  private cache: { at: number; dialogs: DialogInfo[] } | null = null;
  private inflight: Promise<void> | null = null;

  constructor(
    private readonly scan: ScanFn = scanDialogs,
    private readonly ttlMs = 4_000,
    private readonly maxWaitMs = 3_000,
    private readonly now: () => number = Date.now,
    private readonly enabled: boolean = process.env.CC5_DIALOG_WATCH !== "0",
  ) {}

  private refresh(): Promise<void> {
    if (!this.inflight) {
      this.inflight = this.scan(false)
        .then((r) => {
          this.cache = { at: this.now(), dialogs: r.dialogs };
        })
        .catch((err) => {
          console.error("[CC5 MCP] dialog scan failed:", err instanceof Error ? err.message : err);
        })
        .finally(() => {
          this.inflight = null;
        });
    }
    return this.inflight;
  }

  /** Current warning text (or null). Waits at most maxWaitMs for a fresh scan, else uses the stale cache. */
  async getWarning(): Promise<string | null> {
    if (!this.enabled) return null;
    const fresh = this.cache && this.now() - this.cache.at < this.ttlMs;
    if (!fresh) {
      const p = this.refresh();
      await Promise.race([p, new Promise<void>((r) => setTimeout(r, this.maxWaitMs).unref())]);
    }
    return this.cache ? formatDialogWarning(this.cache.dialogs) : null;
  }

  /** Store the result of an explicit list_dialogs scan. */
  update(dialogs: DialogInfo[]): void {
    this.cache = { at: this.now(), dialogs };
  }
}

type ToolContent = { type: string; text?: string };
type ToolResult = { content?: ToolContent[] } & Record<string, unknown>;

/**
 * Wrap server.tool so that EVERY tool result gets the dialog warning prepended.
 * Call before registering tools. Tools named in `exempt` are left alone.
 */
export function withDialogWatch(server: McpServer, watcher: DialogWatcher, exempt: string[] = ["list_dialogs"]): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const original = (server.tool as any).bind(server) as (...a: unknown[]) => unknown;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (server as any).tool = (...args: unknown[]) => {
    const name = args[0] as string;
    const handler = args[args.length - 1];
    if (typeof handler !== "function" || exempt.includes(name)) return original(...args);
    const wrapped = async (...hargs: unknown[]) => {
      const result = (await (handler as (...a: unknown[]) => Promise<ToolResult>)(...hargs)) as ToolResult;
      const warning = await watcher.getWarning();
      if (!warning || !result || !Array.isArray(result.content)) return result;
      return { ...result, content: [{ type: "text", text: warning }, ...result.content] };
    };
    return original(...args.slice(0, -1), wrapped);
  };
}
