"""モーフを1つずつ少し(+と-)動かし、元の画像とのずれ(fit_step.py の合計)が減る向きだけを残す。

使い方: <mediapipe の python> auto_tune.py <歩幅> [回数=1]
記録: FIT_WORK/fit/auto_tune.log(1行ずつ)、最後の値は FIT_WORK/fit/auto_tune_result.json
環境変数は fit_step.py と同じ(REF_FRONT, REF_SIDE, FIT_WORK)。MORPHS は顔に合わせて足し引きしてよい。
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:5101"
WORK = Path(os.environ.get("FIT_WORK", os.getcwd()))
HERE = Path(__file__).resolve().parent
LOG = WORK / "fit" / "auto_tune.log"
MIN_GAIN = 1.5  # これより減らなければ採らない(撮るたびの揺れを避ける)

MORPHS = [
    ("鼻すじ付け根の深さ", "cc embed morphs/embed_nose1"),
    ("鼻すじ付け根の高さ", "essential head morphs/pack_nose1"),
    ("眉間の付け根", "2019-08-22-16-19-51_nose ridge brow depth"),
    ("鼻の出", "cc embed morphs/embed_nose3"),
    ("鼻の大きさ", "cc embed morphs/embed_nose5"),
    ("鼻の高さ位置", "cc embed morphs/embed_nose4"),
    ("鼻先の高さ", "cc embed morphs/embed_nose6"),
    ("小鼻", "essential head morphs/pack_nose15"),
    ("鼻先の丸さ", "essential head morphs/pack_nose23"),
    ("鼻先の上向き", "2019-08-26-16-22-32_nose upturn"),
    ("眉の骨", "2019-10-09-10-23-12_brow ridge depth"),
    ("眉の出", "cc embed morphs/embed_brow1"),
    ("額の下", "2019-10-13-19-19-09_forehead lower depth"),
    ("口の出", "cc embed morphs/embed_mouth2"),
    ("口の高さ", "cc embed morphs/embed_mouth3"),
    ("あご先の出", "cc embed morphs/embed_jaw4"),
    ("あご先の長さ", "cc embed morphs/embed_jaw5"),
    ("目じり", "cc embed morphs/embed_eye3"),
    ("目の大きさ", "cc embed morphs/embed_eye6"),
    ("頬の大きさ", "2019-11-12-21-31-42_cheek scale"),
    ("鼻すじの出", "2019-09-22-17-38-21_nose ridge depth"),
    ("鼻すじ中ほど", "2019-08-26-14-09-57_nose ridge middle depth"),
    ("鼻すじ下側", "2019-08-26-14-12-00_nose ridge lower depth"),
    ("鼻すじの曲がり", "2019-08-04-19-22-02_nose_curve"),
    ("鼻の曲がり", "2020-01-07-12-43-01_nose bend"),
    ("鼻の角度", "2020-01-07-13-01-35_nose angle"),
    ("鼻先の奥行き", "essential head morphs/pack_nose8"),
]


def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode("utf-8"))


def get(mid):
    r = post("/morph/get", {"morph_id": mid})
    return float(r.get("result", r).get("value", 0.0))


def setv(mid, v):
    post("/morph/set", {"morph_id": mid, "value": round(max(-1.0, min(1.0, v)), 3)})


def score(tag):
    res = subprocess.run([sys.executable, str(HERE / "fit_step.py"), tag], cwd=WORK, capture_output=True,
                         text=True, encoding="utf-8")
    m = re.search(r"合計のずれ\(小さいほど近い\): ([0-9.]+)", res.stdout)
    if not m:
        raise RuntimeError(res.stdout[-800:] + res.stderr[-800:])
    return float(m.group(1))


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    (WORK / "fit").mkdir(parents=True, exist_ok=True)
    step = float(sys.argv[1])
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    best = score("auto_base")
    log(f"開始 歩幅 {step} 基準 {best:.1f}")
    n = 0
    for rd in range(rounds):
        for lab, mid in MORPHS:
            cur = get(mid)
            done = False
            for sgn in (+1, -1):
                v = cur + sgn * step
                if v > 1.0 or v < -1.0:
                    continue
                setv(mid, v)
                n += 1
                s = score(f"auto_{n:03d}")
                if s < best - MIN_GAIN:
                    log(f"採用 {lab} {cur:+.2f} → {v:+.2f}  ずれ {best:.1f} → {s:.1f}")
                    best = s
                    done = True
                    break
                setv(mid, cur)
            if not done:
                log(f"そのまま {lab} {cur:+.2f}")
    final = {lab: get(mid) for lab, mid in MORPHS}
    json.dump({"best": best, "values": final, "ids": dict(MORPHS)}, open(WORK / "fit" / "auto_tune_result.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"終わり ずれ {best:.1f}")


if __name__ == "__main__":
    main()
