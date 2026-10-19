"""
Security tests for the CC5 bridge plugin (cc5-plugin/server.py + cc5_api.py).

Runs with plain CPython 3.10+ outside CC5: RLPy is replaced by a MagicMock and a
background thread stands in for CC5's QTimer that drains the command queue.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)

What is checked:
  * exec_python and the silent Export Head routes are refused by default and run
    only when CC5_ALLOW_EXEC is set; CC5_DEV_MODE does not enable them.
  * Requests with a non-loopback Host (DNS rebinding), any Origin header, or a
    browser Sec-Fetch-Site other than "none" are refused before anything runs.
  * Ordinary routes keep working for the clients the project uses.
"""

from __future__ import annotations

import http.client
import importlib
import json
import os
import sys
import threading
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")

# Stand-in for CC5's embedded RLPy module so the plugin imports outside CC5.
sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import cc5_api  # noqa: E402
import server  # noqa: E402

SILENT_PATHS = {
    "/export/head_mh/silent/install_filter": "silent_install_filter",
    "/export/head_mh/silent/trigger_dialog": "silent_trigger_dialog",
    "/export/head_mh/silent/configure_click": "silent_configure_and_click",
    "/export/head_mh/silent/finalize": "silent_finalize",
}
SILENT_BODY = {"output_dir": "D:/tmp/out", "character_name": "Test"}


def _without_flags() -> mock._patch_dict:
    """Patch os.environ for one test, with the opt-in flags removed."""
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    for name in ("CC5_ALLOW_EXEC", "CC5_DEV_MODE"):
        os.environ.pop(name, None)
    return patcher


class BridgeTestCase(unittest.TestCase):
    """Starts one real bridge server on a free port for the whole class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._stop = threading.Event()

        def pump() -> None:  # plays the role of CC5's 16 ms QTimer
            while not cls._stop.is_set():
                server.process_command_queue()
                cls._stop.wait(0.005)

        cls._pump = threading.Thread(target=pump, daemon=True)
        cls._pump.start()
        cls._server_thread = server.start_server(port=0)
        cls.port = server._httpd.server_address[1]

    @classmethod
    def tearDownClass(cls) -> None:
        server.stop_server()
        cls._server_thread.join(timeout=5)
        cls._stop.set()
        cls._pump.join(timeout=5)

    def setUp(self) -> None:
        self.addCleanup(_without_flags().stop)

    def request(self, method: str, path: str, body: dict | None = None,
                headers: dict | None = None) -> tuple[int, object]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            all_headers = {"Content-Type": "application/json"}
            all_headers.update(headers or {})
            data = json.dumps(body).encode("utf-8") if body is not None else None
            conn.request(method, path, body=data, headers=all_headers)
            resp = conn.getresponse()
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
        finally:
            conn.close()

    def stub_actions(self, **stubs: object) -> dict[str, mock.MagicMock]:
        """Replace ACTION_MAP entries with mocks for the duration of a test."""
        mocks = {name: mock.MagicMock(return_value=value) for name, value in stubs.items()}
        patcher = mock.patch.dict(server.ACTION_MAP, mocks)
        patcher.start()
        self.addCleanup(patcher.stop)
        return mocks


class ExecGateTests(BridgeTestCase):
    def test_exec_python_refused_by_default(self) -> None:
        status, data = self.request("POST", "/exec/python", {"code": "6*7"})
        self.assertEqual(status, 403)
        self.assertIn("'exec_python' is disabled", data["error"])
        self.assertIn("CC5_ALLOW_EXEC=1", data["error"])
        self.assertIn("setx CC5_ALLOW_EXEC 1", data["error"])

    def test_refused_exec_never_reaches_cc5(self) -> None:
        stubs = self.stub_actions(exec_python={"success": True, "result": "ran"})
        status, _ = self.request("POST", "/exec/python", {"code": "6*7"})
        self.assertEqual(status, 403)
        stubs["exec_python"].assert_not_called()

    def test_each_silent_route_refused_by_default(self) -> None:
        stubs = self.stub_actions(**{a: {"success": True} for a in SILENT_PATHS.values()})
        for path, action in SILENT_PATHS.items():
            with self.subTest(path=path):
                status, data = self.request("POST", path, SILENT_BODY)
                self.assertEqual(status, 403)
                self.assertIn(f"'{action}' is disabled", data["error"])
                stubs[action].assert_not_called()

    def test_dev_mode_does_not_enable_exec(self) -> None:
        with mock.patch.object(server, "DEV_MODE", True):
            os.environ["CC5_DEV_MODE"] = "1"
            status, _ = self.request("POST", "/exec/python", {"code": "6*7"})
        self.assertEqual(status, 403)

    def test_reload_secret_does_not_enable_exec(self) -> None:
        with mock.patch.object(server, "RELOAD_SECRET", "s3cret"):
            status, _ = self.request("POST", "/exec/python", {"code": "6*7"},
                                     headers={"X-Reload-Token": "s3cret"})
        self.assertEqual(status, 403)

    def test_disabled_values_keep_exec_off(self) -> None:
        for value in ("0", "false", "no", "", "off"):
            with self.subTest(value=value):
                os.environ["CC5_ALLOW_EXEC"] = value
                status, _ = self.request("POST", "/exec/python", {"code": "6*7"})
                self.assertEqual(status, 403)

    def test_exec_python_runs_with_allow_exec(self) -> None:
        os.environ["CC5_ALLOW_EXEC"] = "1"
        status, data = self.request("POST", "/exec/python", {"code": "6*7"})
        self.assertEqual(status, 200)
        self.assertEqual(data["result"], {"success": True, "result": "42"})

    def test_true_and_yes_also_enable_exec(self) -> None:
        for value in ("true", "YES"):
            with self.subTest(value=value):
                os.environ["CC5_ALLOW_EXEC"] = value
                status, data = self.request("POST", "/exec/python", {"code": "result = 2 + 3"})
                self.assertEqual(status, 200)
                self.assertEqual(data["result"]["result"], "5")

    def test_silent_routes_pass_through_with_allow_exec(self) -> None:
        os.environ["CC5_ALLOW_EXEC"] = "1"
        stubs = self.stub_actions(**{a: {"success": True, "stub": a} for a in SILENT_PATHS.values()})
        for path, action in SILENT_PATHS.items():
            with self.subTest(path=path):
                status, data = self.request("POST", path, SILENT_BODY)
                self.assertEqual(status, 200)
                self.assertEqual(data["result"]["stub"], action)
                stubs[action].assert_called_once()

    def test_safe_routes_work_without_allow_exec(self) -> None:
        stubs = self.stub_actions(
            get_avatars=[{"name": "A"}],
            get_morph_value={"success": True, "value": 0.5},
            get_export_status={"phase": "idle"},
        )
        self.assertEqual(self.request("GET", "/avatars"), (200, {"result": [{"name": "A"}]}))
        status, data = self.request("POST", "/morph/get", {"morph_id": "Nose_Size"})
        self.assertEqual((status, data["result"]["value"]), (200, 0.5))
        status, _ = self.request("GET", "/export/head_mh/status")
        self.assertEqual(status, 200)
        stubs["get_morph_value"].assert_called_once()

    def test_health_reports_new_version(self) -> None:
        status, data = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["result"]["version"], server.API_VERSION)


class ReloadGateTests(BridgeTestCase):
    def test_reload_refused_when_dev_mode_off(self) -> None:
        with mock.patch.object(server, "DEV_MODE", False), \
                mock.patch.object(server, "reload_modules") as reload_mock:
            status, data = self.request("GET", "/reload")
        self.assertEqual(status, 403)
        self.assertIn("CC5_DEV_MODE=1", data["error"])
        reload_mock.assert_not_called()

    def test_reload_allowed_in_dev_mode(self) -> None:
        with mock.patch.object(server, "DEV_MODE", True), \
                mock.patch.object(server, "reload_modules", return_value={"success": True}) as reload_mock:
            status, _ = self.request("GET", "/reload")
        self.assertEqual(status, 200)
        reload_mock.assert_called_once()

    def test_api_listing_is_short_when_dev_mode_off(self) -> None:
        with mock.patch.object(server, "DEV_MODE", False):
            status, data = self.request("GET", "/api")
        self.assertEqual(status, 200)
        self.assertNotIn("endpoints", data["result"])


class HostAndOriginTests(BridgeTestCase):
    def test_loopback_hosts_accepted(self) -> None:
        for host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"LOCALHOST:{self.port}"):
            with self.subTest(host=host):
                status, _ = self.request("GET", "/health", headers={"Host": host})
                self.assertEqual(status, 200)

    def test_bad_hosts_refused(self) -> None:
        bad_hosts = (
            f"evil.example:{self.port}",   # DNS rebinding: attacker's own name
            f"127.0.0.1.evil.example:{self.port}",
            "127.0.0.1",                    # no port
            "127.0.0.1:1",                  # wrong port
            f"0.0.0.0:{self.port}",
            "",
        )
        for host in bad_hosts:
            with self.subTest(host=host):
                status, data = self.request("GET", "/health", headers={"Host": host})
                self.assertEqual(status, 403)
                self.assertIn("Host header", data["error"])

    def test_rebinding_host_cannot_run_exec_even_when_enabled(self) -> None:
        os.environ["CC5_ALLOW_EXEC"] = "1"
        stubs = self.stub_actions(exec_python={"success": True})
        status, _ = self.request("POST", "/exec/python", {"code": "1"},
                                 headers={"Host": f"evil.example:{self.port}"})
        self.assertEqual(status, 403)
        stubs["exec_python"].assert_not_called()

    def test_any_origin_refused(self) -> None:
        for origin in ("https://evil.example", "null", f"http://127.0.0.1:{self.port}",
                       "http://localhost:3000"):
            with self.subTest(origin=origin):
                status, data = self.request("GET", "/health", headers={"Origin": origin})
                self.assertEqual(status, 403)
                self.assertIn("Origin", data["error"])

    def test_origin_blocks_post_even_when_exec_enabled(self) -> None:
        os.environ["CC5_ALLOW_EXEC"] = "1"
        stubs = self.stub_actions(exec_python={"success": True},
                                  silent_trigger_dialog={"success": True})
        for path in ("/exec/python", "/export/head_mh/silent/trigger_dialog"):
            with self.subTest(path=path):
                status, _ = self.request("POST", path, {"code": "1"},
                                         headers={"Origin": "https://evil.example",
                                                  "Content-Type": "text/plain"})
                self.assertEqual(status, 403)
        stubs["exec_python"].assert_not_called()
        stubs["silent_trigger_dialog"].assert_not_called()

    def test_browser_triggered_get_refused(self) -> None:
        # e.g. <img src="http://127.0.0.1:5101/reload"> sends no Origin, but does
        # send Sec-Fetch-Site in current browsers.
        with mock.patch.object(server, "DEV_MODE", True), \
                mock.patch.object(server, "reload_modules") as reload_mock:
            for site in ("cross-site", "same-site", "same-origin"):
                with self.subTest(site=site):
                    status, _ = self.request("GET", "/reload", headers={"Sec-Fetch-Site": site})
                    self.assertEqual(status, 403)
        reload_mock.assert_not_called()

    def test_typed_url_in_browser_allowed(self) -> None:
        # The user typing the URL into the address bar sends Sec-Fetch-Site: none.
        status, _ = self.request("GET", "/health", headers={"Sec-Fetch-Site": "none"})
        self.assertEqual(status, 200)

    def test_node_fetch_headers_allowed(self) -> None:
        # Node's fetch (used by the MCP server) sends sec-fetch-mode but no Origin.
        status, _ = self.request("GET", "/health", headers={
            "Host": f"localhost:{self.port}", "sec-fetch-mode": "cors",
            "user-agent": "node", "accept": "*/*",
        })
        self.assertEqual(status, 200)

    def test_curl_style_form_post_allowed(self) -> None:
        # The skills use `curl -d '{...}'` (form content type, no Origin).
        os.environ["CC5_ALLOW_EXEC"] = "1"
        status, data = self.request("POST", "/exec/python", {"code": "6*7"},
                                    headers={"Content-Type": "application/x-www-form-urlencoded",
                                             "User-Agent": "curl/8.21.0"})
        self.assertEqual(status, 200)
        self.assertEqual(data["result"]["result"], "42")


class CheckRequestHeadersUnitTests(unittest.TestCase):
    def test_returns_none_for_good_request(self) -> None:
        self.assertIsNone(server.check_request_headers({"Host": "127.0.0.1:5101"}, 5101))
        self.assertIsNone(server.check_request_headers({"Host": "[::1]:5101"}, 5101))

    def test_missing_host_refused(self) -> None:
        self.assertIsNotNone(server.check_request_headers({}, 5101))

    def test_long_host_is_truncated_in_message(self) -> None:
        reason = server.check_request_headers({"Host": "a" * 5000}, 5101)
        self.assertLess(len(reason), 300)


class Cc5ApiGateTests(unittest.TestCase):
    """The same gate inside cc5_api, which is hot-reloaded separately from server.py."""

    def setUp(self) -> None:
        self.addCleanup(_without_flags().stop)

    def test_exec_python_refused_by_default(self) -> None:
        result = cc5_api.exec_python("6*7")
        self.assertFalse(result["success"])
        self.assertIn("CC5_ALLOW_EXEC=1", result["error"])

    def test_dev_mode_does_not_enable_exec(self) -> None:
        os.environ["CC5_DEV_MODE"] = "1"
        self.assertFalse(cc5_api.exec_python("6*7")["success"])

    def test_silent_steps_refused_by_default(self) -> None:
        calls = {
            "silent_install_filter": lambda: cc5_api.silent_install_filter("D:/tmp/out", "Test"),
            "silent_trigger_dialog": cc5_api.silent_trigger_dialog,
            "silent_configure_and_click": cc5_api.silent_configure_and_click,
            "silent_finalize": cc5_api.silent_finalize,
        }
        for name, call in calls.items():
            with self.subTest(name=name):
                result = call()
                self.assertFalse(result["success"])
                self.assertIn(f"'{name}' is disabled", result["error"])

    def test_exec_python_runs_with_allow_exec(self) -> None:
        os.environ["CC5_ALLOW_EXEC"] = "1"
        self.assertEqual(cc5_api.exec_python("6*7"), {"success": True, "result": "42"})


class DefaultsTests(unittest.TestCase):
    def test_dev_mode_is_off_when_unset(self) -> None:
        patcher = _without_flags()
        try:
            importlib.reload(server)
            self.assertFalse(server.DEV_MODE)
            os.environ["CC5_DEV_MODE"] = "1"
            importlib.reload(server)
            self.assertTrue(server.DEV_MODE)
        finally:
            patcher.stop()
            importlib.reload(server)

    def test_exec_gate_lists_exactly_the_risky_actions(self) -> None:
        self.assertEqual(
            server.EXEC_GATED_ACTIONS,
            {"exec_python", *SILENT_PATHS.values()},
        )
        for action in server.EXEC_GATED_ACTIONS:
            self.assertIn(action, server.ACTION_MAP)


if __name__ == "__main__":
    unittest.main()
