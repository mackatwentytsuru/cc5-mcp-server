# Owner: after wearing the boot with High Heels 100, skin showed on the inner shin and under the
# foot. Move each boot (in the heel pose, before carrying it back to flat feet) by the amount that
# hid the most skin: IN cm toward the middle, BACK cm to the back (+y), DOWN cm down. Shape unchanged.
# blender -b --python v28_boot_shift.py -- POSED_BOOT_FBX OUT_FBX IN BACK DOWN
import sys
import bpy
import numpy as np

IN, OUT, a, b, c = sys.argv[sys.argv.index("--") + 1:]
inward, back, down = float(a) / 100, float(b) / 100, float(c) / 100

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=IN)
o = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = o; o.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
P = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
P[:, 0] -= np.sign(P[:, 0]) * inward          # each boot is wholly on its own side of x = 0
P[:, 1] += back
P[:, 2] -= down
o.data.vertices.foreach_set("co", P.ravel()); o.data.update()
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, axis_forward="-Z", axis_up="Y",
                         global_scale=1.0, apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
                         path_mode="COPY", embed_textures=False, add_leaf_bones=False, bake_anim=False)
print("done", (P.min(0) * 100).round(1), (P.max(0) * 100).round(1))
