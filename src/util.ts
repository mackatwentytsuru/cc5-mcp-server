/**
 * Shared utilities for MCP tool callbacks.
 */

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
