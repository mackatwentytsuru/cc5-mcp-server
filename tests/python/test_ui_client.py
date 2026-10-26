"""
scripts/ui_client.py against a stand-in bridge: job polling (including the 504 "CC5 is busy" reply),
window PNGs, and the exit codes.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from ui_support import ROOT  # sets up sys.path

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ui_client  # noqa: E402


class StubBridge:
    """A bridge that answers from a script: replies[path] is a list of (status, body) used in order."""

    def __init__(self, replies: dict[str, list[tuple[int, Any]]]) -> None:
        self.replies = replies
        self.requests: list[tuple[str, dict]] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any) -> None:
                pass

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                stub.requests.append((self.path, body))
                queue = stub.replies.get(self.path, [(404, {"error": "not found"})])
                status, payload = queue.pop(0) if len(queue) > 1 else queue[0]
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def busy() -> tuple[int, dict]:
    return 504, {"error": "Timeout waiting for CC5 to process command"}


class UiClientTest(unittest.TestCase):
    def bridge(self, replies: dict[str, list[tuple[int, Any]]]) -> StubBridge:
        stub = StubBridge(replies)
        self.addCleanup(stub.close)
        return stub

    def test_post_unwraps_the_result_and_returns_error_bodies(self) -> None:
        stub = self.bridge({"/ok": [(200, {"result": {"success": True, "n": 1}})],
                            "/bad": [(400, {"success": False, "error": "nope"})]})
        self.assertEqual(ui_client.post("/ok", {}, stub.url), {"success": True, "n": 1})
        self.assertEqual(ui_client.post("/bad", {}, stub.url)["error"], "nope")

    def test_run_job_waits_through_busy_replies(self) -> None:
        stub = self.bridge({
            "/ui/preset/apply": [(200, {"result": {"success": True, "job_id": "preset-1", "state": "queued"}})],
            "/ui/job": [busy(), (200, {"result": {"success": True, "state": "running", "windows": []}}), busy(),
                        (200, {"result": {"success": True, "state": "done", "result": {"success": True, "files": []}}})],
        })
        res = ui_client.run_job("/ui/preset/apply", {"file_path": "x"}, stub.url, timeout_s=30,
                                poll_s=0, sleep=lambda _s: None)
        self.assertTrue(res["success"])
        self.assertEqual((res["job_id"], res["job_state"]), ("preset-1", "done"))
        self.assertEqual([r[0] for r in stub.requests].count("/ui/job"), 4)

    def test_a_refused_start_is_returned_as_it_is(self) -> None:
        stub = self.bridge({"/ui/preset/apply": [(400, {"success": False, "error": "file not found"})]})
        res = ui_client.run_job("/ui/preset/apply", {}, stub.url, sleep=lambda _s: None)
        self.assertEqual(res["error"], "file not found")
        self.assertEqual(len(stub.requests), 1)

    def test_a_failed_job_returns_its_error(self) -> None:
        stub = self.bridge({
            "/ui/skingen/editor": [(200, {"result": {"success": True, "job_id": "e-1"}})],
            "/ui/job": [(200, {"result": {"success": True, "state": "failed",
                                          "result": {"success": False, "error": "RuntimeError: x"}}})]})
        res = ui_client.run_job("/ui/skingen/editor", {"active": False}, stub.url, poll_s=0, sleep=lambda _s: None)
        self.assertFalse(res["success"])
        self.assertEqual(res["job_state"], "failed")

    def test_gives_up_and_reports_the_open_windows(self) -> None:
        windows = [{"title": "Mystery", "text": "?", "buttons": ["OK"]}]
        stub = self.bridge({
            "/ui/capture_crop": [(200, {"result": {"success": True, "job_id": "c-1"}})],
            "/ui/job": [(200, {"result": {"success": True, "state": "running", "windows": windows}})]})
        res = ui_client.run_job("/ui/capture_crop", {}, stub.url, timeout_s=0.05, poll_s=0.01)
        self.assertFalse(res["success"])
        self.assertEqual(res["windows"], windows)

    def test_save_window_pngs(self) -> None:
        png = base64.b64encode(b"PNGDATA").decode()
        reply = {"windows": [{"index": 0, "png_base64": png}, {"index": 1}], "main_window": {"png_base64": png}}
        with tempfile.TemporaryDirectory() as folder:
            paths = ui_client.save_window_pngs(reply, folder)
            self.assertEqual(len(paths), 2)
            with open(paths[0], "rb") as fh:
                self.assertEqual(fh.read(), b"PNGDATA")

    def test_describe_windows(self) -> None:
        text = ui_client.describe_windows({"windows": [
            {"title": "License", "text": "expired", "buttons": ["OK"], "needs_human": "license"},
            {"title": "Baking", "text": "wait", "buttons": [], "progress": True}]})
        self.assertIn("[needs a person]", text)
        self.assertIn("[progress]", text)
        self.assertEqual(ui_client.describe_windows({}), "(no windows open)")

    def run_cli(self, stub: StubBridge, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ui_client.main(["--base", stub.url, *argv])
        return code, out.getvalue()

    def test_cli_layers_prints_state(self) -> None:
        stub = self.bridge({"/ui/skingen/state": [(200, {"result": {"success": True, "layers": [{"name": "Lips"}]}})]})
        code, text = self.run_cli(stub, "layers")
        self.assertEqual(code, 0)
        self.assertIn("Lips", text)

    def test_cli_apply_sends_answers_and_files(self) -> None:
        stub = self.bridge({
            "/ui/preset/apply": [(200, {"result": {"success": True, "job_id": "p-1"}})],
            "/ui/job": [(200, {"result": {"state": "done", "result": {"success": True, "files": []}}})]})
        ui_client_sleep = ui_client.time.sleep
        ui_client.time.sleep = lambda _s: None
        try:
            code, _text = self.run_cli(stub, "apply", "a.ccSkinGenPreset", "b.ccSkinGenPreset",
                                       "--answer", "layer_choice=add", "--answer", "restore_neutral_lash=false")
        finally:
            ui_client.time.sleep = ui_client_sleep
        self.assertEqual(code, 0)
        body = stub.requests[0][1]
        self.assertEqual(body["file_paths"], ["a.ccSkinGenPreset", "b.ccSkinGenPreset"])
        self.assertEqual(body["answers"], {"layer_choice": "add", "restore_neutral_lash": False})

    def test_cli_exit_code_2_when_a_window_needs_a_person(self) -> None:
        stub = self.bridge({
            "/ui/skingen/editor": [(200, {"result": {"success": True, "job_id": "e-1"}})],
            "/ui/job": [(200, {"result": {"state": "done", "result": {
                "success": False, "blocked_by": {"title": "Save", "text": "Save?", "buttons": ["Yes", "No"]}}}})]})
        ui_client_sleep = ui_client.time.sleep
        ui_client.time.sleep = lambda _s: None
        try:
            code, _text = self.run_cli(stub, "editor", "off")
        finally:
            ui_client.time.sleep = ui_client_sleep
        self.assertEqual(code, 2)

    def test_cli_windows_with_shots(self) -> None:
        png = base64.b64encode(b"X").decode()
        stub = self.bridge({"/ui/windows": [(200, {"result": {"success": True, "windows": [
            {"index": 0, "title": "T", "text": "t", "buttons": ["OK"], "png_base64": png}]}})]})
        with tempfile.TemporaryDirectory() as folder:
            code, text = self.run_cli(stub, "windows", "--shots", folder)
            self.assertEqual(code, 0)
            self.assertEqual(len(os.listdir(folder)), 1)
        self.assertTrue(stub.requests[0][1]["screenshot"])


if __name__ == "__main__":
    unittest.main()
