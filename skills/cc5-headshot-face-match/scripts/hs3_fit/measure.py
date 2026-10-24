"""顔の比率を測る道具(Headshot 3 で作った頭をお手本の画像に合わせる用)。

正面: MediaPipe Face Landmarker の目印 → 両目の瞳の間の距離(IPD)で割った値。
横顔: 背景との境(シルエット)から輪郭を取り、鼻・あご・唇の出と角度を測る。

使い方:
  python measure.py front <画像> [--out 確認の絵.png]
  python measure.py side  <画像> --facing left|right [--ipd-px N] [--out ...]
  python measure.py all   <正面> <横顔> --facing left|right [--out-prefix ...]
Python から: measure_front(path) / measure_side(path, facing, ipd_px)
"""
import json
import math
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "face_landmarker.task")

# MediaPipe 478 点の番号(人物の右 = 画像の左。R/L は画像の左右ではなく人物基準)
LM = dict(
    iris_R=468, iris_L=473,
    eyeR_out=33, eyeR_in=133, eyeR_up=159, eyeR_lo=145,
    eyeL_out=263, eyeL_in=362, eyeL_up=386, eyeL_lo=374,
    nose_bridge=168, nose_tip=1, subnasale=2,
    alar_R=129, alar_L=358,        # 小鼻の外側のふくらみ(根元寄り)
    alarw_R=64, alarw_L=294,       # 小鼻の翼(外側)
    mouth_R=61, mouth_L=291,
    lip_up_top=0, lip_up_in=13, lip_lo_in=14, lip_lo_bot=17,
    cheek_R=234, cheek_L=454,      # 耳の前の頬骨あたりの輪郭(顔の最大幅)
    jaw_R=172, jaw_L=397,          # あごの角の少し下
    jaw2_R=136, jaw2_L=365,
    chinside_R=149, chinside_L=378,  # あご先の横
    chin=152,
    glabella=9,
)


def _landmarker():
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=MODEL),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.2,
        min_face_presence_confidence=0.2,
        output_face_blendshapes=False,
    )
    return vision.FaceLandmarker.create_from_options(opts), mp


def _load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return img  # BGR


def skin_mask(bgr, pick="largest"):
    """背景(灰青・濃い紺)と肌(暖色)を R-B で分ける。顔と首と肩を含む塊を返す。"""
    b = bgr[..., 0].astype(np.int16)
    r = bgr[..., 2].astype(np.int16)
    lum = bgr.astype(np.int16).sum(axis=2) // 3
    m = ((r - b) > 8) & (lum > 35)
    m = m.astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return m > 0
    # 一番大きい塊だけ(頭+首+肩)
    if pick == "top":   # 一番上にある塊(全身の絵で頭を取るとき)
        big = 1 + int(np.argmin(stats[1:, cv2.CC_STAT_TOP]))
    else:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    out = (lab == big)
    # 穴(目・口)を埋める
    cnts, _ = cv2.findContours(out.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(m)
    cv2.drawContours(filled, cnts, -1, 255, -1)
    return filled > 0


def get_landmarks(bgr):
    lmk, mp = _landmarker()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    res = lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not res.face_landmarks:
        return None
    h, w = bgr.shape[:2]
    return np.array([[p.x * w, p.y * h] for p in res.face_landmarks[0]], dtype=np.float64)


def _d(a, b):
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def measure_front(path, out_png=None):
    """正面の比率。返り値: (指標 dict, ipd_px, 頭の高さ px(頭頂〜あご先), 目印)。"""
    bgr = _load_rgb(path)
    pts = get_landmarks(bgr)
    if pts is None:
        raise RuntimeError("顔の目印が取れなかった: " + path)
    P = {k: pts[v] for k, v in LM.items()}
    ipd = _d(P["iris_R"], P["iris_L"])
    mask = skin_mask(bgr)
    cx = int(round((P["iris_R"][0] + P["iris_L"][0]) / 2))
    col = np.where(mask[:, cx])[0]
    top_y = float(col.min()) if len(col) else float("nan")
    eye_y = (P["iris_R"][1] + P["iris_L"][1]) / 2
    chin_y = P["chin"][1]
    n = lambda v: v / ipd  # IPD で割る
    eyeR_w = _d(P["eyeR_out"], P["eyeR_in"])
    eyeL_w = _d(P["eyeL_out"], P["eyeL_in"])
    eyeR_o = _d(P["eyeR_up"], P["eyeR_lo"])
    eyeL_o = _d(P["eyeL_up"], P["eyeL_lo"])

    def tilt(out_, in_):  # 目じりが目がしらより上なら正(度)
        dx = abs(out_[0] - in_[0])
        dy = in_[1] - out_[1]
        return math.degrees(math.atan2(dy, dx))

    m = {
        "eye_w": n((eyeR_w + eyeL_w) / 2),
        "eye_open": n((eyeR_o + eyeL_o) / 2),
        "eye_aspect": ((eyeR_o + eyeL_o) / (eyeR_w + eyeL_w)),   # 開き/幅
        "eye_gap_in": n(_d(P["eyeR_in"], P["eyeL_in"])),          # 目がしら同士
        "eye_gap_over_w": _d(P["eyeR_in"], P["eyeL_in"]) / ((eyeR_w + eyeL_w) / 2),
        "eye_tilt_deg": (tilt(P["eyeR_out"], P["eyeR_in"]) + tilt(P["eyeL_out"], P["eyeL_in"])) / 2,
        "nose_w_alar": n(_d(P["alar_R"], P["alar_L"])),
        "nose_w_wing": n(_d(P["alarw_R"], P["alarw_L"])),
        "nose_len": n(P["subnasale"][1] - P["nose_bridge"][1]),   # 鼻根〜鼻の下(縦)
        "nose_tip_to_lip": n(P["lip_up_top"][1] - P["subnasale"][1]),  # 鼻の下〜上唇の山
        "mouth_w": n(_d(P["mouth_R"], P["mouth_L"])),
        "lip_up_th": n(P["lip_up_in"][1] - P["lip_up_top"][1]),
        "lip_lo_th": n(P["lip_lo_bot"][1] - P["lip_lo_in"][1]),
        "cheek_w": n(_d(P["cheek_R"], P["cheek_L"])),
        "jaw_w": n(_d(P["jaw_R"], P["jaw_L"])),
        "jaw2_w": n(_d(P["jaw2_R"], P["jaw2_L"])),
        "chin_w": n(_d(P["chinside_R"], P["chinside_L"])),
        "chin_len": n(chin_y - P["lip_lo_bot"][1]),               # 下唇の下〜あご先
        "lower_face": n(chin_y - P["subnasale"][1]),              # 鼻の下〜あご先
        "mid_face": n(P["subnasale"][1] - eye_y),                 # 目〜鼻の下
        "eye_to_chin": n(chin_y - eye_y),
        "head_h": n(chin_y - top_y),                              # 頭頂〜あご先
        "top_to_eye": n(eye_y - top_y),
        "lower_over_mid": (chin_y - P["subnasale"][1]) / (P["subnasale"][1] - eye_y),
        "cheek_over_eye2chin": _d(P["cheek_R"], P["cheek_L"]) / (chin_y - eye_y),
        "jaw_over_cheek": _d(P["jaw_R"], P["jaw_L"]) / _d(P["cheek_R"], P["cheek_L"]),
        "chin_over_cheek": _d(P["chinside_R"], P["chinside_L"]) / _d(P["cheek_R"], P["cheek_L"]),
        "nose_w_over_eye_gap": _d(P["alar_R"], P["alar_L"]) / _d(P["eyeR_in"], P["eyeL_in"]),
    }
    # 鼻の穴の見え方: 小鼻の間・鼻先〜鼻の下の箱の中で、まわりより暗い画素の面積(IPD の 2 乗が単位)
    try:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
        x0 = int(min(P["alar_R"][0], P["alar_L"][0]))
        x1 = int(max(P["alar_R"][0], P["alar_L"][0]))
        y0 = int(P["nose_tip"][1] - 0.05 * ipd)
        y1 = int(P["subnasale"][1] + 0.03 * ipd)
        box = gray[y0:y1, x0:x1]
        dark = box < 0.55 * np.median(box)
        m["nostril_dark"] = float(dark.sum()) / (ipd * ipd)
    except Exception:
        m["nostril_dark"] = 0.0
    info = dict(ipd_px=ipd, head_h_px=chin_y - top_y, eye_y=eye_y, top_y=top_y, chin_y=chin_y,
                shape=bgr.shape[:2])
    if out_png:
        _draw_front(bgr, pts, P, top_y, out_png)
    return m, info, P


def _draw_front(bgr, pts, P, top_y, out_png):
    img = bgr.copy()
    h, w = img.shape[:2]
    for k, p in P.items():
        cv2.circle(img, (int(p[0]), int(p[1])), 3, (0, 0, 255), -1)
    cx = int((P["iris_R"][0] + P["iris_L"][0]) / 2)
    cv2.line(img, (cx - 40, int(top_y)), (cx + 40, int(top_y)), (0, 255, 0), 2)
    # 顔まわりを切り出して 2 倍に拡大し、名前を小さく書く
    x0 = int(min(p[0] for p in P.values()) - 40)
    x1 = int(max(p[0] for p in P.values()) + 40)
    y0 = int(P["glabella"][1] - 60)
    y1 = int(P["chin"][1] + 40)
    crop = img[max(0, y0):y1, max(0, x0):x1]
    crop = cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for k, p in P.items():
        X = int((p[0] - max(0, x0)) * 2) + 6
        Y = int((p[1] - max(0, y0)) * 2) - 6
        if k in ("eyeR_up", "eyeL_up", "eyeR_lo", "eyeL_lo", "nose_tip", "alarw_R", "alarw_L", "lip_up_in", "lip_lo_in"):
            continue
        cv2.putText(crop, k, (X, Y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(out_png, crop)
    cv2.imwrite(out_png.replace(".png", "_full.png"), img)


# --------------------------------------------------------------------------
# 横顔(シルエット)
# --------------------------------------------------------------------------

def _front_profile(mask, facing):
    """各行の顔側のふち x。facing='left' なら左端。返り値 xs[y](なければ nan)。"""
    h, w = mask.shape
    xs = np.full(h, np.nan)
    for y in range(h):
        row = np.where(mask[y])[0]
        if len(row):
            xs[y] = row.min() if facing == "left" else row.max()
    return xs


def _smooth(a, sigma):
    a = np.asarray(a, dtype=np.float64)
    ok = ~np.isnan(a)
    if ok.sum() < 5:
        return a
    idx = np.arange(len(a))
    b = np.interp(idx, idx[ok], a[ok])
    rad = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(b, rad, mode="edge")
    return np.convolve(pad, k, mode="valid")


def measure_side(path, facing="left", ipd_px=None, out_png=None, head_h_front_px=None, top_to_eye=None):
    """横顔の指標。ipd_px: この画像での IPD の画素数(正面から換算した値)を渡す。
    head_h_front_px を渡すと、頭頂〜あご先の高さを使って IPD を換算する(写真用)。"""
    bgr = _load_rgb(path)
    h, w = bgr.shape[:2]
    mask = skin_mask(bgr)
    if facing == "right":      # 左向きにそろえる(以後は左向きで計算)
        bgr = bgr[:, ::-1].copy()
        mask = mask[:, ::-1].copy()
    ys = np.where(mask.any(axis=1))[0]
    top = int(ys.min())
    # 頭頂の x(最上行の中央)
    top_x = float(np.where(mask[top + 2])[0].mean())

    xs_raw = _front_profile(mask, "left")
    xs = _smooth(xs_raw, 2.0)

    # 顔の高さの目安: 頭頂〜あご先は後で出す。まず鼻先を探すために、頭頂から
    # 画像下端までの範囲で「首より前に出ている部分」を使う。
    # あご先の仮の位置 = 頭頂から (画像の高さの 0.62〜0.8) までで最も左に出る点 の下
    # → 鼻先: 頭頂から 38%〜80% の高さで最小 x
    # 先に頭の高さ H0 を仮置き(頭頂〜首の細くなる所)にして、そこから絞る。
    # 首の位置: 顔側ふちが急に右へ戻る所は使わず、鼻先を「頭頂から y 範囲で最小の x」で探す。
    est_chin = top + int(0.80 * (h * 0.7))  # 粗い仮値(後で上書き)
    # 粗い鼻先: 頭頂からの距離 0.30h〜0.62h の範囲で最小 x
    lo, hi = top + int(0.30 * h), top + int(0.62 * h)
    tip_y = int(lo + np.nanargmin(xs[lo:hi]))
    tip_x = xs[tip_y]

    # 鼻の下(subnasale): 鼻先より下で、いちど x が戻る(凹む)所 = 鼻先〜鼻先+0.12h の最大 x の極大
    seg = xs[tip_y: tip_y + int(0.08 * h)]
    # 凹みの底: 最初の局所最大(極大)を探す。なければ区間の最大
    sn_off = _first_local_max(seg)
    sn_y = tip_y + sn_off
    sn_x = xs[sn_y]

    # 上唇の出(labrale sup.): sn より下の最初の局所最小
    seg = xs[sn_y: sn_y + int(0.08 * h)]
    ls_off = _first_local_min(seg)
    ls_y = sn_y + ls_off
    ls_x = xs[ls_y]
    # 下唇の出: ls より下の次の局所最小(唇の谷=口の線をはさむ)
    seg = xs[ls_y + 3: ls_y + int(0.10 * h)]
    st_off = _first_local_max(seg)                 # 口の線(stomion)あたりの凹み
    st_y = ls_y + 3 + st_off
    seg = xs[st_y + 3: st_y + int(0.08 * h)]
    li_off = _first_local_min(seg)
    li_y = st_y + 3 + li_off
    li_x = xs[li_y]
    # あご下(menton): 首の前のふちより手前(左)の、いちばん下の肌の行
    y_n = min(h - 2, li_y + int(0.28 * h))
    neck_x = float(xs[y_n])
    ipd_ = ipd_px if ipd_px else 0.2 * h
    x_end = int(neck_x - 0.25 * ipd_)
    menton_y = li_y
    for x in range(int(xs[li_y]), max(int(xs[li_y]) + 5, x_end)):
        col = mask[:, x]
        yy = li_y
        if not col[yy]:
            continue
        while yy + 1 < h and col[yy + 1]:
            yy += 1
        if yy - li_y < 0.2 * h:
            menton_y = max(menton_y, yy)
    # 下唇とあごの間の凹み(mentolabial sulcus): 下唇のあとの最初の極大。なければ下唇〜あご下の 35% の所
    seg = xs[li_y + 2: menton_y]
    ms_off = _first_local_max(seg) if len(seg) > 6 else 0
    ms_y = li_y + 2 + ms_off
    if ms_off >= len(seg) - 3:     # 極大が見つからず端に張りついた
        ms_y = li_y + int(0.35 * (menton_y - li_y))
    ms_x = xs[ms_y]
    # あご先(pogonion): 凹みからあご下までで最も前(左)の点
    seg = xs[ms_y: menton_y + 1]
    pg_y = ms_y + int(np.nanargmin(seg)) if len(seg) else menton_y
    pg_x = xs[pg_y]
    # 鼻根(nasion): 目の高さの付近で一番引っ込んだ所
    H0 = menton_y - top
    ipd_here = ipd_px if ipd_px else 0.2 * H0
    eye_row = top + (top_to_eye * ipd_here if top_to_eye else 0.5 * H0)
    w0 = max(top + 5, int(eye_row - 0.45 * ipd_here))
    w1 = min(tip_y - 5, int(eye_row + 0.45 * ipd_here))
    na_y = int(w0 + np.nanargmax(xs[w0:w1]))
    na_x = xs[na_y]

    H_px = menton_y - top
    if ipd_px is None:
        if head_h_front_px is not None:
            ipd_px = None  # 呼び出し側で head_h から換算
        else:
            raise ValueError("ipd_px か head_h_front_px の片方が必要")
    scale_note = ""
    return _side_result(locals(), h, w, out_png, bgr)


def _tip_radius(xs, tip_y, ipd_px):
    """鼻先まわりの輪郭(鼻先から上下 0.12*IPD)に円を当てた半径(画素)。"""
    r = max(4, int(0.12 * ipd_px))
    ys = np.arange(tip_y - r, tip_y + r + 1)
    x = xs[ys]
    A = np.c_[2 * x, 2 * ys, np.ones(len(ys))]
    b = x ** 2 + ys ** 2
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    rad2 = sol[2] + sol[0] ** 2 + sol[1] ** 2
    return float(np.sqrt(max(rad2, 1.0)))


def _first_local_max(a):
    a = np.asarray(a, dtype=np.float64)
    for i in range(2, len(a) - 2):
        if a[i] >= a[i - 1] and a[i] >= a[i + 1] and a[i] > a[max(0, i - 4)] + 0.0:
            if a[i] - min(a[:i]) >= 1.0:
                return i
    return int(np.nanargmax(a))


def _first_local_min(a):
    a = np.asarray(a, dtype=np.float64)
    for i in range(2, len(a) - 2):
        if a[i] <= a[i - 1] and a[i] <= a[i + 1]:
            if max(a[:i + 1]) - a[i] >= 1.0:
                return i
    return int(np.nanargmin(a))


def _side_result(L, h, w, out_png, bgr):
    top, tip_y, tip_x = L["top"], L["tip_y"], L["tip_x"]
    sn_y, sn_x, ls_y, ls_x = L["sn_y"], L["sn_x"], L["ls_y"], L["ls_x"]
    li_y, li_x, ms_y, ms_x = L["li_y"], L["li_x"], L["ms_y"], L["ms_x"]
    pg_y, pg_x, menton_y = L["pg_y"], L["pg_x"], L["menton_y"]
    na_y, na_x, st_y = L["na_y"], L["na_x"], L["st_y"]
    ipd_px = L["ipd_px"]
    H_px = L["H_px"]
    n = lambda v: float(v) / ipd_px
    xs = L["xs"]

    def ang(v1, v2):
        a = math.degrees(math.atan2(v1[1], v1[0]) - math.atan2(v2[1], v2[0]))
        a = abs(a) % 360
        return 360 - a if a > 180 else a

    # 座標は (x右向き, y下向き)。左向きの顔なので前 = -x。
    dorsum_ang = math.degrees(math.atan2(na_x - tip_x, tip_y - na_y))  # 鼻すじが垂直から前へ何度傾くか
    nasolabial = ang((tip_x - sn_x, tip_y - sn_y), (ls_x - sn_x, ls_y - sn_y))
    # 鼻先の上向き: 鼻柱(鼻先→鼻の下)が水平に対してなす角(下向きなら小さい、上向きなら大きい)
    columella_up = math.degrees(math.atan2(sn_y - tip_y, sn_x - tip_x))
    # 90 = 真下に垂れた鼻柱、より小さい…(x は右が正)
    m = {
        "nose_proj": n(na_x - tip_x),                 # 鼻根から鼻先までの前への出
        "nose_proj_sn": n(sn_x - tip_x),              # 鼻の下から鼻先まで(鼻先の出)
        "dorsum_angle_deg": dorsum_ang,               # 鼻すじの傾き(垂直から)
        "nasolabial_deg": nasolabial,                 # 鼻唇角(大きいほど鼻先が上向き)
        "columella_deg": columella_up,
        "nose_len_side": n(sn_y - na_y),              # 鼻根〜鼻の下
        "nose_to_lip_len": n(ls_y - sn_y),
        "lip_up_proj": n(sn_x - ls_x),                # 上唇の出(鼻の下基準)
        "lip_lo_proj": n(sn_x - li_x),
        "chin_recess": n(pg_x - sn_x),                # あご先が鼻の下の線より引っ込む量(大きいほど引っ込み)
        "chin_proj_from_lip": n(pg_x - ls_x),
        "chin_len_side": n(menton_y - li_y),          # 下唇〜あご下
        "lower_face_side": n(menton_y - sn_y),        # 鼻の下〜あご下(顔の下半分)
        "mentolabial_depth": n(ms_x - li_x),          # 下唇とあごの間の凹み
        "head_h_side": n(H_px),
        "tip_radius": n(_tip_radius(xs, tip_y, ipd_px)),            # 鼻先の丸さ(大きいほど丸い)
        "nasion_depth": n(xs[na_y] - xs[int(na_y - 0.05 * h)]),  # 目頭あたりの凹みの深さ(額に対し)
    }
    info = dict(ipd_px=ipd_px, tip=(tip_x, tip_y), sn=(sn_x, sn_y), ls=(ls_x, ls_y),
                li=(li_x, li_y), ms=(ms_x, ms_y), pg=(pg_x, pg_y), menton_y=menton_y,
                na=(na_x, na_y), top=top, st_y=st_y)
    if out_png:
        _draw_side(bgr, L, out_png)
    return m, info


def _draw_side(bgr, L, out_png):
    img = bgr.copy()
    h, w = img.shape[:2]
    s = max(1, int(round(w / 700)))
    xs = L["xs"]
    for y in range(0, h, 2):
        if not np.isnan(xs[y]):
            cv2.circle(img, (int(xs[y]), y), 1, (0, 255, 0), -1)
    pts = {"top": (L["top_x"], L["top"]), "na": (L["na_x"], L["na_y"]), "tip": (L["tip_x"], L["tip_y"]),
           "sn": (L["sn_x"], L["sn_y"]), "ls": (L["ls_x"], L["ls_y"]), "st": (L["xs"][L["st_y"]], L["st_y"]),
           "li": (L["li_x"], L["li_y"]), "ms": (L["ms_x"], L["ms_y"]), "pg": (L["pg_x"], L["pg_y"]),
           "menton": (L["pg_x"] + 0.1 * w * 0.5, L["menton_y"])}
    for k, (x, y) in pts.items():
        cv2.circle(img, (int(x), int(y)), s * 3, (0, 0, 255), -1)
        cv2.putText(img, k, (int(x) + 8, int(y) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5 * s,
                    (0, 255, 255), max(1, s), cv2.LINE_AA)
    cv2.line(img, (0, int(L["menton_y"])), (w, int(L["menton_y"])), (255, 128, 0), 1)
    cv2.line(img, (0, int(L["top"])), (w, int(L["top"])), (255, 128, 0), 1)
    cv2.imwrite(out_png, img)


# 呼び出し側の便利関数 ---------------------------------------------------

def measure_pair(front_path, side_path, facing, scale_mode, out_prefix=None):
    """正面と横顔をまとめて測る。
    scale_mode='photo': 横顔の IPD = 正面の IPD × (横顔の頭の高さ / 正面の頭の高さ)(写真は別々に撮ったので)
    scale_mode='render': 同じカメラなので横顔の IPD = 正面の IPD"""
    fm, finfo, _ = measure_front(front_path, (out_prefix + "_front.png") if out_prefix else None)
    ipd = finfo["ipd_px"]
    bgr = _load_rgb(side_path)
    # 横顔の頭の高さを先に出すため、いったん仮の ipd で測る
    tte = fm["top_to_eye"]
    sm0, sinfo0 = measure_side(side_path, facing, ipd_px=ipd, top_to_eye=tte)
    if scale_mode == "photo":
        H_side_px = sm0["head_h_side"] * ipd
        ipd_side = ipd * (H_side_px / finfo["head_h_px"])
        sm, sinfo = measure_side(side_path, facing, ipd_px=ipd_side, top_to_eye=tte,
                                 out_png=(out_prefix + "_side.png") if out_prefix else None)
    else:
        sm, sinfo = measure_side(side_path, facing, ipd_px=ipd, top_to_eye=tte,
                                 out_png=(out_prefix + "_side.png") if out_prefix else None)
    return fm, sm, dict(front=finfo, side=sinfo)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["front", "side", "pair"])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--facing", default="left")
    ap.add_argument("--ipd-px", type=float)
    ap.add_argument("--scale", default="render")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.mode == "front":
        m, info, _ = measure_front(a.paths[0], a.out)
        print(json.dumps({"m": m, "info": info}, indent=1, default=float, ensure_ascii=False))
    elif a.mode == "side":
        m, info = measure_side(a.paths[0], a.facing, ipd_px=a.ipd_px, out_png=a.out)
        print(json.dumps({"m": m, "info": info}, indent=1, default=float, ensure_ascii=False))
    else:
        fm, sm, info = measure_pair(a.paths[0], a.paths[1], a.facing, a.scale, a.out)
        print(json.dumps({"front": fm, "side": sm, "info": info}, indent=1, default=float, ensure_ascii=False))
