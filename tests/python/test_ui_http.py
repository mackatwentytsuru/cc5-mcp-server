"""
The /ui routes through the REAL bridge server (HTTP in, the command queue, the job guard, JSON out).

A pump thread plays CC5's main thread: it drains the bridge's command queue and runs the fake Qt
event loop (queued timers), exactly the one thread that touches Qt in CC5. The HTTP side only
sends requests, as the MCP server does.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from ui_support import cc5_ui, fake_qt

import server  # noqa: E402
import RLPy  # noqa: E402  (the MagicMock stand-in)


class UiOverHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stop = threading.Event()
        cls.hold = threading.Event()               # while set, the fake Qt event loop does not run
        cls.q = fake_qt.make_qt()
        cls.server_thread = server.start_server(port=0)      # patches the routes (and reloads the helper modules)
        cls.port = server._httpd.server_address[1]
        cls.patchers = [mock.patch.object(cc5_ui, "_qt", return_value=cls.q),
                        mock.patch.object(cc5_ui, "_now", fake_qt.now)]
        for patcher in cls.patchers:
            patcher.start()

        def pump() -> None:
            while not cls.stop.is_set():
                server.process_command_queue()
                if not cls.hold.is_set():
                    fake_qt.drain(5)
                cls.stop.wait(0.003)

        cls.pump = threading.Thread(target=pump, daemon=True)
        cls.pump.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.hold.clear()
        cls.stop.set()
        cls.pump.join(timeout=5)
        for patcher in cls.patchers:
            patcher.stop()
        server.stop_server()
        cls.server_thread.join(timeout=5)

    def setUp(self) -> None:
        self.hold.clear()
        # let the previous test's job finish before looking at the fake Qt from this thread
        deadline = time.time() + 5
        while cc5_ui.running_job() is not None and time.time() < deadline:
            time.sleep(0.01)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.avatar = mock.Mock()
        self.avatar.GetName.return_value = "Beyon"
        status = mock.Mock()
        status.IsError.return_value = False
        for patcher in (mock.patch.object(RLPy.RScene, "GetAvatars", return_value=[self.avatar]),
                        mock.patch.object(RLPy.RFileIO, "LoadFile", return_value=status)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def request(self, path: str, body: dict | None = None) -> tuple[int, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            conn.request("POST", path, body=json.dumps(body or {}).encode(),
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, json.loads(resp.read() or b"{}")
        finally:
            conn.close()

    def wait_job(self, job_id: str, timeout: float = 10) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            status, data = self.request("/ui/job", {"job_id": job_id})
            if status == 200 and data["result"]["state"] in ("done", "failed"):
                return data["result"]
            time.sleep(0.01)
        self.fail(f"job {job_id} did not finish")

    def preset_file(self, name: str = "Curled.ccAvatarPreset") -> str:
        path = os.path.join(self.dir.name, name).replace("\\", "/")
        with open(path, "wb") as fh:
            fh.write(b"x")
        return path

    # --- tests -------------------------------------------------------------------------------

    def test_every_ui_route_is_registered_on_the_real_server(self) -> None:
        for path in ("/ui/windows", "/ui/widgets", "/ui/job", "/ui/capture_crop", "/ui/skingen/state",
                     "/ui/skingen/editor", "/ui/skingen/layer", "/ui/preset/list", "/ui/preset/apply",
                     "/ui/click"):
            self.assertIn(path, server.POST_ROUTES)
            self.assertNotEqual(server.POST_ROUTES[path], "ui_modules_missing", path)

    def test_read_routes_answer_json_over_http(self) -> None:
        status, data = self.request("/ui/windows", {})
        self.assertEqual((status, data["result"]["success"], data["result"]["count"]), (200, True, 0))
        status, data = self.request("/ui/skingen/state", {})
        self.assertEqual(status, 200)
        self.assertFalse(data["result"]["editor_found"])
        status, data = self.request("/ui/widgets", {})
        self.assertEqual(status, 400)                       # no filter: a refusal is HTTP 400 with the reason
        self.assertIn("give at least one", data["error"])

    def test_apply_preset_end_to_end_with_the_apply_window_answered(self) -> None:
        def load_file(path: str) -> mock.Mock:
            dlg = fake_qt.make_dialog(self.q, "Apply Character Preset", "Apply this preset?", ["Apply", "Cancel"],
                                      [("Restore neutral lash strip", False)])
            dlg.findChildren(self.q.QPushButton)[0].on_click = lambda: setattr(dlg, "_visible", False)
            return mock.Mock(**{"IsError.return_value": False})
        RLPy.RFileIO.LoadFile.side_effect = load_file
        status, data = self.request("/ui/preset/apply", {"file_path": self.preset_file()})
        self.assertEqual(status, 200, data)
        self.assertTrue(data["result"]["job_id"].startswith("preset-"))
        result = self.wait_job(data["result"]["job_id"])["result"]
        self.assertTrue(result["success"], result)
        self.assertEqual([a["pressed"] for a in result["answered"]], ["apply"])
        json.dumps(result)                                   # everything in the reply is plain JSON

    def test_bad_requests_are_400_with_a_reason(self) -> None:
        status, data = self.request("/ui/preset/apply", {"file_path": os.path.join(self.dir.name, "scene.ccProject")})
        self.assertEqual(status, 400)
        self.assertIn("not a preset type", data["error"])
        status, data = self.request("/ui/skingen/editor", {"active": "yes"})
        self.assertEqual(status, 400)

    def test_other_commands_wait_while_a_job_runs_and_the_read_only_ones_do_not(self) -> None:
        def load_file(path: str) -> mock.Mock:
            bake = fake_qt.make_dialog(self.q, "Baking", "Please wait", [])      # a progress window ...
            fake_qt.Timer.singleShot(3000, lambda: setattr(bake, "_visible", False))   # ... that goes away
            return mock.Mock(**{"IsError.return_value": False})
        RLPy.RFileIO.LoadFile.side_effect = load_file
        self.hold.set()                                      # the fake Qt loop stands still: the job stays "queued"
        status, data = self.request("/ui/preset/apply", {"file_path": self.preset_file()})
        self.assertEqual(status, 200, data)
        job_id = data["result"]["job_id"]

        status, data = self.request("/workflow/items", {})
        self.assertEqual(status, 400)
        self.assertIn("was NOT run", data["error"])
        self.assertIn(job_id, data["error"])
        status, data = self.request("/ui/click", {"window": "Body Wrap", "text": "Paste"})
        self.assertEqual(status, 400)
        self.assertIn("was NOT run", data["error"])
        for path in ("/ui/windows", "/ui/skingen/state"):
            self.assertEqual(self.request(path, {})[0], 200, path)
        status, data = self.request("/ui/job", {"job_id": job_id})
        self.assertEqual((status, data["result"]["state"]), (200, "queued"))
        status, data = self.request("/ui/preset/apply", {"file_path": self.preset_file("b.ccAvatarPreset")})
        self.assertEqual(status, 400)
        self.assertIn("another UI job is still running", data["error"])

        self.hold.clear()
        self.assertTrue(self.wait_job(job_id)["result"]["success"])

    def test_click_presses_one_named_button_and_refusals_are_400(self) -> None:
        win = fake_qt.Widget(name="BodyWrapWindow", title="Body Wrap")
        win._is_window = True
        paste = fake_qt.PushButton("Paste", win, name="qtPasteButton")
        points = fake_qt.PushButton("Generate AI Points", win, name="qtGeneratePoints")
        align = fake_qt.PushButton("Align Points", win, name="qtAlignPoints")
        self.q.app.tops.append(win)
        self.addCleanup(self.q.app.tops.remove, win)
        status, data = self.request("/ui/click", {"window": "Body Wrap", "text": "Paste", "wait_ms": 200})
        self.assertEqual(status, 200, data)
        result = self.wait_job(data["result"]["job_id"])["result"]
        self.assertTrue(result["success"], result)
        self.assertEqual(paste.clicks, 1)
        self.assertTrue(result["png_base64"])
        status, data = self.request("/ui/click", {"window": "Body Wrap", "text": "Generate AI Points"})
        self.assertEqual(status, 400)
        self.assertIn("mentions 'point'", data["error"])
        self.assertEqual(points.clicks, 0)
        status, data = self.request("/ui/click", {"window": "Body Wrap", "text": "Align Points", "wait_ms": 200})
        self.assertEqual(status, 200, data)             # the owner's exception (2026-10-31)
        self.assertTrue(self.wait_job(data["result"]["job_id"])["result"]["success"])
        self.assertEqual(align.clicks, 1)


if __name__ == "__main__":
    unittest.main()
