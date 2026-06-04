/**
 * Camera control tools for CC5.
 */

import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CC5Bridge } from "../cc5-bridge.js";
import { bridgeCall } from "../util.js";

export function registerCameraTools(server: McpServer, bridge: CC5Bridge) {
  server.tool(
    "get_camera_info",
    "Get the current camera's position and focal length in CC5.",
    {},
    async () => bridgeCall(
      () => bridge.getCameraInfo(),
      (info) => {
        if (info.error) return `Camera error: ${info.error}`;
        const pos = info.position;
        return `Camera: ${info.name}\nPosition: (${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)})\nFocal length: ${info.focal_length}mm`;
      },
    )
  );

  server.tool(
    "set_camera_focal_length",
    "Set the focal length of the current camera in CC5. Common values: 35mm (wide), 50mm (normal), 85mm (portrait), 135mm (telephoto).",
    {
      focal_length: z.number().positive().describe("Focal length in mm (e.g., 50, 85, 135)"),
    },
    async ({ focal_length }) => bridgeCall(
      () => bridge.setCameraFocalLength(focal_length),
      (result) => result.success
        ? `Camera focal length set to ${result.focal_length ?? focal_length}mm`
        : `Failed: ${result.error}`,
    )
  );
}
