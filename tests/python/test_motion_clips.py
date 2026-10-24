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


if __name__ == "__main__":
    unittest.main()
