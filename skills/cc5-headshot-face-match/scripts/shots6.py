"""キャラの顔を6つの角度(正面・30°・45°・真横・上・下)で撮って1枚にまとめる。

使い方: python shots6.py <名前>   例: python shots6.py v59_01
CC5 の HTTP 窓口 (127.0.0.1:5101) を使う。体の向きは最後に正面へ戻す。
"""
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

API = "http://127.0.0.1:5101"
AVATAR = "HD Neutral F"  # 引数の2つめで変えられる
WORK = Path(__file__).resolve().parent
SIZE = 1400
TILE = 420

ANGLES = [
    ("正面", [0, 0, 0]),
    ("30°", [0, 0, 30]),
    ("45°", [0, 0, 45]),
    ("真横(左向き)", [0, 0, -90]),
    ("上から", [15, 0, 0]),
    ("下から", [-15, 0, 0]),
]


def post(path, body):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode("utf-8"))


def head_crop(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    skin = (r > 140) & (g > 90) & (r - b > 20) & (r - g < 90)
    rows = np.where(skin.sum(axis=1) > 6)[0]
    if rows.size == 0:
        return img.crop((0, 0, SIZE, SIZE))
    y0 = int(rows[0])
    band = skin[y0:y0 + 380]
    xs = np.where(band.any(axis=0))[0]
    cx = int(np.mean(np.where(band)[1])) if xs.size else SIZE // 2
    # 頭の幅に合わせて切り出す大きさを決める(頭が大きく写る時も切れないように)
    side = max(620, int((xs.max() - xs.min()) * 1.45)) if xs.size else 620
    side = min(side, SIZE)
    top = max(0, y0 - 30)
    left = max(0, min(SIZE - side, cx - side // 2))
    return img.crop((left, top, left + side, top + side))


def font(size):
    for name in ("C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/msgothic.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    global AVATAR
    tag = sys.argv[1] if len(sys.argv) > 1 else "shot"
    if len(sys.argv) > 2:
        AVATAR = sys.argv[2]
    tiles = []
    try:
        for label, rot in ANGLES:
            post("/workflow/transform/set", {"item_name": AVATAR, "rotate": rot})
            post("/camera/frame", {"view": "face"})
            out = WORK / f"{tag}_{rot[0]}_{rot[2]}.png"
            post("/viewport/capture", {"output_path": str(out), "width": SIZE, "height": SIZE})
            tiles.append((label, head_crop(Image.open(out)).resize((TILE, TILE))))
    finally:
        post("/workflow/transform/set", {"item_name": AVATAR, "rotate": [0, 0, 0]})
        post("/camera/frame", {"view": "face"})

    sheet = Image.new("RGB", (TILE * 3, TILE * 2 + 40), (30, 30, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 4), tag, fill=(255, 255, 255), font=font(26))
    for i, (label, tile) in enumerate(tiles):
        x, y = (i % 3) * TILE, 40 + (i // 3) * TILE
        sheet.paste(tile, (x, y))
        draw.text((x + 8, y + 6), label, fill=(255, 255, 0), font=font(28))
    path = WORK / f"_sheet_{tag}.jpg"
    sheet.save(path, quality=90)
    print(path)


if __name__ == "__main__":
    main()
