"""
Small stdlib client for the bridge's /ui/ routes (preset apply, SkinGen, window reading, framed crop).

Use it from your own scripts:

    from ui_client import run_job, post
    res = run_job("/ui/preset/apply", {"file_path": "C:/.../Nature.ccSkinGenPreset"})

or from a shell (CC5_BRIDGE_URL, default http://127.0.0.1:5101, is the bridge or an ssh tunnel to it):

    python scripts/ui_client.py windows --shots D:/tmp/shots
    python scripts/ui_client.py apply "C:/.../Curled.ccAvatarPreset" --answer layer_choice=replace
    python scripts/ui_client.py editor off
    python scripts/ui_client.py layers
    python scripts/ui_client.py layer opacity --index 0 --opacity 60
    python scripts/ui_client.py presets makeup_lip --query rose
    python scripts/ui_client.py crop --crop 1230,1610,2190,1930 --out D:/tmp/eyes.png

Slow work is a job: the first call returns a job id at once, this client polls /ui/job until it is
done. When a window needs a person, the exit code is 2 and the window is printed (and saved as PNG
with --shots); nothing is ever pressed except the known questions listed in cc5_ui.WINDOW_RULES.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable

DEFAULT_BASE = "http://127.0.0.1:5101"
BUSY_MARK = "Timeout waiting for CC5"      # the bridge's 504: CC5's main thread is busy (baking, modal window)


def _base(base: str | None) -> str:
    return (base or os.environ.get("CC5_BRIDGE_URL") or DEFAULT_BASE).rstrip("/")


def post(path: str, body: dict[str, Any] | None = None, base: str | None = None, timeout: float = 40) -> dict[str, Any]:
    """POST JSON to the bridge. Returns the result dict; a 400/504 reply body is returned too."""
    request = urllib.request.Request(_base(base) + path, data=json.dumps(body or {}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            data = json.loads(reply.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            data = json.loads(err.read().decode("utf-8"))
        except ValueError:
            return {"success": False, "error": f"HTTP {err.code}"}
        return data if isinstance(data, dict) else {"success": False, "error": str(data)}
    return data.get("result", data) if isinstance(data, dict) else {"success": False, "error": str(data)}


def health(base: str | None = None) -> dict[str, Any]:
    """GET /health (blocked main thread = a window is waiting, or CC5 is baking)."""
    with urllib.request.urlopen(_base(base) + "/health", timeout=10) as reply:
        return json.loads(reply.read().decode("utf-8")).get("result", {})


def run_job(path: str, body: dict[str, Any] | None = None, base: str | None = None, timeout_s: float = 300,
            poll_s: float = 1.5, sleep: Callable[[float], None] | None = None,
            post_fn: Callable[..., dict[str, Any]] = post) -> dict[str, Any]:
    """Start a job route and wait for its result. Never raises on a busy CC5; returns the result dict,
    or {"success": False, "state": "running", "windows": [...]} when the time ran out."""
    started = post_fn(path, body, base)
    if not started.get("success") or "job_id" not in started:
        return started
    job_id = started["job_id"]
    deadline = time.time() + timeout_s
    network_errors = 0
    last: dict[str, Any] = {}
    while time.time() < deadline:
        (sleep or time.sleep)(poll_s)
        try:
            last = post_fn("/ui/job", {"job_id": job_id}, base)
        except (urllib.error.URLError, OSError) as exc:
            network_errors += 1
            if network_errors > 5:
                return {"success": False, "job_id": job_id, "error": f"bridge unreachable: {exc}"}
            continue
        if BUSY_MARK in str(last.get("error", "")):
            continue
        if last.get("state") in ("done", "failed"):
            return {**last.get("result", {}), "job_id": job_id, "job_state": last["state"]}
        if last.get("success") is False:
            return last
    return {"success": False, "job_id": job_id, "state": last.get("state", "running"),
            "error": f"still running after {timeout_s:.0f}s", "windows": last.get("windows", [])}


def save_window_pngs(result: dict[str, Any], folder: str, tag: str = "window") -> list[str]:
    """Write the png_base64 of every window in a /ui/windows reply to folder; returns the paths."""
    os.makedirs(folder, exist_ok=True)
    paths = []
    for entry in result.get("windows", []) + ([result["main_window"]] if "main_window" in result else []):
        if entry.get("png_base64"):
            name = f"{tag}_{int(time.time())}_{entry.get('index', 'main')}.png"
            path = os.path.join(folder, name)
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(entry["png_base64"]))
            paths.append(path)
    return paths


def describe_windows(result: dict[str, Any]) -> str:
    lines = []
    for w in result.get("windows", []):
        flag = " [needs a person]" if w.get("needs_human") else (" [progress]" if w.get("progress") else "")
        lines.append(f"- '{w['title']}': {w['text'][:160]} | buttons: {w['buttons']}{flag}")
    return "\n".join(lines) or "(no windows open)"


def _split_floats(text: str) -> list[float]:
    return [float(part) for part in text.split(",")]


def _parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument("--base", help="bridge URL (default CC5_BRIDGE_URL or http://127.0.0.1:5101)")
    top.add_argument("--timeout", type=float, default=300, help="seconds to wait for a job")
    sub = top.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("windows", help="list the open windows")
    w.add_argument("--shots", help="folder for PNGs of the windows")
    w.add_argument("--main", action="store_true", help="also the main window")
    a = sub.add_parser("apply", help="apply preset file(s) to the first avatar")
    a.add_argument("files", nargs="+")
    a.add_argument("--avatar")
    a.add_argument("--answer", action="append", default=[], metavar="KEY=VALUE",
                   help="layer_choice=replace|add, skingen_exit=yes|no, restore_neutral_lash=true|false")
    a.add_argument("--watch", default="", help="list scene items whose name starts with this")
    e = sub.add_parser("editor", help="SkinGen editor on/off")
    e.add_argument("state", choices=("on", "off"))
    sub.add_parser("layers", help="SkinGen editor state and layers")
    ly = sub.add_parser("layer", help="select|show|hide|opacity|delete one layer")
    ly.add_argument("action", choices=("select", "show", "hide", "opacity", "delete"))
    ly.add_argument("--index", type=int)
    ly.add_argument("--name")
    ly.add_argument("--opacity", type=int)
    ly.add_argument("--scope", choices=("selected_layer", "current_material", "all_material"))
    ly.add_argument("--confirm", action="store_true")
    p = sub.add_parser("presets", help="list preset files")
    p.add_argument("category")
    p.add_argument("--query", default="")
    c = sub.add_parser("crop", help="render the framed view big and cut a box")
    c.add_argument("--view", default="face")
    c.add_argument("--size", type=int, default=3600)
    c.add_argument("--crop", type=_split_floats, help="x0,y0,x1,y1 in render pixels")
    c.add_argument("--fraction", type=_split_floats, help="x0,y0,x1,y1 as 0..1")
    c.add_argument("--out", required=True, help="PNG path of the crop (on the CC5 machine)")
    return top


def _answers(pairs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key] = value.lower() == "true" if value.lower() in ("true", "false") else value
    return out


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run = lambda path, body: run_job(path, body, args.base, args.timeout)   # noqa: E731
    if args.cmd == "windows":
        result = post("/ui/windows", {"screenshot": bool(args.shots), "target": "main" if args.main else "dialogs"},
                      args.base)
        print(describe_windows(result))
        if args.shots:
            print("\n".join(save_window_pngs(result, args.shots)))
        return 0 if result.get("success") else 1
    if args.cmd == "layers":
        result = post("/ui/skingen/state", {}, args.base)
    elif args.cmd == "presets":
        result = post("/ui/preset/list", {"category": args.category, "query": args.query}, args.base)
    elif args.cmd == "apply":
        body: dict[str, Any] = {"file_paths": args.files, "answers": _answers(args.answer), "watch_prefix": args.watch}
        if args.avatar:
            body["avatar_name"] = args.avatar
        result = run("/ui/preset/apply", body)
    elif args.cmd == "editor":
        result = run("/ui/skingen/editor", {"active": args.state == "on"})
    elif args.cmd == "layer":
        body = {k: v for k, v in {"action": args.action, "index": args.index, "name": args.name,
                                  "opacity": args.opacity, "scope": args.scope,
                                  "confirm": True if args.confirm else None}.items() if v is not None}
        result = run("/ui/skingen/layer", body)
    else:
        body = {"view": args.view, "size": args.size, "output_path": args.out}
        if args.crop:
            body["crop"] = args.crop
        if args.fraction:
            body["crop_fraction"] = args.fraction
        result = run("/ui/capture_crop", body)
    result.pop("png_base64", None)
    print(json.dumps(result, indent=2, ensure_ascii=False)[:6000])
    if result.get("blocked_by") or any(f.get("blocked_by") for f in result.get("files", [])):
        return 2
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
