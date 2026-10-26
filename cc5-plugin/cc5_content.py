"""
Content presets by script: list what is on hand, and apply a file to an avatar.

Applying is RLPy.RFileIO.LoadFile(path) with the avatar selected, plus a Qt timer that answers the
few question windows the load opens (cc5_ui.WINDOW_RULES). Verified on 2026-10-26 for
.ccAvatarPreset (eyelash presets), .rlEyelashElement and .ccSkinGenPreset (makeup). A SkinGen
preset also opens the SkinGen editor, which hides hair, hat and the eyelash strips until the
editor is switched off again (cc5_skingen.ui_skingen_editor).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Callable, Iterator

import RLPy

import cc5_ui

# Content library folders, as the "$/" virtual paths RLPy.RApplication understands. All but "hair"
# were read on a real CC5 (docs/ui-automation-test-steps_ja.md). Browse further with `folder`.
PRESET_FOLDERS: dict[str, list[str]] = {
    "eyelash_preset": ["$/Avatar Preset/Eyelash"],
    "eyelash_element": ["$/Avatar Preset/Eyelash Element"],
    "makeup_eyelash": ["$/Makeup/Eyelash"],
    "makeup_eye": ["$/Makeup/Eye Makeup"],
    "makeup_lip": ["$/Makeup/Lip Makeup"],
    "makeup_full": ["$/Makeup/Full Makeup"],
    "makeup_foundation": ["$/Makeup/Foundation Makeup"],
    "makeup_eyebrow": ["$/Makeup/Eyebrow"],
    "skingen_tools": ["$/Makeup/SkinGen Tools", "$/Skin/SkinGen Tools"],
    "skin": ["$/Skin"],
    "avatar_preset": ["$/Avatar Preset"],
    "hair": ["$/Hair"],
}

# Files RLPy lists next to content that are not content themselves.
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".db", ".json", ".xml", ".txt", ".ini"}
# The ONLY file types apply_preset loads (lower case). Anything that replaces the scene or the
# character (.ccProject, .ccAvatar, .iAvatar, FBX, ...) is not on the list on purpose; a type that
# is missing here can be added by editing this tuple.
ALLOWED_APPLY_EXTS = frozenset({
    ".ccavatarpreset", ".ccskingenpreset", ".rleyelashelement", ".rlhairelement", ".rlhairstyle", ".rlhair",
    ".cchair", ".cccloth", ".ccshoes", ".ccacc", ".ccfacialprofile", ".cccustomslider", ".imtl",
    ".italk", ".imotionplus", ".rlmotion",
})

LIST_DEFAULT_LIMIT = 200
LIST_MAX_LIMIT = 1000
MAX_FOLDERS_WALKED = 300
MAX_DEPTH = 5
MAX_FILES_PER_CALL = 10
DEFAULT_FILE_SECONDS = 240
SCENE_TYPES = ("Cloth", "Hair", "Accessory", "Prop")
DEFAULT_ROOTS = ("C:/Users/Public/Documents/Reallusion/Reallusion Templates",
                  "C:/Users/Public/Documents/Reallusion/Reallusion Custom")


# --- listing -----------------------------------------------------------------------------

def _roots() -> list[str]:
    raw = os.environ.get("CC5_CONTENT_ROOTS", "")
    roots = [r.strip() for r in raw.split(os.pathsep) if r.strip()] if raw else list(DEFAULT_ROOTS)
    return [r.replace("\\", "/").rstrip("/") for r in roots]


def _rlpy_listing() -> bool:
    app = getattr(RLPy, "RApplication", None)
    return hasattr(app, "GetContentFilesInFolder") and hasattr(app, "GetContentFoldersInFolder")


def _list_files(folder: str, errors: list[str]) -> list[str]:
    """Files directly in a "$/" folder (RLPy first; else the content roots on disk)."""
    if _rlpy_listing():
        try:
            return [str(f).replace("\\", "/") for f in (RLPy.RApplication.GetContentFilesInFolder(folder) or [])]
        except Exception as exc:
            errors.append(f"{folder}: {type(exc).__name__}: {exc}")
            return []
    out: list[str] = []
    for root in _roots():
        path = f"{root}/{folder[2:]}"
        if os.path.isdir(path):
            out.extend(f"{path}/{name}" for name in sorted(os.listdir(path)) if os.path.isfile(f"{path}/{name}"))
    return out


def _list_folders(folder: str, errors: list[str]) -> list[str]:
    """Sub-folders of a "$/" folder as full "$/" paths."""
    names: list[str] = []
    if _rlpy_listing():
        try:
            names = [str(f).replace("\\", "/") for f in (RLPy.RApplication.GetContentFoldersInFolder(folder) or [])]
        except Exception as exc:
            errors.append(f"{folder}: {type(exc).__name__}: {exc}")
    else:
        for root in _roots():
            path = f"{root}/{folder[2:]}"
            if os.path.isdir(path):
                names.extend(n for n in sorted(os.listdir(path)) if os.path.isdir(f"{path}/{n}"))
    return sorted({_child_folder(folder, n) for n in names if n})


def _child_folder(parent: str, child: str) -> str:
    """RLPy may return a sub-folder as a name, a "$/" path or a disk path; make it a "$/" path."""
    if child.startswith("$/"):
        return child.rstrip("/")
    if ":" in child or child.startswith("/"):
        child = child.rstrip("/").rsplit("/", 1)[-1]        # a disk path: only its last part is the name
    return f"{parent.rstrip('/')}/{child.strip('/')}"


def collect_files(folders: list[str], recursive: bool = True,
                  errors: list[str] | None = None) -> tuple[list[dict[str, Any]], list[str], bool]:
    """(entries, folders_seen, truncated) for the given "$/" folders; listing errors go to `errors`."""
    errors = errors if errors is not None else []
    entries: list[dict[str, Any]] = []
    seen: list[str] = []
    queue = [(f, 0) for f in folders]
    while queue and len(seen) < MAX_FOLDERS_WALKED:
        folder, depth = queue.pop(0)
        if folder in seen:
            continue
        seen.append(folder)
        for path in _list_files(folder, errors):
            ext = os.path.splitext(path)[1]
            if ext.lower() in SKIP_EXTS:
                continue
            entries.append({"name": os.path.splitext(os.path.basename(path))[0], "path": path,
                            "folder": folder, "ext": ext, "installed": os.path.isfile(path)})
        if recursive and depth < MAX_DEPTH:
            queue.extend((sub, depth + 1) for sub in _list_folders(folder, errors))
    return entries, seen, bool(queue)


def _valid_folder(folder: str) -> str | None:
    if not folder.startswith("$/") or ".." in folder or "\x00" in folder:
        return "folder must be a content path like '$/Makeup/Lip Makeup' (no '..')"
    return None


def ui_list_presets(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/preset/list: preset files in the content library. Read-only.

    Body: category (one of PRESET_FOLDERS) or folder ("$/..." path); query (substring of name),
    names (exact names to look for: the reply lists the ones not on hand), ext (".ccSkinGenPreset"),
    recursive (default true), list_folders (only the sub-folders of `folder`), limit.
    Content that is still in the cloud (not downloaded) is NOT listed: it is not on disk.
    """
    p = body or {}
    folder = str(p.get("folder") or "").strip().replace("\\", "/")
    category = str(p.get("category") or "").strip().lower()
    if folder:
        error = _valid_folder(folder)
        if error:
            return {"success": False, "error": error}
        folders = [folder]
    elif category in PRESET_FOLDERS:
        folders = list(PRESET_FOLDERS[category])
    else:
        return {"success": False, "error": "give category (" + ", ".join(PRESET_FOLDERS) + ") or folder ('$/...')"}
    errors: list[str] = []
    if p.get("list_folders"):
        subs = sorted({s for f in folders for s in _list_folders(f, errors)})
        return {"success": True, "folders": folders, "subfolders": subs, **({"errors": errors} if errors else {})}
    entries, seen, truncated = collect_files(folders, p.get("recursive", True) is not False, errors)
    out: dict[str, Any] = {"success": True, "folders": seen[:50]}
    names = [str(n) for n in (p.get("names") or [])]
    if names:                                     # judged on everything found, before query / ext narrow it
        have = {e["name"].lower() for e in entries}
        out["missing"] = [n for n in names if n.lower() not in have]
    ext = str(p.get("ext") or "").lower()
    if ext:
        entries = [e for e in entries if e["ext"].lower() == ext]
    query = str(p.get("query") or "").strip().lower()
    if query:
        entries = [e for e in entries if query in e["name"].lower() or query in e["path"].lower()]
    limit = cc5_ui._clamp_int(p.get("limit", LIST_DEFAULT_LIMIT), 1, LIST_MAX_LIMIT, LIST_DEFAULT_LIMIT)
    out.update({"total": len(entries), "presets": entries[:limit], "truncated": truncated or len(entries) > limit})
    if errors:
        out["errors"] = errors[:10]
    out["note"] = "Only content on disk is listed; items still in the cloud are not (download them in the Content panel)."
    return out


# --- applying ----------------------------------------------------------------------------

def check_preset_path(path: str) -> str | None:
    """Why this file may not be applied, or None."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext not in ALLOWED_APPLY_EXTS:
        return (f"{ext or 'no extension'} is not a preset type this tool applies "
                f"(allowed: {', '.join(sorted(ALLOWED_APPLY_EXTS))}); use load_asset for other content on purpose")
    error = cc5_ui.path_problem(path, {ext})
    if error:
        return error
    if not os.path.isfile(path):
        return f"file not found: {path}"
    return None


def _avatar(name: str = "") -> Any:
    avatars = list(RLPy.RScene.GetAvatars() or [])
    if not name:
        return avatars[0] if avatars else None
    return next((a for a in avatars if a.GetName() == name), None)


def scene_items() -> list[str]:
    """Cloth, hair, accessory and prop items in the scene as 'Type:Name' (sorted)."""
    found: list[str] = []
    for kind in SCENE_TYPES:
        enum = getattr(RLPy, "EObjectType_" + kind, None)
        if enum is None:
            continue
        try:
            found.extend(f"{kind}:{o.GetName()}" for o in (RLPy.RScene.FindObjects(enum) or []))
        except Exception:
            continue
    return sorted(found)


def _status_error(status: Any) -> bool | None:
    try:
        return bool(status.IsError())
    except Exception:
        return None


def _skingen_summary() -> dict[str, Any] | None:
    module = sys.modules.get("cc5_skingen")
    if module is None:
        return None
    state = module.read_state()
    if not state["editor_found"]:
        return None
    return {"editor_active": state["editor_active"], "layers": [l["name"] for l in state["layers"]]}


def _apply_one(avatar_name: str, path: str, choices: dict[str, Any], limit_s: float, watch: str,
               baseline: set[tuple[str, str]]) -> Iterator[float]:
    entry: dict[str, Any] = {"path": path, "ok": False}
    avatar = _avatar(avatar_name)                  # looked up again for every file: a load may rebuild it
    if avatar is None:
        entry["error"] = f"avatar not found: {avatar_name or '(none in the scene)'}"
        return entry
    before = scene_items()
    try:
        RLPy.RScene.ClearSelectObjects()
        RLPy.RScene.SelectObject(avatar)
        status = RLPy.RFileIO.LoadFile(path)          # a nested loop: the answerer's timer fires inside it
    except Exception as exc:
        entry["error"] = f"LoadFile raised {type(exc).__name__}: {exc}"
        return entry
    entry["status_error"] = _status_error(status)
    settled = yield from cc5_ui.settle_steps(limit_s, choices, baseline=baseline)
    after = scene_items()
    entry["added"] = [i for i in after if i not in before]
    entry["removed"] = [i for i in before if i not in after]
    if watch:
        entry["watched"] = [i.split(":", 1)[1] for i in after if i.split(":", 1)[1].startswith(watch)]
    entry["settled"] = settled["ok"]
    if not settled["ok"]:
        entry["blocked_by"] = settled.get("blocked_by")
        entry["error"] = cc5_ui.settle_error(settled)
    elif entry["status_error"]:
        entry["error"] = "LoadFile reported an error"
    entry["ok"] = settled["ok"] and not entry["status_error"]
    return entry


def _apply_budget(files: int, per_file_s: float) -> float:
    """Longest a whole apply job may take (also the answerer's time limit)."""
    return files * (per_file_s + 30) + 120


def _apply_steps(p: dict[str, Any]) -> Iterator[float]:
    choices = p["choices"]
    avatar = _avatar(p.get("avatar_name", ""))
    if avatar is None:
        return {"success": False, "error": "avatar not found: " + (p.get("avatar_name") or "(none in the scene)")}
    avatar_name = avatar.GetName()
    answerer = cc5_ui.WindowAnswerer(choices, max_seconds=_apply_budget(len(p["paths"]), p["timeout_s"])).start()
    files: list[dict[str, Any]] = []
    try:
        baseline = cc5_ui.baseline_keys()
        for path in p["paths"]:
            answerer.touch()
            entry = yield from _apply_one(avatar_name, path, choices, p["timeout_s"], p.get("watch_prefix", ""), baseline)
            files.append(entry)
            if not entry["ok"]:
                break                                   # do not pile more loads on top of a problem
    finally:
        answered = answerer.stop()
    api = cc5_ui._api()
    if hasattr(api, "_invalidate_caches"):
        api._invalidate_caches()
    out: dict[str, Any] = {"success": all(f["ok"] for f in files) and len(files) == len(p["paths"]),
                           "avatar": avatar_name, "files": files, "answered": answered,
                           "skipped": p["paths"][len(files):]}
    if answerer.blocked:
        out["blocked_windows"] = answerer.blocked
    skingen = _skingen_summary()
    if skingen is not None:
        out["skingen"] = skingen
        if skingen["editor_active"]:
            out["note"] = ("The SkinGen editor is open: hair, hat and eyelash strips stay hidden until it is "
                           "switched off (skingen_editor active=false, which bakes).")
    if not out["success"]:
        failed = next((f for f in files if not f["ok"]), None)
        out["error"] = (failed or {}).get("error", "not every file was applied")
    return out


def ui_apply_preset(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /ui/preset/apply: apply content file(s) to an avatar. Starts a job (poll /ui/job).

    Body: file_path or file_paths (up to 10, applied in order), avatar_name (default: the first
    avatar), answers {layer_choice: replace|add, restore_neutral_lash: bool, skingen_exit: yes|no},
    timeout_s (default 240 per file), watch_prefix (list scene items whose name starts with it,
    e.g. "Lash_"). Only the windows in cc5_ui.WINDOW_RULES are answered; anything else is reported.
    Only the file types in ALLOWED_APPLY_EXTS are loaded.
    """
    p = dict(body or {})
    if p.get("file_paths") and p.get("file_path"):
        return {"success": False, "error": "give file_path or file_paths, not both"}
    raw = p.get("file_paths") or ([p["file_path"]] if p.get("file_path") else [])
    if not isinstance(raw, (list, tuple)) or not raw or len(raw) > MAX_FILES_PER_CALL:
        return {"success": False, "error": f"give file_path or file_paths (1 to {MAX_FILES_PER_CALL} files)"}
    paths = [str(x).strip().replace("\\", "/") for x in raw]
    for path in paths:
        error = check_preset_path(path)
        if error:
            return {"success": False, "error": error, "path": path}
    try:
        p["choices"] = cc5_ui.normalize_choices(p.get("answers"))
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    if _avatar(str(p.get("avatar_name") or "")) is None:
        return {"success": False, "error": "avatar not found: " + str(p.get("avatar_name") or "(none in the scene)")}
    p["paths"] = paths
    p["timeout_s"] = cc5_ui._clamp_int(p.get("timeout_s", DEFAULT_FILE_SECONDS), 10, 900, DEFAULT_FILE_SECONDS)
    p["watch_prefix"] = str(p.get("watch_prefix") or "")
    return cc5_ui.start_job("preset", _apply_steps, p, max_seconds=_apply_budget(len(paths), p["timeout_s"]) + 60)


ROUTES: dict[str, tuple[str, Callable[..., dict[str, Any]]]] = {
    "/ui/preset/list": ("ui_list_presets", ui_list_presets),
    "/ui/preset/apply": ("ui_apply_preset", ui_apply_preset),
}
