"""
cc5_skingen: reading the editor, editor on/off, layer show/hide/select/opacity/delete.

The SkinGen panel is a small fake built from the widget names found on a real CC5
(see cc5-plugin/cc5_skingen.py); runs without CC5 or Qt.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import unittest

from skingen_panel import Panel
from ui_support import UiTestCase, cc5_ui, fake_qt  # sets up sys.path and the RLPy stand-in

import cc5_skingen  # noqa: E402


class StateTest(UiTestCase):
    def test_reads_layers_visibility_and_selection(self) -> None:
        panel = Panel()
        panel.eye(1).setChecked(True)               # checked = hidden
        panel.table.selected = [2]
        state = cc5_skingen.read_state()
        self.assertTrue(state["editor_found"] and state["editor_active"])
        self.assertEqual([(l["name"], l["visible"], l["selected"]) for l in state["layers"]],
                         [("Lips", True, False), ("Eyeshadow", False, False), ("Blush", True, True)])
        self.assertEqual((state["selected"], state["opacity"], state["opacity_range"]), (2, 100, [0, 100]))
        self.assertEqual(state["layers"][0]["number"], "1")

    def test_reads_tab_and_combos(self) -> None:
        panel = Panel()
        fake_qt.PushButton("Makeup", panel.root, name="qtMakeupPushButton", checked=True)
        fake_qt.PushButton("Skin", panel.root, name="qtSkinPushButton", checked=False)
        fake_qt.ComboBox(panel.root, name="qtMaterialComboBox", text="Head")
        state = cc5_skingen.read_state()
        self.assertEqual(state["tab"], "makeup")
        self.assertEqual(state["combos"], {"material": "Head"})

    def test_a_missing_editor_gets_a_hint(self) -> None:
        state = cc5_skingen.ui_skingen_state({})
        self.assertTrue(state["success"])
        self.assertFalse(state["editor_found"])
        self.assertIn("hint", state)
        self.assertEqual(state["layers"], [])

    def test_prefers_the_visible_copy_of_a_widget(self) -> None:
        hidden = Panel(layers=("Old",))
        hidden.table._visible = False
        Panel(layers=("Shown1", "Shown2"))
        self.assertEqual([l["name"] for l in cc5_skingen.read_state()["layers"]], ["Shown1", "Shown2"])


class ResolveLayerTest(unittest.TestCase):
    LAYERS = [{"index": 0, "name": "Lips"}, {"index": 1, "name": "Eyeshadow"}, {"index": 2, "name": "lips"}]

    def test_by_index(self) -> None:
        self.assertEqual(cc5_skingen.resolve_layer(self.LAYERS, index="1"), (1, None))

    def test_index_out_of_range_or_bad(self) -> None:
        self.assertIn("out of range", cc5_skingen.resolve_layer(self.LAYERS, index=5)[1])
        self.assertIn("whole number", cc5_skingen.resolve_layer(self.LAYERS, index="x")[1])

    def test_by_unique_name_ignoring_case(self) -> None:
        self.assertEqual(cc5_skingen.resolve_layer(self.LAYERS, name="EYESHADOW"), (1, None))

    def test_ambiguous_and_unknown_names(self) -> None:
        self.assertIn("several layers", cc5_skingen.resolve_layer(self.LAYERS, name="lips")[1])
        self.assertIn("no layer named", cc5_skingen.resolve_layer(self.LAYERS, name="Blush")[1])

    def test_needs_index_or_name(self) -> None:
        self.assertIn("give index or name", cc5_skingen.resolve_layer(self.LAYERS)[1])


class EditorTest(UiTestCase):
    def wire_exit_flow(self, panel: Panel, extra_dialog: tuple[str, str, list[str]] | None = None) -> dict:
        """Clicking the switch (while on) opens the exit question; Yes bakes for 5 s then turns it off."""
        seen: dict = {"question": None}

        def close_bake() -> None:
            bake._visible = False

        def on_yes() -> None:
            seen["question"]._visible = False
            panel.switch.setChecked(False)
            bake._visible = True
            fake_qt.Timer.singleShot(5000, close_bake)

        def on_switch() -> None:
            if extra_dialog is not None:
                self.dialog(*extra_dialog)
                return
            question = self.dialog("SkinGen", "Would you like to exit SkinGen editing mode ?", ["Yes", "No"])
            yes_button, no_button = question.findChildren(self.q.QPushButton)
            yes_button.on_click = on_yes
            no_button.on_click = lambda: setattr(question, "_visible", False)
            seen["question"] = question

        bake = self.dialog("Baking", "Please wait", [])
        bake._visible = False
        panel.switch.on_click = on_switch
        return seen

    def test_switching_off_answers_yes_and_waits_for_the_bake(self) -> None:
        panel = Panel()
        self.wire_exit_flow(panel)
        res = self.finish(cc5_skingen.ui_skingen_editor({"active": False}))
        self.assertTrue(res["success"], res)
        self.assertEqual((res["changed"], res["editor_active"]), (True, False))
        self.assertEqual([e["pressed"] for e in res["answered"]], ["yes"])
        self.assertFalse(panel.switch.isChecked())
        self.assertGreaterEqual(res["waited_s"], 1)

    def test_exit_answer_no_keeps_the_editor_on(self) -> None:
        panel = Panel()
        self.wire_exit_flow(panel)
        started = cc5_skingen.ui_skingen_editor({"active": False, "exit_answer": "no", "timeout_s": 10})
        res = self.finish(started)
        self.assertFalse(res["success"])
        self.assertIn("did not change", res["error"])
        self.assertEqual([e["pressed"] for e in res["answered"]], ["no"])
        self.assertTrue(panel.switch.isChecked())

    def test_already_in_the_wanted_state_does_nothing(self) -> None:
        panel = Panel(active=False)
        res = self.finish(cc5_skingen.ui_skingen_editor({"active": False}))
        self.assertEqual((res["success"], res["changed"]), (True, False))
        self.assertEqual(panel.switch.clicks, 0)

    def test_switching_on(self) -> None:
        panel = Panel(active=False)
        panel.switch.on_click = lambda: panel.switch.setChecked(True)
        res = self.finish(cc5_skingen.ui_skingen_editor({"active": True}))
        self.assertTrue(res["success"], res)
        self.assertEqual((res["changed"], res["editor_active"]), (True, True))

    def test_an_unknown_window_is_reported_and_not_answered(self) -> None:
        panel = Panel()
        self.wire_exit_flow(panel, extra_dialog=("Save", "Save changes to the project?", ["Yes", "No"]))
        panel.switch.on_click = lambda: (self.dialog("Save", "Save changes to the project?", ["Yes", "No"]),
                                         panel.switch.setChecked(False))
        res = self.finish(cc5_skingen.ui_skingen_editor({"active": False}))
        self.assertFalse(res["success"])
        self.assertEqual(res["blocked_by"]["title"], "Save")
        self.assertIn("needs a person", res["error"])

    def test_the_answerer_is_stopped_afterwards(self) -> None:
        panel = Panel()
        self.wire_exit_flow(panel)
        self.finish(cc5_skingen.ui_skingen_editor({"active": False}))
        self.assertEqual(fake_qt.Timer.active_timers, [])

    def test_bad_arguments(self) -> None:
        Panel()
        self.assertFalse(cc5_skingen.ui_skingen_editor({})["success"])
        self.assertFalse(cc5_skingen.ui_skingen_editor({"active": "yes"})["success"])
        self.assertFalse(cc5_skingen.ui_skingen_editor({"active": False, "exit_answer": "maybe"})["success"])

    def test_no_switch_is_an_immediate_error(self) -> None:
        res = cc5_skingen.ui_skingen_editor({"active": False})
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])


class LayerTest(UiTestCase):
    def test_hide_and_show(self) -> None:
        panel = Panel()
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "hide", "index": 1}))
        self.assertTrue(res["success"], res)
        self.assertFalse(res["layer"]["visible"])
        self.assertTrue(panel.eye(1).isChecked())
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "show", "name": "Eyeshadow"}))
        self.assertTrue(res["layer"]["visible"])

    def test_hiding_a_hidden_layer_does_not_click_again(self) -> None:
        panel = Panel()
        panel.eye(0).setChecked(True)
        self.finish(cc5_skingen.ui_skingen_layer({"action": "hide", "index": 0}))
        self.assertEqual(panel.eye(0).clicks, 0)

    def test_select(self) -> None:
        panel = Panel()
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "select", "index": 2}))
        self.assertTrue(res["success"])
        self.assertEqual(res["selected"], 2)
        self.assertEqual(panel.table.select_calls, [2])

    def test_opacity_selects_the_layer_then_sets_the_box(self) -> None:
        panel = Panel()
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "opacity", "name": "Blush", "opacity": 35}))
        self.assertTrue(res["success"], res)
        self.assertEqual((res["layer"], res["opacity_before"], res["opacity_after"]), (2, 100, 35))
        self.assertEqual(panel.table.select_calls, [2])
        self.assertEqual(panel.spin.value(), 35)

    def test_opacity_on_the_selected_layer_does_not_reselect(self) -> None:
        panel = Panel()
        panel.table.selected = [0]
        self.finish(cc5_skingen.ui_skingen_layer({"action": "opacity", "index": 0, "opacity": 50}))
        self.assertEqual(panel.table.select_calls, [])

    def test_opacity_is_validated(self) -> None:
        Panel()
        for bad in (150, -1, 12.5, "abc", None):
            res = cc5_skingen.ui_skingen_layer({"action": "opacity", "index": 0, "opacity": bad})
            self.assertFalse(res["success"], bad)
        self.assertTrue(cc5_skingen.ui_skingen_layer({"action": "opacity", "index": 0, "opacity": 0})["success"])

    def test_opacity_box_missing_is_reported(self) -> None:
        panel = Panel()
        panel.spin._name = "other"
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "opacity", "index": 0, "opacity": 10}))
        self.assertFalse(res["success"])
        self.assertIn("opacity box", res["error"])

    def test_opacity_read_back_mismatch_is_a_failure(self) -> None:
        panel = Panel()
        panel.spin.setValue = lambda v: None        # a box that ignores the value
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "opacity", "index": 0, "opacity": 10}))
        self.assertFalse(res["success"])
        self.assertIn("reads 100", res["error"])

    def test_bad_layer_and_action(self) -> None:
        Panel()
        self.assertFalse(cc5_skingen.ui_skingen_layer({"action": "explode", "index": 0})["success"])
        self.assertFalse(cc5_skingen.ui_skingen_layer({"action": "hide", "index": 9})["success"])
        self.assertFalse(cc5_skingen.ui_skingen_layer({"action": "hide"})["success"])

    def test_no_table(self) -> None:
        self.assertIn("not found", cc5_skingen.ui_skingen_layer({"action": "hide", "index": 0})["error"])

    def test_only_one_job_at_a_time(self) -> None:
        Panel()
        first = cc5_skingen.ui_skingen_layer({"action": "hide", "index": 0})
        second = cc5_skingen.ui_skingen_layer({"action": "hide", "index": 1})
        self.assertTrue(first["success"])
        self.assertFalse(second["success"])


class DeleteTest(UiTestCase):
    def test_delete_needs_confirm(self) -> None:
        panel = Panel()
        res = cc5_skingen.ui_skingen_layer({"action": "delete", "index": 0})
        self.assertFalse(res["success"])
        self.assertIn("confirm", res["error"])
        self.assertEqual(panel.deleted, [])

    def test_delete_selected_layer_through_the_menu(self) -> None:
        panel = Panel()
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "index": 1, "confirm": True}))
        self.assertTrue(res["success"], res)
        self.assertEqual(panel.deleted, ["selected:1"])
        self.assertEqual((res["layers_before"], res["layers_after"]), (3, 2))
        self.assertEqual([l["name"] for l in res["layers"]], ["Lips", "Blush"])

    def test_current_and_all_material_need_no_row(self) -> None:
        panel = Panel()
        self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "scope": "current_material", "confirm": True}))
        self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "scope": "all_material", "confirm": True}))
        self.assertEqual(panel.deleted, ["current_material", "all_material"])
        self.assertEqual(panel.table.select_calls, [])

    def test_bad_scope(self) -> None:
        Panel()
        res = cc5_skingen.ui_skingen_layer({"action": "delete", "scope": "everything", "confirm": True})
        self.assertFalse(res["success"])

    def test_a_confirmation_window_is_reported_and_left_open(self) -> None:
        panel = Panel()
        question = []
        panel.delete_button._menu._actions[0].on_trigger = lambda: question.append(
            self.dialog("Delete", "Delete the selected layer?", ["Yes", "No"]))
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "index": 0, "confirm": True}))
        self.assertFalse(res["success"])
        self.assertEqual(res["blocked_by"]["title"], "Delete")
        self.assertEqual([b.clicks for b in question[0].findChildren(self.q.QPushButton)], [0, 0])

    def test_button_without_a_menu_deletes_the_selected_layer_only(self) -> None:
        panel = Panel(with_menu=False)
        panel.delete_button.on_click = panel.delete_selected
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "index": 0, "confirm": True}))
        self.assertTrue(res["success"], res)
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "scope": "all_material", "confirm": True}))
        self.assertFalse(res["success"])
        self.assertIn("no menu", res["error"])

    def test_missing_menu_entry_lists_what_exists(self) -> None:
        panel = Panel()
        panel.delete_button._menu._actions.pop(0)
        res = self.finish(cc5_skingen.ui_skingen_layer({"action": "delete", "index": 0, "confirm": True}))
        self.assertFalse(res["success"])
        self.assertIn("Current Material", res["error"])


class RoutesTest(unittest.TestCase):
    def test_routes(self) -> None:
        self.assertEqual(set(cc5_skingen.ROUTES), {"/ui/skingen/state", "/ui/skingen/editor", "/ui/skingen/layer"})
        for _path, (action, fn) in cc5_skingen.ROUTES.items():
            self.assertTrue(action.startswith("ui_skingen_") and callable(fn))


if __name__ == "__main__":
    unittest.main()
