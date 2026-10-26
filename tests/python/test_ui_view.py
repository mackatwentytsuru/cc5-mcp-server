"""
cc5_uiview: window list with pictures, the read-only widget finder, and the framed capture.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from ui_support import UiTestCase, cc5_api, cc5_ui, fake_qt

import cc5_uiview  # noqa: E402
import RLPy  # noqa: E402  (the MagicMock stand-in)


class WidgetFinderTest(UiTestCase):
    def setUp(self) -> None:
        super().setUp()
        root = fake_qt.Widget(name="qtAttributeRootTab", visible=True)
        panel = fake_qt.Widget(name="MixSubstancePanel", parent=root, visible=True)
        self.spin = fake_qt.SpinBox(panel, name="qtSpinBox", value=40)
        self.hidden = fake_qt.SpinBox(root, name="qtSpinBox", value=1)
        self.hidden._visible = False
        self.button = fake_qt.PushButton("Activate Editor", panel, name="qtModeSwitchPushButton")

    def test_needs_a_filter(self) -> None:
        self.assertFalse(cc5_uiview.ui_widgets({})["success"])

    def test_by_object_name_visible_only(self) -> None:
        res = cc5_uiview.ui_widgets({"object_name": "qtSpinBox"})
        self.assertEqual((res["count"], res["widgets"][0]["value"]), (1, 40))
        self.assertIn("MixSubstancePanel", res["widgets"][0]["path"])

    def test_include_hidden(self) -> None:
        self.assertEqual(cc5_uiview.ui_widgets({"object_name": "qtSpinBox", "visible_only": False})["count"], 2)

    def test_by_text_class_and_ancestor(self) -> None:
        self.assertEqual(cc5_uiview.ui_widgets({"text_contains": "activate"})["widgets"][0]["object_name"],
                         "qtModeSwitchPushButton")
        self.assertEqual(cc5_uiview.ui_widgets({"class_name": "SpinBox", "ancestor": "MixSubstancePanel"})["count"], 1)
        self.assertEqual(cc5_uiview.ui_widgets({"name_contains": "switch"})["count"], 1)

    def test_limit(self) -> None:
        res = cc5_uiview.ui_widgets({"class_name": "Widget", "visible_only": False, "limit": 1})
        self.assertEqual(res["shown"], 1)
        self.assertGreater(res["count"], 1)

    def test_a_password_field_never_gives_its_text(self) -> None:
        root = fake_qt.Widget(name="login", visible=True)
        fake_qt.LineEdit(root, text="hunter2", echo=fake_qt.LineEdit.Password, name="qtPassword")
        fake_qt.LineEdit(root, text="visible text", name="qtUser")
        secret = cc5_uiview.ui_widgets({"object_name": "qtPassword"})["widgets"][0]
        self.assertNotIn("text", secret)
        self.assertTrue(secret["secret"])
        self.assertEqual(cc5_uiview.ui_widgets({"object_name": "qtUser"})["widgets"][0]["text"], "visible text")


class WindowsRouteTest(UiTestCase):
    def test_reports_windows_and_what_would_be_answered(self) -> None:
        self.dialog("Apply Character Preset", "Apply?", ["Apply", "Cancel"])
        self.dialog("Delete", "Delete?", ["Yes", "No"])
        res = cc5_uiview.ui_windows({})
        self.assertEqual(res["count"], 2)
        self.assertEqual(res["windows"][0]["answerable_as"], "apply_preset")
        self.assertIsNone(res["windows"][1]["answerable_as"])
        self.assertNotIn("png_base64", res["windows"][0])
        self.assertNotIn("_full", res["windows"][0])

    def test_a_blocked_rule_window_says_why(self) -> None:
        self.dialog("Apply Character Preset", "Apply (license check)", ["Apply"])
        res = cc5_uiview.ui_windows({})
        self.assertIsNone(res["windows"][0]["answerable_as"])
        self.assertIn("a person must decide", res["windows"][0]["blocked_reason"])
        self.assertEqual(res["windows"][0]["needs_human"], "licen")

    def test_screenshot_returns_png(self) -> None:
        dlg = self.dialog("Mystery", "?", ["OK"])
        res = cc5_uiview.ui_windows({"screenshot": True, "max_width": 200})
        self.assertEqual(dlg.grabbed, 1)
        self.assertTrue(res["windows"][0]["png_base64"])
        self.assertEqual(res["windows"][0]["png_size"][0], 200)

    def test_main_window_target(self) -> None:
        self.q.app.tops.append(fake_qt.MainWindow(title="Character Creator 5", visible=True))
        res = cc5_uiview.ui_windows({"target": "main", "screenshot": True})
        self.assertEqual(res["main_window"]["title"], "Character Creator 5")
        self.assertIn("png_base64", res["main_window"])
        self.assertEqual(res["count"], 0)

    def test_routes(self) -> None:
        self.assertEqual(set(cc5_uiview.ROUTES), {"/ui/windows", "/ui/widgets", "/ui/capture_crop"})


class CaptureCropTest(UiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.full = os.path.join(self.dir.name, "full.png").replace("\\", "/")
        self.out = os.path.join(self.dir.name, "crop.png").replace("\\", "/")
        self.api = mock.Mock()
        self.api.frame_camera.return_value = {"success": True}
        self.api.capture_viewport.return_value = {"success": True, "path": self.full}
        self.api._validate_path.side_effect = cc5_api._validate_path
        self.avatar = mock.Mock()
        self.avatar.GetName.return_value = "Beyon"
        for patcher in (mock.patch.object(cc5_ui, "_api", return_value=self.api),
                        mock.patch.object(RLPy.RScene, "GetAvatars", return_value=[self.avatar])):
            patcher.start()
            self.addCleanup(patcher.stop)
        RLPy.RScene.SelectObject.reset_mock()
        fake_qt.Image.files[self.full] = (3600, 3600)

    def run_crop(self, **body):
        body.setdefault("full_path", self.full)
        body.setdefault("output_path", self.out)
        return self.finish(cc5_uiview.ui_capture_crop(body))

    def test_crops_a_pixel_box(self) -> None:
        res = self.run_crop(crop=[1230, 1610, 2190, 1930])
        self.assertTrue(res["success"], res)
        self.assertEqual(res["crop_size"], [960, 320])
        self.assertEqual(fake_qt.Image.saved[self.out], (960, 320))
        self.assertTrue(res["png_base64"])
        self.api.capture_viewport.assert_called_once_with(self.full, 3600, 3600)
        self.api.frame_camera.assert_called_once_with("face")

    def test_selects_the_avatar_before_framing(self) -> None:
        order = []
        RLPy.RScene.SelectObject.side_effect = lambda a: order.append("select")
        self.api.frame_camera.side_effect = lambda v: order.append("frame") or {"success": True}
        self.run_crop(crop=[0, 0, 100, 100])
        RLPy.RScene.SelectObject.side_effect = None
        self.assertEqual(order[:2], ["select", "frame"])

    def test_crops_a_fraction_box(self) -> None:
        res = self.run_crop(crop_fraction=[0.25, 0.25, 0.75, 0.5])
        self.assertEqual(res["crop_box"], [900, 900, 2700, 1800])

    def test_waits_after_framing_before_rendering(self) -> None:
        cc5_uiview.ui_capture_crop({"full_path": self.full, "output_path": self.out, "settle_ms": 1200})
        fake_qt.drain(1)
        self.assertEqual(fake_qt.Timer.pending_ms(), [1200])
        self.api.capture_viewport.assert_not_called()

    def test_without_a_box_returns_a_preview_to_measure_on(self) -> None:
        res = self.run_crop()
        self.assertTrue(res["success"])
        self.assertNotIn("crop_path", res)
        self.assertEqual(res["render_size"], [3600, 3600])
        self.assertEqual(res["preview_size"], [cc5_uiview.PREVIEW_WIDTH, cc5_uiview.PREVIEW_WIDTH])
        self.assertAlmostEqual(res["preview_scale"], 3600 / cc5_uiview.PREVIEW_WIDTH, places=3)
        self.assertTrue(res["png_base64"])

    def test_box_outside_the_render_is_an_error(self) -> None:
        self.assertFalse(self.run_crop(crop=[5000, 5000, 6000, 6000])["success"])

    def test_window_screenshot_fallback_is_refused(self) -> None:
        self.api.capture_viewport.return_value = {"success": True, "path": "x", "fallback": "window_screenshot"}
        res = self.run_crop(crop=[0, 0, 100, 100])
        self.assertFalse(res["success"])
        self.assertIn("not be comparable", res["error"])

    def test_capture_failure_is_reported(self) -> None:
        self.api.capture_viewport.return_value = {"success": False, "error": "RenderImage did not create file"}
        self.assertIn("RenderImage", self.run_crop(crop=[0, 0, 10, 10])["error"])

    def test_bad_arguments_are_refused_before_a_job_starts(self) -> None:
        bad = [
            {"output_path": os.path.join(self.dir.name, "x.jpg")},
            {"output_path": "D:/../x.png"},
            {"output_path": "//server/share/x.png"},
            {"crop": [1, 2, 3]},
            {"crop": [1, 2, 3, "x"]},
            {"crop": [0, 0, 10, 10], "crop_fraction": [0, 0, 1, 1]},
            {"crop_fraction": [0.5, 0.5, 0.2, 0.9]},
            {"crop_fraction": [0, 0, 2, 1]},
            {"output_path": self.full},
        ]
        for body in bad:
            body = {"full_path": self.full, "output_path": self.out, **body}
            self.assertFalse(cc5_uiview.ui_capture_crop(body)["success"], body)
        self.assertEqual(fake_qt.Timer.singles, [])

    def test_an_existing_file_is_not_replaced_without_overwrite(self) -> None:
        with open(self.out, "wb") as fh:
            fh.write(b"precious")
        res = cc5_uiview.ui_capture_crop({"full_path": self.full, "output_path": self.out})
        self.assertFalse(res["success"])
        self.assertIn("overwrite=true", res["error"])
        self.assertTrue(cc5_uiview.ui_capture_crop({"full_path": self.full, "output_path": self.out, "overwrite": True})["success"])

    def test_default_names_are_new_every_time(self) -> None:
        a, b = {}, {}
        cc5_uiview._png_target(a, "output_path", "cc5_framed_crop", False)
        cc5_uiview._png_target(b, "output_path", "cc5_framed_crop", False)
        self.assertNotEqual(a["output_path"], b["output_path"])

    def test_output_folders_are_created(self) -> None:
        deep = os.path.join(self.dir.name, "a", "b", "crop.png").replace("\\", "/")
        self.run_crop(crop=[0, 0, 100, 100], output_path=deep)
        self.assertTrue(os.path.isdir(os.path.dirname(deep)))

    def test_size_is_clamped(self) -> None:
        cc5_uiview.ui_capture_crop({"size": 99999, "full_path": self.full, "output_path": self.out})
        fake_qt.drain()
        self.assertEqual(self.api.capture_viewport.call_args.args[1], cc5_uiview.MAX_RENDER_SIZE)

    def test_render_of_another_size_is_flagged(self) -> None:
        fake_qt.Image.files[self.full] = (1280, 1280)
        self.assertIn("warning", self.run_crop())


class CropBoxTest(unittest.TestCase):
    def test_box_is_ordered_and_clamped(self) -> None:
        self.assertEqual(cc5_uiview.crop_box({"crop": [900, 700, -5, 10]}, 1000, 800), (0, 10, 900, 700))

    def test_too_small_box_is_none(self) -> None:
        self.assertIsNone(cc5_uiview.crop_box({"crop": [10, 10, 11, 11]}, 100, 100))


if __name__ == "__main__":
    unittest.main()
