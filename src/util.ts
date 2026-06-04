/**
 * Shared utilities for MCP tool callbacks.
 */

/**
 * Wraps a bridge call with try/catch, returning a structured MCP content response.
 * Prevents unhandled errors from propagating to the MCP SDK.
 */
export async function bridgeCall<T>(
  fn: () => Promise<T>,
  formatSuccess: (result: T) => string,
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  try {
    const result = await fn();
    return { content: [{ type: "text" as const, text: formatSuccess(result) }] };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [{
        type: "text" as const,
        text: `CC5 bridge error: ${message}. Is CC5 running with the MCP Bridge plugin?`,
      }],
    };
  }
}
