# Owner: with CC/iC Blender Tools the character comes in with the feet already in High Heels 100
# (same shape as the CC5 scene). Put the whole Tripo boot (v28 fit, shape unchanged, only moved
# into this frame) on those feet, give it the body's skin weights, and export back to CC with the
# add-on's own "Export to CC" (FbxKey round trip). The old v28c boot is removed.
# blender -b --python v29_boot_bt.py -- IMPORT_BLEND POSED_BOOT_FBX OBJ_PARTS_NPZ OUT_FBX
import sys
import bpy
import numpy as np

BLEND, BOOT, PARTS, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"][0]
body = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.startswith("CC_Base_Body")][0]
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith("tripo_mesh"):
        print("remove old boot", o.name); bpy.data.objects.remove(o)

# body at rest (what the boot is bound to) vs the body in the CC5 scene frame
R = np.array([(body.matrix_world @ v.co)[:] for v in body.data.vertices])
H = np.load(PARTS)["CC_Base_Body"] / 100.0
moves = {}
for side in (-1, 1):
    m = (H[:, 0] * side > 0) & (H[:, 2] < 0.5)
    X, Y = H[m], R[m]
    cx, cy = X.mean(0), Y.mean(0)
    U, _, Vt = np.linalg.svd((X - cx).T @ (Y - cy)); Rm = Vt.T @ U.T
    if np.linalg.det(Rm) < 0:
        Vt[2] *= -1; Rm = Vt.T @ U.T
    r = np.linalg.norm((X - cx) @ Rm.T + cy - Y, axis=1) * 100
    print("side %+d turn %.2f deg, rest vs scene residual cm median %.2f max %.2f" % (
        side, np.degrees(np.arccos(min(1, (np.trace(Rm) - 1) / 2))), np.median(r), r.max()))
    moves[side] = (Rm, cy - Rm @ cx)

bpy.ops.import_scene.fbx(filepath=BOOT)
boot = [o for o in bpy.context.selected_objects if o.type == "MESH"][0]
bpy.ops.object.select_all(action="DESELECT")
boot.select_set(True); bpy.context.view_layer.objects.active = boot
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
P = np.empty(len(boot.data.vertices) * 3); boot.data.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
for side in (-1, 1):
    m = P[:, 0] * side > 0
    Rm, t = moves[side]
    P[m] = P[m] @ Rm.T + t
boot.data.vertices.foreach_set("co", P.ravel()); boot.data.update()
boot.name = BOOT.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_posed", "")
boot.data.materials.clear(); boot.data.materials.append(bpy.data.materials.new("beyon_boot_pbr"))

# weights from the body, bound in this rest pose: each boot vertex blends the weights of its
# nearest leg vertices of the body (the Data Transfer modifier left them empty in background mode)
from mathutils.kdtree import KDTree
gname = {g.index: g.name for g in body.vertex_groups}
BW = [{gname[g.group]: g.weight for g in v.groups if g.weight > 0.001} for v in body.data.vertices]
leg = [i for i in range(len(R)) if R[i, 2] < R[:, 2].min() + 0.75]
kd = KDTree(len(leg))
for k, i in enumerate(leg):
    kd.insert(R[i], k)
kd.balance()
groups = {}
for vi, p in enumerate(P):
    hits = kd.find_n(p, 4)
    w = np.array([1.0 / (d + 0.003) for _, _, d in hits]); w /= w.sum()
    acc = {}
    for (_, k, _), wk in zip(hits, w):
        for n, x in BW[leg[k]].items():
            acc[n] = acc.get(n, 0.0) + x * wk
    tot = sum(acc.values())
    for n, x in acc.items():
        if x / tot > 0.01:
            groups.setdefault(n, []).append((vi, x / tot))
for n, lst in groups.items():
    g = boot.vertex_groups.new(name=n)
    for vi, x in lst:
        g.add([vi], x, "REPLACE")
print("boot weight groups", sorted(groups))
boot.parent = arm
boot.matrix_parent_inverse = arm.matrix_world.inverted()
am = boot.modifiers.new("Armature", "ARMATURE"); am.object = arm

bpy.ops.wm.save_as_mainfile(filepath=OUT[:-4] + ".blend")
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True); bpy.context.view_layer.objects.active = arm
r = bpy.ops.cc3.exporter(param="EXPORT_CC3", filepath=OUT)
print("EXPORT", r)
