"""
HTTP bridge server for CC5 MCP plugin.

Uses Python's built-in http.server — no external dependencies needed.
All RLPy calls are queued and executed on the main thread via QTimer.
"""

from __future__ import annotations

import hmac
import importlib
import json
import os
import queue
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

import cc5_api

RELOAD_SECRET = os.environ.get("CC5_RELOAD_SECRET", "")
API_VERSION = "1.2.0"


def _env_flag(name: str) -> bool:
    """True when the environment variable is set to 1 / true / yes (any case)."""
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


# Development mode: enables /reload without a secret and the full /api listing.
# Off by default. It does NOT enable code execution -- that is CC5_ALLOW_EXEC.
DEV_MODE = _env_flag("CC5_DEV_MODE")

# Actions that run arbitrary code inside CC5, or drive CC5's UI (dialogs and
# keystrokes) without the user confirming anything. They are refused unless
# CC5_ALLOW_EXEC=1 is set in the environment CC5 was started from. This is the
# ONLY switch: any local program can reach the bridge, so the MCP server keeps no
# on/off of its own; it forwards the call and shows this answer (and reads the
# state from GET /health -> exec_allowed). The check is by action name, so a
# route re-added by cc5_api._auto_patch_server() after a hot reload cannot
# bypass it.
EXEC_GATED_ACTIONS: frozenset[str] = frozenset({
    "exec_python",
    "silent_install_filter",
    "silent_trigger_dialog",
    "silent_configure_and_click",
    "silent_finalize",
})

# Host names a legitimate local client puts in the Host header. A page that uses
# DNS rebinding to reach 127.0.0.1 still sends its own host name, so it fails here.
_LOOPBACK_HOSTNAMES = ("127.0.0.1", "localhost", "[::1]")


def exec_allowed() -> bool:
    """Whether CC5_ALLOW_EXEC is on. Read per request, never cached."""
    return _env_flag("CC5_ALLOW_EXEC")


def exec_disabled_error(action: str) -> str:
    """The refusal text. cc5_api._exec_gate returns the same words (a test keeps them equal)."""
    return (
        f"'{action}' is disabled. It can run arbitrary code or drive CC5's UI without "
        "confirmation, so it is off by default. Whether it runs is decided ONLY by "
        "CC5_ALLOW_EXEC in the environment Character Creator 5 was started from; the "
        "MCP server has no switch of its own. To turn it on: set CC5_ALLOW_EXEC=1 for the "
        "Windows user (run 'setx CC5_ALLOW_EXEC 1'), then quit CC5 and start it again "
        "(from the Start menu or a new terminal). To turn "
        "it off: run 'setx CC5_ALLOW_EXEC 0' (or delete the variable), then restart CC5. "
        "That is the owner's decision: do not try to get around this refusal (for example "
        "by calling the HTTP bridge or another route directly); ask the owner. See the "
        "Security section of the README."
    )


def check_request_headers(headers: Any, port: int) -> str | None:
    """Return why a request must be refused, or None when it may proceed.

    - Host must be a loopback name plus this server's port (blocks DNS rebinding).
    - An Origin header means a web page sent the request: refuse it.
    - Sec-Fetch-Site other than "none" means a page triggered the request. This
      also covers GETs that browsers send without Origin (e.g. <img src=...>).

    curl, Python urllib, PowerShell and Node fetch all send a loopback Host and
    neither Origin nor Sec-Fetch-Site, so normal clients are unaffected.
    """
    host = (headers.get("Host") or "").strip().lower()
    if host not in {f"{name}:{port}" for name in _LOOPBACK_HOSTNAMES}:
        return (
            f"Host header {host[:100]!r} is not allowed. "
            f"Use http://127.0.0.1:{port} or http://localhost:{port}."
        )
    if headers.get("Origin") is not None:
        return "Requests from web pages (with an Origin header) are not accepted."
    fetch_site = headers.get("Sec-Fetch-Site")
    if fetch_site is not None and fetch_site.strip().lower() != "none":
        return "Requests triggered by a web page (Sec-Fetch-Site) are not accepted."
    return None


# Thread-safe command queue: HTTP thread -> main thread
command_queue: queue.Queue = queue.Queue(maxsize=100)
_store_lock = threading.Lock()
response_store: dict[str, Any] = {}
response_events: dict[str, threading.Event] = {}

_command_counter = 0
_counter_lock = threading.Lock()
_processing = False  # Re-entrance guard for process_command_queue

# Main-thread heartbeat. Updated by process_command_queue (16 ms QTimer).
# The HTTP server runs on its own thread, so /health answers even when CC5's main
# thread is frozen by a modal dialog. Comparing now() against this timestamp is the
# only reliable way to tell "bridge alive" from "CC5 actually able to run RLPy".
_last_main_thread_tick: float = 0.0
# Above this age the main thread is considered blocked (QTimer interval is 16 ms).
MAIN_THREAD_STALL_SEC = 2.0

MAX_REQUEST_BYTES = 1 * 1024 * 1024  # 1 MB

# Module-level reference for shutdown
_httpd: HTTPServer | None = None


def _next_command_id() -> str:
    global _command_counter
    with _counter_lock:
        _command_counter += 1
        return f"cmd_{_command_counter}"


# --- Required parameters per action (validated before queue dispatch) ---

REQUIRED_PARAMS: dict[str, list[str]] = {
    "search_morphs":        ["query"],
    "get_morph_value":      ["morph_id"],
    "set_morph_value":      ["morph_id", "value"],
    "set_multiple_morphs":  ["morphs"],
    "load_asset":           ["file_path"],
    "export_fbx":           ["output_path"],
    "set_subdivision_level": ["level"],
    "set_camera_focal_length": ["focal_length"],
    "camera_dolly":         ["notches"],
    "set_light_color":      ["light_name", "r", "g", "b"],
    "get_light_info":       ["light_name"],
    "set_light_multiplier": ["light_name", "multiplier"],
    "set_light_active":     ["light_name", "active"],
    "set_light_shadow":     ["light_name"],
    "set_ambient":          ["r", "g", "b"],
    "set_expression":       ["expressions"],
    "get_diffuse_color":    ["mesh_name", "material_name"],
    "set_diffuse_color":    ["mesh_name", "material_name", "r", "g", "b"],
    "get_material_properties": ["mesh_name", "material_name"],
    "set_material_opacity":    ["mesh_name", "material_name", "opacity"],
    "set_material_glossiness": ["mesh_name", "material_name", "glossiness"],
    "set_material_specular":   ["mesh_name", "material_name", "specular"],
    "get_shader_parameters":   ["mesh_name", "material_name"],
    "set_shader_parameter":    ["mesh_name", "material_name", "parameter_name", "values"],
    # Tier 1: Content Management
    "remove_scene_item":    ["item_name"],
    # Tier 3: Convenience Color Shortcuts
    "set_eye_color":        ["r", "g", "b"],
    "set_hair_color":       ["r", "g", "b"],
    "set_lip_color":        ["r", "g", "b"],
    "set_skin_color":       ["r", "g", "b"],
    # Tier 4: Visibility
    "set_item_visible":     ["item_name", "visible"],
    "exec_python":          ["code"],
    # Mesh-to-MetaHuman pipeline helpers
    "export_head_metahuman":   ["output_dir", "character_name"],
    "silent_install_filter":   ["output_dir", "character_name"],
    # ActorMIXER PRO: Create Mixer Assets (safety gate)
    "create_actor_mixer":      ["confirm_create"],
}

# --- Dynamic dispatch tables (can be hot-patched at runtime) ---

ACTION_MAP: dict[str, Any] = {
    "get_avatars":           lambda p: cc5_api.get_avatars(),
    "get_avatar_info":       lambda p: cc5_api.get_avatar_info(),
    "get_morph_catalog":     lambda p: cc5_api.get_morph_catalog(),
    "search_morphs":         lambda p: cc5_api.search_morphs(p["query"], p.get("category", "")),
    "get_morph_value":       lambda p: cc5_api.get_morph_value(p["morph_id"]),
    "set_morph_value":       lambda p: cc5_api.set_morph_value(p["morph_id"], float(p["value"])),
    "set_multiple_morphs":   lambda p: cc5_api.set_multiple_morphs(p["morphs"]),
    "create_default_avatar": lambda p: cc5_api.create_default_avatar(),
    "delete_avatar":         lambda p: cc5_api.delete_avatar(p.get("name", "")),
    "load_asset":            lambda p: cc5_api.load_asset(p["file_path"]),
    "export_fbx":            lambda p: cc5_api.export_fbx(
        p["output_path"],
        int(p.get("options", 0)),
        target_tool=p.get("target_tool", ""),
        sub_d_level=(int(p["sub_d_level"]) if p.get("sub_d_level") is not None else None),
        include_current_pose=bool(p.get("include_current_pose", False)),
        delete_hidden_faces=bool(p.get("delete_hidden_faces", False)),
        use_smooth_mesh=bool(p.get("use_smooth_mesh", False)),
        remove_eyelash=bool(p.get("remove_eyelash", False)),
        remove_tearline_occlusion=bool(p.get("remove_tearline_occlusion", False)),
        embed_textures=bool(p.get("embed_textures", False)),
        export_motion=bool(p.get("export_motion", True)),
        fps=(int(p["fps"]) if p.get("fps") is not None else None),
        motion_range=p.get("motion_range"),
        convert_image_format=bool(p.get("convert_image_format", False)),
        texture_size=(int(p["texture_size"]) if p.get("texture_size") is not None else None),
    ),
    "capture_viewport":      lambda p: cc5_api.capture_viewport(p.get("output_path", ""), int(p.get("width", 1280)), int(p.get("height", 720))),
    "set_subdivision_level": lambda p: cc5_api.set_subdivision_level(int(p["level"])),
    "undo":                  lambda p: cc5_api.undo(),
    "redo":                  lambda p: cc5_api.redo(),
    "get_camera_info":       lambda p: cc5_api.get_camera_info(),
    "set_camera_focal_length": lambda p: cc5_api.set_camera_focal_length(float(p["focal_length"])),
    "frame_camera":          lambda p: cc5_api.frame_camera(p.get("view", "face")),
    "list_cameras":          lambda p: cc5_api.list_cameras(),
    "qt_viewport_probe":     lambda p: cc5_api.qt_viewport_probe(),
    "selected_objects":      lambda p: cc5_api.selected_objects(),
    "select_avatar":         lambda p: cc5_api.select_avatar(p.get("name", "")),
    "camera_dolly":          lambda p: cc5_api.camera_dolly(p["notches"], p.get("method", "win32")),
    "list_avatar_parts":     lambda p: cc5_api.list_avatar_parts(),
    "remove_avatar_part":    lambda p: cc5_api.remove_avatar_part(p.get("name", ""), p.get("type", "")),
    "get_lights":            lambda p: cc5_api.get_lights(),
    "set_light_color":       lambda p: cc5_api.set_light_color(p["light_name"], float(p["r"]), float(p["g"]), float(p["b"])),
    "get_light_info":        lambda p: cc5_api.get_light_info(p["light_name"]),
    "set_light_multiplier":  lambda p: cc5_api.set_light_multiplier(p["light_name"], float(p["multiplier"])),
    "set_light_active":      lambda p: cc5_api.set_light_active(p["light_name"], bool(p["active"])),
    "set_light_shadow":      lambda p: cc5_api.set_light_shadow(
        p["light_name"],
        (bool(p["cast_shadow"]) if p.get("cast_shadow") is not None else None),
        (float(p["darken_strength"]) if p.get("darken_strength") is not None else None),
    ),
    "get_visual_settings":   lambda p: cc5_api.get_visual_settings(),
    "set_ambient":           lambda p: cc5_api.set_ambient(float(p["r"]), float(p["g"]), float(p["b"])),
    "set_ibl":               lambda p: cc5_api.set_ibl(p.get("image_path", ""), bool(p.get("enable", True))),
    "get_expression_info":   lambda p: cc5_api.get_expression_info(),
    "get_facial_profile":    lambda p: cc5_api.get_facial_profile(),
    "convert_facial_profile": lambda p: cc5_api.convert_facial_profile(
        p.get("target_profile_path", ""),
        bool(p.get("dry_run", True)),
        p.get("backup_current_to", ""),
    ),
    "set_expression":        lambda p: cc5_api.set_expression(p["expressions"]),
    "reset_expression":      lambda p: cc5_api.reset_expression(),
    "reset_all_morphs":      lambda p: cc5_api.reset_all_morphs(p.get("avatar_name", "")),
    "get_material_info":     lambda p: cc5_api.get_material_info(p.get("avatar_name", "")),
    "get_diffuse_color":     lambda p: cc5_api.get_diffuse_color(p["mesh_name"], p["material_name"]),
    "set_diffuse_color":     lambda p: cc5_api.set_diffuse_color(p["mesh_name"], p["material_name"], float(p["r"]), float(p["g"]), float(p["b"])),
    "get_material_properties": lambda p: cc5_api.get_material_properties(p["mesh_name"], p["material_name"]),
    "set_material_opacity":  lambda p: cc5_api.set_material_opacity(p["mesh_name"], p["material_name"], float(p["opacity"])),
    "set_material_glossiness": lambda p: cc5_api.set_material_glossiness(p["mesh_name"], p["material_name"], float(p["glossiness"])),
    "set_material_specular": lambda p: cc5_api.set_material_specular(p["mesh_name"], p["material_name"], float(p["specular"])),
    "get_shader_parameters": lambda p: cc5_api.get_shader_parameters(p["mesh_name"], p["material_name"]),
    "set_shader_parameter": lambda p: cc5_api.set_shader_parameter(p["mesh_name"], p["material_name"], p["parameter_name"], list(p["values"])),
    # Tier 1: Content Management
    "list_clothes":          lambda p: cc5_api.list_clothes(),
    "list_hair":             lambda p: cc5_api.list_hair(),
    "list_accessories":      lambda p: cc5_api.list_accessories(),
    "remove_scene_item":     lambda p: cc5_api.remove_scene_item(p["item_name"]),
    "browse_content":        lambda p: cc5_api.browse_content(p.get("folder_type", "cloth_upper")),
    # Tier 3: Convenience Color Shortcuts
    "set_eye_color":         lambda p: cc5_api.set_eye_color(float(p["r"]), float(p["g"]), float(p["b"])),
    "set_hair_color":        lambda p: cc5_api.set_hair_color(float(p["r"]), float(p["g"]), float(p["b"])),
    "set_lip_color":         lambda p: cc5_api.set_lip_color(float(p["r"]), float(p["g"]), float(p["b"])),
    "set_skin_color":        lambda p: cc5_api.set_skin_color(float(p["r"]), float(p["g"]), float(p["b"])),
    # Tier 4: Visibility & Scene
    "set_item_visible":      lambda p: cc5_api.set_item_visible(p["item_name"], bool(p["visible"])),
    "get_scene_objects":     lambda p: cc5_api.get_scene_objects(),
    "exec_python":           lambda p: cc5_api.exec_python(p["code"]),
    # Mesh-to-MetaHuman pipeline helpers
    "bake_skin_textures":    lambda p: cc5_api.bake_skin_textures(int(p.get("resolution", 4096))),
    "export_head_metahuman": lambda p: cc5_api.export_head_metahuman(
        p["output_dir"], p["character_name"], p.get("gender", "Female"),
    ),
    "silent_install_filter": lambda p: cc5_api.silent_install_filter(
        p["output_dir"], p["character_name"],
    ),
    "silent_trigger_dialog": lambda p: cc5_api.silent_trigger_dialog(),
    "silent_configure_and_click": lambda p: cc5_api.silent_configure_and_click(
        p.get("gender", "Female"), int(p.get("max_texture_size", 4096)),
    ),
    "silent_finalize": lambda p: cc5_api.silent_finalize(),
    "get_export_status": lambda p: cc5_api.get_export_status(),
    # ActorMIXER PRO: Create Mixer Assets
    "create_actor_mixer": lambda p: cc5_api.create_actor_mixer(p),
    "get_mixer_status":   lambda p: cc5_api.get_mixer_status(),
}

# POST path -> action name
POST_ROUTES: dict[str, str] = {
    "/morphs/search":    "search_morphs",
    "/morph/get":        "get_morph_value",
    "/morph/set":        "set_morph_value",
    "/morphs/set":       "set_multiple_morphs",
    "/morphs/reset":     "reset_all_morphs",
    "/avatar/create":    "create_default_avatar",
    "/avatar/delete":    "delete_avatar",
    "/asset/load":       "load_asset",
    "/export/fbx":       "export_fbx",
    "/viewport/capture": "capture_viewport",
    "/subdivision":      "set_subdivision_level",
    "/undo":             "undo",
    "/redo":             "redo",
    "/camera/focal":     "set_camera_focal_length",
    "/camera/frame":     "frame_camera",
    "/camera/dolly":     "camera_dolly",
    "/scene/select_avatar": "select_avatar",
    "/avatar/part/remove": "remove_avatar_part",
    "/light/color":      "set_light_color",
    "/light/info":       "get_light_info",
    "/light/multiplier": "set_light_multiplier",
    "/light/active":     "set_light_active",
    "/light/shadow":     "set_light_shadow",
    "/visual/ambient":   "set_ambient",
    "/visual/ibl":       "set_ibl",
    "/expression/set":   "set_expression",
    "/expression/reset": "reset_expression",
    "/facial/profile/convert": "convert_facial_profile",
    "/material/info":    "get_material_info",
    "/material/color/get": "get_diffuse_color",
    "/material/color/set": "set_diffuse_color",
    "/material/properties": "get_material_properties",
    "/material/opacity":    "set_material_opacity",
    "/material/glossiness": "set_material_glossiness",
    "/material/specular":   "set_material_specular",
    "/material/shader/get": "get_shader_parameters",
    "/material/shader/set": "set_shader_parameter",
    # Tier 1: Content Management
    "/item/remove":      "remove_scene_item",
    "/content/browse":   "browse_content",
    # Tier 3: Convenience Color Shortcuts
    "/color/eye":        "set_eye_color",
    "/color/hair":       "set_hair_color",
    "/color/lip":        "set_lip_color",
    "/color/skin":       "set_skin_color",
    # Tier 4: Visibility
    "/item/visible":     "set_item_visible",
    "/exec/python":      "exec_python",
    # Mesh-to-MetaHuman pipeline helpers
    "/skin/bake":        "bake_skin_textures",
    "/export/head_mh":   "export_head_metahuman",
    "/export/head_mh/silent/install_filter":  "silent_install_filter",
    "/export/head_mh/silent/trigger_dialog":  "silent_trigger_dialog",
    "/export/head_mh/silent/configure_click": "silent_configure_and_click",
    "/export/head_mh/silent/finalize":        "silent_finalize",
    # ActorMIXER PRO: Create Mixer Assets
    "/actor_mixer/create":                    "create_actor_mixer",
}

# GET path -> action name (None = handle inline)
GET_ROUTES: dict[str, str | None] = {
    "/health":         None,
    "/reload":         None,
    "/api":            None,
    "/avatars":        "get_avatars",
    "/avatar/info":    "get_avatar_info",
    "/morphs/catalog": "get_morph_catalog",
    "/camera/info":    "get_camera_info",
    "/camera/list":    "list_cameras",
    "/avatar/parts":   "list_avatar_parts",
    "/debug/qt":       "qt_viewport_probe",
    "/scene/selected": "selected_objects",
    "/lights":         "get_lights",
    "/visual/settings": "get_visual_settings",
    "/expressions":    "get_expression_info",
    "/facial/profile": "get_facial_profile",
    "/material/info":  "get_material_info",
    # Tier 1: Content Management
    "/clothes":        "list_clothes",
    "/hair":           "list_hair",
    "/accessories":    "list_accessories",
    # Tier 4: Scene
    "/scene/objects":  "get_scene_objects",
    # Silent export polling
    "/export/head_mh/status": "get_export_status",
    # ActorMIXER PRO: Create Mixer Assets polling
    "/actor_mixer/status": "get_mixer_status",
}


def _health_payload() -> dict:
    """Health info including main-thread liveness.

    `main_thread_blocked` is the field that matters: the HTTP thread answers even
    when CC5 is frozen behind a modal dialog, so "connected" alone is not enough.
    """
    now = time.time()
    age = (now - _last_main_thread_tick) if _last_main_thread_tick else None
    blocked = (age is None) or (age > MAIN_THREAD_STALL_SEC)
    payload = {
        "status": "ok",
        "service": "cc5-mcp-bridge",
        "version": API_VERSION,
        "main_thread_blocked": blocked,
        "ms_since_main_thread_tick": None if age is None else int(age * 1000),
        "queue_depth": command_queue.qsize(),
        # The one switch for exec_python and the silent Export Head routes (CC5's own
        # environment). The MCP server reads it from here instead of its own env.
        "exec_allowed": exec_allowed(),
    }
    if blocked:
        payload["hint"] = (
            "CC5's main thread is not draining the command queue. A modal dialog is the "
            "usual cause -- check the CC5 window and dismiss it. Commands sent now will "
            "not execute until the main thread resumes."
        )
    return payload


def process_command_queue() -> None:
    """Drain the queue and execute RLPy calls on the main thread. Called by QTimer."""
    global _processing, _last_main_thread_tick
    # Heartbeat: proves the CC5 main thread is still running this QTimer callback.
    # A modal dialog blocks the main thread, so this stops updating while the HTTP
    # thread keeps answering /health -- that combination is how callers detect a stall.
    _last_main_thread_tick = time.time()
    if _processing:
        return
    _processing = True
    try:
        while not command_queue.empty():
            try:
                cmd = command_queue.get_nowait()
            except queue.Empty:
                break

            cmd_id = cmd["id"]
            action = cmd["action"]
            params = cmd["params"]

            try:
                handler = ACTION_MAP.get(action)
                result = handler(params) if handler else {"success": False, "error": f"Unknown action: {action}"}
            except Exception as e:
                print(f"[CC5 MCP Bridge] Action '{action}' failed: {traceback.format_exc()}")
                result = {"success": False, "error": str(e)}

            # Tell direct HTTP callers about open dialogs too (the MCP tools add their own
            # notice; plain curl callers missed a Yes/No question on 10-22).
            if isinstance(result, dict):
                try:
                    dialogs = cc5_api.open_dialog_summary()
                    if dialogs:
                        # First key of the reply, so a curl caller cannot miss it (10-24).
                        first = dialogs[0]
                        warn = "DIALOG OPEN - do not send the next call: %s: %s" % (
                            first.get("title", ""), str(first.get("text", ""))[:160])
                        result = {"DIALOG_OPEN": warn, **result, "open_dialogs": dialogs}
                except Exception:
                    pass

            with _store_lock:
                event = response_events.pop(cmd_id, None)
                if event:
                    response_store[cmd_id] = result
                    event.set()

            command_queue.task_done()
    finally:
        _processing = False


def _validate_params(action: str, params: dict) -> str | None:
    """Validate required parameters. Returns error message or None."""
    required = REQUIRED_PARAMS.get(action)
    if not required:
        return None
    missing = [f for f in required if f not in params]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    return None


def _execute_sync(action: str, params: dict, timeout: float = 30.0) -> tuple[int, Any]:
    """Queue a command, wait for main-thread execution, return (http_status, result)."""
    # Opt-in gate. Checked here, on the single path every GET and POST action
    # takes, so no route table entry (even one hot-patched later) can skip it.
    if action in EXEC_GATED_ACTIONS and not exec_allowed():
        return 403, {"error": exec_disabled_error(action)}

    # Validate required params before queueing (returns 400, not 500)
    error = _validate_params(action, params)
    if error:
        return 400, {"error": error}

    cmd_id = _next_command_id()
    event = threading.Event()

    with _store_lock:
        response_events[cmd_id] = event

    try:
        command_queue.put_nowait({"id": cmd_id, "action": action, "params": params})
    except queue.Full:
        with _store_lock:
            response_events.pop(cmd_id, None)
        return 503, {"error": "server busy, command queue full"}

    if not event.wait(timeout=timeout):
        with _store_lock:
            response_events.pop(cmd_id, None)
            response_store.pop(cmd_id, None)
        return 504, {"error": "Timeout waiting for CC5 to process command"}

    with _store_lock:
        result = response_store.pop(cmd_id, None)
        response_events.pop(cmd_id, None)

    if isinstance(result, dict) and result.get("success") is False:
        return 400, result

    return 200, {"result": result}


def reload_modules() -> dict[str, Any]:
    """Hot-reload cc5_api so code changes take effect without server restart."""
    global cc5_api
    try:
        importlib.reload(cc5_api)
        cc5_api = sys.modules["cc5_api"]
        return {"success": True, "message": "cc5_api reloaded"}
    except Exception as e:
        print(f"[CC5 MCP Bridge] Reload failed: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


def _api_info() -> dict[str, Any]:
    """Return API discovery information."""
    return {
        "service": "cc5-mcp-bridge",
        "version": API_VERSION,
        "endpoints": {
            "GET": {p: a or "inline" for p, a in GET_ROUTES.items()},
            "POST": dict(POST_ROUTES),
        },
        "required_params": REQUIRED_PARAMS,
    }


class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the CC5 bridge API."""

    # Socket timeout (seconds) for reading a request and writing the reply. The
    # server handles one connection at a time, so without it an idle or stalled
    # connection (e.g. a browser preconnect) would block every other request.
    # Waiting for CC5 to run a command is not socket I/O and is not affected.
    timeout = 10

    def log_message(self, format: str, *args: Any) -> None:
        # Log non-2xx responses for debugging. For log_request() the arguments
        # are (request line, status code, size); log_error() passes (code, message).
        status = str(args[1]) if len(args) > 1 else ""
        if not status.startswith("2"):
            print(f"[CC5 MCP Bridge] {format % args}")

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reject_untrusted(self) -> bool:
        """Answer 403 and return True when the request fails the Host/Origin checks."""
        reason = check_request_headers(self.headers, self.server.server_address[1])
        if reason is None:
            return False
        print(f"[CC5 MCP Bridge] Refused {self.command} {self.path[:200]!r}: {reason}")
        self._discard_body()
        self.close_connection = True
        self._send_json(403, {"error": reason})
        return True

    def _discard_body(self, limit: int = 64 * 1024) -> None:
        """Read and drop a small request body before refusing the request.

        Closing a socket with unread data makes Windows send a reset, and the
        client would then see a connection error instead of the 403 message.
        """
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if 0 < length <= limit:
                self.rfile.read(length)
        except (ValueError, OSError):
            pass

    def _read_json(self) -> dict:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            raise ValueError(f"Invalid Content-Length: {raw_length!r}")
        if length <= 0:
            return {}
        if length > MAX_REQUEST_BYTES:
            raise ValueError(f"Request body too large: {length} bytes (max {MAX_REQUEST_BYTES})")
        try:
            data = self.rfile.read(min(length, MAX_REQUEST_BYTES))
            parsed = json.loads(data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON in request body: {e}") from e
        if not isinstance(parsed, dict):
            raise ValueError("Request body must be a JSON object")
        return parsed

    def do_GET(self) -> None:
        if self._reject_untrusted():
            return
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json(200, {"result": _health_payload()})
            return

        if path == "/api":
            if DEV_MODE:
                self._send_json(200, {"result": _api_info()})
            else:
                self._send_json(200, {"result": {"service": "cc5-mcp-bridge", "version": API_VERSION}})
            return

        if path == "/reload":
            if not DEV_MODE and not RELOAD_SECRET:
                self._send_json(403, {"error": (
                    "/reload is disabled. Set CC5_DEV_MODE=1 (or CC5_RELOAD_SECRET, then send "
                    "the X-Reload-Token header) in the environment CC5 starts from, then restart CC5."
                )})
                return
            if RELOAD_SECRET:
                token = self.headers.get("X-Reload-Token", "")
                # Compare bytes: compare_digest raises TypeError on non-ASCII str.
                if not hmac.compare_digest(token.encode("utf-8"), RELOAD_SECRET.encode("utf-8")):
                    self._send_json(403, {"error": "Forbidden"})
                    return
            result = reload_modules()
            status = 200 if result.get("success") else 500
            self._send_json(status, {"result": result})
            return

        action = GET_ROUTES.get(path)
        if action:
            status, data = _execute_sync(action, {})
            self._send_json(status, data)
        else:
            self._send_json(404, {"error": f"Not found: {path}"})

    def do_POST(self) -> None:
        if self._reject_untrusted():
            return
        path = urlparse(self.path).path

        try:
            params = self._read_json()
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
            return

        action = POST_ROUTES.get(path)
        if action:
            status, data = _execute_sync(action, params)
            self._send_json(status, data)
        else:
            self._send_json(404, {"error": f"Not found: {path}"})


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def start_server(port: int = 5101) -> threading.Thread:
    """Start the HTTP bridge server in a background daemon thread."""
    global _httpd
    # cc5_api is imported at the top of this module, before ACTION_MAP exists, so its
    # own _auto_patch_server() call is a no-op on a fresh start. Run it now so the
    # /workflow/* routes are there without a /reload.
    cc5_api._auto_patch_server()
    httpd = ReusableHTTPServer(("127.0.0.1", port), BridgeHandler)
    _httpd = httpd

    def run() -> None:
        httpd.serve_forever()

    print(
        "[CC5 MCP Bridge] dev mode (/reload, full /api): "
        f"{'ON' if DEV_MODE else 'off'} | exec_python + silent Export Head: "
        f"{'ON (CC5_ALLOW_EXEC)' if exec_allowed() else 'off'}"
    )
    if DEV_MODE and not RELOAD_SECRET:
        print("[CC5 MCP Bridge] WARNING: /reload endpoint has no authentication. Set CC5_RELOAD_SECRET env var to secure it.")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def stop_server() -> None:
    """Shut down the HTTP server gracefully."""
    global _httpd
    if _httpd is not None:
        _httpd.shutdown()
        _httpd.server_close()  # release the listening socket (frees the port)
        _httpd = None


# cc5_api is imported at the top of this module, before ACTION_MAP / POST_ROUTES exist, so its
# _auto_patch_server() found nothing to patch and the /workflow/* routes only appeared after a
# /reload. Patch once more now that the tables are defined.
try:
    cc5_api._auto_patch_server()
except Exception as _e:  # pragma: no cover - only runs inside CC5
    print(f"[CC5 MCP Bridge] route patch at startup failed: {_e}")
