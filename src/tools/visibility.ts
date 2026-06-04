/**
 * Visibility and scene object tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerVisibilityTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "set_item_visible",
    "Show or hide a scene item (clothing, hair, accessory, prop, light) by name. Use list_clothes, list_hair, list_accessories, or get_scene_objects to find item names.",
    {
      item_name: z.string().max(256).describe("Name of the item to show/hide"),
      visible: z.boolean().describe("true to show, false to hide"),
    },
    async ({ item_name, visible }) => bridgeCall(
      () => bridge.setItemVisible(item_name, visible),
      (result) => result.success
        ? `Item '${result.item ?? item_name}' is now ${result.visible ? "visible" : "hidden"}`
        : `Failed: ${result.error}`,
    )
  );

  server.tool(
    "get_scene_objects",
    "List all objects in the CC5 scene: avatars, props, lights, and cameras. Useful for getting an overview of the scene.",
    {},
    async () => bridgeCall(
      () => bridge.getSceneObjects(),
      (objects) => {
        if (objects.length === 0) {
          return "Scene is empty.";
        }
        const grouped: Record<string, string[]> = {};
        for (const obj of objects) {
          const category = grouped[obj.type] ?? [];
          category.push(`${obj.name} (ID: ${obj.id})`);
          grouped[obj.type] = category;
        }
        const lines: string[] = [`Found ${objects.length} object(s) in scene:`];
        for (const [type, items] of Object.entries(grouped)) {
          lines.push(`\n${type}s (${items.length}):`);
          for (const item of items) {
            lines.push(`  - ${item}`);
          }
        }
        return lines.join("\n");
      },
    )
  );
}
