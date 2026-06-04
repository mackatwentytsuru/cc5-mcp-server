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
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

import cc5_api

RELOAD_SECRET = os.environ.get("CC5_RELOAD_SECRET", "")
DEV_MODE = os.environ.get("CC5_DEV_MODE", "1") == "1"  # Default: dev mode on
API_VERSION = "1.1.0"

# Thread-safe command queue: HTTP thread -> main thread
command_queue: queue.Queue = queue.Queue(maxsize=100)
_store_lock = threading.Lock()
response_store: dict[str, Any] = {}
response_events: dict[str, threading.Event] = {}

_command_counter = 0
_counter_lock = threading.Lock()
_processing = False  # Re-entrance guard for process_command_queue

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
    "set_light_color":      ["light_name", "r", "g", "b"],
    "get_light_info":       ["light_name"],
    "set_light_multiplier": ["light_name", "multiplier"],
    "get_diffuse_color":    ["mesh_name", "material_name"],
    "set_diffuse_color":    ["mesh_name", "material_name", "r", "g", "b"],
    "get_material_properties": ["mesh_name", "material_name"],
    "set_material_opacity":    ["mesh_name", "material_name", "opacity"],
    "set_material_glossiness": ["mesh_name", "material_name", "glossiness"],
    "set_material_specular":   ["mesh_name", "material_name", "specular"],
    # Tier 1: Content Management
    "remove_scene_item":    ["item_name"],
    # Tier 3: Convenience Color Shortcuts
    "set_eye_color":        ["r", "g", "b"],
    "set_hair_color":       ["r", "g", "b"],
    "set_lip_color":        ["r", "g", "b"],
    # Tier 4: Visibility
    "set_item_visible":     ["item_name", "visible"],
    "exec_python":          ["code"],
    # Mesh-to-MetaHuman pipeline helpers
    "export_head_metahuman":   ["output_dir", "character_name"],
    "silent_install_filter":   ["output_dir", "character_name"],
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
    ),
    "capture_viewport":      lambda p: cc5_api.capture_viewport(p.get("output_path", "")),
    "set_subdivision_level": lambda p: cc5_api.set_subdivision_level(int(p["level"])),
    "undo":                  lambda p: cc5_api.undo(),
    "redo":                  lambda p: cc5_api.redo(),
    "get_camera_info":       lambda p: cc5_api.get_camera_info(),
    "set_camera_focal_length": lambda p: cc5_api.set_camera_focal_length(float(p["focal_length"])),
    "get_lights":            lambda p: cc5_api.get_lights(),
    "set_light_color":       lambda p: cc5_api.set_light_color(p["light_name"], float(p["r"]), float(p["g"]), float(p["b"])),
    "get_light_info":        lambda p: cc5_api.get_light_info(p["light_name"]),
    "set_light_multiplier":  lambda p: cc5_api.set_light_multiplier(p["light_name"], float(p["multiplier"])),
    "get_expression_info":   lambda p: cc5_api.get_expression_info(),
    "reset_all_morphs":      lambda p: cc5_api.reset_all_morphs(p.get("avatar_name", "")),
    "get_material_info":     lambda p: cc5_api.get_material_info(p.get("avatar_name", "")),
    "get_diffuse_color":     lambda p: cc5_api.get_diffuse_color(p["mesh_name"], p["material_name"]),
    "set_diffuse_color":     lambda p: cc5_api.set_diffuse_color(p["mesh_name"], p["material_name"], float(p["r"]), float(p["g"]), float(p["b"])),
    "get_material_properties": lambda p: cc5_api.get_material_properties(p["mesh_name"], p["material_name"]),
    "set_material_opacity":  lambda p: cc5_api.set_material_opacity(p["mesh_name"], p["material_name"], float(p["opacity"])),
    "set_material_glossiness": lambda p: cc5_api.set_material_glossiness(p["mesh_name"], p["material_name"], float(p["glossiness"])),
    "set_material_specular": lambda p: cc5_api.set_material_specular(p["mesh_name"], p["material_name"], float(p["specular"])),
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
}

# POST path -> action name
POST_ROUTES: dict[str, str] = {
    "/morphs/search":    "search_morphs",
    "/morph/get":        "get_morph_value",
    "/morph/set":        "set_morph_value",
    "/morphs/set":       "set_multiple_morphs",
    "/morphs/reset":     "reset_all_morphs",
    "/avatar/create":    "create_default_avatar",
    "/asset/load":       "load_asset",
    "/export/fbx":       "export_fbx",
    "/viewport/capture": "capture_viewport",
    "/subdivision":      "set_subdivision_level",
    "/undo":             "undo",
    "/redo":             "redo",
    "/camera/focal":     "set_camera_focal_length",
    "/light/color":      "set_light_color",
    "/light/info":       "get_light_info",
    "/light/multiplier": "set_light_multiplier",
    "/material/info":    "get_material_info",
    "/material/color/get": "get_diffuse_color",
    "/material/color/set": "set_diffuse_color",
    "/material/properties": "get_material_properties",
    "/material/opacity":    "set_material_opacity",
    "/material/glossiness": "set_material_glossiness",
    "/material/specular":   "set_material_specular",
    # Tier 1: Content Management
    "/item/remove":      "remove_scene_item",
    "/content/browse":   "browse_content",
    # Tier 3: Convenience Color Shortcuts
    "/color/eye":        "set_eye_color",
    "/color/hair":       "set_hair_color",
    "/color/lip":        "set_lip_color",
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
    "/lights":         "get_lights",
    "/expressions":    "get_expression_info",
    "/material/info":  "get_material_info",
    # Tier 1: Content Management
    "/clothes":        "list_clothes",
    "/hair":           "list_hair",
    "/accessories":    "list_accessories",
    # Tier 4: Scene
    "/scene/objects":  "get_scene_objects",
    # Silent export polling
    "/export/head_mh/status": "get_export_status",
}


def process_command_queue() -> None:
    """Drain the queue and execute RLPy calls on the main thread. Called by QTimer."""
    global _processing
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
                result = handler(params) if handler else {"error": f"Unknown action: {action}"}
            except Exception as e:
                print(f"[CC5 MCP Bridge] Action '{action}' failed: {traceback.format_exc()}")
                result = {"error": str(e)}

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

    def log_message(self, format: str, *args: Any) -> None:
        # Log non-2xx responses for debugging
        if args and not str(args[0]).startswith("2"):
            print(f"[CC5 MCP Bridge] {format % args}")

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json(200, {"result": {"status": "ok", "service": "cc5-mcp-bridge", "version": API_VERSION}})
            return

        if path == "/api":
            if DEV_MODE:
                self._send_json(200, {"result": _api_info()})
            else:
                self._send_json(200, {"result": {"service": "cc5-mcp-bridge", "version": API_VERSION}})
            return

        if path == "/reload":
            if not DEV_MODE and not RELOAD_SECRET:
                self._send_json(403, {"error": "/reload disabled. Set CC5_DEV_MODE=1 or CC5_RELOAD_SECRET."})
                return
            if RELOAD_SECRET:
                token = self.headers.get("X-Reload-Token", "")
                if not hmac.compare_digest(token, RELOAD_SECRET):
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
        path = urlparse(self.path).path

        try:
            params = self._read_json()
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
            return

        action = POST_ROUTES.get(path)
        if action:
            if action == "exec_python" and not DEV_MODE and not RELOAD_SECRET:
                self._send_json(403, {"error": "/exec/python disabled. Set CC5_DEV_MODE=1 or CC5_RELOAD_SECRET."})
                return
            status, data = _execute_sync(action, params)
            self._send_json(status, data)
        else:
            self._send_json(404, {"error": f"Not found: {path}"})


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def start_server(port: int = 5101) -> threading.Thread:
    """Start the HTTP bridge server in a background daemon thread."""
    global _httpd
    httpd = ReusableHTTPServer(("127.0.0.1", port), BridgeHandler)
    _httpd = httpd

    def run() -> None:
        httpd.serve_forever()

    if not RELOAD_SECRET:
        print("[CC5 MCP Bridge] WARNING: /reload endpoint has no authentication. Set CC5_RELOAD_SECRET env var to secure it.")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def stop_server() -> None:
    """Shut down the HTTP server gracefully."""
    global _httpd
    if _httpd is not None:
        _httpd.shutdown()
        _httpd = None
