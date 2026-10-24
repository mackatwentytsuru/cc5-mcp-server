"""
offset_mesh finds the turn between RIMesh.GetVertices(True) and the true world.

GetVertices(True) came back turned 90 degrees about Z for a choker, and writing those
values back turned the choker sideways (10-24). The turn is found against an OBJ that
CC5 exported; these tests run outside CC5 (RLPy is a MagicMock).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")

sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import cc5_api  # noqa: E402

WORLD = [(-7.2, -3.0, 154.6), (7.1, 11.3, 163.0), (0.5, 4.0, 158.2), (-2.0, 8.0, 160.1)]


def _turned_minus_90(points):
    """What GetVertices(True) returned for the choker: world turned -90 degrees about Z."""
    return [SimpleNamespace(x=y, y=-x, z=z) for x, y, z in points]


class FrameTurnTest(unittest.TestCase):
    def test_finds_the_90_degree_turn(self) -> None:
        turn, errors = cc5_api._wf_frame_turn(_turned_minus_90(WORLD), WORLD, range(len(WORLD)))
        self.assertEqual(turn, 90)
        self.assertLess(errors[90], 1e-9)

    def test_a_few_mm_of_conform_still_match(self) -> None:
        nudged = [(x, y, z + 0.4) for x, y, z in WORLD]
        turn, _errors = cc5_api._wf_frame_turn(_turned_minus_90(nudged), WORLD, range(len(WORLD)))
        self.assertEqual(turn, 90)

    def test_rejects_a_different_vertex_order(self) -> None:
        shuffled = WORLD[1:] + WORLD[:1]
        turn, _errors = cc5_api._wf_frame_turn(_turned_minus_90(shuffled), WORLD, range(len(WORLD)))
        self.assertIsNone(turn)

    def test_reads_only_the_v_lines_of_an_obj(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "c.obj")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# c\nv 1 2 3\nvt 0.5 0.5\nvn 0 0 1\nv 4 5 6\nf 1 2 1\n")
            self.assertEqual(cc5_api._wf_read_obj_vertices(path), [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)])


if __name__ == "__main__":
    unittest.main()
