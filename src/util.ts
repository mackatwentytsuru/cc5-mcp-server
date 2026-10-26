/**
 * Shared utilities for MCP tool callbacks.
 */

const TRUTHY_FLAG_VALUES = new Set(["1", "true", "yes"]);

/**
 * True when the environment variable is set to 1 / true / yes (any case).
 * Read on every call so the result always reflects the current environment.
 */
export function isEnvFlagEnabled(name: string, env: NodeJS.ProcessEnv = process.env): boolean {
  const raw = env[name];
  return raw !== undefined && TRUTHY_FLAG_VALUES.has(raw.trim().toLowerCase());
}

/**
 * Wraps a bridge call with try/catch, returning a structured MCP content response.
 * Prevents unhandled errors from propagating to the MCP SDK.
 * Logs the full error (including stack) to stderr so MCP stdio is not corrupted.
 */
export async function bridgeCall<T>(
  fn: () => Promise<T>,
  formatSuccess: (result: T) => string,
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  try {
    const result = await fn();
    return { content: [{ type: "text" as const, text: formatSuccess(result) }] };
  } catch (err: unknown) {
    console.error("[CC5 Bridge] bridgeCall caught error:", err);
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [{
        type: "text" as const,
        text: `CC5 bridge error: ${message}. Is CC5 running with the MCP Bridge plugin?`,
      }],
    };
  }
}

/** One block of a tool result: text or an inline image (base64). */
export type ToolContent =
  | { type: "text"; text: string }
  | { type: "image"; data: string; mimeType: string };

export function textContent(text: string): ToolContent {
  return { type: "text" as const, text };
}

export function pngContent(base64: string): ToolContent {
  return { type: "image" as const, data: base64, mimeType: "image/png" };
}

/**
 * Like bridgeCall, but the formatter returns several content blocks (text and images), and may
 * itself call the bridge again (for example to fetch a screenshot of an open window).
 */
export async function bridgeCallRich<T>(
  fn: () => Promise<T>,
  format: (result: T) => ToolContent[] | Promise<ToolContent[]>,
): Promise<{ content: ToolContent[] }> {
  try {
    const result = await fn();
    return { content: await format(result) };
  } catch (err: unknown) {
    console.error("[CC5 Bridge] bridgeCallRich caught error:", err);
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [textContent(`CC5 bridge error: ${message}. Is CC5 running with the MCP Bridge plugin?`)],
    };
  }
}
