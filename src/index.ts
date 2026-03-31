#!/usr/bin/env node

/**
 * CC5 MCP Server - Entry Point
 *
 * MCP Server for Reallusion Character Creator 5.
 * Enables AI-powered character creation via natural language.
 *
 * Architecture:
 *   LLM <-> MCP Server (this) <-> HTTP <-> CC5 Plugin (Flask) <-> RLPy API <-> CC5
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CC5Bridge } from "./cc5-bridge.js";
import { registerMorphTools } from "./tools/morph.js";
import { registerSceneTools } from "./tools/scene.js";
import { registerAssetTools } from "./tools/asset.js";
import { registerCharacterTools } from "./tools/character.js";
import { registerMorphResources } from "./resources/morphs.js";

async function main() {
  const server = new McpServer({
    name: "cc5-mcp-server",
    version: "1.0.0",
  });

  // Bridge to CC5's Python plugin HTTP server
  const bridge = new CC5Bridge(process.env.CC5_BRIDGE_URL);

  // Register all tools
  registerMorphTools(server, bridge);
  registerSceneTools(server, bridge);
  registerAssetTools(server, bridge);
  registerCharacterTools(server, bridge);

  // Register resources
  registerMorphResources(server, bridge);

  // Connect via stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("[CC5 MCP] Server started on stdio transport");
}

main().catch((error) => {
  console.error("[CC5 MCP] Fatal error:", error);
  process.exit(1);
});
