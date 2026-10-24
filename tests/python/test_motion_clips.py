"""
motion/clear also deletes facial clips, and load_asset answers the expression questions.

An .iTalk load fills the face (and viseme) component, not the skeleton; a leftover
expression went into the next motion-only FBX export (10-25). These tests run outside CC5
(RLPy is a MagicMock).

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

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


class _Comp:
    """A component holding clips; viseme=True names deletion like RIVisemeComponent."""

    def __init__(self, n: int, viseme: bool = False) -> None:
        self.clips = [mock.MagicMock(name=f"clip{i}") for i in range(n)]
        if viseme:
            self.RemoveVisemesClip = lambda _time: self.clips.pop()
        else:
            self.DeleteClip = lambda clip: self.clips.remove(clip)

    def GetClipCount(self) -> int:
        return len(self.clips)

    def GetClip(self, i: int):
        return self.clips[i]


def _avatar(skel: int, face: int, viseme: int):
    av = mock.MagicMock(name="avatar")
    comps = {"skeleton": _Comp(skel), "face": _Comp(face), "viseme": _Comp(viseme, viseme=True)}
    av.GetSkeletonComponent.return_value = comps["skeleton"]
    av.GetFaceComponent.return_value = comps["face"]
    av.GetVisemeComponent.return_value = comps["viseme"]
    av.GetMorphComponent.return_value = object()          # no clips: left out
    return av, comps


class MotionClearTest(unittest.TestCase):
    def test_clears_body_face_and_viseme_clips(self) -> None:
        av, comps = _avatar(2, 1, 1)
        with mock.patch.object(cc5_api, "get_first_avatar", return_value=av):
            res = cc5_api.wf_motion_clear({})
        self.assertTrue(res["success"], res)
        self.assertEqual((res["deleted"], res["face_deleted"]), (2, 1))
        self.assertEqual(res["other_deleted"], {"viseme": 1})
        self.assertEqual([c.GetClipCount() for c in comps.values()], [0, 0, 0])

    def test_face_false_keeps_facial_clips(self) -> None:
        av, comps = _avatar(1, 1, 1)
        with mock.patch.object(cc5_api, "get_first_avatar", return_value=av):
            res = cc5_api.wf_motion_clear({"face": False})
        self.assertTrue(res["success"], res)
        self.assertEqual(comps["face"].GetClipCount(), 1)
        self.assertEqual(comps["viseme"].GetClipCount(), 1)

    def test_dry_run_only_counts(self) -> None:
        av, comps = _avatar(0, 1, 0)
        with mock.patch.object(cc5_api, "get_first_avatar", return_value=av):
            res = cc5_api.wf_motion_clear({"dry_run": True})
        self.assertEqual((res["clips"], res["face_clips"]), (0, 1))
        self.assertEqual(comps["face"].GetClipCount(), 1)


class LoadAnswersTest(unittest.TestCase):
    def test_known_expression_questions_have_answers(self) -> None:
        rules = cc5_api._WfAutoAnswer(cc5_api._LOAD_AUTO_ANSWERS).rules
        text = ("the italk file contains custom expressions which can not be found on the target "
                "character. the result may not be the same as the original.")
        self.assertEqual([v for k, v in rules.items() if k in text], ["ExPlus"])

    def test_empty_rules_answer_nothing(self) -> None:
        with cc5_api._WfAutoAnswer({}) as auto:
            pass
        self.assertEqual(auto.pressed, [])


class MaterialOwnerTest(unittest.TestCase):
    """Material routes key the item that owns the mesh, not the avatar (10-25)."""

    def _scene(self):
        avatar = mock.MagicMock(name="avatar")
        cloth = mock.MagicMock(name="corset")
        cloth.GetName.return_value = "Corset_low"
        cloth.GetMeshNames.return_value = ["Corset_low"]
        avatar.GetClothes.return_value = [cloth]
        avatar.GetHairs.return_value = []
        avatar.GetAccessories.return_value = []
        avatar.GetMeshNames.return_value = ["CC_Base_Body", "Corset_low"]
        for obj in (avatar, cloth):
            obj.GetMaterialComponent.return_value.GetMaterialNames.return_value = ["corset_satin", "Std_Skin_Body"]
        return avatar, cloth

    def test_cloth_mesh_uses_the_cloth_component(self) -> None:
        avatar, cloth = self._scene()
        comp, err = cc5_api._get_valid_mesh_material(avatar, "Corset_low", "corset_satin")
        self.assertIsNone(err)
        self.assertIs(comp, cloth.GetMaterialComponent.return_value)

    def test_body_mesh_uses_the_avatar_component(self) -> None:
        avatar, _cloth = self._scene()
        comp, err = cc5_api._get_valid_mesh_material(avatar, "CC_Base_Body", "Std_Skin_Body")
        self.assertIsNone(err)
        self.assertIs(comp, avatar.GetMaterialComponent.return_value)



class ExpressionKeysTest(unittest.TestCase):
    """Batch expression keys: every frame in one call; a failed key is reported (10-25)."""

    def _avatar(self, error_frames=()):
        avatar = mock.MagicMock(name="avatar")
        face = avatar.GetFaceComponent.return_value
        face.GetExpressionGroups.return_value = ["MouthBase"]
        face.GetExpressionNames.return_value = ["Mouth_Corner_Pull_L", "Mouth_Corner_Pull_R"]
        calls = []

        def add(time, names, weights, interval):
            calls.append((time, list(names), list(weights)))
            status = mock.MagicMock()
            status.IsError.return_value = time in error_frames
            return status
        face.AddExpressionKeys.side_effect = add
        return avatar, calls

    def _fps(self):
        fps = mock.MagicMock()
        fps.IndexedFrameTime.side_effect = lambda f: f
        return fps

    def test_keys_every_frame_in_one_call(self) -> None:
        avatar, calls = self._avatar()
        keys = [{"frame": f, "expressions": {"Mouth_Corner_Pull_L": 0.8, "Bogus": 1.0}} for f in range(5)]
        with mock.patch.object(cc5_api, "get_first_avatar", return_value=avatar),                 mock.patch.object(cc5_api.RLPy.RGlobal, "GetFps", return_value=self._fps()):
            res = cc5_api.wf_expression_keys({"keys": keys})
        self.assertTrue(res["success"], res)
        self.assertEqual(res["keyed_frames"], 5)
        self.assertEqual(res["unknown"], ["Bogus"])
        self.assertEqual([c[0] for c in calls], [0, 1, 2, 3, 4])

    def test_a_failed_key_fails_the_call(self) -> None:
        avatar, _calls = self._avatar(error_frames={2})
        keys = [{"frame": f, "expressions": {"Mouth_Corner_Pull_R": 0.5}} for f in range(4)]
        with mock.patch.object(cc5_api, "get_first_avatar", return_value=avatar),                 mock.patch.object(cc5_api.RLPy.RGlobal, "GetFps", return_value=self._fps()):
            res = cc5_api.wf_expression_keys({"keys": keys})
        self.assertFalse(res["success"])
        self.assertEqual(res["failed_frames"], [2])


if __name__ == "__main__":
    unittest.main()
