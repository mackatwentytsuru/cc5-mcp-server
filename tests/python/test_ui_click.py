"""
cc5_uiclick: press ONE named button of a CC5 window (/ui/click), with a fake Qt.

What is checked: the matching (window by title or objectName, button by objectName and/or text,
menu entries), every refusal (no match, ambiguous, hidden, disabled, the deny words, a window that
needs a person, a modal window), and the job (click on a Qt timer, picture after wait_ms, a click that
opens a modal window, a click that raises).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import json
import unittest

from ui_support import UiTestCase, cc5_ui, fake_qt

import cc5_uiclick  # noqa: E402


class ClickTestCase(UiTestCase):
    """A floating tool window like Body Wrap, with two buttons."""

    def setUp(self) -> None:
        super().setUp()
        self.win = self.tool_window("Body Wrap", name="BodyWrapWindow")
        self.save = fake_qt.PushButton("Save Skeleton", self.win, name="qtSaveSkeletonButton")
        self.paste = fake_qt.PushButton("Paste", self.win, name="qtPasteButton")

    def tool_window(self, title: str, name: str = "") -> fake_qt.Widget:
        w = fake_qt.Widget(name=name, title=title)
        w._is_window = True
        self.q.app.tops.append(w)
        return w

    def click(self, **body):
        body.setdefault("window", "Body Wrap")
        return cc5_uiclick.ui_click(body)

    def run_click(self, **body):
        return self.finish(self.click(**body))

    def assert_refused(self, res: dict, *needles: str) -> None:
        self.assertFalse(res["success"], res)
        for needle in needles:
            self.assertIn(needle, res["error"])
        self.assertEqual(fake_qt.Timer.singles, [], "a refused request must not start a job")


class MatchingTest(ClickTestCase):
    def test_presses_the_button_by_text_and_returns_picture_and_dialogs(self) -> None:
        result = self.run_click(text="Save Skeleton")
        self.assertTrue(result["success"], result)
        self.assertEqual((self.save.clicks, self.paste.clicks), (1, 0))
        self.assertTrue(result["click_returned"])
        self.assertEqual(result["window"], "Body Wrap")
        self.assertEqual(result["pressed"]["object_name"], "qtSaveSkeletonButton")
        self.assertTrue(result["window_open"])
        self.assertTrue(result["png_base64"])
        self.assertEqual(self.win.grabbed, 1)
        self.assertEqual(result["dialogs"], [])
        self.assertNotIn("checked_before", result)

    def test_by_object_name_and_by_loose_case_and_spacing(self) -> None:
        self.run_click(object_name="qtPasteButton")
        self.run_click(text="  save   SKELETON ")
        self.run_click(text="&Paste")
        self.assertEqual((self.save.clicks, self.paste.clicks), (1, 2))

    def test_shortcut_marker_on_the_button_is_ignored(self) -> None:
        detect = fake_qt.PushButton("&Detect Joints", self.win, name="qtDetect")
        self.run_click(text="Detect Joints")
        self.assertEqual(detect.clicks, 1)

    def test_window_by_title_any_case_or_by_object_name(self) -> None:
        self.run_click(window="BODY WRAP", text="Paste")
        self.run_click(window="BodyWrapWindow", text="Paste")
        self.assertEqual(self.paste.clicks, 2)

    def test_unknown_window_lists_the_open_ones(self) -> None:
        self.assert_refused(self.click(window="Headshot", text="Paste"), "no open CC5 window", "'Body Wrap'")

    def test_two_windows_with_one_title_are_ambiguous_until_the_object_name_picks_one(self) -> None:
        self.tool_window("Body Wrap")
        self.assert_refused(self.click(text="Paste"), "2 open windows are called")
        self.run_click(window="BodyWrapWindow", text="Paste")
        self.assertEqual(self.paste.clicks, 1)

    def test_no_such_button_lists_the_visible_ones_only(self) -> None:
        fake_qt.PushButton("Secret", self.win, visible=False)
        res = self.click(text="Load Skeleton")
        self.assert_refused(res, "no button with text 'Load Skeleton'", "'Save Skeleton' [qtSaveSkeletonButton]")
        self.assertNotIn("Secret", res["error"])

    def test_two_visible_matches_are_ambiguous_until_object_name_picks_one(self) -> None:
        other = fake_qt.PushButton("Paste", self.win, name="qtPasteHair")
        self.assert_refused(self.click(text="Paste"), "2 visible buttons match", "qtPasteHair")
        self.run_click(text="Paste", object_name="qtPasteHair")
        self.assertEqual((other.clicks, self.paste.clicks), (1, 0))

    def test_hidden_duplicates_do_not_count_and_are_never_pressed(self) -> None:
        ghost = fake_qt.PushButton("Paste", self.win, name="qtPasteGhost", visible=False)
        result = self.run_click(text="Paste")
        self.assertEqual((self.paste.clicks, ghost.clicks), (1, 0))
        self.assertEqual(result["hidden_skipped"], 1)
        only_hidden = fake_qt.PushButton("Bake", self.win, visible=False)
        self.assert_refused(self.click(text="Bake"), "is hidden")
        self.assertEqual(only_hidden.clicks, 0)

    def test_buttons_of_a_child_dialog_belong_to_that_dialog(self) -> None:
        child = fake_qt.Dialog(title="Confirm", parent=self.win)
        ok = fake_qt.PushButton("OK", child)
        self.assert_refused(self.click(text="OK"), "no button with text 'OK'")
        self.assertEqual(ok.clicks, 0)

    def test_a_dock_panel_inside_the_main_window(self) -> None:
        main = fake_qt.MainWindow(title="Character Creator 5 - test.ccProject")
        self.q.app.tops.append(main)
        dock = fake_qt.DockWidget(name="qtModifyDock", title="Modify", parent=main)
        refresh = fake_qt.PushButton("Refresh", dock, name="qtRefresh")
        result = self.run_click(window="Modify", text="Refresh")
        self.assertEqual(refresh.clicks, 1)
        self.assertEqual(dock.grabbed, 1)                    # the picture is of the panel that was named
        self.assertEqual(result["window"], "Modify")


class RefusalTest(ClickTestCase):
    REFUSED = (
        "Generate AI Points", "Align Points (AI)", "Get AI Points", "Wrap Points", "ポイントを使う", "Buy Now", "ＢＵＹ", "購入する", "Purchase",
        "pUrChAsE", "Pur chase", "Delete", "削除", "Remove Layer", "License", "Licence info", "ライセンス",
        "Activate", "Deactivate", "Upgrade", "Credits", "クレジット", "Subscribe", "Pay", "支払い",
        "Log In", "Update", "Terms of Use",
    )

    def test_every_deny_word_in_the_text_is_refused(self) -> None:
        for i, label in enumerate(self.REFUSED):
            with self.subTest(label=label):
                button = fake_qt.PushButton(label, self.win, name=f"qtB{i}")
                self.assert_refused(self.click(object_name=f"qtB{i}"), "refused")
                self.assertEqual(button.clicks, 0)

    def test_deny_word_in_the_object_name_or_the_tool_tip(self) -> None:
        trash = fake_qt.ToolButton("", self.win, name="qtDeleteToolButton")
        self.assert_refused(self.click(object_name="qtDeleteToolButton"), "mentions 'delete'")
        tip = fake_qt.PushButton("OK", self.win, name="qtOk")
        tip._tooltip = "<html><b>Pur</b>chase this item</html>"
        self.assert_refused(self.click(object_name="qtOk"), "mentions 'purchase'")
        points = fake_qt.PushButton("Go", self.win, name="qtGo")
        points._tooltip = "Replace the hand-fixed points"
        self.assert_refused(self.click(object_name="qtGo"), "mentions 'point'")
        self.assertEqual((trash.clicks, tip.clicks, points.clicks), (0, 0, 0))

    def test_owner_exception_presses_exactly_the_two_wrap_point_buttons(self) -> None:
        gen = fake_qt.PushButton("GENERATE WRAP POINTS", self.win, name="qtGenerateWrapPointsButton")
        gen._tooltip = "Generate the wrap points"
        align = fake_qt.PushButton("&Align Points", self.win, name="qtAlignPointsButton")
        self.run_click(text="Generate Wrap Points")
        self.run_click(object_name="qtAlignPointsButton")
        self.assertEqual((gen.clicks, align.clicks), (1, 1))

    def test_exception_still_refuses_any_other_deny_word_and_similar_names(self) -> None:
        credit = fake_qt.PushButton("Align Points", self.win, name="qtAlignCredit")
        credit._tooltip = "Costs one credit"
        buy = fake_qt.PushButton("Generate Wrap Points", self.win, name="qtBuyWrapPoints")
        buy._tooltip = ""
        self.assert_refused(self.click(object_name="qtAlignCredit"), "mentions 'credit'")
        self.assert_refused(self.click(object_name="qtBuyWrapPoints"), "mentions 'buy'")
        self.assertEqual((credit.clicks, buy.clicks), (0, 0))

    def test_exception_is_only_inside_the_body_wrap_window_and_not_for_menu_entries(self) -> None:
        other = self.tool_window("Headshot 3", name="HeadshotWindow")
        elsewhere = fake_qt.PushButton("Align Points", other, name="qtAlignElsewhere")
        self.assert_refused(self.click(window="Headshot 3", text="Align Points"), "mentions 'point'")
        self.assertEqual(elsewhere.clicks, 0)
        self.assertIsNone(cc5_uiclick.deny_reason("Generate Wrap Points", skip_words=frozenset({"point"})))
        self.assertEqual(cc5_uiclick.deny_reason("Generate Wrap Points"), "point")

    def test_ordinary_buttons_are_not_caught_by_the_short_words(self) -> None:
        for label in ("Display", "Replay", "Repaint", "Detect Joints", "Paste", "Save Skeleton", "Load Skeleton",
                      "Bake Textures", "Create CC Actor", "Refine Mesh", "Generate Skeleton", "OK", "Cancel"):
            self.assertIsNone(cc5_uiclick.deny_reason(label, "qtButton", ""), label)

    def test_deny_reason_names_the_word(self) -> None:
        self.assertEqual(cc5_uiclick.deny_reason("Generate Wrap Points"), "point")
        self.assertEqual(cc5_uiclick.deny_reason("", "qtBuyButton"), "buy")
        self.assertEqual(cc5_uiclick.deny_reason("Log In"), "log in")
        self.assertEqual(cc5_uiclick.deny_reason("Save", "", "<b>Del</b>ete all"), "delete")

    def test_the_word_list_is_the_agreed_one(self) -> None:
        self.assertEqual(set(cc5_uiclick.DENY_WORDS), {
            "point", "ポイント", "buy", "購入", "purchase", "delete", "削除", "remove", "license", "licence",
            "ライセンス", "activate", "upgrade", "credit", "クレジット", "subscribe", "pay", "支払"})

    def test_disabled_button_is_refused(self) -> None:
        self.save._enabled = False
        self.assert_refused(self.click(text="Save Skeleton"), "disabled")
        self.assertEqual(self.save.clicks, 0)

    def test_nothing_is_pressed_while_a_window_needs_a_person(self) -> None:
        self.dialog("License", "Your license has expired", ["OK"])
        self.assert_refused(self.click(text="Paste"), "a person must decide")
        self.assertEqual(self.paste.clicks, 0)

    def test_a_modal_window_blocks_buttons_outside_it_but_not_inside(self) -> None:
        dlg = self.dialog("Save Skeleton", "Choose a file name", ["Save", "Cancel"])
        dlg._modal = True
        self.assert_refused(self.click(text="Paste"), "modal window 'Save Skeleton' is open")
        self.run_click(window="Save Skeleton", text="Cancel")
        cancel = [b for b in dlg.findChildren(fake_qt.PushButton) if b.text() == "Cancel"][0]
        self.assertEqual((self.paste.clicks, cancel.clicks), (0, 1))


class MenuTest(ClickTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.load = fake_qt.Action("Load Skeleton")
        self.store = fake_qt.Action("Save Skeleton")
        self.disk = fake_qt.ToolButton("", self.win, name="qtSkeletonFileButton")
        self.disk._tooltip = "Skeleton file"
        self.entries = [self.load, fake_qt.Action("", separator=True), self.store]
        self.disk._menu = fake_qt.ActionMenu(self.entries)

    def test_menu_item_triggers_that_entry_not_the_button(self) -> None:
        result = self.run_click(object_name="qtSkeletonFileButton", menu_item="save skeleton")
        self.assertTrue(result["success"], result)
        self.assertEqual((self.store.triggered, self.load.triggered, self.disk.clicks), (1, 0, 0))
        self.assertEqual(result["pressed"]["menu_item"], "save skeleton")
        self.assertEqual(result["pressed"]["tooltip"], "Skeleton file")

    def test_a_menu_button_without_menu_item_is_refused_and_lists_the_entries(self) -> None:
        self.assert_refused(self.click(object_name="qtSkeletonFileButton"), "drop-down menu",
                            "'Load Skeleton', 'Save Skeleton'", "menu_item")
        self.assertEqual(self.disk.clicks, 0)

    def test_menu_entry_refusals(self) -> None:
        self.entries += [fake_qt.Action("Hidden", visible=False), fake_qt.Action("Delete Skeleton"),
                         fake_qt.Action("More", submenu=fake_qt.ActionMenu([]))]
        cases = (("Export", "is not there"), ("Hidden", "is hidden"), ("More", "sub-menu"),
                 ("Delete Skeleton", "mentions 'delete'"))
        for item, needle in cases:
            with self.subTest(item=item):
                self.assert_refused(self.click(object_name="qtSkeletonFileButton", menu_item=item), needle)
        self.store._enabled = False
        self.assert_refused(self.click(object_name="qtSkeletonFileButton", menu_item="Save Skeleton"), "disabled")
        self.assert_refused(self.click(object_name="qtPasteButton", menu_item="Save Skeleton"), "no drop-down menu")
        self.assertEqual(sum(a.triggered for a in self.entries), 0)


class JobTest(ClickTestCase):
    def test_the_click_runs_on_a_qt_timer_and_the_picture_comes_after_wait_ms(self) -> None:
        started = self.click(text="Paste", wait_ms=2500)
        self.assertTrue(started["success"], started)
        self.assertTrue(started["job_id"].startswith("click-"))
        fake_qt.drain(1)                                     # the job's first step: schedules the click
        self.assertEqual(fake_qt.Timer.pending_ms(), [cc5_uiclick.CLICK_DELAY_MS, cc5_uiclick.CLICK_DELAY_MS + 2500])
        self.assertEqual(self.paste.clicks, 0)
        result = self.finish(started)
        self.assertEqual((self.paste.clicks, result["waited_ms"]), (1, 2500))

    def test_a_click_that_opens_a_modal_window_is_reported_and_nothing_is_answered(self) -> None:
        opened = []

        def open_modal() -> None:
            dlg = fake_qt.make_dialog(self.q, "Save Skeleton", "File name?", ["Save", "Cancel"])
            dlg._modal = True
            opened.append(dlg)
            fake_qt.drain()                                  # the modal window's own event loop runs the next step

        self.save.on_click = open_modal
        started = self.click(text="Save Skeleton")
        fake_qt.drain()
        job = cc5_ui.ui_job({"job_id": started["job_id"]})
        json.dumps(job)
        result = job["result"]
        self.assertTrue(result["success"], result)
        self.assertFalse(result["click_returned"])
        self.assertIn("has not returned yet", result["note"])
        self.assertEqual([d["title"] for d in result["dialogs"]], ["Save Skeleton"])
        self.assertTrue(result["dialogs"][0]["png_base64"])
        self.assertEqual([b.clicks for b in opened[0].findChildren(fake_qt.PushButton)], [0, 0])

    def test_a_click_that_raises_is_reported(self) -> None:
        def boom() -> None:
            raise RuntimeError("Internal C++ object already deleted")

        self.paste.on_click = boom
        result = self.run_click(text="Paste")
        self.assertFalse(result["success"])
        self.assertIn("RuntimeError", result["error"])
        self.assertTrue(result["click_returned"])

    def test_the_button_is_checked_again_when_the_job_starts(self) -> None:
        started = self.click(text="Paste")
        self.paste._enabled = False                          # greyed out before the job's first step
        result = self.finish(started)
        self.assertFalse(result["success"])
        self.assertIn("disabled", result["error"])
        self.assertEqual(self.paste.clicks, 0)

    def test_toggle_buttons_report_checked_before_and_after(self) -> None:
        toggle = fake_qt.PushButton("Show Mesh", self.win, name="qtShowMesh")
        toggle.isCheckable = lambda: True
        toggle.on_click = lambda: toggle.setChecked(not toggle.isChecked())
        result = self.run_click(object_name="qtShowMesh")
        self.assertEqual((result["checked_before"], result["checked_after"]), (False, True))

    def test_a_window_that_closed_after_the_click_has_no_picture(self) -> None:
        self.paste.on_click = lambda: setattr(self.win, "_visible", False)
        result = self.run_click(text="Paste")
        self.assertFalse(result["window_open"])
        self.assertNotIn("png_base64", result)
        self.assertEqual(self.win.grabbed, 0)

    def test_screenshot_false_returns_no_pictures(self) -> None:
        self.dialog("Note", "Saved.", ["OK"])
        result = self.run_click(text="Paste", screenshot=False)
        self.assertNotIn("png_base64", result)
        self.assertEqual(result["dialogs"][0]["title"], "Note")
        self.assertNotIn("png_base64", result["dialogs"][0])

    def test_one_ui_job_at_a_time(self) -> None:
        cc5_ui.start_job("other", lambda p: {"success": True}, {})
        res = self.click(text="Paste")
        self.assertFalse(res["success"])
        self.assertIn("another UI job", res["error"])


class ArgumentsTest(ClickTestCase):
    def test_bad_requests_are_refused_before_anything_runs(self) -> None:
        bad = (
            {},
            {"window": "Body Wrap"},
            {"window": "", "text": "Paste"},
            {"window": 3, "text": "Paste"},
            {"window": "Body Wrap", "text": ""},
            {"window": "Body Wrap", "text": "Paste", "objectname": "qtPasteButton"},
            {"window": "Body Wrap", "text": "x" * 300},
            {"window": "Body Wrap", "text": "Paste", "screenshot": "yes"},
            {"window": "Body Wrap", "menu_item": "Save Skeleton"},
        )
        for body in bad:
            with self.subTest(body=body):
                self.assertFalse(cc5_uiclick.ui_click(body)["success"])
        self.assertEqual(fake_qt.Timer.singles, [])
        self.assertEqual(self.paste.clicks, 0)

    def test_wait_ms_default_and_limits(self) -> None:
        def wait(value: object = None) -> int:
            body = {"window": "w", "text": "t"}
            if value is not None:
                body["wait_ms"] = value
            return cc5_uiclick.read_args(body)[0]["wait_ms"]

        self.assertEqual(wait(), cc5_uiclick.DEFAULT_WAIT_MS)
        self.assertEqual(wait(999_999), cc5_uiclick.MAX_WAIT_MS)
        self.assertEqual(wait(1), cc5_uiclick.MIN_WAIT_MS)
        self.assertEqual(wait("nope"), cc5_uiclick.DEFAULT_WAIT_MS)

    def test_route(self) -> None:
        self.assertEqual(cc5_uiclick.ROUTES, {"/ui/click": ("ui_click", cc5_uiclick.ui_click)})


if __name__ == "__main__":
    unittest.main()
