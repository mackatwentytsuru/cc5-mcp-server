"""
cc5_ui core: the safety word list, window reading, the answers we allow, the answerer timer, jobs,
the job guard, waiting for CC5 to be quiet, path checks and widget lookup.

Runs outside CC5 with a fake Qt (tests/python/fake_qt.py); RLPy is a MagicMock.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from ui_support import UiTestCase, cc5_ui, fake_qt


class ForbiddenWordsTest(unittest.TestCase):
    def test_plain_words(self) -> None:
        for text in ("Software License", "Please purchase", "Login required", "Terms and Conditions",
                     "Update available", "Activate your serial", "trial content", "Sign-in", "Log-in",
                     "Licensing", "Deactivate this PC", "Unsubscribe", "Enter your password"):
            self.assertIsNotNone(cc5_ui.forbidden_reason(text), text)

    def test_disguised_words(self) -> None:
        for text in ("LİCENSE", "LOGİN", "TRİAL", "Lic\u00adense", "Ｌｉｃｅｎｓｅ", "Lic ense", "Lic<b>ense</b>"):
            self.assertIsNotNone(cc5_ui.forbidden_reason(cc5_ui.clean_text(text)), text)
        self.assertIsNotNone(cc5_ui.forbidden_reason("unlicensed copy"))

    def test_japanese_words(self) -> None:
        for text in ("ライセンスが切れています", "ログインしてください", "購入しますか", "利用規約に同意", "アップデート"):
            self.assertIsNotNone(cc5_ui.forbidden_reason(text), text)

    def test_the_windows_we_answer_are_not_forbidden(self) -> None:
        for text in ("Apply Character Preset", "Apply Eyelash Elements Restore neutral lash strip",
                     "Would you like to exit SkinGen editing mode ?",
                     "Do you want to add a new layer or replace the current layer?",
                     "Baking textures Please wait", "Industrial_Lip Tutorial"):
            self.assertIsNone(cc5_ui.forbidden_reason(text), text)

    def test_clean_text(self) -> None:
        self.assertEqual(cc5_ui.clean_text("<p>Add a new layer\n or  <b>replace</b>?</p>"), "Add a new layer or replace ?")
        self.assertEqual(cc5_ui.clean_text("size < 5 and > 2"), "size < 5 and > 2")


class PathProblemTest(UiTestCase):
    def test_refuses_traversal_unc_streams_and_wrong_extensions(self) -> None:
        for path in ("C:/a/../b.png", "//server/share/a.png", "\\\\server\\share\\a.png", "C:/a/b.png:stream",
                     "a:b/c.png", "", "C:/a/b.jpg", "C:/a/b\x00.png"):
            self.assertIsNotNone(cc5_ui.path_problem(path, {".png"}), repr(path))

    def test_accepts_normal_paths(self) -> None:
        for path in ("C:/work/a.png", "C:\\work\\a.PNG", "D:/x y/ä.png", "/tmp/a.png", "relative/a.png"):
            self.assertIsNone(cc5_ui.path_problem(path, {".png"}), path)


class WindowScanTest(UiTestCase):
    def test_lists_visible_dialogs_only(self) -> None:
        self.dialog("Apply Eyelash Elements", "Apply the eyelash?", ["&Apply", "Cancel"],
                    [("Restore neutral lash strip", False)])
        gone = self.dialog("Closed", "x", ["OK"])
        gone._visible = False
        self.q.app.tops.append(fake_qt.MainWindow(title="Character Creator", visible=True))
        self.q.app.tops.append(fake_qt.Menu(visible=True))
        self.assertEqual([i["title"] for i, _w in cc5_ui.scan_windows()], ["Apply Eyelash Elements"])

    def test_empty_frames_are_ignored(self) -> None:
        self.dialog("Frame", "", [])
        self.assertEqual(cc5_ui.scan_windows(), [])

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

    def test_license_text_anywhere_in_the_window_needs_a_person(self) -> None:
        for build in (
            lambda d: fake_qt.Label("Your license has expired", d),                     # a label
            lambda d: fake_qt.PushButton("Buy now", d),                                  # a button
            lambda d: fake_qt.CheckBox("I agree to the terms", d),                       # a check box
            lambda d: fake_qt.TextEdit(d, "END USER LICENSE AGREEMENT ..."),             # a text box
            lambda d: fake_qt.GroupBox("Account login", d),                              # a group title
        ):
            dlg = fake_qt.Dialog(title="Apply Character Preset", visible=True)
            fake_qt.Label("Apply the preset?", dlg)
            fake_qt.PushButton("Apply", dlg)
            build(dlg)
            self.assertIsNotNone(cc5_ui.describe_window(dlg, self.q)["needs_human"])

    def test_password_fields_and_long_documents_need_a_person(self) -> None:
        dlg = fake_qt.Dialog(title="Hello", visible=True)
        fake_qt.LineEdit(dlg, echo=fake_qt.LineEdit.Password)
        self.assertEqual(cc5_ui.describe_window(dlg, self.q)["needs_human"], "password field")
        dlg = fake_qt.Dialog(title="Hello", visible=True)
        fake_qt.TextEdit(dlg, "lorem ipsum " * 100)
        self.assertIn("long text", cc5_ui.describe_window(dlg, self.q)["needs_human"])

    def test_a_licence_window_is_never_a_progress_window(self) -> None:
        info = cc5_ui.describe_window(self.dialog("Loading", "Please wait while we check your license", []), self.q)
        self.assertFalse(info["progress"])
        self.assertEqual(info["needs_human"], "licen")

    def test_other_windows_only_when_asked(self) -> None:
        tool = fake_qt.Widget(title="Floating Panel", visible=True)
        fake_qt.PushButton("Go", tool)
        self.q.app.tops.append(tool)
        self.assertEqual(cc5_ui.scan_windows(), [])
        found = cc5_ui.scan_windows(include_other=True)
        self.assertEqual([i["title"] for i, _w in found], ["Floating Panel"])
        self.assertFalse(found[0][0]["dialog"])

    def test_public_info_hides_the_private_text(self) -> None:
        info = cc5_ui.describe_window(self.dialog("T", "text", ["OK"]), self.q)
        self.assertIn("_full", info)
        self.assertNotIn("_full", cc5_ui.public_info(info))

    def test_baseline_keys_skip_windows_that_need_a_person(self) -> None:
        self.dialog("Palette", "tool", ["Close"])
        self.dialog("License", "license expired", ["OK"])
        self.assertEqual({k[0] for k in cc5_ui.baseline_keys()}, {"Palette"})


class DecideTest(UiTestCase):
    def info(self, title: str, text: str, buttons: list[str], needs_human: str | None = None) -> dict:
        return {"title": title, "text": text, "buttons": buttons, "needs_human": needs_human}

    def test_apply_windows_press_apply_and_tick_the_lash_box(self) -> None:
        choices = cc5_ui.normalize_choices()
        for title in ("Apply Character Preset", "Apply Eyelash Elements", "  APPLY eyelash elements "):
            d = cc5_ui.decide(self.info(title, "options", ["Apply", "Cancel"]), choices)
            self.assertEqual(d["press"], "apply", title)
            self.assertEqual(d["ticks"], [("neutral lash", True)])

    def test_other_apply_windows_are_not_ours(self) -> None:
        for title in ("Apply Settings", "Apply Coupon Code", "Applying...", "Apply for Pro", "Apply"):
            self.assertIsNone(cc5_ui.decide(self.info(title, "x", ["Apply"]), cc5_ui.normalize_choices()), title)

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

    def test_a_question_inside_a_bigger_window_is_not_ours(self) -> None:
        info = self.info("Delete", "Deleting will exit SkinGen editing mode. Discard changes?", ["Discard", "Keep"])
        self.assertIsNone(cc5_ui.decide(info, cc5_ui.normalize_choices()))
        info = self.info("Save", "exit SkinGen editing mode ? Save the project first", ["Yes", "No", "Save"])
        self.assertIsNone(cc5_ui.decide(info, cc5_ui.normalize_choices()))

    def test_unknown_window_is_left_alone(self) -> None:
        self.assertIsNone(cc5_ui.decide(self.info("Delete", "Delete this layer?", ["Yes", "No"]), cc5_ui.normalize_choices()))
        self.assertIsNone(cc5_ui.decide(self.info("Save", "Save changes?", ["Yes", "No"]), cc5_ui.normalize_choices()))

    def test_a_rule_window_that_needs_a_person_is_blocked(self) -> None:
        d = cc5_ui.decide(self.info("Apply Character Preset", "Apply", ["Apply"], needs_human="licen"),
                          cc5_ui.normalize_choices())
        self.assertIn("blocked", d)
        self.assertNotIn("press", d)

    def test_the_decision_uses_the_full_text_not_the_clipped_one(self) -> None:
        info = {"title": "x", "text": "short", "buttons": ["Yes", "No"], "needs_human": None,
                "_full": "Would you like to exit SkinGen editing mode ?"}
        self.assertEqual(cc5_ui.decide(info, cc5_ui.normalize_choices())["press"], "yes")

    def test_missing_button_is_blocked_not_guessed(self) -> None:
        info = self.info("SkinGen", "add a new layer or replace the current layer?", ["Add", "Cancel"])
        self.assertIn("blocked", cc5_ui.decide(info, cc5_ui.normalize_choices()))


class ChoicesTest(unittest.TestCase):
    def test_defaults(self) -> None:
        self.assertEqual(cc5_ui.normalize_choices(),
                         {"layer_choice": "replace", "skingen_exit": "yes", "restore_neutral_lash": True})

    def test_bad_values_and_keys_are_refused(self) -> None:
        for bad in ({"layer_choice": "cancel"}, {"skingen_exit": "maybe"}, {"restore_neutral_lash": "yes"},
                    {"press_anything": "ok"}, ["layer_choice"], "replace"):
            with self.assertRaises(ValueError):
                cc5_ui.normalize_choices(bad)

    def test_values_are_lowercased(self) -> None:
        self.assertEqual(cc5_ui.normalize_choices({"layer_choice": " Add "})["layer_choice"], "add")


class AnswererTest(UiTestCase):
    def start(self, **kwargs):
        return cc5_ui.WindowAnswerer(cc5_ui.normalize_choices(), **kwargs).start()

    def test_presses_apply_and_ticks_the_box(self) -> None:
        dlg = self.dialog("Apply Eyelash Elements", "Apply?", ["Apply", "Cancel"], [("Restore neutral lash strip", False)])
        apply_btn = dlg.findChildren(self.q.QPushButton)[0]
        apply_btn.on_click = lambda: setattr(dlg, "_visible", False)
        ans = self.start()
        ans._timer.fire()
        self.assertEqual(apply_btn.clicks, 1)
        self.assertTrue(dlg.findChildren(self.q.QCheckBox)[0].isChecked())
        self.assertEqual([e["pressed"] for e in ans.stop()], ["apply"])
        self.assertIsNone(ans._timer)

    def test_never_presses_a_license_window(self) -> None:
        dlg = self.dialog("Apply Character Preset", "Apply your license key", ["Apply"])
        ans = self.start()
        ans._timer.fire()
        self.assertEqual(dlg.findChildren(self.q.QPushButton)[0].clicks, 0)
        self.assertEqual(len(ans.blocked), 1)

    def test_a_licence_window_stops_all_pressing(self) -> None:
        lic = self.dialog("License", "Your license has expired", ["OK"])
        apply_win = self.dialog("Apply Character Preset", "Apply?", ["Apply", "Cancel"])
        ans = self.start()
        ans._timer.fire()
        self.assertEqual([b.clicks for b in apply_win.findChildren(self.q.QPushButton)], [0, 0])
        self.assertEqual(lic.findChildren(self.q.QPushButton)[0].clicks, 0)
        self.assertIn("nothing is pressed", ans.blocked[0]["why"])

    def test_other_questions_are_not_touched(self) -> None:
        dlg = self.dialog("Delete", "Delete all layers?", ["Yes", "No"])
        ans = self.start()
        ans._timer.fire()
        self.assertEqual([b.clicks for b in dlg.findChildren(self.q.QPushButton)], [0, 0])

    def test_only_buttons_of_that_window_are_pressed(self) -> None:
        dlg = self.dialog("Apply Character Preset", "Apply?", ["Cancel"])
        inner = fake_qt.Dialog(title="Inner", visible=True, parent=dlg)       # a child window with its own Apply
        inner_apply = fake_qt.PushButton("Apply", inner)
        ans = self.start()
        ans._timer.fire()
        self.assertEqual(inner_apply.clicks, 0)

    def test_one_window_is_pressed_at_most_three_times(self) -> None:
        dlg = self.dialog("Apply Character Preset", "x", ["Apply"])      # never closes
        ans = self.start()
        for _ in range(6):
            ans._timer.fire()
        self.assertEqual(dlg.findChildren(self.q.QPushButton)[0].clicks, cc5_ui.MAX_PRESSES_PER_WINDOW)
        self.assertTrue(any("still open" in b["why"] for b in ans.blocked))

    def test_the_count_belongs_to_the_window_not_to_a_python_wrapper(self) -> None:
        dlg = self.dialog("Apply Character Preset", "x", ["Apply"])
        ans = self.start()
        for _ in range(2):
            ans._timer.fire()
        self.assertEqual(dlg.property(cc5_ui.PRESS_PROPERTY), 2)

    def test_total_presses_are_capped(self) -> None:
        ans = self.start(max_presses=2)
        for _ in range(4):
            win = self.dialog("Apply Character Preset", "x", ["Apply"])
            win.findChildren(self.q.QPushButton)[0].on_click = lambda w=win: setattr(w, "_visible", False)
            ans._timer.fire()
        self.assertEqual(len(ans.log), 2)

    def test_stops_itself_after_the_time_limit_and_touch_restarts_the_clock(self) -> None:
        ans = self.start(max_seconds=100)
        fake_qt.Timer.clock[0] += 90
        ans.touch()
        fake_qt.Timer.clock[0] += 90
        ans._timer.fire()
        self.assertIsNotNone(ans._timer)
        fake_qt.Timer.clock[0] += 20
        ans._timer.fire()
        self.assertIsNone(ans._timer)

    def test_a_new_answerer_replaces_the_old_one(self) -> None:
        first = self.start()
        second = self.start()
        self.assertIsNone(first._timer)
        self.assertIsNotNone(second._timer)
        cc5_ui.stop_active_answerer()
        self.assertIsNone(second._timer)

    def test_a_crashing_tick_does_not_escape(self) -> None:
        ans = self.start()
        with mock.patch.object(cc5_ui, "scan_windows", side_effect=RuntimeError("boom")):
            ans._timer.fire()                         # must not raise


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

    def test_failure_in_a_later_step_runs_the_finally_blocks(self) -> None:
        cleaned = []

        def make(_p):
            try:
                yield 10
                raise ValueError("bad second step")
            finally:
                cleaned.append(True)
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain()
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["state"], "failed")
        self.assertEqual(cleaned, [True])

    def test_a_generator_that_yields_junk_fails_the_job_instead_of_hanging(self) -> None:
        cleaned = []

        def make(_p):
            try:
                yield "soon"
            finally:
                cleaned.append(True)
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain()
        self.assertEqual(cc5_ui.ui_job({"job_id": started["job_id"]})["state"], "failed")
        self.assertEqual(cleaned, [True])

    def test_only_one_job_at_a_time(self) -> None:
        first = cc5_ui.start_job("a", lambda p: {"success": True}, {})
        second = cc5_ui.start_job("b", lambda p: {"success": True}, {})
        self.assertFalse(second["success"])
        self.assertIn(first["job_id"], second["error"])
        fake_qt.drain()
        self.assertTrue(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])

    def test_a_job_blocks_for_as_long_as_it_says_it_may_take(self) -> None:
        cc5_ui.start_job("a", lambda p: {"success": True}, {}, max_seconds=3000)
        fake_qt.Timer.clock[0] += cc5_ui.JOB_STALE_SECONDS + 1
        self.assertFalse(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])
        fake_qt.Timer.clock[0] += 3000
        self.assertTrue(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])

    def test_a_stale_running_job_no_longer_blocks(self) -> None:
        cc5_ui.start_job("a", lambda p: {"success": True}, {})
        fake_qt.Timer.clock[0] += cc5_ui.JOB_STALE_SECONDS + 1
        self.assertTrue(cc5_ui.start_job("b", lambda p: {"success": True}, {})["success"])

    def test_unknown_job(self) -> None:
        self.assertFalse(cc5_ui.ui_job({"job_id": "nope"})["success"])

    def test_old_jobs_are_pruned(self) -> None:
        for _ in range(cc5_ui.JOB_KEEP + 5):
            cc5_ui.start_job("t", lambda p: {"success": True}, {})
            fake_qt.drain()
        self.assertEqual(len(cc5_ui._jobs()), cc5_ui.JOB_KEEP)

    def test_running_job_reports_open_windows_without_private_text(self) -> None:
        self.dialog("Mystery", "Who knows", ["OK"])

        def make(_p):
            yield 1000
            return {"success": True}
        started = cc5_ui.start_job("t", make, {})
        fake_qt.drain(1)
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        self.assertEqual(job["windows"][0]["title"], "Mystery")
        self.assertNotIn("_full", job["windows"][0])

    def test_scheduling_failure_is_reported(self) -> None:
        with mock.patch.object(cc5_ui, "_later", side_effect=RuntimeError("no timer")):
            res = cc5_ui.start_job("t", lambda p: {"success": True}, {})
        self.assertFalse(res["success"])


class JobGuardTest(UiTestCase):
    def test_other_actions_wait_while_a_job_runs(self) -> None:
        self.assertIsNone(cc5_ui.job_guard_message("set_morph_value"))
        cc5_ui.start_job("preset", lambda p: {"success": True}, {})
        self.assertIn("set_morph_value", cc5_ui.job_guard_message("set_morph_value"))
        for action in ("ui_job", "ui_windows", "ui_widgets", "ui_skingen_state"):
            self.assertIsNone(cc5_ui.job_guard_message(action), action)
        fake_qt.drain()
        self.assertIsNone(cc5_ui.job_guard_message("set_morph_value"))

    def test_can_be_switched_off(self) -> None:
        cc5_ui.start_job("preset", lambda p: {"success": True}, {})
        with mock.patch.dict(os.environ, {"CC5_UI_JOB_GUARD": "0"}):
            self.assertIsNone(cc5_ui.job_guard_message("set_morph_value"))

    def test_install_wraps_once_and_keeps_the_originals(self) -> None:
        calls = []
        handlers = {"get_avatars": lambda p: calls.append("avatars") or {"success": True},
                    "ui_job": cc5_ui.ui_job, "ui_apply_preset": lambda p: {"success": True}}
        originals = dict(handlers)
        cc5_ui.install_job_guard(handlers)
        cc5_ui.install_job_guard(handlers)            # repeating must not wrap twice
        self.assertIs(handlers["get_avatars"]._cc5_guarded, originals["get_avatars"])
        self.assertIs(handlers["ui_job"], originals["ui_job"])
        self.assertIs(handlers["ui_apply_preset"], originals["ui_apply_preset"])
        self.assertEqual(handlers["get_avatars"]({}), {"success": True})
        cc5_ui.start_job("preset", lambda p: {"success": True}, {})
        res = handlers["get_avatars"]({})
        self.assertFalse(res["success"])
        self.assertIn("was NOT run", res["error"])
        self.assertEqual(calls, ["avatars"])


class SettleTest(UiTestCase):
    def test_quiet_after_two_empty_polls(self) -> None:
        self.assertTrue(self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))["ok"])

    def test_progress_windows_are_waited_out(self) -> None:
        bake = self.dialog("Baking", "Please wait", [])

        def on_step(n: int) -> None:
            if n == 4:
                bake._visible = False
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()), on_step)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["waited_s"], 4)

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
        self.assertNotIn("_full", result["blocked_by"])
        self.assertGreaterEqual(result["waited_s"], 3)

    def test_a_license_window_stops_the_wait_at_once(self) -> None:
        self.dialog("License", "License expired", ["OK"])
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))
        self.assertFalse(result["ok"])
        self.assertLess(result["waited_s"], 1)

    def test_a_license_check_is_not_waited_out_as_progress(self) -> None:
        self.dialog("Loading", "Please wait, checking your license", [])
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))
        self.assertFalse(result["ok"])
        self.assertEqual(result["blocked_by"]["needs_human"], "licen")

    def test_gives_up_at_the_limit(self) -> None:
        self.dialog("Baking", "Please wait", [])
        self.assertTrue(self.run_steps(cc5_ui.settle_steps(10, cc5_ui.normalize_choices()))["timeout"])

    def test_a_long_freeze_does_not_use_up_the_time_limit(self) -> None:
        def on_step(n: int) -> None:
            if n == 1:
                fake_qt.Timer.clock[0] += 600         # CC5 froze for ten minutes (a bake)
        result = self.run_steps(cc5_ui.settle_steps(10, cc5_ui.normalize_choices()), on_step)
        self.assertTrue(result["ok"])

    def test_extra_condition_must_hold(self) -> None:
        flag = {"ok": False}

        def on_step(n: int) -> None:
            flag["ok"] = n >= 3
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices(), extra_ok=lambda: flag["ok"]), on_step)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["waited_s"], 3)

    def test_windows_that_were_open_before_the_job_are_ignored(self) -> None:
        self.dialog("Palette", "tool window", ["Close"])
        baseline = cc5_ui.baseline_keys()
        self.assertTrue(self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices(), baseline=baseline))["ok"])
        self.assertFalse(self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices()))["ok"])

    def test_nothing_is_answered_when_answerable_is_false(self) -> None:
        self.dialog("Apply Character Preset", "x", ["Apply"])
        result = self.run_steps(cc5_ui.settle_steps(60, cc5_ui.normalize_choices(), answerable=False))
        self.assertFalse(result["ok"])

    def test_settle_error_texts(self) -> None:
        self.assertIn("needs a person", cc5_ui.settle_error({"blocked_by": {"title": "T", "text": "x", "buttons": ["OK"]}}))
        self.assertIn("still busy", cc5_ui.settle_error({"blocked_by": None}))


class WidgetLookupTest(UiTestCase):
    def test_find_by_names_is_one_pass_and_visible_first(self) -> None:
        root = fake_qt.Widget(name="root", visible=True)
        hidden = fake_qt.SpinBox(root, name="qtSpinBox")
        hidden._visible = False
        shown = fake_qt.SpinBox(root, name="qtSpinBox")
        found = cc5_ui.find_by_names(["qtSpinBox", "missing"])
        self.assertEqual(found["qtSpinBox"], [shown, hidden])
        self.assertEqual(found["missing"], [])

    def test_find_by_name_within_a_parent(self) -> None:
        a = fake_qt.Widget(name="a", visible=True)
        b = fake_qt.Widget(name="b", visible=True)
        in_a = fake_qt.SpinBox(a, name="qtSpinBox")
        fake_qt.SpinBox(b, name="qtSpinBox")
        self.assertEqual(cc5_ui.find_by_name("qtSpinBox", a), [in_a])
        self.assertEqual(len(cc5_ui.find_by_name("qtSpinBox")), 2)


class RoutesTest(unittest.TestCase):
    def test_core_routes(self) -> None:
        self.assertEqual(set(cc5_ui.ROUTES), {"/ui/job"})


if __name__ == "__main__":
    unittest.main()
