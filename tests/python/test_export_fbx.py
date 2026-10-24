"""
export_fbx must never report success unless an FBX file really exists.

Regression for the 2026-10-21 bug: with trial (unpurchased) content in the
project, RFileIO.ExportFbxFile returned an RStatus error, the plugin ignored it
and reported success, and no file was written.

Runs with plain CPython outside CC5 (RLPy is a stand-in):

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_DIR = os.path.join(ROOT, "cc5-plugin")

sys.modules.setdefault("RLPy", mock.MagicMock(name="RLPy"))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import cc5_api  # noqa: E402


class FakeStatus:
    def __init__(self, is_error: bool, code: int = 0) -> None:
        self._is_error = is_error
        self._code = code

    def IsError(self) -> bool:  # noqa: N802 - mirrors RLPy
        return self._is_error

    def GetStatusCode(self) -> int:  # noqa: N802
        return self._code


def make_rlpy(export_impl, trial_content: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        RExportFbxSetting=mock.MagicMock(),
        RFileIO=types.SimpleNamespace(ExportFbxFile=export_impl),
        RGlobal=types.SimpleNamespace(
            IsTrialContentMode=lambda: trial_content,
            IsTrialVersion=lambda: False,
        ),
    )


class ExportFbxVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = os.path.join(self._tmp.name, "sub", "body.fbx")
        patch = mock.patch.object(cc5_api, "get_first_avatar", return_value=object())
        patch.start()
        self.addCleanup(patch.stop)

    def run_export(self, rlpy: types.SimpleNamespace) -> dict:
        with mock.patch.object(cc5_api, "RLPy", rlpy):
            return cc5_api.export_fbx(
                self.out, target_tool="Default", export_motion=False,
                embed_textures=True, sub_d_level=0,
            )

    def test_rstatus_error_is_a_failure_and_names_trial_content(self) -> None:
        rlpy = make_rlpy(lambda *a: FakeStatus(True, 1), trial_content=True)
        result = self.run_export(rlpy)
        self.assertFalse(result["success"])
        self.assertIn("trial", result["error"].lower())
        self.assertIn("IsError=True", result["error"])
        self.assertFalse(os.path.exists(self.out))

    def test_rstatus_error_without_trial_content_says_cause_unknown(self) -> None:
        result = self.run_export(make_rlpy(lambda *a: FakeStatus(True, 1)))
        self.assertFalse(result["success"])
        self.assertIn("Cause unknown", result["error"])

    def test_success_status_but_no_file_is_a_failure(self) -> None:
        result = self.run_export(make_rlpy(lambda *a: FakeStatus(False)))
        self.assertFalse(result["success"])
        self.assertIn("no file was created", result["error"])

    def test_none_return_without_file_is_a_failure(self) -> None:
        result = self.run_export(make_rlpy(lambda *a: None))
        self.assertFalse(result["success"])

    def test_false_bool_is_a_failure(self) -> None:
        result = self.run_export(make_rlpy(lambda *a: False))
        self.assertFalse(result["success"])

    def test_empty_file_is_a_failure(self) -> None:
        def write_empty(avatar, path, *rest):
            open(path, "wb").close()
            return FakeStatus(False)

        result = self.run_export(make_rlpy(write_empty))
        self.assertFalse(result["success"])
        self.assertIn("empty", result["error"])

    def test_stale_file_from_an_earlier_export_is_a_failure(self) -> None:
        os.makedirs(os.path.dirname(self.out))
        with open(self.out, "wb") as f:
            f.write(b"old")
        old = time.time() - 3600
        os.utime(self.out, (old, old))
        result = self.run_export(make_rlpy(lambda *a: FakeStatus(False)))
        self.assertFalse(result["success"])
        self.assertIn("stale", result["error"])

    def test_real_file_is_a_success_and_size_is_reported(self) -> None:
        def write_file(avatar, path, *rest):
            with open(path, "wb") as f:
                f.write(b"x" * 1234)
            return FakeStatus(False)

        result = self.run_export(make_rlpy(write_file))
        self.assertTrue(result["success"], result)
        self.assertTrue(any("1234 bytes" in n for n in result["notes"]))

    def test_success_without_a_return_value_still_needs_the_file(self) -> None:
        def write_file(avatar, path, *rest):
            with open(path, "wb") as f:
                f.write(b"fbx")

        result = self.run_export(make_rlpy(write_file))
        self.assertTrue(result["success"], result)


TEXTURE_FLAG = 1 << 20
TEXTURE_SIZES = {
    "EExportTextureSize_Original": "size-original",
    "EExportTextureSize_Size_2048": "size-2048",
    "EExportTextureSize_Size_4096": "size-4096",
}


def write_fbx(avatar, path, *rest):
    with open(path, "wb") as f:
        f.write(b"fbx")
    return FakeStatus(False)


class ExportFbxTextureTests(unittest.TestCase):
    """UE exports must carry the skin/hair detail maps (10-25: v58b/v59/Ariana lost
    roughness, SSS, micro-normal and wrinkle maps and were capped at 2048)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = os.path.join(self._tmp.name, "ue", "char.fbx")
        patch = mock.patch.object(cc5_api, "get_first_avatar", return_value=object())
        patch.start()
        self.addCleanup(patch.stop)
        self.rlpy = make_rlpy(write_fbx)
        self.rlpy.EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory = TEXTURE_FLAG
        for name, value in TEXTURE_SIZES.items():
            setattr(self.rlpy, name, value)
        self.setting = self.rlpy.RExportFbxSetting.return_value

    def run_export(self, **kwargs) -> dict:
        with mock.patch.object(cc5_api, "RLPy", self.rlpy):
            return cc5_api.export_fbx(self.out, export_motion=False, sub_d_level=0, **kwargs)

    def test_ue5_preset_writes_all_textures_as_image_files(self) -> None:
        result = self.run_export(target_tool="UE5")
        self.assertTrue(result["success"], result)
        flags = self.setting.SetOption.call_args.args[0]
        self.assertTrue(flags & TEXTURE_FLAG)

    def test_ue5_preset_keeps_original_texture_size_by_default(self) -> None:
        result = self.run_export(target_tool="UE5")
        self.setting.SetTextureSize.assert_called_once_with("size-original")
        self.assertEqual(result["texture_size"], 0)

    def test_texture_size_is_passed_as_the_cc5_enum(self) -> None:
        result = self.run_export(target_tool="UE5", texture_size=4096)
        self.setting.SetTextureSize.assert_called_once_with("size-4096")
        self.assertEqual(result["texture_size"], 4096)

    def test_unsupported_texture_size_is_reported_not_applied(self) -> None:
        result = self.run_export(target_tool="UE5", texture_size=3000)
        self.setting.SetTextureSize.assert_not_called()
        self.assertNotIn("texture_size", result)
        self.assertTrue(any("3000" in n for n in result["notes"]))

    def test_default_preset_leaves_texture_size_alone(self) -> None:
        self.run_export(target_tool="Default")
        self.setting.SetTextureSize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
