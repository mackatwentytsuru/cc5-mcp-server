"""モーフを動かしたあとの1回分の確かめ: 正面と真横(左向き)を撮って測り、元の画像との差と重ねた絵を出す。

使い方: <mediapipe の python> fit_step.py <名前> [キャラ名=CC3_Base_Plus]
  環境変数: REF_FRONT(元の正面の画像)、REF_SIDE(元の横顔・左向き)、FIT_WORK(作業フォルダ。省略時は今のフォルダ)
  元の画像の測り値 FIT_WORK/measure/photo.json が無ければ最初に作る。
出力: FIT_WORK/fit/<名前>_front.png, _side.png, _measure.json, _cmp.jpg, _side_zoom.jpg と、差の表(標準出力)
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API = "http://127.0.0.1:5101"
WORK = Path(os.environ.get("FIT_WORK", os.getcwd()))
OUT = WORK / "fit"
HS3FIT = Path(__file__).resolve().parent / "hs3_fit"
REF_FRONT = Path(os.environ["REF_FRONT"])
REF_SIDE = Path(os.environ["REF_SIDE"])
PHOTO_JSON = WORK / "measure" / "photo.json"

KEYS = [
    ("front", "eye_w", "目の幅"), ("front", "eye_open", "目の縦の開き"), ("front", "eye_tilt_deg", "目じりの上がり(度)"),
    ("front", "nose_w_alar", "小鼻の幅"), ("front", "nose_len", "鼻の長さ"), ("front", "nose_tip_to_lip", "鼻の下〜上唇"),
    ("front", "mouth_w", "口の幅"), ("front", "cheek_w", "頬の幅"), ("front", "jaw_w", "えらの幅"), ("front", "chin_w", "あご先の幅"),
    ("front", "chin_len", "下唇〜あご先"), ("front", "top_to_eye", "頭頂〜目"), ("front", "head_h", "頭の高さ"),
    ("side", "nose_proj", "鼻の高さ(付け根から)"), ("side", "nose_proj_sn", "鼻先の出(鼻の下から)"),
    ("side", "nasolabial_deg", "鼻唇角(度)"), ("side", "dorsum_angle_deg", "鼻すじの傾き(度)"), ("side", "tip_radius", "鼻先の丸さ"),
    ("side", "nasion_depth", "付け根のくぼみ"), ("side", "nose_len_side", "鼻の長さ(横)"), ("side", "lip_lo_proj", "下唇の出"),
    ("side", "chin_recess", "あご先の引っ込み"), ("side", "chin_len_side", "下唇〜あご下(横)"), ("side", "head_h_side", "頭の高さ(横)"),
]


def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode("utf-8"))


def capture(avatar, rot, path):
    """遠近の少ない決まった視点(正面 = front、横 = left)で全身を大きく撮り、頭のまわりだけ切り出す。
    rot[2] が 0 なら正面、それ以外なら横(left の視点。顔は右を向くので左右反転して左向きにそろえる)。"""
    import numpy as np
    if rot[2] == 0:
        # 正面は、まっすぐ前からの顔の視点(全身の正面の視点は下から見上げる形になるため)
        post("/workflow/transform/set", {"item_name": avatar, "rotate": [0, 0, 0]})
        post("/camera/frame", {"view": "face"})
        post("/viewport/capture", {"output_path": str(path), "width": 1400, "height": 1400})
        return
    view = "left"
    post("/workflow/transform/set", {"item_name": avatar, "rotate": [0, 0, 0]})
    post("/camera/frame", {"view": view})
    big = path.with_name(path.stem + "_full.png")
    post("/viewport/capture", {"output_path": str(big), "width": 6000, "height": 6000})
    im = Image.open(big).convert("RGB")
    a = np.asarray(im).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    skin = (r > 120) & (r - b > 20)
    rows = np.where(skin.sum(axis=1) > 3)[0]
    y0 = int(rows[0])
    head = skin[y0:y0 + int(im.height * 0.11)]
    xs = np.where(head.any(axis=0))[0]
    cx = int((xs.min() + xs.max()) / 2)
    side = int(im.height * 0.16)
    box = (cx - side // 2, max(0, y0 - side // 10), cx + side // 2, max(0, y0 - side // 10) + side)
    crop = im.crop(box).resize((1400, 1400), Image.LANCZOS)
    if view == "left":
        crop = crop.transpose(Image.FLIP_LEFT_RIGHT)
    crop.save(path)
    big.unlink(missing_ok=True)


def aligned_front(path, info, size=(700, 860), ipd_t=200, center=(350, 330)):
    im = Image.open(path).convert("RGB")
    s = ipd_t / info["ipd_px"]
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    out = Image.new("RGB", size, (40, 40, 40))
    out.paste(im, (int(center[0] - im.width / 2), int(center[1] - info["eye_y"] * s)))
    return out


def aligned_side(path, info, head_px, size=(760, 860), head_t=580, tip=(140, 430)):
    im = Image.open(path).convert("RGB")
    s = head_t / head_px
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    out = Image.new("RGB", size, (40, 40, 40))
    out.paste(im, (int(tip[0] - info["tip"][0] * s), int(tip[1] - info["tip"][1] * s)))
    return out


def main():
    name = sys.argv[1]
    avatar = sys.argv[2] if len(sys.argv) > 2 else "CC3_Base_Plus"
    OUT.mkdir(parents=True, exist_ok=True)
    if not PHOTO_JSON.exists():
        PHOTO_JSON.parent.mkdir(parents=True, exist_ok=True)
        pr = subprocess.run([sys.executable, "measure.py", "pair", str(REF_FRONT), str(REF_SIDE), "--facing", "left", "--scale", "photo"],
                            cwd=HS3FIT, capture_output=True, text=True, encoding="utf-8")
        PHOTO_JSON.write_text(pr.stdout, encoding="utf-8")
    fpath, spath = OUT / f"{name}_front.png", OUT / f"{name}_side.png"
    try:
        capture(avatar, [0, 0, 0], fpath)
        capture(avatar, [0, 0, -90], spath)
    finally:
        post("/workflow/transform/set", {"item_name": avatar, "rotate": [0, 0, 0]})
        post("/camera/frame", {"view": "face"})
    res = subprocess.run([sys.executable, "measure.py", "pair", str(fpath), str(spath), "--facing", "left", "--scale", "render"],
                         cwd=HS3FIT, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(res.stderr[-2000:])
        sys.exit(1)
    r = json.loads(res.stdout)
    json.dump(r, open(OUT / f"{name}_measure.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    p = json.load(open(PHOTO_JSON, encoding="utf-8"))
    total = 0.0
    for part, k, lab in KEYS:
        a, b = p[part][k], r[part][k]
        pct = (b - a) / abs(a) * 100 if abs(a) > 1e-6 else 0.0
        total += min(abs(pct), 60)
        flag = "  ★" if abs(pct) >= 8 else ""
        print(f"{lab:16s} 元 {a:8.3f}  3D {b:8.3f}  ({pct:+6.1f}%){flag}")
    print(f"合計のずれ(小さいほど近い): {total:.1f}")

    f = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 24)
    pa = aligned_front(REF_FRONT, p["info"]["front"])
    ra = aligned_front(fpath, r["info"]["front"])
    ps_head = p["side"]["head_h_side"] * p["info"]["side"]["ipd_px"]
    rs_head = r["side"]["head_h_side"] * r["info"]["side"]["ipd_px"]
    psd = aligned_side(REF_SIDE, p["info"]["side"], ps_head)
    rsd = aligned_side(spath, r["info"]["side"], rs_head)
    tiles = [("元 正面", pa), ("3D 正面", ra), ("重ね", Image.blend(pa, ra, 0.5)),
             ("元 横顔", psd), ("3D 横顔", rsd), ("重ね", Image.blend(psd, rsd, 0.5))]
    W = sum(t.width for _, t in tiles)
    sheet = Image.new("RGB", (W, 900), (30, 30, 34))
    d = ImageDraw.Draw(sheet)
    x = 0
    for lab, t in tiles:
        sheet.paste(t, (x, 40))
        d.text((x + 8, 6), lab, fill=(255, 255, 0), font=f)
        x += t.width
    sheet.thumbnail((2600, 900))
    sheet.save(OUT / f"{name}_cmp.jpg", quality=86)
    # 横顔の鼻・口・あごの拡大(元 / 3D / 重ね)
    box = (40, 180, 440, 700)
    zs = [im.crop(box).resize((560, 728), Image.LANCZOS) for im in (psd, rsd, Image.blend(psd, rsd, 0.5))]
    zoom = Image.new("RGB", (560 * 3, 768), (30, 30, 34))
    dz = ImageDraw.Draw(zoom)
    for i, (lab, z) in enumerate(zip(("元 横顔", "3D 横顔", "重ね"), zs)):
        zoom.paste(z, (i * 560, 40))
        dz.text((i * 560 + 8, 6), lab, fill=(255, 255, 0), font=f)
    zoom.save(OUT / f"{name}_side_zoom.jpg", quality=88)
    print(OUT / f"{name}_cmp.jpg")


if __name__ == "__main__":
    main()
