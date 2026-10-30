"""
/workflow/save refuses arguments it does not know (a mistyped "save as" used to overwrite the open
project), and every bridge route points at an action that exists (including the /ui/ routes).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from unittest import mock

from ui_support import UiTestCase, cc5_api, cc5_ui  # sets up sys.path and the RLPy stand-in

import RLPy  # noqa: E402  (the MagicMock stand-in)


class SaveProjectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.current = os.path.join(self.dir.name, "beyon_v61.ccProject").replace("\\", "/")
        self.saved: list[str] = []
        for patcher in (
            mock.patch.object(cc5_api, "_wf_current_project_path", return_value=self.current),
            mock.patch.object(RLPy.RFileIO, "SaveProject", side_effect=self.saved.append),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def target(self, name: str) -> str:
        return os.path.join(self.dir.name, name).replace("\\", "/")

    def test_file_path_saves_under_that_name(self) -> None:
        res = cc5_api.wf_save_project({"file_path": self.target("copy.ccProject")})
        self.assertTrue(res["success"], res)
        self.assertEqual(self.saved, [self.target("copy.ccProject")])
        self.assertEqual((res["in_place"], res["overwrote_existing"]), (False, False))

    def test_path_is_accepted_as_the_same_thing(self) -> None:
        res = cc5_api.wf_save_project({"path": self.target("copy2.ccProject")})
        self.assertTrue(res["success"], res)
        self.assertEqual(self.saved, [self.target("copy2.ccProject")])

    def test_both_names_must_agree(self) -> None:
        res = cc5_api.wf_save_project({"file_path": self.target("a.ccProject"), "path": self.target("b.ccProject")})
        self.assertFalse(res["success"])
        self.assertEqual(self.saved, [])

    def test_an_unknown_argument_saves_nothing(self) -> None:
        for body in ({"filename": self.target("x.ccProject")}, {"output_path": self.target("x.ccProject")},
                     {"file_path": self.target("x.ccProject"), "overwrite": True}):
            res = cc5_api.wf_save_project(body)
            self.assertFalse(res["success"], body)
            self.assertIn("nothing was saved", res["error"])
        self.assertEqual(self.saved, [])

    def test_no_argument_saves_in_place(self) -> None:
        res = cc5_api.wf_save_project({})
        self.assertTrue(res["success"], res)
        self.assertEqual(self.saved, [self.current])
        self.assertTrue(res["in_place"])

    def test_overwriting_an_existing_file_is_reported(self) -> None:
        existing = self.target("old.ccProject")
        with open(existing, "wb") as fh:
            fh.write(b"x")
        res = cc5_api.wf_save_project({"file_path": existing})
        self.assertTrue(res["overwrote_existing"])

    def test_safety_copies_and_wrong_extensions_are_still_refused(self) -> None:
        self.assertFalse(cc5_api.wf_save_project({"file_path": self.target("x_hs_ok.ccProject")})["success"])
        self.assertFalse(cc5_api.wf_save_project({"file_path": self.target("x.txt")})["success"])
        self.assertEqual(self.saved, [])

    def test_no_known_current_path_still_asks_for_one(self) -> None:
        with mock.patch.object(cc5_api, "_wf_current_project_path", return_value=""):
            res = cc5_api.wf_save_project({})
        self.assertFalse(res["success"])
        self.assertIn("file_path is required", res["error"])


class RouteTableTest(UiTestCase):
    """Patch a stand-in server the way the bridge does and check the tables hang together."""

    def patched(self) -> types.SimpleNamespace:
        srv = types.SimpleNamespace(ACTION_MAP={}, POST_ROUTES={}, GET_ROUTES={}, REQUIRED_PARAMS={})
        with mock.patch.dict(sys.modules, {"server": srv}):
            cc5_api._auto_patch_server()
        return srv

    def test_every_route_has_an_action(self) -> None:
        srv = self.patched()
        for path, action in {**srv.POST_ROUTES, **srv.GET_ROUTES}.items():
            self.assertIn(action, srv.ACTION_MAP, f"{path} -> {action} has no handler")

    def test_the_two_routes_that_used_to_miss_their_handler(self) -> None:
        srv = self.patched()
        for action in ("wf_dialog_table_combo", "wf_import_blender"):
            handler = srv.ACTION_MAP[action]
            self.assertIs(getattr(handler, "_cc5_guarded", handler), getattr(cc5_api, action))

    def test_other_actions_wait_while_a_ui_job_runs_but_the_read_only_ones_do_not(self) -> None:
        srv = self.patched()                          # (reloads cc5_ui, which drops the fake Qt: patch it again)
        busy = {"id": "preset-1", "kind": "preset"}
        with mock.patch.object(cc5_ui, "_qt", return_value=self.q),                 mock.patch.object(cc5_ui, "running_job", return_value=busy):
            refused = srv.ACTION_MAP["get_avatars"]({})
            self.assertFalse(refused["success"])
            self.assertIn("preset-1", refused["error"])
            for action, body in (("ui_job", {"job_id": "x"}), ("ui_windows", {}), ("ui_skingen_state", {})):
                self.assertNotIn("was NOT run", str(srv.ACTION_MAP[action](body)), action)

    def test_patching_twice_does_not_wrap_twice(self) -> None:
        srv = types.SimpleNamespace(ACTION_MAP={}, POST_ROUTES={}, GET_ROUTES={}, REQUIRED_PARAMS={})
        with mock.patch.dict(sys.modules, {"server": srv}):
            cc5_api._auto_patch_server()
            cc5_api._auto_patch_server()
        handler = srv.ACTION_MAP["get_avatars"]
        self.assertFalse(hasattr(handler._cc5_guarded, "_cc5_guarded"))

    def test_ui_routes_are_registered(self) -> None:
        srv = self.patched()
        for path in cc5_api._UI_ROUTE_PATHS:
            action = srv.POST_ROUTES[path]
            self.assertTrue(action.startswith("ui_"), path)
            self.assertNotEqual(action, "ui_modules_missing", path)
            self.assertTrue(callable(srv.ACTION_MAP[action]))

    def test_a_missing_helper_module_gives_a_clear_error_not_a_crash(self) -> None:
        srv = types.SimpleNamespace(ACTION_MAP={}, POST_ROUTES={}, GET_ROUTES={}, REQUIRED_PARAMS={})
        only_core = {"cc5_ui": cc5_ui, "cc5_uiview": sys.modules["cc5_uiview"]}
        with mock.patch.object(cc5_api, "_load_ui_modules", return_value=only_core):
            cc5_api._patch_ui_routes(srv)
        self.assertNotEqual(srv.POST_ROUTES["/ui/windows"], "ui_modules_missing")
        self.assertEqual(srv.POST_ROUTES["/ui/preset/apply"], "ui_modules_missing")
        self.assertEqual(srv.POST_ROUTES["/ui/skingen/layer"], "ui_modules_missing")
        self.assertEqual(srv.POST_ROUTES["/ui/click"], "ui_modules_missing")
        res = srv.ACTION_MAP["ui_modules_missing"]({})
        self.assertFalse(res["success"])
        self.assertIn("cc5_content.py", res["error"])
        self.assertIn("cc5_uiclick.py", res["error"])
        self.assertIn("cc5_uiview.py", res["error"])

    def test_load_survives_a_broken_module(self) -> None:
        real_import = __import__("importlib").import_module

        def flaky(name, *args, **kwargs):
            if name == "cc5_content":
                raise ImportError("boom")
            return real_import(name, *args, **kwargs)

        with mock.patch("importlib.import_module", side_effect=flaky), \
                mock.patch.dict(sys.modules, {}, clear=False):
            sys.modules.pop("cc5_content", None)
            loaded = cc5_api._load_ui_modules()
        self.assertNotIn("cc5_content", loaded)
        self.assertIn("cc5_ui", loaded)


if __name__ == "__main__":
    unittest.main()
