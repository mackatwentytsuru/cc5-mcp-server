/**
 * Morph catalog resource.
 * Exposes the full list of available morph sliders as an MCP resource,
 * so the LLM knows exactly which morphs can be adjusted.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";

export function registerMorphResources(server: McpServer, bridge: CC5Bridge) {
  // Static resource: full morph catalog
  server.resource(
    "morph-catalog",
    "cc5://morphs/catalog",
    {
      description:
        "Complete catalog of all available morph sliders in CC5, grouped by category. " +
        "Read this resource first to understand which morph IDs you can use with adjust_morph and adjust_multiple_morphs tools.",
      mimeType: "application/json",
    },
    async (uri) => {
      try {
        const catalog = await bridge.getMorphCatalog();
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify(catalog, null, 2),
            },
          ],
        };
      } catch {
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify({
                error: "CC5 bridge not available. Make sure CC5 is running with the MCP Bridge plugin.",
                hint: "Use check_cc5_connection tool to verify connectivity.",
              }),
            },
          ],
        };
      }
    }
  );

  // Static resource: current avatar state
  server.resource(
    "avatar-state",
    "cc5://avatar/current",
    {
      description:
        "Current state of the active avatar, including all non-zero morph values. " +
        "Read this to understand the character's current appearance before making changes.",
      mimeType: "application/json",
    },
    async (uri) => {
      try {
        const info = await bridge.getAvatarInfo();
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify(info, null, 2),
            },
          ],
        };
      } catch {
        return {
          contents: [
            {
              uri: uri.href,
              mimeType: "application/json",
              text: JSON.stringify({ error: "CC5 bridge not available" }),
            },
          ],
        };
      }
    }
  );
}
