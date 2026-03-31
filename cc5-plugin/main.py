"""
CC5 MCP Bridge Plugin - Entry Point

Starts a local HTTP server inside Character Creator 5 so the MCP server
can control CC5 via the RLPy API.

Install location:
  C:/Program Files/Reallusion/Character Creator 5/Bin64/OpenPlugin/CC5_MCP_Bridge/
"""

import os
import sys

# Add plugin directory to path so cc5_api and server modules are importable
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

import RLPy
from PySide2.QtCore import QTimer  # CC5 uses PySide2

import server as bridge_server

_timer = None
_server_thread = None

BRIDGE_PORT = 5100


def load_plugin():
    """Entry point called by CC5 when the plugin is loaded."""
    global _timer, _server_thread

    print("[CC5 MCP Bridge] Loading plugin...")

    try:
        _server_thread = bridge_server.start_server(port=BRIDGE_PORT)

        _timer = QTimer()
        _timer.timeout.connect(bridge_server.process_command_queue)
        _timer.start(100)  # Poll every 100ms

        print(f"[CC5 MCP Bridge] Bridge server running on http://127.0.0.1:{BRIDGE_PORT}")
    except Exception as e:
        print(f"[CC5 MCP Bridge] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return RLPy.RStatus.Failure

    return RLPy.RStatus.Success


def unload_plugin():
    """Called by CC5 when the plugin is unloaded."""
    global _timer, _server_thread

    if _timer is not None:
        _timer.stop()
        _timer = None

    _server_thread = None
    print("[CC5 MCP Bridge] Plugin unloaded.")
