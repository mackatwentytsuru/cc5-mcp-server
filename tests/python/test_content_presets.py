"""
cc5_content: listing presets and applying them with LoadFile while the known question windows
are answered.

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any
from unittest import mock

from skingen_panel import Panel
from ui_support import UiTestCase, cc5_ui, fake_qt

import cc5_content  # noqa: E402
import RLPy  # noqa: E402  (the MagicMock stand-in)

TREE = {
    "$/Makeup/Lip Makeup": {"files": ["C:/lib/Makeup/Lip Makeup/Nature.ccSkinGenPreset",
                                      "C:/lib/Makeup/Lip Makeup/Rouge.ccSkinGenPreset",
                                      "C:/lib/Makeup/Lip Makeup/Rouge.png"],
                            "folders": ["Special"]},
    "$/Makeup/Lip Makeup/Special": {"files": ["C:/lib/Makeup/Lip Makeup/Special/Glitter.ccSkinGenPreset"], "folders": []},
    "$/Avatar Preset/Eyelash": {"files": [], "folders": ["$/Avatar Preset/Eyelash/1.HD Natural"]},
    "$/Avatar Preset/Eyelash/1.HD Natural": {"files": ["C:/lib/Avatar Preset/Eyelash/1.HD Natural/Curled.ccAvatarPreset"],
                                              "folders": []},
}


def _files(folder: str) -> list[str]:
    return TREE.get(folder, {"files": []})["files"]


def _folders(folder: str) -> list[str]:
    return TREE.get(folder, {"folders": []})["folders"]


class ListTest(unittest.TestCase):
    def setUp(self) -> None:
        for patcher in (mock.patch.object(RLPy.RApplication, "GetContentFilesInFolder", side_effect=_files),
                        mock.patch.object(RLPy.RApplication, "GetContentFoldersInFolder", side_effect=_folders),
                        mock.patch.object(os.path, "isfile", side_effect=lambda p: p.endswith((".ccSkinGenPreset", ".ccAvatarPreset")))):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_lists_a_category_recursively_without_thumbnails(self) -> None:
        res = cc5_content.ui_list_presets({"category": "makeup_lip"})
        self.assertTrue(res["success"], res)
        self.assertEqual([e["name"] for e in res["presets"]], ["Nature", "Rouge", "Glitter"])
        self.assertEqual(res["presets"][2]["folder"], "$/Makeup/Lip Makeup/Special")
        self.assertTrue(all(e["installed"] for e in res["presets"]))

    def test_not_recursive(self) -> None:
        res = cc5_content.ui_list_presets({"category": "makeup_lip", "recursive": False})
        self.assertEqual([e["name"] for e in res["presets"]], ["Nature", "Rouge"])

    def test_sub_folders_given_as_full_paths_are_followed(self) -> None:
        res = cc5_content.ui_list_presets({"category": "eyelash_preset"})
        self.assertEqual([e["name"] for e in res["presets"]], ["Curled"])

    def test_query_ext_and_names(self) -> None:
        res = cc5_content.ui_list_presets({"category": "makeup_lip", "query": "ro", "names": ["Rouge", "French Rose"]})
        self.assertEqual([e["name"] for e in res["presets"]], ["Rouge"])
        self.assertEqual(res["missing"], ["French Rose"])
        res = cc5_content.ui_list_presets({"category": "makeup_lip", "ext": ".CCSKINGENPRESET", "limit": 2})
        self.assertEqual((len(res["presets"]), res["total"], res["truncated"]), (2, 3, True))

    def test_list_folders(self) -> None:
        res = cc5_content.ui_list_presets({"folder": "$/Makeup/Lip Makeup", "list_folders": True})
        self.assertEqual(res["subfolders"], ["$/Makeup/Lip Makeup/Special"])

    def test_a_path_that_is_not_a_content_folder_is_refused(self) -> None:
        for folder in ("C:/Windows", "$/../etc", "Makeup"):
            self.assertFalse(cc5_content.ui_list_presets({"folder": folder})["success"], folder)
        self.assertFalse(cc5_content.ui_list_presets({"category": "nope"})["success"])
        self.assertFalse(cc5_content.ui_list_presets({})["success"])

    def test_child_folder_forms(self) -> None:
        join = cc5_content._child_folder
        self.assertEqual(join("$/A", "B"), "$/A/B")
        self.assertEqual(join("$/A", "$/A/B/"), "$/A/B")
        self.assertEqual(join("$/A/", "C:/Lib/A/B"), "$/A/B")


class DiskFallbackTest(unittest.TestCase):
    def test_lists_from_the_content_roots_when_rlpy_cannot(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            lip = os.path.join(root, "Makeup", "Lip Makeup")
            os.makedirs(os.path.join(lip, "Sub"))
            for name in ("Nature.ccSkinGenPreset", "Nature.png", os.path.join("Sub", "Deep.ccSkinGenPreset")):
                with open(os.path.join(lip, name), "wb") as fh:
                    fh.write(b"x")
            with mock.patch.object(cc5_content, "_rlpy_listing", return_value=False), \
                    mock.patch.dict(os.environ, {"CC5_CONTENT_ROOTS": root}):
                res = cc5_content.ui_list_presets({"category": "makeup_lip"})
        self.assertEqual(sorted(e["name"] for e in res["presets"]), ["Deep", "Nature"])
        self.assertTrue(all(e["installed"] for e in res["presets"]))


class PathCheckTest(unittest.TestCase):
    def test_denied_and_unknown_extensions(self) -> None:
        for path in ("C:/x/scene.ccProject", "C:/x/char.ccAvatar", "C:/x/model.fbx", "C:/x/notes.txt", "C:/x/file"):
            self.assertIsNotNone(cc5_content.check_preset_path(path), path)

    def test_traversal_and_missing_file(self) -> None:
        self.assertIn("traversal", cc5_content.check_preset_path("C:/x/../y/Nature.ccSkinGenPreset"))
        self.assertIn("not found", cc5_content.check_preset_path("C:/nowhere/Nature.ccSkinGenPreset"))

    def test_content_files_pass(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            for name in ("a.ccSkinGenPreset", "b.rlEyelashElement", "c.ccAvatarPreset", "d.iMtl"):
                path = os.path.join(root, name)
                with open(path, "wb") as fh:
                    fh.write(b"x")
                self.assertIsNone(cc5_content.check_preset_path(path), name)


class ApplyTest(UiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.avatar = mock.Mock()
        self.avatar.GetName.return_value = "Beyon"
        self.items = ["Cloth:Lash_Up_Old", "Cloth:Lash_Low_Old", "Hair:Bob"]
        self.loads: list[str] = []
        self.on_load = lambda path: None
        self.status = mock.Mock()
        self.status.IsError.return_value = False
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        for patcher in (
            mock.patch.object(RLPy.RScene, "GetAvatars", return_value=[self.avatar]),
            mock.patch.object(RLPy.RFileIO, "LoadFile", side_effect=self.load_file),
            mock.patch.object(cc5_content, "scene_items", side_effect=lambda: sorted(self.items)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        RLPy.RScene.SelectObject.reset_mock()

    def file(self, name: str) -> str:
        path = os.path.join(self.files.name, name).replace("\\", "/")
        with open(path, "wb") as fh:
            fh.write(b"x")
        return path

    def load_file(self, path: str) -> Any:
        """Stands in for the blocking LoadFile: a nested loop where the answerer's timer fires."""
        self.loads.append(path)
        self.on_load(path)
        for _ in range(8):
            for timer in list(fake_qt.Timer.active_timers):
                timer.fire()
        return self.status

    def close_on_click(self, dlg) -> None:
        for b in dlg.findChildren(self.q.QPushButton):
            b.on_click = lambda d=dlg: setattr(d, "_visible", False)

    def apply(self, **body) -> dict:
        return self.finish(cc5_content.ui_apply_preset(body))

    def test_eyelash_preset_is_applied_with_the_apply_window_answered(self) -> None:
        path = self.file("Curled.ccAvatarPreset")
        windows = []

        def on_load(_p: str) -> None:
            dlg = self.dialog("Apply Character Preset", "Apply this preset?", ["Apply", "Cancel"],
                              [("Restore neutral lash strip", False)])
            self.close_on_click(dlg)
            windows.append(dlg)
            self.items[:] = ["Cloth:Lash_Up_Curled", "Cloth:Lash_Low_Curled", "Hair:Bob"]
        self.on_load = on_load
        res = self.apply(file_path=path, watch_prefix="Lash_")
        self.assertTrue(res["success"], res)
        entry = res["files"][0]
        self.assertEqual(entry["added"], ["Cloth:Lash_Low_Curled", "Cloth:Lash_Up_Curled"])
        self.assertEqual(entry["removed"], ["Cloth:Lash_Low_Old", "Cloth:Lash_Up_Old"])
        self.assertEqual(entry["watched"], ["Lash_Low_Curled", "Lash_Up_Curled"])
        self.assertEqual([a["pressed"] for a in res["answered"]], ["apply"])
        self.assertTrue(windows[0].findChildren(self.q.QCheckBox)[0].isChecked())
        RLPy.RScene.SelectObject.assert_called_with(self.avatar)
        self.assertEqual(fake_qt.Timer.active_timers, [])

    def test_two_element_files_are_applied_in_order(self) -> None:
        up, low = self.file("Wavy_Up.rlEyelashElement"), self.file("Extended_Low.rlEyelashElement")
        res = self.apply(file_paths=[up, low])
        self.assertTrue(res["success"], res)
        self.assertEqual(self.loads, [up, low])

    def test_a_failing_file_stops_the_rest(self) -> None:
        a, b = self.file("a.ccAvatarPreset"), self.file("b.ccAvatarPreset")
        self.status.IsError.return_value = True
        res = self.apply(file_paths=[a, b])
        self.assertFalse(res["success"])
        self.assertEqual(self.loads, [a])
        self.assertEqual(res["skipped"], [b])
        self.assertIn("LoadFile reported an error", res["error"])

    def test_loadfile_raising_is_reported_per_file(self) -> None:
        path = self.file("a.ccAvatarPreset")
        self.on_load = lambda p: (_ for _ in ()).throw(RuntimeError("No character picked."))
        res = self.apply(file_path=path)
        self.assertFalse(res["success"])
        self.assertIn("No character picked", res["error"])
        self.assertEqual(fake_qt.Timer.active_timers, [])

    def test_an_unknown_window_is_reported_not_answered(self) -> None:
        path = self.file("a.ccAvatarPreset")
        windows = []
        self.on_load = lambda p: windows.append(self.dialog("Overwrite", "Overwrite the existing preset?", ["Yes", "No"]))
        res = self.apply(file_path=path)
        self.assertFalse(res["success"])
        self.assertEqual(res["files"][0]["blocked_by"]["title"], "Overwrite")
        self.assertEqual([b.clicks for b in windows[0].findChildren(self.q.QPushButton)], [0, 0])

    def test_a_license_window_is_never_pressed(self) -> None:
        path = self.file("a.ccAvatarPreset")
        windows = []
        self.on_load = lambda p: windows.append(self.dialog("Apply", "Your license has expired. Apply", ["Apply"]))
        res = self.apply(file_path=path)
        self.assertFalse(res["success"])
        self.assertEqual(windows[0].findChildren(self.q.QPushButton)[0].clicks, 0)
        self.assertEqual(res["files"][0]["blocked_by"]["needs_human"], "license")

    def test_skingen_layer_question_defaults_to_replace(self) -> None:
        path = self.file("Nature.ccSkinGenPreset")
        panel = Panel(layers=("Lips",))
        windows = []

        def on_load(_p: str) -> None:
            dlg = self.dialog("SkinGen", "Do you want to add a new layer or replace the current layer?",
                              ["Add", "Replace", "Cancel"])
            self.close_on_click(dlg)
            windows.append(dlg)
        self.on_load = on_load
        res = self.apply(file_path=path)
        self.assertTrue(res["success"], res)
        self.assertEqual([a["pressed"] for a in res["answered"]], ["replace"])
        self.assertEqual(res["skingen"], {"editor_active": True, "layers": ["Lips"]})
        self.assertIn("SkinGen editor is open", res["note"])
        self.assertEqual(panel.switch.clicks, 0)

    def test_layer_choice_add(self) -> None:
        path = self.file("Nature.ccSkinGenPreset")
        self.on_load = lambda p: self.close_on_click(self.dialog(
            "SkinGen", "add a new layer or replace the current layer?", ["Add", "Replace"]))
        res = self.apply(file_path=path, answers={"layer_choice": "add"})
        self.assertEqual([a["pressed"] for a in res["answered"]], ["add"])

    def test_bad_requests_are_refused_before_any_load(self) -> None:
        path = self.file("a.ccAvatarPreset")
        self.assertFalse(cc5_content.ui_apply_preset({})["success"])
        self.assertFalse(cc5_content.ui_apply_preset({"file_paths": [path] * 11})["success"])
        self.assertFalse(cc5_content.ui_apply_preset({"file_path": self.file("scene.ccProject")})["success"])
        self.assertFalse(cc5_content.ui_apply_preset({"file_path": path, "answers": {"press": "anything"}})["success"])
        self.assertFalse(cc5_content.ui_apply_preset({"file_path": path, "avatar_name": "Nobody"})["success"])
        self.assertEqual(self.loads, [])

    def test_no_avatar(self) -> None:
        path = self.file("a.ccAvatarPreset")
        with mock.patch.object(RLPy.RScene, "GetAvatars", return_value=[]):
            self.assertIn("avatar not found", cc5_content.ui_apply_preset({"file_path": path})["error"])

    def test_routes(self) -> None:
        self.assertEqual(set(cc5_content.ROUTES), {"/ui/preset/list", "/ui/preset/apply"})


if __name__ == "__main__":
    unittest.main()
