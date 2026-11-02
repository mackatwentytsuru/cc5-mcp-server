"""
Tests for the configurable bridge port (CC5_BRIDGE_PORT) and scripts/cc5_http.py.

Runs with plain CPython 3.10+ outside CC5 (RLPy is a MagicMock):

    python -m unittest discover -s tests/python -v

What is checked:
  * resolve_bridge_port: default 5101, a valid CC5_BRIDGE_PORT is used, and
    non-integers or ports outside 1024-65535 raise ValueError.
  * A bridge on a non-default port accepts Host 127.0.0.1:<that port> and refuses
    Host 127.0.0.1:5101 (the Host check follows the port it really listens on).
  * cc5_http.py validates its inputs and reaches a bridge on any port.
"""

from __future__ import annotations

import http.client
import io
import json
import os
import sys
import threading
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")
SCRIPTS_DIR = os.path.join(ROOT, "scripts")

sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
for _path in (PLUGIN_DIR, SCRIPTS_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import cc5_http  # noqa: E402
import server  # noqa: E402


class ResolveBridgePortTest(unittest.TestCase):
    def test_default_when_unset_or_blank(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CC5_BRIDGE_PORT", None)
            self.assertEqual(server.resolve_bridge_port(), 5101)
        self.assertEqual(server.resolve_bridge_port("  "), 5101)

    def test_env_value_is_used(self) -> None:
        with mock.patch.dict(os.environ, {"CC5_BRIDGE_PORT": "5111"}):
            self.assertEqual(server.resolve_bridge_port(), 5111)

    def test_bounds_are_inclusive(self) -> None:
        self.assertEqual(server.resolve_bridge_port("1024"), 1024)
        self.assertEqual(server.resolve_bridge_port("65535"), 65535)

    def test_bad_values_raise(self) -> None:
        for bad in ("abc", "51.1", "-5111", "80", "1023", "65536", "5111; rm"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                server.resolve_bridge_port(bad)


class BridgeOnOtherPortTest(unittest.TestCase):
    """One real bridge on a free (non-5101) port."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._stop = threading.Event()

        def pump() -> None:  # plays CC5's 16 ms QTimer
            while not cls._stop.is_set():
                server.process_command_queue()
                cls._stop.wait(0.005)

        cls._pump = threading.Thread(target=pump, daemon=True)
        cls._pump.start()
        cls._server_thread = server.start_server(port=0)
        cls.port = server._httpd.server_address[1]
        assert cls.port != 5101

    @classmethod
    def tearDownClass(cls) -> None:
        server.stop_server()
        cls._server_thread.join(timeout=5)
        cls._stop.set()
        cls._pump.join(timeout=5)

    def _get(self, host: str) -> int:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.putrequest("GET", "/health", skip_host=True)
            conn.putheader("Host", host)
            conn.endheaders()
            reply = conn.getresponse()
            reply.read()
            return reply.status
        finally:
            conn.close()

    def test_host_with_real_port_is_accepted(self) -> None:
        self.assertEqual(self._get(f"127.0.0.1:{self.port}"), 200)

    def test_host_with_default_port_is_refused(self) -> None:
        self.assertEqual(self._get("127.0.0.1:5101"), 403)

    def test_cc5_http_reaches_the_bridge(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = cc5_http.main(["--port", str(self.port), "--path", "/health"])
        self.assertEqual(code, 0)
        self.assertIn("status", json.loads(out.getvalue()).get("result", {}))

    def test_cc5_http_reports_http_errors(self) -> None:
        with redirect_stdout(io.StringIO()):
            code = cc5_http.main(["--port", str(self.port), "--path", "/no/such/route"])
        self.assertEqual(code, 1)


class Cc5HttpInputTest(unittest.TestCase):
    def test_valid_port(self) -> None:
        self.assertEqual(cc5_http.valid_port("5111"), 5111)
        for bad in ("x", "80", "70000"):
            with self.subTest(bad=bad), self.assertRaises(Exception):
                cc5_http.valid_port(bad)

    def test_build_request(self) -> None:
        self.assertEqual(cc5_http.build_request("get", "/health", None), ("GET", "/health", None))
        self.assertEqual(cc5_http.build_request("POST", "/a", None), ("POST", "/a", b"{}"))
        self.assertEqual(cc5_http.build_request("POST", "/a", '{"x":1}')[2], b'{"x":1}')
        for args in (("PUT", "/a", None), ("GET", "health", None), ("POST", "/a", "{bad")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                cc5_http.build_request(*args)

    def test_unreachable_port_exit_code(self) -> None:
        with mock.patch.object(cc5_http, "call", side_effect=ConnectionRefusedError("refused")):
            self.assertEqual(cc5_http.main(["--port", "5999"]), 3)


if __name__ == "__main__":
    unittest.main()
