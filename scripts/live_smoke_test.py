#!/usr/bin/env python3
"""
Comprehensive LIVE smoke test for the CC5 MCP bridge.

Exercises ~44 bridge routes against a running CC5 (3D Creator mode). Creates a
default avatar and a few content items, so it mutates the scene (run on a scratch
project). Prints PASS/FAIL per check and exits non-zero on failure.

Prereq: CC5 running with the bridge up. Launch with:
    powershell -ExecutionPolicy Bypass -File scripts/launch_cc5_for_test.ps1
Then:
    python scripts/live_smoke_test.py

NOTE: this talks to the bridge DIRECTLY (HTTP), so it does NOT exercise the
TypeScript validation layer (e.g. asset.ts validateAssetPath). Keep the TS unit
tests (npm test) as the check for that layer.
"""
import json
import os
import sys
import tempfile
import urllib.request

BASE = os.environ.get("CC5_BRIDGE_URL", "http://127.0.0.1:5101")
P, F, S = [], [], []


def call(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, None
    except Exception as e:
        return None, {"_err": str(e)}


def res(r):
    return r.get("result") if isinstance(r, dict) and "result" in r else r


def ok(name, cond, extra=""):
    (P if cond else F).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {str(extra)[:90]}")


def skip(name, why=""):
    S.append(name)
    print(f"  [SKIP] {name}  {why}")


def is_resp(r):
    return isinstance(res(r), (dict, list))


print("== Scene / Avatar ==")
s, r = call("GET", "/health"); ok("check_cc5_connection", s == 200 and res(r).get("status") == "ok")
s, r = call("POST", "/avatar/create"); ok("create_avatar", res(r).get("success"))
s, r = call("GET", "/avatars"); avs = res(r); ok("list_avatars", isinstance(avs, list) and bool(avs))
s, r = call("GET", "/avatar/info"); ok("get_avatar_info", s == 200 and is_resp(r))
s, r = call("GET", "/scene/objects"); ok("get_scene_objects", s == 200 and is_resp(r))

print("== Morphs ==")
s, r = call("GET", "/morphs/catalog"); ok("get_morph_catalog", s == 200 and is_resp(r))
s, r = call("POST", "/morphs/search", {"query": "jaw"}); sr = res(r)
ok("search_morphs (list)", isinstance(sr, list) and bool(sr), f"n={len(sr) if isinstance(sr, list) else sr}")
mid = sr[0]["id"] if isinstance(sr, list) and sr else None
mid2 = sr[1]["id"] if isinstance(sr, list) and len(sr) > 1 else mid
s, r = call("POST", "/morph/set", {"morph_id": mid, "value": 0.3}); ok("adjust_morph", res(r).get("success"))
s, r = call("POST", "/morph/get", {"morph_id": mid}); gv = res(r)
ok("get_morph_value", gv.get("success") and abs(gv.get("value", 0) - 0.3) < 0.01, gv)
s, r = call("POST", "/morphs/set", {"morphs": [{"morph_id": mid, "value": 0.1}, {"morph_id": mid2, "value": 0.2}]})
ok("adjust_multiple_morphs", res(r).get("success"))
s, r = call("POST", "/morphs/reset"); ok("reset_morphs", res(r).get("success") is not False and is_resp(r))

print("== Materials / Color ==")
s, r = call("GET", "/material/info"); mi = res(r); ok("get_material_info (success+meshes)", isinstance(mi, dict) and mi.get("success") and "meshes" in mi)
mesh = mat = None
for k, v in (mi.get("meshes", {}) if isinstance(mi, dict) else {}).items():
    if isinstance(v, list) and v:
        mesh, mat = k, v[0]; break
if mesh:
    s, r = call("POST", "/material/color/get", {"mesh_name": mesh, "material_name": mat}); ok("get_diffuse_color", res(r).get("success") and "r" in res(r))
    s, r = call("POST", "/material/properties", {"mesh_name": mesh, "material_name": mat}); ok("get_material_properties", res(r).get("success"))
    s, r = call("POST", "/material/color/set", {"mesh_name": mesh, "material_name": mat, "r": .7, "g": .6, "b": .5}); ok("set_diffuse_color", res(r).get("success"))
    s, r = call("POST", "/material/opacity", {"mesh_name": mesh, "material_name": mat, "opacity": 100}); ok("set_material_opacity", res(r).get("success"))
    s, r = call("POST", "/material/glossiness", {"mesh_name": mesh, "material_name": mat, "glossiness": 20}); ok("set_material_glossiness", res(r).get("success"))
    s, r = call("POST", "/material/specular", {"mesh_name": mesh, "material_name": mat, "specular": 50}); ok("set_material_specular", res(r).get("success"))
else:
    for n in ["get_diffuse_color", "get_material_properties", "set_diffuse_color", "set_material_opacity", "set_material_glossiness", "set_material_specular"]:
        skip(n, "no mesh")
s, r = call("POST", "/color/eye", {"r": .3, "g": .2, "b": .1}); ok("set_eye_color", res(r).get("success") is not False and is_resp(r))
s, r = call("POST", "/color/lip", {"r": .6, "g": .3, "b": .3}); ok("set_lip_color", res(r).get("success") is not False and is_resp(r))
# set_hair_color correctly errors on a bald avatar (no hair materials) — accept clean error.
s, r = call("POST", "/color/hair", {"r": .2, "g": .1, "b": .05}); ok("set_hair_color (clean result)", isinstance(res(r), dict) and ("success" in res(r)))

print("== Lights / Camera / Expression ==")
s, r = call("GET", "/lights"); lts = res(r); ok("get_lights", s == 200 and is_resp(r))
lname = lts[0].get("name") if isinstance(lts, list) and lts and isinstance(lts[0], dict) else None
if lname:
    s, r = call("POST", "/light/info", {"light_name": lname}); ok("get_light_info", is_resp(r))
    # round-trip: set red, read back ~1.0/0/0 (RRgb.Red() is 0-255, get divides by 255)
    call("POST", "/light/color", {"light_name": lname, "r": 1.0, "g": 0.0, "b": 0.0})
    s, r = call("POST", "/light/info", {"light_name": lname}); c = res(r).get("color", {}) if isinstance(res(r), dict) else {}
    ok("set_light_color round-trip", abs(c.get("r", 0) - 1.0) < 0.05 and c.get("g", 1) < 0.05, c)
    s, r = call("POST", "/light/multiplier", {"light_name": lname, "multiplier": 1.0}); ok("set_light_multiplier", res(r).get("success") is not False and is_resp(r))
else:
    for n in ["get_light_info", "set_light_color round-trip", "set_light_multiplier"]:
        skip(n, "no light")
s, r = call("GET", "/camera/info"); ok("get_camera_info", s == 200 and is_resp(r))
s, r = call("POST", "/camera/focal", {"focal_length": 50}); ok("set_camera_focal_length (responds)", is_resp(r))
s, r = call("GET", "/expressions"); ok("get_expression_info (success)", isinstance(res(r), dict) and res(r).get("success"))
s, r = call("POST", "/subdivision", {"level": 0}); ok("set_subdivision_level", res(r).get("success"))

print("== Content + asset load + item ops (real cloth) ==")
s, r = call("GET", "/clothes"); ok("list_clothes", s == 200 and is_resp(r))
s, r = call("GET", "/hair"); ok("list_hair", s == 200 and is_resp(r))
s, r = call("GET", "/accessories"); ok("list_accessories", s == 200 and is_resp(r))
s, r = call("POST", "/content/browse", {"folder_type": "shoes"}); cb = res(r)
ok("browse_content (.ccShoes)", isinstance(cb, list) and cb and str(cb[0]).lower().endswith(".ccshoes"), f"n={len(cb) if isinstance(cb, list) else cb}")
shoe = cb[0] if isinstance(cb, list) and cb and str(cb[0]).lower().endswith(".ccshoes") else None
if shoe:
    s, r = call("POST", "/asset/load", {"file_path": shoe}, timeout=120); ok("load_asset (.ccShoes)", res(r).get("success"))
    s, r = call("GET", "/clothes"); cl = res(r)
    cloth_name = None
    if isinstance(cl, list) and cl:
        cloth_name = cl[0].get("name") if isinstance(cl[0], dict) else (cl[0] if isinstance(cl[0], str) else None)
    if cloth_name:
        s, r = call("POST", "/item/visible", {"item_name": cloth_name, "visible": False}); ok("set_item_visible HIDE real cloth", res(r).get("success"), res(r))
        s, r = call("POST", "/item/visible", {"item_name": cloth_name, "visible": True}); ok("set_item_visible SHOW real cloth", res(r).get("success"))
        s, r = call("POST", "/item/remove", {"item_name": cloth_name}); ok("remove_scene_item real cloth", res(r).get("success"), res(r))
    else:
        for n in ["set_item_visible HIDE real cloth", "set_item_visible SHOW real cloth", "remove_scene_item real cloth"]:
            skip(n, "no cloth name")
else:
    for n in ["load_asset (.ccShoes)", "set_item_visible HIDE real cloth", "set_item_visible SHOW real cloth", "remove_scene_item real cloth"]:
        skip(n, "no shoe")
s, r = call("POST", "/item/visible", {"item_name": "___nope___", "visible": False}); ok("set_item_visible (clean not-found)", isinstance(res(r), dict) and res(r).get("success") is False)
s, r = call("POST", "/item/remove", {"item_name": "___nope___"}); ok("remove_scene_item (clean not-found)", isinstance(res(r), dict) and res(r).get("success") is False)

print("== Export / Capture / Bake / Edit / Exec ==")
s, r = call("POST", "/viewport/capture"); cap = res(r)
ok("capture_viewport", isinstance(cap, dict) and (cap.get("success") or cap.get("base64") or cap.get("path")))
fbx = os.path.join(tempfile.gettempdir(), "cc5_smoke_export.fbx")
s, r = call("POST", "/export/fbx", {"output_path": fbx}, timeout=180); ok("export_fbx (responds)", isinstance(res(r), dict))
s, r = call("POST", "/skin/bake", {}, timeout=120); ok("bake_skin_textures (responds)", is_resp(r))
s, r = call("GET", "/export/head_mh/status"); ok("export_head_mh status", s == 200 and is_resp(r))
s, r = call("POST", "/undo"); ok("undo", res(r).get("success") is not False and is_resp(r))
s, r = call("POST", "/redo"); ok("redo", res(r).get("success") is not False and is_resp(r))
s, r = call("POST", "/exec/python", {"code": "result=6*7"}); ok("exec_python", res(r).get("success") and str(res(r).get("result")) == "42")

print(f"\n==== {len(P)} PASS / {len(F)} FAIL / {len(S)} SKIP ====")
if F:
    print("FAILED:", ", ".join(F))
if S:
    print("SKIPPED:", ", ".join(S))
sys.exit(1 if F else 0)
