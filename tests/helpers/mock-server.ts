/**
 * Shared mock MCP server for tool registration tests.
 */

import { vi } from "vitest";

export type ToolHandler = (args: Record<string, unknown>) => Promise<{ content: Array<{ type: string; text: string }> }>;

export interface CapturedTool {
  name: string;
  handler: ToolHandler;
}

export function createMockServer() {
  const registered: CapturedTool[] = [];
  const toolSpy = vi.fn((...args: unknown[]) => {
    const name = args[0] as string;
    const handler = args[args.length - 1] as ToolHandler;
    registered.push({ name, handler });
  });
  return {
    tool: toolSpy,
    getRegisteredTool: (name: string): ToolHandler => {
      const entry = registered.find((r) => r.name === name);
      if (!entry) throw new Error(`Tool '${name}' was not registered`);
      return entry.handler;
    },
  };
}
