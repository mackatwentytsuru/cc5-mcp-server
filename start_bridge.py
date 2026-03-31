"""
CC5 MCP Bridge - Script Editor Starter

CC5 の Script Editor からこのスクリプトを実行すると
ブリッジサーバーが http://127.0.0.1:5100 で起動します。

使い方:
  CC5メニュー → Script → Load Script → このファイルを選択 → Run
"""

import os
import sys

# プラグインディレクトリをパスに追加
_plugin_dir = r"C:\Program Files\Reallusion\Character Creator 5\Bin64\OpenPlugin\CC5_MCP_Bridge"
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

import RLPy
from PySide2.QtCore import QTimer

import server as bridge_server

BRIDGE_PORT = 5100

# グローバル参照（GCされないように保持）
_timer = None
_thread = None

def _start():
    global _timer, _thread
    _thread = bridge_server.start_server(port=BRIDGE_PORT)
    _timer = QTimer()
    _timer.timeout.connect(bridge_server.process_command_queue)
    _timer.start(100)
    print(f"[CC5 MCP Bridge] Started on http://127.0.0.1:{BRIDGE_PORT}")

_start()
