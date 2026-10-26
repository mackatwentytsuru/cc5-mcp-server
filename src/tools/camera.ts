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

  server.tool(
    "frame_camera",
    "Move the viewport camera to a preset view. Use 'face' to frame the head close-up (so eye/lip/skin color and facial morphs are actually visible in capture_viewport — a full-body shot is too small), 'home'/'all' to reset to the whole character, or front/back/left/right/top/bottom/focus.",
    {
      view: z.enum(["face", "front", "back", "left", "right", "top", "bottom", "home", "all", "focus"])
        .default("face").describe("Preset view. 'face' = head close-up, 'home'/'all' = whole body."),
    },
    async ({ view }) => bridgeCall(
      () => bridge.frameCamera(view),
      (result) => result.success
        ? `Camera framed to '${result.view ?? view}' view.`
        : `Failed: ${result.error}`,
    )
  );

  const xyz = (p?: number[]) => (p ? `(${p.map((v) => v.toFixed(1)).join(", ")})` : "(unknown)");

  server.tool(
    "list_cameras",
    "List every camera in CC5 with its position (cm), focal length, vertical angle of view and whether scripts can move it. The viewport's Preview Camera is read-only to scripts (its focal length cannot be set either); move it with frame_camera presets and dolly_camera.",
    {},
    async () => bridgeCall(
      () => bridge.listCameras(),
      (result) => {
        if (!result.success) return `Failed: ${result.error}`;
        return (result.cameras ?? []).map((c) =>
          `${c.name}${c.current ? " (current)" : ""}: position ${xyz(c.position)}, ` +
          `focal ${c.focal_length ?? "?"}mm, angle of view ${c.angle_of_view ?? "?"} deg, ` +
          `${c.transform_writable ? "movable by scripts" : "read-only to scripts"}`,
        ).join("\n") || "No cameras.";
      },
    )
  );

  server.tool(
    "dolly_camera",
    "Move the viewport camera straight toward or away from the subject, exactly as the mouse wheel does, without moving the user's mouse. One notch = one wheel click (15 cm at the 'face' view at first, but the step size can change during a session: it became 42 cm once, so do NOT compare options shot with different dolly counts; use capture_framed_crop for equal framing). Positive backs away (less perspective; crop a larger capture to keep the framing), negative comes closer. Call frame_camera first to start from a known view.",
    {
      notches: z.number().int().min(-200).max(200).refine((n) => n !== 0, "notches must not be 0")
        .describe("Wheel clicks: positive = back away, negative = come closer"),
    },
    async ({ notches }) => bridgeCall(
      () => bridge.dollyCamera(notches),
      (result) => result.success
        ? `Camera moved ${(result.moved_cm ?? 0).toFixed(1)} cm (${notches} notches): ${xyz(result.before)} -> ${xyz(result.after)}`
        : `Failed: ${result.error}`,
    )
  );
}
