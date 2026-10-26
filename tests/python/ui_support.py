"""
Shared set-up for the cc5_ui / cc5_skingen / cc5_content tests: path, RLPy stand-in, a fresh
fake Qt and fake clock for every test. Not a test module itself.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any, Callable, Iterator
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")

sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import cc5_api  # noqa: E402
import cc5_ui  # noqa: E402
import cc5_uiview  # noqa: E402,F401  (imported so tests can find it in sys.modules)
import fake_qt  # noqa: E402

__all__ = ["UiTestCase", "cc5_api", "cc5_ui", "fake_qt", "PLUGIN_DIR", "ROOT"]


class UiTestCase(unittest.TestCase):
    """Fresh fake Qt and clock for every test; cc5_ui talks to the fake."""

    def setUp(self) -> None:
        self.q = fake_qt.make_qt()
        for patcher in (mock.patch.object(cc5_ui, "_qt", return_value=self.q),
                        mock.patch.object(cc5_ui, "_now", fake_qt.now)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def dialog(self, title: str, text: str, buttons: list[str],
               boxes: list[tuple[str, bool]] | None = None) -> Any:
        return fake_qt.make_dialog(self.q, title, text, buttons, boxes)

    @staticmethod
    def run_steps(gen: Iterator[float], on_step: Callable[[int], None] | None = None) -> Any:
        """Drive a job generator by hand; returns its return value. on_step(n) runs before step n."""
        n = 0
        while True:
            if on_step:
                on_step(n)
            try:
                wait = next(gen)
            except StopIteration as stop:
                return stop.value
            fake_qt.Timer.clock[0] += wait / 1000.0
            n += 1
            assert n < 500, "generator never finished"

    @staticmethod
    def finish(started: dict[str, Any]) -> dict[str, Any]:
        """Let a started job run to the end and return its result."""
        assert started.get("success"), started
        fake_qt.drain()
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        assert job["state"] in ("done", "failed"), job
        json.dumps(job)                           # every job reply must be plain JSON (it goes over HTTP)
        return job["result"]
