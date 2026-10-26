"""
Physics (Soft Cloth) workflow routes in cc5_api, against a fake RLPy.

The fake RIPhysicsComponent has only the methods that exist in CC5's RLPy.py
(GetSoftPhysicsMeshNameList, SetSoftPhysXProperty, SetPhysicsSoftColthWeightMap,
...). Runs with plain CPython outside CC5:

    python -m unittest discover -s tests/python -v      (or: npm run test:py)
"""

from __future__ import annotations

import os
import sys
import tempfile
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
    def __init__(self, is_error: bool = False) -> None:
        self._is_error = is_error

    def IsError(self) -> bool:  # noqa: N802 - mirrors RLPy
        return self._is_error

    def GetStatusCode(self) -> int:  # noqa: N802
        return 1 if self._is_error else 0


class FakePhysics:
    """Stand-in for RIPhysicsComponent with the RLPy.py method names."""

    def __init__(self, meshes=None, clamp=None, known_shapes=("CC_Base_Hip", "CC_Base_Spine02")):
        self.meshes = {"Skirt": ["Skirt_Mat"]} if meshes is None else meshes
        self.active = False
        self.props: dict[tuple[str, str, str], float] = {}
        self.clamp = clamp or {}
        self.shapes = {name: {"enabled": True, "value": 0.5} for name in known_shapes}
        self.weight_maps: dict[tuple[str, str], str] = {}
        self.calls: list[tuple] = []

    def GetSoftPhysicsMeshNameList(self):  # noqa: N802
        return list(self.meshes)

    def GetSoftPhysicsMaterialNameList(self, mesh):  # noqa: N802
        return list(self.meshes.get(mesh, []))

    def IsActivatePhysicsEnable(self):  # noqa: N802
        return self.active

    def SetActivatePhysicsEnable(self, enable):  # noqa: N802
        self.calls.append(("activate", enable))
        self.active = enable
        return FakeStatus()

    def GetSoftPhysXProperty(self, mesh, material, key):  # noqa: N802
        return self.props.get((mesh, material, key), 1.0)

    def SetSoftPhysXProperty(self, mesh, material, key, value):  # noqa: N802
        self.calls.append(("prop", mesh, material, key, value))
        if key in self.clamp:
            value = self.clamp[key]
        self.props[(mesh, material, key)] = value
        return FakeStatus()

    def GetSoftPhysXCollisionEnable(self, mesh, material, name):  # noqa: N802
        if name not in self.shapes:
            raise RuntimeError("unknown collision")
        return self.shapes[name]["enabled"]

    def GetSoftPhysXCollisionValue(self, mesh, material, name):  # noqa: N802
        if name not in self.shapes:
            raise RuntimeError("unknown collision")
        return self.shapes[name]["value"]

    def SetSoftPhysXCollisionEnable(self, mesh, material, name, enable):  # noqa: N802
        self.calls.append(("col_enable", name, enable))
        self.shapes[name]["enabled"] = enable
        return FakeStatus()

    def SetSoftPhysXCollisionValue(self, mesh, material, name, value):  # noqa: N802
        self.calls.append(("col_value", name, value))
        self.shapes[name]["value"] = value
        return FakeStatus()

    def SetPhysicsSoftColthWeightMap(self, *args):  # noqa: N802
        self.calls.append(("weight_map",) + args)
        mesh, material, path = args
        self.weight_maps[(mesh, material)] = path
        return FakeStatus()

    def GetPhysicsSoftColthWeightMap(self, mesh, material):  # noqa: N802
        return object() if (mesh, material) in self.weight_maps else None


class FakeItem:
    def __init__(self, name: str, physics=None, has_getter: bool = True) -> None:
        self._name = name
        self._physics = physics
        if has_getter:
            self.GetPhysicsComponent = lambda: self._physics  # noqa: N815

    def GetName(self) -> str:  # noqa: N802
        return self._name


def fake_rlpy() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        RGlobal=types.SimpleNamespace(BeginAction=lambda name: None, EndAction=lambda: None),
    )


class PhysicsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.physics = FakePhysics()
        self.item = FakeItem("Skirt", self.physics)
        self.kind = "cloth"
        patches = [
            mock.patch.object(cc5_api, "RLPy", fake_rlpy()),
            mock.patch.object(
                cc5_api, "_wf_resolve", side_effect=lambda name=None, item_id=None: (self.item, self.kind, None)
            ),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)


class PhysicsInfoTests(PhysicsTestCase):
    def test_info_lists_meshes_and_properties(self) -> None:
        result = cc5_api.wf_physics_info({"item_name": "Skirt"})
        self.assertTrue(result["success"], result)
        self.assertEqual(result["meshes"], [{"mesh": "Skirt", "materials": ["Skirt_Mat"]}])
        self.assertFalse(result["activate"])
        self.assertIn("TetherLimit", result["properties"])
        self.assertTrue(result["weight_map_import"])

    def test_prop_without_physics_component_gets_clear_error(self) -> None:
        self.item = FakeItem("Box", has_getter=False)
        self.kind = "prop"
        result = cc5_api.wf_physics_info({"item_name": "Box"})
        self.assertFalse(result["success"])
        self.assertIn("no GetPhysicsComponent", result["error"])
        self.assertIn("Props have no physics component", result["error"])

    def test_none_component(self) -> None:
        self.item = FakeItem("Hat", physics=None)
        result = cc5_api.wf_physics_info({"item_name": "Hat"})
        self.assertFalse(result["success"])
        self.assertIn("returned None", result["error"])


class PhysicsActivateTests(PhysicsTestCase):
    def test_activate_on_and_read_back(self) -> None:
        result = cc5_api.wf_physics_activate({"item_name": "Skirt", "enable": True})
        self.assertTrue(result["success"], result)
        self.assertTrue(result["activate"])
        self.assertTrue(result["verified"])
        self.assertEqual(self.physics.calls, [("activate", True)])

    def test_enable_must_be_bool(self) -> None:
        result = cc5_api.wf_physics_activate({"item_name": "Skirt", "enable": "yes"})
        self.assertFalse(result["success"])
        self.assertEqual(self.physics.calls, [])

    def test_read_back_mismatch_fails(self) -> None:
        self.physics.SetActivatePhysicsEnable = lambda enable: FakeStatus()  # ignored
        result = cc5_api.wf_physics_activate({"item_name": "Skirt", "enable": True})
        self.assertFalse(result["success"])
        self.assertIn("still False", result["error"])

    def test_refused_status_fails(self) -> None:
        self.physics.SetActivatePhysicsEnable = lambda enable: FakeStatus(is_error=True)
        result = cc5_api.wf_physics_activate({"item_name": "Skirt", "enable": True})
        self.assertFalse(result["success"])
        self.assertIn("refused", result["error"])


class WeightMapTests(PhysicsTestCase):
    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.png = os.path.join(self._tmp.name, "skirt_weight.png")
        with open(self.png, "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n")

    def test_loads_with_file_path_overload(self) -> None:
        result = cc5_api.wf_physics_load_weight_map({"item_name": "Skirt", "file_path": self.png})
        self.assertTrue(result["success"], result)
        self.assertEqual(result["mesh"], "Skirt")
        self.assertEqual(result["material"], "Skirt_Mat")
        self.assertTrue(result["weight_map_present"])
        self.assertEqual(self.physics.calls, [("weight_map", "Skirt", "Skirt_Mat", self.png)])

    def test_unknown_material_is_allowed_with_note(self) -> None:
        result = cc5_api.wf_physics_load_weight_map(
            {"item_name": "Skirt", "mesh_name": "Skirt", "material_name": "Belt", "file_path": self.png}
        )
        self.assertTrue(result["success"], result)
        self.assertTrue(any("Belt" in note for note in result["notes"]))

    def test_rejects_non_png_and_missing_file(self) -> None:
        bad = cc5_api.wf_physics_load_weight_map({"item_name": "Skirt", "file_path": self.png[:-4] + ".jpg"})
        self.assertFalse(bad["success"])
        self.assertIn("extension", bad["error"])
        missing = cc5_api.wf_physics_load_weight_map(
            {"item_name": "Skirt", "file_path": os.path.join(self._tmp.name, "nope.png")}
        )
        self.assertFalse(missing["success"])
        self.assertIn("not found", missing["error"])

    def test_missing_rlpy_method_points_to_gui(self) -> None:
        del FakePhysics.SetPhysicsSoftColthWeightMap  # restored below
        self.addCleanup(setattr, FakePhysics, "SetPhysicsSoftColthWeightMap", _SET_WEIGHT_MAP)
        result = cc5_api.wf_physics_load_weight_map({"item_name": "Skirt", "file_path": self.png})
        self.assertFalse(result["success"])
        self.assertTrue(result["gui_only"])
        self.assertIn("Weight Map", result["error"])

    def test_exception_points_to_gui(self) -> None:
        def boom(*args):
            raise RuntimeError("bad overload")

        self.physics.SetPhysicsSoftColthWeightMap = boom
        result = cc5_api.wf_physics_load_weight_map({"item_name": "Skirt", "file_path": self.png})
        self.assertFalse(result["success"])
        self.assertTrue(result["gui_only"])
        self.assertIn("bad overload", result["error"])


_SET_WEIGHT_MAP = FakePhysics.SetPhysicsSoftColthWeightMap


class SoftParamsTests(PhysicsTestCase):
    def test_get_all_params(self) -> None:
        result = cc5_api.wf_physics_get_params({"item_name": "Skirt"})
        self.assertTrue(result["success"], result)
        self.assertEqual(set(result["params"]), set(cc5_api._WF_SOFT_PHYSX_PROPERTIES))

    def test_get_rejects_unknown_name(self) -> None:
        result = cc5_api.wf_physics_get_params({"item_name": "Skirt", "names": ["Mass", "Wobble"]})
        self.assertFalse(result["success"])
        self.assertIn("Wobble", result["error"])
        self.assertIn("Mass", result["allowed"])

    def test_set_writes_and_reads_back(self) -> None:
        result = cc5_api.wf_physics_set_params(
            {"item_name": "Skirt", "values": {"mass": 2.5, "Self Collision": True}}
        )
        self.assertTrue(result["success"], result)
        self.assertEqual(result["before"], {"Mass": 1.0, "SelfCollision": 1.0})
        self.assertEqual(result["after"], {"Mass": 2.5, "SelfCollision": 1.0})
        self.assertIn(("prop", "Skirt", "Skirt_Mat", "Mass", 2.5), self.physics.calls)
        self.assertIn(("prop", "Skirt", "Skirt_Mat", "SelfCollision", 1.0), self.physics.calls)

    def test_set_unknown_name_touches_nothing(self) -> None:
        result = cc5_api.wf_physics_set_params({"item_name": "Skirt", "values": {"Mass": 1, "Wobble": 2}})
        self.assertFalse(result["success"])
        self.assertEqual(self.physics.calls, [])

    def test_set_rejects_non_numbers(self) -> None:
        result = cc5_api.wf_physics_set_params({"item_name": "Skirt", "values": {"Mass": "heavy"}})
        self.assertFalse(result["success"])
        self.assertEqual(self.physics.calls, [])

    def test_set_reports_clamped_value(self) -> None:
        self.physics.clamp = {"Mass": 1.0}
        result = cc5_api.wf_physics_set_params({"item_name": "Skirt", "values": {"Mass": 50}})
        self.assertFalse(result["success"])
        self.assertIn("read-back differs for Mass", result["error"])
        self.assertEqual(result["mismatched"]["Mass"], {"wanted": 50.0, "got": 1.0})

    def test_unknown_mesh_is_rejected_with_listing(self) -> None:
        result = cc5_api.wf_physics_get_params({"item_name": "Skirt", "mesh_name": "Top"})
        self.assertFalse(result["success"])
        self.assertEqual(result["meshes"], [{"mesh": "Skirt", "materials": ["Skirt_Mat"]}])

    def test_several_meshes_need_a_name(self) -> None:
        self.physics.meshes = {"Top": ["A"], "Skirt": ["B", "C"]}
        result = cc5_api.wf_physics_get_params({"item_name": "Dress"})
        self.assertFalse(result["success"])
        self.assertIn("mesh_name is required", result["error"])
        material = cc5_api.wf_physics_get_params({"item_name": "Dress", "mesh_name": "Skirt"})
        self.assertFalse(material["success"])
        self.assertIn("material_name is required", material["error"])

    def test_no_soft_cloth_meshes(self) -> None:
        self.physics.meshes = {}
        result = cc5_api.wf_physics_get_params({"item_name": "Skirt"})
        self.assertFalse(result["success"])
        self.assertIn("no soft-cloth meshes", result["error"])


class CollisionTests(PhysicsTestCase):
    def test_get_probes_given_names(self) -> None:
        result = cc5_api.wf_physics_get_collision(
            {"item_name": "Skirt", "collision_names": ["CC_Base_Hip", "Nope"]}
        )
        self.assertTrue(result["success"], result)
        self.assertEqual(result["shapes"], [{"name": "CC_Base_Hip", "enabled": True, "value": 0.5}])
        self.assertEqual(result["unknown"], ["Nope"])
        self.assertEqual(result["probed"], 2)

    def test_get_defaults_to_avatar_bones(self) -> None:
        with mock.patch.object(
            cc5_api, "_wf_physics_bone_names", return_value=["CC_Base_Hip", "CC_Base_Spine02", "CC_Base_Head"]
        ):
            result = cc5_api.wf_physics_get_collision({"item_name": "Skirt"})
        self.assertTrue(result["success"], result)
        self.assertEqual([s["name"] for s in result["shapes"]], ["CC_Base_Hip", "CC_Base_Spine02"])
        self.assertNotIn("unknown", result)

    def test_set_enable_and_value(self) -> None:
        result = cc5_api.wf_physics_set_collision(
            {"item_name": "Skirt", "shapes": [{"name": "CC_Base_Hip", "enabled": False, "value": 1.25}]}
        )
        self.assertTrue(result["success"], result)
        shape = result["shapes"][0]
        self.assertEqual(shape["before"], {"name": "CC_Base_Hip", "enabled": True, "value": 0.5})
        self.assertEqual(shape["after"], {"name": "CC_Base_Hip", "enabled": False, "value": 1.25})

    def test_set_validates_shapes_first(self) -> None:
        for shapes in ([], [{"name": "CC_Base_Hip"}], [{"name": "X", "enabled": "no"}], [{"value": 1}]):
            result = cc5_api.wf_physics_set_collision({"item_name": "Skirt", "shapes": shapes})
            self.assertFalse(result["success"], shapes)
        self.assertEqual(self.physics.calls, [])

    def test_set_unknown_shape_reports_error(self) -> None:
        result = cc5_api.wf_physics_set_collision(
            {"item_name": "Skirt", "shapes": [{"name": "Nope", "enabled": True}]}
        )
        self.assertFalse(result["success"])
        self.assertIn("Nope", result["error"])


class RouteRegistrationTests(unittest.TestCase):
    def test_auto_patch_registers_physics_routes(self) -> None:
        fake_server = types.SimpleNamespace(
            ACTION_MAP={}, POST_ROUTES={}, GET_ROUTES={}, REQUIRED_PARAMS={}
        )
        with mock.patch.dict(sys.modules, {"server": fake_server}):
            cc5_api._auto_patch_server()
        expected = {
            "/workflow/physics/info": "wf_physics_info",
            "/workflow/physics/activate": "wf_physics_activate",
            "/workflow/physics/weight_map": "wf_physics_load_weight_map",
            "/workflow/physics/params/get": "wf_physics_get_params",
            "/workflow/physics/params/set": "wf_physics_set_params",
            "/workflow/physics/collision/get": "wf_physics_get_collision",
            "/workflow/physics/collision/set": "wf_physics_set_collision",
        }
        for route, action in expected.items():
            self.assertEqual(fake_server.POST_ROUTES.get(route), action)
            # the UI job guard wraps every handler; the wrapper keeps the original in _cc5_guarded
            handler = fake_server.ACTION_MAP[action]
            self.assertIs(getattr(handler, "_cc5_guarded", handler), getattr(cc5_api, action))


if __name__ == "__main__":
    unittest.main()
