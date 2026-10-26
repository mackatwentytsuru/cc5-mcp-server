"""
cc5_ui: window reading, the answers we allow, jobs, waiting, widget finder, framed capture.

Runs outside CC5 with a fake Qt (tests/python/fake_qt.py); RLPy is a MagicMock.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import unittest
from unittest import mock


from ui_support import UiTestCase, cc5_api, cc5_ui, fake_qt  # noqa: E402


class TextHelpersTest(unittest.TestCase):
    def test_clean_text_strips_tags_and_spaces(self) -> None:
        self.assertEqual(cc5_ui.clean_text("<p>Add a new layer\n or  <b>replace</b>?</p>"), "Add a new layer or replace ?")

    def test_clean_text_keeps_plain_less_than(self) -> None:
        self.assertEqual(cc5_ui.clean_text("size < 5 and > 2"), "size < 5 and > 2")

    def test_forbidden_words_are_found(self) -> None:
        for text in ("Software License", "Please purchase", "Login required", "Terms and Conditions",
                     "Update available", "Activate your serial", "trial content"):
            self.assertIsNotNone(cc5_ui.forbidden_reason(text), text)

    def test_normal_questions_are_not_forbidden(self) -> None:
        self.assertIsNone(cc5_ui.forbidden_reason("Apply Eyelash Elements", "Restore neutral lash strip"))
        self.assertIsNone(cc5_ui.forbidden_reason("", "Would you like to exit SkinGen editing mode ?"))


class WindowScanTest(UiTestCase):
    def test_lists_visible_dialogs_only(self) -> None:
        self.dialog("Apply Eyelash Elements", "Apply the eyelash?", ["&Apply", "Cancel"],
                    [("Restore neutral lash strip", False)])
        self.dialog("Hidden", "never shown", ["OK"]).hidden = True
        gone = self.dialog("Closed", "x", ["OK"])
        gone._visible = False
        main = fake_qt.MainWindow(title="Character Creator", visible=True)
        self.q.app.tops.append(main)
        self.q.app.tops.append(fake_qt.Menu(visible=True))
        found = cc5_ui.scan_windows()
        titles = [info["title"] for info, _w in found]
        self.assertEqual(titles, ["Apply Eyelash Elements", "Hidden"])

    def test_describe_reads_buttons_checkboxes_and_progress(self) -> None:
        dlg = self.dialog("Apply Eyelash Elements", "Apply the eyelash?", ["&Apply", "Cancel"],
                          [("Restore neutral lash strip", True)])
        info = cc5_ui.describe_window(dlg, self.q)
        self.assertEqual(info["buttons"], ["Apply", "Cancel"])
        self.assertEqual(info["checkboxes"], [{"text": "Restore neutral lash strip", "checked": True}])
        self.assertFalse(info["progress"])
        self.assertIsNone(info["needs_human"])
        bake = cc5_ui.describe_window(self.dialog("Baking", "Please wait", []), self.q)
        self.assertTrue(bake["progress"])

    def test_progress_bar_marks_progress(self) -> None:
        dlg = self.dialog("Working", "texture", [])
        fake_qt.ProgressBar(parent=dlg)
        self.assertTrue(cc5_ui.describe_window(dlg, self.q)["progress"])

    def test_license_window_needs_a_person(self) -> None:
        info = cc5_ui.describe_window(self.dialog("License", "Your license has expired", ["OK"]), self.q)
        self.assertEqual(info["needs_human"], "license")

    def test_other_windows_only_when_asked(self) -> None:
        tool = fake_qt.Widget(title="Floating Panel", visible=True)
        self.q.app.tops.append(tool)
        self.assertEqual(cc5_ui.scan_windows(), [])
        self.assertEqual([i["title"] for i, _w in cc5_ui.scan_windows(include_other=True)], ["Floating Panel"])


class DecideTest(UiTestCase):
    def info(self, title: str, text: str, buttons: list[str]) -> dict:
        return {"title": title, "text": text, "buttons": buttons}

    def test_apply_windows_press_apply_and_tick_the_lash_box(self) -> None:
        choices = cc5_ui.normalize_choices()
        for title in ("Apply Character Preset", "Apply Eyelash Elements"):
            d = cc5_ui.decide(self.info(title, "options", ["Apply", "Cancel"]), choices)
            self.assertEqual(d["press"], "apply")
            self.assertEqual(d["ticks"], [("neutral lash", True)])

    def test_restore_lash_can_be_turned_off(self) -> None:
        choices = cc5_ui.normalize_choices({"restore_neutral_lash": False})
        d = cc5_ui.decide(self.info("Apply Character Preset", "", ["Apply"]), choices)
        self.assertEqual(d["ticks"], [("neutral lash", False)])

    def test_layer_question_defaults_to_replace_and_can_be_add(self) -> None:
        text = "Do you want to add a new layer or replace the current layer?"
        buttons = ["Add", "Replace", "Cancel"]
        d = cc5_ui.decide(self.info("SkinGen", text, buttons), cc5_ui.normalize_choices())
        self.assertEqual(d["press"], "replace")
        d = cc5_ui.decide(self.info("SkinGen", text, buttons), cc5_ui.normalize_choices({"layer_choice": "add"}))
        self.assertEqual(d["press"], "add")

    def test_skingen_exit_yes_or_no(self) -> None:
        info = self.info("", "Would you like to exit SkinGen editing mode ?", ["Yes", "No"])
        self.assertEqual(cc5_ui.decide(info, cc5_ui.normalize_choices())["press"], "yes")
        self.assertEqual(cc5_ui.decide(info, cc5_ui.normalize_choices({"skingen_exit": "no"}))["press"], "no")

    def test_unknown_window_is_left_alone(self) -> None:
        self.assertIsNone(cc5_ui.decide(self.info("Delete", "Delete this layer?", ["Yes", "No"]), cc5_ui.normalize_choices()))
        self.assertIsNone(cc5_ui.decide(self.info("Save", "Save changes?", ["Yes", "No"]), cc5_ui.normalize_choices()))

    def test_rule_window_that_mentions_a_license_is_blocked(self) -> None:
        d = cc5_ui.decide(self.info("Apply License Update", "Apply", ["Apply"]), cc5_ui.normalize_choices())
        self.assertIn("blocked", d)
        self.assertNotIn("press", d)

    def test_missing_button_is_blocked_not_guessed(self) -> None:
        info = self.info("SkinGen", "add a new layer or replace the current layer?", ["Add", "Cancel"])
        self.assertIn("blocked", cc5_ui.decide(info, cc5_ui.normalize_choices()))


class ChoicesTest(unittest.TestCase):
    def test_defaults(self) -> None:
        self.assertEqual(cc5_ui.normalize_choices(),
                         {"layer_choice": "replace", "skingen_exit": "yes", "restore_neutral_lash": True})

    def test_bad_values_and_keys_are_refused(self) -> None:
        for bad in ({"layer_choice": "cancel"}, {"skingen_exit": "maybe"}, {"restore_neutral_lash": "yes"},
                    {"press_anything": "ok"}):
            with self.assertRaises(ValueError):
                cc5_ui.normalize_choices(bad)

    def test_values_are_lowercased(self) -> None:
        self.assertEqual(cc5_ui.normalize_choices({"layer_choice": " Add "})["layer_choice"], "add")


class AnswererTest(UiTestCase):
    def test_presses_apply_and_ticks_the_box(self) -> None:
        dlg = self.dialog("Apply Eyelash Elements", "Apply?", ["Apply", "Cancel"], [("Restore neutral lash strip", False)])
        apply_btn = dlg.findChildren(self.q.QPushButton)[0]
        apply_btn.on_click = lambda: setattr(dlg, "_visible", False)
        ans = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        ans._timer.fire()
        self.assertEqual(apply_btn.clicks, 1)
        self.assertTrue(dlg.findChildren(self.q.QCheckBox)[0].isChecked())
        log = ans.stop()
        self.assertEqual([e["pressed"] for e in log], ["apply"])
        self.assertIsNone(ans._timer)

    def test_never_presses_a_license_window(self) -> None:
        dlg = self.dialog("Apply License", "Apply your license key", ["Apply"])
        ans = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        ans._timer.fire()
        self.assertEqual(dlg.findChildren(self.q.QPushButton)[0].clicks, 0)
        self.assertEqual(len(ans.blocked), 1)

    def test_other_questions_are_not_touched(self) -> None:
        dlg = self.dialog("Delete", "Delete all layers?", ["Yes", "No"])
        ans = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        ans._timer.fire()
        self.assertEqual([b.clicks for b in dlg.findChildren(self.q.QPushButton)], [0, 0])

    def test_one_window_is_pressed_at_most_three_times(self) -> None:
        dlg = self.dialog("Apply Character Preset", "x", ["Apply"])      # never closes
        ans = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        for _ in range(6):
            ans._timer.fire()
        self.assertEqual(dlg.findChildren(self.q.QPushButton)[0].clicks, cc5_ui.MAX_PRESSES_PER_WINDOW)

    def test_stops_itself_after_the_time_limit(self) -> None:
        ans = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        fake_qt.Timer.clock[0] += cc5_ui.ANSWERER_MAX_SECONDS + 1
        ans._timer.fire()
        self.assertIsNone(ans._timer)

    def test_a_new_answerer_replaces_the_old_one(self) -> None:
        first = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        second = cc5_ui.WindowAnswerer(cc5_ui.normalize_choices()).start()
        self.assertIsNone(first._timer)
        self.assertIsNotNone(second._timer)
        second.stop()
        self.assertIsNone(getattr(cc5_ui._holder(), "_cc5_ui_answerer", None))


class JobTest(UiTestCase):
    def test_plain_function_job(self) -> None:
        started = cc5_ui.start_job("t", lambda p: {"success": True, "n": p["n"]}, {"n": 7})
        self.assertTrue(started["success"])
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["state"], "queued")
        fake_qt.drain()
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        self.assertEqual((job["state"], job["result"]["n"]), ("done", 7))

    def test_generator_job_waits_between_steps(self) -> None:
        def make(_p):
            yield 500
            yield 250
            return {"success": True, "steps": 2}
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain(1)                                   # begin: first step runs, one wait pending
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["state"], "running")
        self.assertEqual(fake_qt.Timer.pending_ms(), [500])
        fake_qt.drain()
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["result"], {"success": True, "steps": 2})

    def test_failures_are_stored_not_raised(self) -> None:
        def boom(_p):
            raise RuntimeError("no widget")
        started = cc5_ui.start_job("t", boom, {})
        fake_qt.drain()
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        self.assertEqual(job["state"], "failed")
        self.assertIn("no widget", job["result"]["error"])

    def test_failure_in_a_later_step(self) -> None:
        def make(_p):
            yield 10
            raise ValueError("bad second step")
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain()
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["state"], "failed")

    def test_only_one_job_at_a_time(self) -> None:
        first = cc5_ui.start_job("a", lambda p: {"success": True}, {})
        second = cc5_ui.start_job("b", lambda p: {"success": True}, {})
        self.assertFalse(second["success"])
        self.assertIn(first["job_id"], second["error"])
        fake_qt.drain()
        self.assertTrue(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])

    def test_a_stale_running_job_no_longer_blocks(self) -> None:
        cc5_ui.start_job("a", lambda p: {"success": True}, {})
        fake_qt.Timer.clock[0] += cc5_ui.JOB_STALE_SECONDS + 1
        self.assertTrue(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])

    def test_unknown_job(self) -> None:
        res = cc5_ui.ui_job({"job_id": "nope"})
        self.assertFalse(res["success"])

    def test_old_jobs_are_pruned(self) -> None:
        for _ in range(cc5_ui.JOB_KEEP + 5):
            cc5_ui.start_job("t", lambda p: {"success": True}, {})
            fake_qt.drain()
        self.assertEqual(len(cc5_ui._jobs()), cc5_ui.JOB_KEEP)

    def test_running_job_reports_open_windows(self) -> None:
        self.dialog("Mystery", "Who knows", ["OK"])
        def make(_p):
            yield 1000
            return {"success": True}
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain(1)
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        self.assertEqual(job["windows"][0]["title"], "Mystery")


class SettleTest(UiTestCase):
    def test_quiet_after_two_empty_polls(self) -> None:
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))
        self.assertTrue(result["ok"])

    def test_progress_windows_are_waited_out(self) -> None:
        bake = self.dialog("Baking", "Please wait", [])

        def on_step(n: int) -> None:
            if n == 4:
                bake._visible = False
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()), on_step)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["waited_s"], 5)

    def test_a_question_we_answer_is_waited_out(self) -> None:
        ask = self.dialog("Apply Character Preset", "x", ["Apply"])

        def on_step(n: int) -> None:
            if n == 2:
                ask._visible = False
        self.assertTrue(self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()), on_step)["ok"])

    def test_an_unknown_window_stops_the_wait_after_the_grace_time(self) -> None:
        self.dialog("Delete", "Delete all layers?", ["Yes", "No"])
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))
        self.assertFalse(result["ok"])
        self.assertEqual(result["blocked_by"]["title"], "Delete")
        self.assertGreaterEqual(result["waited_s"], 4)

    def test_a_license_window_stops_the_wait_at_once(self) -> None:
        self.dialog("License", "License expired", ["OK"])
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))
        self.assertFalse(result["ok"])
        self.assertEqual(result["waited_s"], 0)

    def test_gives_up_at_the_limit(self) -> None:
        self.dialog("Baking", "Please wait", [])
        result = self.run_steps(cc5_ui.settle_steps(10, cc5_ui.normalize_choices()))
        self.assertTrue(result["timeout"])

    def test_extra_condition_must_hold(self) -> None:
        flag = {"ok": False}

        def on_step(n: int) -> None:
            flag["ok"] = n >= 3
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices(), extra_ok=lambda: flag["ok"]), on_step)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["waited_s"], 3)


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
        self.assertFalse(cc5_ui.ui_widgets({})["success"])

    def test_by_object_name_visible_only(self) -> None:
        res = cc5_ui.ui_widgets({"object_name": "qtSpinBox"})
        self.assertEqual((res["count"], res["widgets"][0]["value"]), (1, 40))
        self.assertIn("MixSubstancePanel", res["widgets"][0]["path"])

    def test_include_hidden(self) -> None:
        self.assertEqual(cc5_ui.ui_widgets({"object_name": "qtSpinBox", "visible_only": False})["count"], 2)

    def test_by_text_class_and_ancestor(self) -> None:
        self.assertEqual(cc5_ui.ui_widgets({"text_contains": "activate"})["widgets"][0]["object_name"],
                         "qtModeSwitchPushButton")
        self.assertEqual(cc5_ui.ui_widgets({"class_name": "SpinBox", "ancestor": "MixSubstancePanel"})["count"], 1)
        self.assertEqual(cc5_ui.ui_widgets({"name_contains": "switch"})["count"], 1)

    def test_limit(self) -> None:
        res = cc5_ui.ui_widgets({"class_name": "Widget", "visible_only": False, "limit": 1})
        self.assertEqual(res["shown"], 1)
        self.assertGreater(res["count"], 1)


class WindowsRouteTest(UiTestCase):
    def test_reports_windows_and_what_would_be_answered(self) -> None:
        self.dialog("Apply Character Preset", "Apply?", ["Apply", "Cancel"])
        self.dialog("Delete", "Delete?", ["Yes", "No"])
        res = cc5_ui.ui_windows({})
        self.assertEqual(res["count"], 2)
        self.assertEqual(res["windows"][0]["answerable_as"], "apply_preset")
        self.assertIsNone(res["windows"][1]["answerable_as"])
        self.assertNotIn("png_base64", res["windows"][0])

    def test_screenshot_returns_png(self) -> None:
        dlg = self.dialog("Mystery", "?", ["OK"])
        res = cc5_ui.ui_windows({"screenshot": True, "max_width": 200})
        self.assertEqual(dlg.grabbed, 1)
        self.assertTrue(res["windows"][0]["png_base64"])
        self.assertEqual(res["windows"][0]["png_size"][0], 200)

    def test_main_window_target(self) -> None:
        main = fake_qt.MainWindow(title="Character Creator 5", visible=True)
        self.q.app.tops.append(main)
        res = cc5_ui.ui_windows({"target": "main", "screenshot": True})
        self.assertEqual(res["main_window"]["title"], "Character Creator 5")
        self.assertIn("png_base64", res["main_window"])
        self.assertEqual(res["count"], 0)


class CaptureCropTest(UiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.api = mock.Mock()
        self.api.frame_camera.return_value = {"success": True}
        self.api.capture_viewport.return_value = {"success": True, "path": "full"}
        self.api._validate_path.side_effect = cc5_api._validate_path
        patcher = mock.patch.object(cc5_ui, "_api", return_value=self.api)
        patcher.start()
        self.addCleanup(patcher.stop)
        fake_qt.Image.files["D:/t/full.png"] = (3600, 3600)

    def run_crop(self, **body):
        body.setdefault("full_path", "D:/t/full.png")
        body.setdefault("output_path", "D:/t/crop.png")
        started = cc5_ui.ui_capture_crop(body)
        self.assertTrue(started["success"], started)
        fake_qt.drain()
        return cc5_ui.ui_job({"job_id": started["job_id"]})["result"]

    def test_crops_a_pixel_box(self) -> None:
        res = self.run_crop(crop=[1230, 1610, 2190, 1930])
        self.assertTrue(res["success"], res)
        self.assertEqual(res["crop_size"], [960, 320])
        self.assertEqual(fake_qt.Image.saved["D:/t/crop.png"], (960, 320))
        self.assertTrue(res["png_base64"])
        self.api.capture_viewport.assert_called_once_with("D:/t/full.png", 3600, 3600)
        self.api.frame_camera.assert_called_once_with("face")

    def test_crops_a_fraction_box(self) -> None:
        res = self.run_crop(crop_fraction=[0.25, 0.25, 0.75, 0.5])
        self.assertEqual(res["crop_box"], [900, 900, 2700, 1800])

    def test_waits_after_framing_before_rendering(self) -> None:
        cc5_ui.ui_capture_crop({"full_path": "D:/t/full.png", "output_path": "D:/t/crop.png", "settle_ms": 1200})
        fake_qt.drain(1)
        self.assertEqual(fake_qt.Timer.pending_ms(), [1200])
        self.api.capture_viewport.assert_not_called()

    def test_without_a_box_returns_the_full_render_only(self) -> None:
        res = self.run_crop()
        self.assertTrue(res["success"])
        self.assertNotIn("crop_path", res)
        self.assertEqual(res["render_size"], [3600, 3600])

    def test_box_outside_the_render_is_an_error(self) -> None:
        res = self.run_crop(crop=[5000, 5000, 6000, 6000])
        self.assertFalse(res["success"])

    def test_window_screenshot_fallback_is_refused(self) -> None:
        self.api.capture_viewport.return_value = {"success": True, "path": "x", "fallback": "window_screenshot"}
        res = self.run_crop(crop=[0, 0, 100, 100])
        self.assertFalse(res["success"])
        self.assertIn("not be comparable", res["error"])

    def test_capture_failure_is_reported(self) -> None:
        self.api.capture_viewport.return_value = {"success": False, "error": "RenderImage did not create file"}
        self.assertIn("RenderImage", self.run_crop(crop=[0, 0, 10, 10])["error"])

    def test_bad_arguments_are_refused_before_a_job_starts(self) -> None:
        self.assertFalse(cc5_ui.ui_capture_crop({"output_path": "D:/t/x.jpg"})["success"])
        self.assertFalse(cc5_ui.ui_capture_crop({"output_path": "D:/../x.png"})["success"])
        self.assertFalse(cc5_ui.ui_capture_crop({"crop": [1, 2, 3]})["success"])

    def test_size_is_clamped(self) -> None:
        cc5_ui.ui_capture_crop({"size": 99999, "full_path": "D:/t/full.png", "output_path": "D:/t/crop.png"})
        fake_qt.drain()
        self.assertEqual(self.api.capture_viewport.call_args.args[1], 8192)

    def test_render_of_another_size_is_flagged(self) -> None:
        fake_qt.Image.files["D:/t/full.png"] = (1280, 1280)
        self.assertIn("warning", self.run_crop())


class CropBoxTest(unittest.TestCase):
    def test_box_is_ordered_and_clamped(self) -> None:
        self.assertEqual(cc5_ui._crop_box({"crop": [900, 700, -5, 10]}, 1000, 800), (0, 10, 900, 700))

    def test_too_small_box_is_none(self) -> None:
        self.assertIsNone(cc5_ui._crop_box({"crop": [10, 10, 11, 11]}, 100, 100))


class RoutesTest(unittest.TestCase):
    def test_every_route_points_at_a_function(self) -> None:
        for path, (action, fn) in cc5_ui.ROUTES.items():
            self.assertTrue(path.startswith("/ui/"))
            self.assertTrue(action.startswith("ui_"))
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main()
