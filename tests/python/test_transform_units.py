"""
get_transform must return the units set_transform takes (cm, degrees, percent).

The raw LocalTransform values are a quaternion's x/y/z and a scale factor; passing them
back into set_transform shrank a hat to 1% (10-24). These tests read through a fake
Transform data block outside CC5 (RLPy is a MagicMock).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")

sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import cc5_api  # noqa: E402


class _Variant:
    def __init__(self, value: float) -> None:
        self._value = value

    def ToFloat(self) -> float:
        return self._value


class _Block:
    def __init__(self, data: dict[str, float]) -> None:
        self._data = data

    def GetData(self, name: str, _time) -> _Variant:
        return _Variant(self._data[name])


def _item_with_block(data: dict[str, float]) -> mock.MagicMock:
    obj = mock.MagicMock(name="item")
    obj.GetControl.return_value.GetDataBlock.return_value = _Block(data)
    return obj


class TransformUnitsTest(unittest.TestCase):
    def test_reads_degrees_and_percent_from_the_data_block(self) -> None:
        obj = _item_with_block({
            "Position/PositionX": 3.62, "Position/PositionY": 10.5, "Position/PositionZ": -2.26,
            "Rotation/RotationX": math.radians(-90.0), "Rotation/RotationY": math.radians(12.5),
            "Rotation/RotationZ": 0.0,
            "Scale/ScaleX": 0.9, "Scale/ScaleY": 0.9, "Scale/ScaleZ": 1.0,
        })
        values = cc5_api._wf_transform_values(obj)
        self.assertEqual(values["move"], [3.62, 10.5, -2.26])
        self.assertEqual(values["rotate"], [-90.0, 12.5, 0.0])
        self.assertEqual(values["scale"], [90.0, 90.0, 100.0])
        self.assertEqual(values["units"]["rotate"], "degrees (Euler X/Y/Z)")
        self.assertNotIn("units_warning", values)

    def test_falls_back_to_raw_values_with_a_warning(self) -> None:
        obj = mock.MagicMock(name="item")
        obj.GetControl.side_effect = RuntimeError("no control")
        transform = obj.LocalTransform.return_value
        transform.T.return_value = mock.Mock(x=1.0, y=2.0, z=3.0)
        transform.R.return_value = mock.Mock(x=-0.73, y=0.19, z=-0.12)
        transform.S.return_value = mock.Mock(x=1.0, y=1.0, z=1.0)
        values = cc5_api._wf_transform_values(obj)
        self.assertEqual(values["move"], [1.0, 2.0, 3.0])
        self.assertEqual(values["rotate"], [-0.73, 0.19, -0.12])
        self.assertIn("do not pass rotate/scale back", values["units_warning"])
        self.assertIn("quaternion", values["units"]["rotate"])


if __name__ == "__main__":
    unittest.main()
