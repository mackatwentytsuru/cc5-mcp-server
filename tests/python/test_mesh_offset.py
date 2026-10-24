"""
offset_mesh maps RIMesh.GetVertices(True) onto the true world before writing.

GetVertices(True) came back turned 90 degrees about Z for a cloth choker, and ~12 degrees
turned and ~2 cm shifted for a skirt converted to an accessory (10-24); writing the raw
values back turned the choker sideways. The map is fitted against an OBJ that CC5
exported; these tests run outside CC5 (RLPy is a MagicMock).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import math
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

WORLD = [(-7.2, -3.0, 154.6), (7.1, 11.3, 163.0), (0.5, 4.0, 158.2), (-2.0, 8.0, 160.1),
         (3.3, -1.0, 150.0), (-5.0, 6.5, 149.2)]


def _as_read(points, deg, shift=(0.0, 0.0, 0.0)):
    """What GetVertices(True) returns: world turned by -deg about Z, then shifted."""
    c, s = math.cos(math.radians(-deg)), math.sin(math.radians(-deg))
    return [SimpleNamespace(x=c * x - s * y + shift[0], y=s * x + c * y + shift[1], z=z + shift[2])
            for x, y, z in points]


class FrameFitTest(unittest.TestCase):
    def test_recovers_a_90_degree_turn(self) -> None:
        fit, error = cc5_api._wf_frame_fit(_as_read(WORLD, 90), WORLD, range(len(WORLD)))
        self.assertLess(error, 1e-6)
        self.assertAlmostEqual(math.degrees(math.atan2(fit[0][1], fit[0][0])), 90.0, places=4)

    def test_recovers_a_small_turn_and_shift(self) -> None:
        read = _as_read(WORLD, 11.6, shift=(1.0, -2.0, 0.05))
        fit, error = cc5_api._wf_frame_fit(read, WORLD, range(len(WORLD)))
        self.assertLess(error, 1e-6)
        mapped = cc5_api._wf_map(fit, read[0].x, read[0].y, read[0].z)
        for got, want in zip(mapped, WORLD[0]):
            self.assertAlmostEqual(got, want, places=5)

    def test_a_different_vertex_order_fits_badly(self) -> None:
        shuffled = WORLD[1:] + WORLD[:1]
        _fit, error = cc5_api._wf_frame_fit(_as_read(shuffled, 90), WORLD, range(len(WORLD)))
        self.assertGreater(error, 1.0)

    def test_reads_only_the_v_lines_of_an_obj(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "c.obj")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# c\nv 1 2 3\nvt 0.5 0.5\nvn 0 0 1\nv 4 5 6\nf 1 2 1\n")
            self.assertEqual(cc5_api._wf_read_obj_vertices(path), [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)])


if __name__ == "__main__":
    unittest.main()
