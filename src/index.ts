#!/usr/bin/env node

/**
 * CC5 MCP Server - Entry Point
 *
 * MCP Server for Reallusion Character Creator 5.
 * Enables AI-powered character creation via natural language.
 *
 * Architecture:
 *   LLM <-> MCP Server (this) <-> HTTP <-> CC5 Plugin (http.server) <-> RLPy API <-> CC5
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CC5Bridge } from "./cc5-bridge.js";
import { registerMorphTools } from "./tools/morph.js";
import { registerSceneTools } from "./tools/scene.js";
import { registerAssetTools } from "./tools/asset.js";
import { registerCharacterTools } from "./tools/character.js";
import { registerEditTools } from "./tools/edit.js";
import { registerCameraTools } from "./tools/camera.js";
import { registerLightTools } from "./tools/light.js";
import { registerExpressionTools } from "./tools/expression.js";
import { registerMaterialTools } from "./tools/material.js";
import { registerContentTools } from "./tools/content.js";
import { registerColorTools } from "./tools/color.js";
import { registerVisibilityTools } from "./tools/visibility.js";
import { registerScriptingTools } from "./tools/scripting.js";
import { registerMetaHumanTools } from "./tools/metahuman.js";
import { registerActorMixerTools } from "./tools/actor-mixer.js";
import { registerMorphResources } from "./resources/morphs.js";

async function main() {
  const server = new McpServer({
    name: "cc5-mcp-server",
    version: "1.1.0",
  });

  // Bridge to CC5's Python plugin HTTP server
  const bridge = new CC5Bridge(process.env.CC5_BRIDGE_URL);

  // Register all tools
  registerMorphTools(server, bridge);
  registerSceneTools(server, bridge);
  registerAssetTools(server, bridge);
  registerCharacterTools(server, bridge);
  registerEditTools(server, bridge);
  registerCameraTools(server, bridge);
  registerLightTools(server, bridge);
  registerExpressionTools(server, bridge);
  registerMaterialTools(server, bridge);
  registerContentTools(server, bridge);
  registerColorTools(server, bridge);
  registerVisibilityTools(server, bridge);
  registerScriptingTools(server, bridge);
  registerMetaHumanTools(server, bridge);
  registerActorMixerTools(server, bridge);

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
