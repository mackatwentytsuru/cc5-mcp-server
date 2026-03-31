"""
HTTP bridge server for CC5 MCP plugin.

Uses Python's built-in http.server — no external dependencies needed.
All RLPy calls are queued and executed on the main thread via QTimer.
"""

import json
import queue
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

import cc5_api

# Thread-safe command queue: HTTP thread -> main thread
command_queue: queue.Queue = queue.Queue()
response_store: dict[str, Any] = {}
response_events: dict[str, threading.Event] = {}

_command_counter = 0
_counter_lock = threading.Lock()


def _next_command_id() -> str:
    global _command_counter
    with _counter_lock:
        _command_counter += 1
        return f"cmd_{_command_counter}"


# --- Action map (called on main thread) ---

ACTION_MAP = {
    "get_avatars":          lambda p: cc5_api.get_avatars(),
    "get_avatar_info":      lambda p: cc5_api.get_avatar_info(),
    "get_morph_catalog":    lambda p: cc5_api.get_morph_catalog(),
    "get_morph_value":      lambda p: cc5_api.get_morph_value(p["morph_id"]),
    "set_morph_value":      lambda p: cc5_api.set_morph_value(p["morph_id"], float(p["value"])),
    "set_multiple_morphs":  lambda p: cc5_api.set_multiple_morphs(p["morphs"]),
    "load_asset":           lambda p: cc5_api.load_asset(p["file_path"]),
    "export_fbx":           lambda p: cc5_api.export_fbx(p["output_path"], int(p.get("options", 0))),
    "set_subdivision_level": lambda p: cc5_api.set_subdivision_level(int(p["level"])),
}


def process_command_queue() -> None:
    """Drain the queue and execute RLPy calls on the main thread. Called by QTimer."""
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
            result = {"error": str(e), "traceback": traceback.format_exc()}

        response_store[cmd_id] = result
        event = response_events.get(cmd_id)
        if event:
            event.set()

        command_queue.task_done()


def _execute_sync(action: str, params: dict, timeout: float = 30.0) -> tuple[int, Any]:
    """Queue a command, wait for main-thread execution, return (http_status, result)."""
    cmd_id = _next_command_id()
    event = threading.Event()
    response_events[cmd_id] = event

    command_queue.put({"id": cmd_id, "action": action, "params": params})

    if not event.wait(timeout=timeout):
        response_events.pop(cmd_id, None)
        response_store.pop(cmd_id, None)
        return 504, {"error": "Timeout waiting for CC5 to process command"}

    result = response_store.pop(cmd_id, None)
    response_events.pop(cmd_id, None)

    if isinstance(result, dict) and "error" in result:
        return 500, result

    return 200, {"result": result}


class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the CC5 bridge API."""

    # Suppress access logs to avoid noise in CC5 console
    def log_message(self, format, *args):
        pass

    def _send_json(self, status: int, data: Any) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "cc5-mcp-bridge"})

        elif path == "/avatars":
            status, data = _execute_sync("get_avatars", {})
            self._send_json(status, data)

        elif path == "/avatar/info":
            status, data = _execute_sync("get_avatar_info", {})
            self._send_json(status, data)

        elif path == "/morphs/catalog":
            status, data = _execute_sync("get_morph_catalog", {})
            self._send_json(status, data)

        else:
            self._send_json(404, {"error": f"Not found: {path}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        params = self._read_json()

        route_map = {
            "/morph/get":    ("get_morph_value",       params),
            "/morph/set":    ("set_morph_value",        params),
            "/morphs/set":   ("set_multiple_morphs",    params),
            "/asset/load":   ("load_asset",             params),
            "/export/fbx":   ("export_fbx",             params),
            "/subdivision":  ("set_subdivision_level",  params),
        }

        if path in route_map:
            action, p = route_map[path]
            status, data = _execute_sync(action, p)
            self._send_json(status, data)
        else:
            self._send_json(404, {"error": f"Not found: {path}"})


def start_server(port: int = 5100) -> threading.Thread:
    """Start the HTTP bridge server in a background daemon thread."""
    httpd = HTTPServer(("127.0.0.1", port), BridgeHandler)

    def run() -> None:
        httpd.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
