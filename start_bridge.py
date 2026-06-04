"""
CC5 MCP Bridge Starter — run from CC5's Script Editor.
"""
import os
import socket
import sys

# Derive plugin dir from this script's location
_plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cc5-plugin")
if not os.path.isdir(_plugin_dir):
    # Fallback: installed plugin location
    _plugin_dir = os.path.join(
        os.environ.get("CC5_ROOT", r"C:\Program Files\Reallusion\Character Creator 5"),
        "Bin64", "OpenPlugin", "CC5_MCP_Bridge",
    )
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

# Clear module cache to load latest code
for m in ["server", "cc5_api"]:
    if m in sys.modules:
        del sys.modules[m]

import RLPy
from PySide2.QtCore import QTimer
import server as bridge_server

BRIDGE_PORT = int(os.environ.get("CC5_BRIDGE_PORT", "5101"))

_timer = None
_thread = None


def _find_free_port(start: int) -> int:
    for port in range(start, start + 10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        finally:
            s.close()
    raise RuntimeError(f"No free port found in range {start}-{start+9}")


def _start():
    global _timer, _thread
    port = _find_free_port(BRIDGE_PORT)
    if port != BRIDGE_PORT:
        print(f"[CC5 MCP Bridge] WARNING: Port {BRIDGE_PORT} in use. Started on {port}. Update CC5_BRIDGE_URL.")
    _thread = bridge_server.start_server(port=port)
    _timer = QTimer()
    _timer.timeout.connect(bridge_server.process_command_queue)
    _timer.start(50)  # 50ms for faster response
    print(f"[CC5 MCP Bridge] Started on http://127.0.0.1:{port}")


_start()
