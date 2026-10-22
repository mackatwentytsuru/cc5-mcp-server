"""
CC5 RLPy API wrapper functions.

Provides a clean interface over RLPy for character manipulation.
All functions MUST be called from the main thread (via QTimer queue).
"""

from __future__ import annotations

import os
import sys
import base64
import math
import tempfile
import time
import urllib.parse
from typing import Any

import RLPy

# --- Path validation (defense-in-depth, mirrors TypeScript validation) ---

_ALLOWED_LOAD_EXTENSIONS = {
    ".iavatar", ".ccavatar", ".ccm", ".iclothes", ".ihair", ".iprop",
    ".ccfbx", ".iclothing", ".ishoe", ".iaccessory", ".ibody", ".iskin",
    ".ccproject", ".rlhair", ".rlhairelement",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

MAX_MORPH_ID_LENGTH = 256

# Default export directory for FBX exports given a bare filename (no directory
# component). Overridable via the CC5_EXPORT_DIR environment variable.
CC5_EXPORT_DIR = os.environ.get("CC5_EXPORT_DIR", r"D:\CC5Export")

# UR-25: prefer EObjectModifiedType_Material for material/color changes.
# Falls back to _Attribute if _Material is not in this build.
_EOMTYPE_MATERIAL = (
    RLPy.EObjectModifiedType_Material
    if hasattr(RLPy, "EObjectModifiedType_Material")
    else RLPy.EObjectModifiedType_Attribute
)



def _validate_morph_id(morph_id: str) -> str | None:
    """Validate morph ID length. Returns error message or None."""
    if len(morph_id) > MAX_MORPH_ID_LENGTH:
        return f"Morph ID too long ({len(morph_id)} chars, max {MAX_MORPH_ID_LENGTH})"
    return None


def _validate_path(file_path: str, allowed_extensions: set[str]) -> str | None:
    """Validate a file path. Returns error message or None if valid."""
    # Defense-in-depth: catch percent-encoded ('%2e%2e') dot segments too.
    decoded = urllib.parse.unquote(file_path)
    if "\x00" in file_path or "\x00" in decoded:
        return "Path contains null byte"
    if ".." in file_path or ".." in decoded:
        return "Path traversal ('..') is not allowed"
    resolved = os.path.realpath(file_path)
    ext = os.path.splitext(resolved)[1].lower()
    if ext not in allowed_extensions:
        return f"Disallowed file extension: {ext}"
    return None


# --- Avatar helpers ---

def get_avatars() -> list[dict[str, Any]]:
    """Get all avatars in the current scene."""
    avatars = RLPy.RScene.GetAvatars()
    return [
        {
            "name": avatar.GetName(),
            "id": avatar.GetID(),
            "type": str(avatar.GetType()),
        }
        for avatar in avatars
    ]


def get_first_avatar():
    """Get the first avatar in the scene (or None)."""
    avatars = RLPy.RScene.GetAvatars()
    return avatars[0] if avatars else None


def get_avatar_by_name(name: str = ""):
    """Get an avatar by name, or the first avatar if no name given."""
    avatars = RLPy.RScene.GetAvatars()
    if not avatars:
        return None
    if not name:
        return avatars[0]
    for avatar in avatars:
        if avatar.GetName() == name:
            return avatar
    return None


# --- Morph helpers ---

_morph_id_cache: dict[int, set[str]] = {}
_morph_catalog_cache: dict[int, dict[str, list[dict[str, str]]]] = {}

# UR-13: set to True after RenderImage fails post-.ccProject load so later
# captures skip the failing attempts and go straight to the fallback.
_render_image_broken: bool = False


def _get_all_morph_ids() -> set[str]:
    """Get all known morph IDs for the current avatar (cached per avatar ID)."""
    avatar = get_first_avatar()
    if not avatar:
        return set()
    avatar_id = avatar.GetID()
    if avatar_id in _morph_id_cache:
        return _morph_id_cache[avatar_id]
    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return set()
    all_ids: set[str] = set()
    categories = shaping_comp.GetShapingMorphCatergoryNames()
    for cat in categories:
        ids = shaping_comp.GetShapingMorphIDs(cat)
        all_ids.update(ids)
    _morph_id_cache[avatar_id] = all_ids
    return all_ids


def _invalidate_caches() -> None:
    """Clear morph ID and catalog caches (call after scene changes)."""
    global _render_image_broken
    _morph_id_cache.clear()
    _morph_catalog_cache.clear()
    _render_image_broken = False


def headshot_from_photo(
    photo_path: str,
    body_type: str = "Neutral",
    baby: bool = False,
) -> dict[str, Any]:
    """Create a Headshot 3 character using Reallusion's bundled RLPy2 pattern.

    The file guard runs before any Headshot API call. Silent mode is restored to
    its previous value even when generation raises, and scene-dependent caches
    are invalidated after every attempted generation because the avatar may have
    been replaced before an exception was reported.
    """
    import time

    if not isinstance(photo_path, str) or not photo_path.strip():
        return {"ok": False, "error": "photo_path must be a non-empty string"}
    resolved_photo = os.path.realpath(photo_path)
    if not os.path.isfile(resolved_photo):
        return {"ok": False, "error": f"photo not found: {resolved_photo}"}

    # Verified by introspecting RLPy2.EHSBodyType on CC5 v5.11.1823:
    #   Male=0 Female=1 Baby=2 Kid=3 Neutral=4 Current=5
    # RLPy (v1) numbers these differently (Neutral=3, no Kid), so never pass raw
    # ints between the two APIs -- always resolve by attribute name as below.
    # "Current" is excluded deliberately: it reuses the avatar already in the
    # scene, which is not what a photo-to-head call should do.
    allowed_body_types = {"Male", "Female", "Baby", "Kid", "Neutral"}
    if body_type not in allowed_body_types:
        return {
            "ok": False,
            "error": f"unsupported body_type: {body_type}",
            "allowed": sorted(allowed_body_types),
        }
    if not isinstance(baby, bool):
        return {
            "ok": False,
            "error": "baby must be a bool",
        }

    import RLPy2

    face_feature_preset = RLPy2.RArrayListWString()
    skin_list = RLPy2.RArrayListWString(3, "None")
    skin_list[0] = "Soft Skin"
    mask_list = RLPy2.RArrayListWString(4, "None")
    mask_list[0] = "No Mask"
    body_type_value = getattr(RLPy2.EHSBodyType, body_type)

    previous_silent = None
    silent_changed = False
    started = time.perf_counter()
    try:
        if hasattr(RLPy, "RGlobal_GetSilentMode") and hasattr(RLPy, "RGlobal_SetSilentMode"):
            previous_silent = bool(RLPy.RGlobal_GetSilentMode())
            RLPy.RGlobal_SetSilentMode(True)
            silent_changed = True
        hs_interface = RLPy2.Headshot3.GetInterface()
        ret = hs_interface.CenerateCharacter(
            resolved_photo,
            body_type_value,
            baby,
            face_feature_preset,
            skin_list,
            mask_list,
        )
        elapsed = time.perf_counter() - started
        return {
            "ok": True,
            "ret": repr(ret),
            "elapsed_seconds": round(elapsed, 3),
            "body_type": body_type,
            "baby": baby,
            "avatar_count": len(RLPy.RScene.GetAvatars()),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return {
            "ok": False,
            "error": repr(exc),
            "elapsed_seconds": round(elapsed, 3),
            "body_type": body_type,
            "baby": baby,
        }
    finally:
        _invalidate_caches()
        if silent_changed:
            try:
                RLPy.RGlobal_SetSilentMode(previous_silent)
            except Exception:
                pass


def get_morph_catalog() -> dict[str, list[dict[str, str]]]:
    """Enumerate all available shaping morph IDs, grouped by category (cached per avatar ID)."""
    avatar = get_first_avatar()
    if not avatar:
        return {}
    avatar_id = avatar.GetID()
    if avatar_id in _morph_catalog_cache:
        return _morph_catalog_cache[avatar_id]

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {}

    catalog: dict[str, list[dict[str, str]]] = {}
    categories = shaping_comp.GetShapingMorphCatergoryNames()

    for cat in categories:
        ids = shaping_comp.GetShapingMorphIDs(cat)
        names = shaping_comp.GetShapingMorphDisplayNames(cat)
        catalog[cat] = [
            {"id": ids[i], "display_name": names[i] if i < len(names) else ids[i]}
            for i in range(len(ids))
        ]

    _morph_catalog_cache[avatar_id] = catalog
    return catalog


MAX_SEARCH_RESULTS = 200


def search_morphs(query: str, category: str = "") -> list[dict[str, str]]:
    """Search morph catalog by display name. Returns matching morphs.
    Iterates the catalog cache populated by get_morph_catalog (UR-12).
    """
    if not query.strip():
        return []
    query_lower = query.lower()
    avatar = get_first_avatar()
    if not avatar:
        return []
    catalog = get_morph_catalog()
    if not catalog:
        return []
    results: list[dict[str, str]] = []
    for cat, entries in catalog.items():
        if category and category.lower() not in cat.lower():
            continue
        for entry in entries:
            morph_id = entry["id"]
            display = entry["display_name"]
            if query_lower in display.lower() or query_lower in morph_id.lower():
                results.append({"id": morph_id, "display_name": display, "category": cat})
    # Deduplicate by ID
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique[:MAX_SEARCH_RESULTS]


def get_morph_value(morph_id: str) -> dict[str, Any]:
    """Get current value of a shaping morph slider."""
    error = _validate_morph_id(morph_id)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component found"}

    value = shaping_comp.GetShapingMorphWeight(morph_id)
    return {"success": True, "morph_id": morph_id, "value": value}


def set_morph_value(morph_id: str, value: float) -> dict[str, Any]:
    """Set a shaping morph slider value (0.0 - 1.0)."""
    error = _validate_morph_id(morph_id)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component found"}

    # Validate morph ID exists
    known_ids = _get_all_morph_ids()
    if known_ids and morph_id not in known_ids:
        return {"success": False, "error": f"Unknown morph ID: {morph_id}"}

    value = max(-1.0, min(1.0, value))
    try:
        RLPy.RGlobal.BeginAction("Set Morph")
        shaping_comp.SetShapingMorphWeight(morph_id, value)
        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()

    return {"success": True, "morph_id": morph_id, "value": value}


MAX_MORPH_BATCH = 500


def set_multiple_morphs(morphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Set multiple morph values at once. Each entry: {"morph_id": str, "value": float} (also accepts "id")."""
    if len(morphs) > MAX_MORPH_BATCH:
        return {"success": False, "error": f"Too many morphs: {len(morphs)}, max {MAX_MORPH_BATCH}"}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component found"}

    # Normalize and validate all entries before applying any
    normalized: list[tuple[str, float]] = []
    for morph in morphs:
        morph_id = morph.get("morph_id", morph.get("id"))
        if not morph_id or "value" not in morph:
            return {"success": False, "error": "Morph entry missing 'morph_id' or 'value'"}
        error = _validate_morph_id(morph_id)
        if error:
            return {"success": False, "error": error}
        normalized.append((morph_id, float(morph["value"])))

    # Validate morph IDs
    known_ids = _get_all_morph_ids()
    if known_ids:
        unknown = [mid for mid, _ in normalized if mid not in known_ids]
        if unknown:
            return {"success": False, "error": f"Unknown morph ID(s): {', '.join(unknown)}"}

    try:
        RLPy.RGlobal.BeginAction("Set Multiple Morphs")
        results = []
        for morph_id, raw_value in normalized:
            value = max(-1.0, min(1.0, raw_value))
            shaping_comp.SetShapingMorphWeight(morph_id, value)
            results.append({"morph_id": morph_id, "value": value})

        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "applied": results}


def _get_cc5_root() -> str:
    """Get CC5 installation root, using RLPy if available.
    GetProgramPath() may return either the exe path (.../Bin64/CharacterCreator.exe)
    or the Bin64 directory. Guard the dirname depth accordingly:
    exe (file) -> Bin64 -> root (dirname twice); Bin64 (dir) -> root (dirname once).
    """
    if hasattr(RLPy, "RApplication") and hasattr(RLPy.RApplication, "GetProgramPath"):
        try:
            app_path = RLPy.RApplication.GetProgramPath()
            if app_path:
                if os.path.isfile(app_path):
                    # exe -> Bin64 -> CC5 root
                    candidate = os.path.dirname(os.path.dirname(app_path))
                else:
                    # Bin64 dir -> CC5 root
                    candidate = os.path.dirname(app_path)
                if os.path.isdir(candidate):
                    return candidate
        except Exception:
            pass
    return os.environ.get("CC5_ROOT", r"C:\Program Files\Reallusion\Character Creator 5")


def create_default_avatar() -> dict[str, Any]:
    """Load the CC5 NEUTRAL base avatar (additive, does not clear scene).

    NOTE: this neutral base has NO skin/eye textures, eyebrows, eyelashes or hair —
    it renders like a pale, blank-eyed mannequin. For a real, textured human face,
    prefer loading a character template instead: browse_content("character") returns
    fully-textured avatars (e.g. CC4 Camila / CC4 Susan) that you load with load_asset.
    Use delete_avatar first if you want to replace what's already in the scene.
    """
    cc5_root = _get_cc5_root()

    # Use .ccAvatar (additive load — does not replace the scene)
    avatar_path = os.path.join(cc5_root, "Program", "CCBaseData", "NeutralAvatar", "RL_CC3_Plus.ccAvatar")
    if not os.path.exists(avatar_path):
        return {"success": False, "error": f"Default avatar not found: {avatar_path}"}

    try:
        result = RLPy.RFileIO.LoadFile(avatar_path)
        _invalidate_caches()
        avatars = RLPy.RScene.GetAvatars()
        name = avatars[-1].GetName() if avatars else "Unknown"
        avatar_id = avatars[-1].GetID() if avatars else None
        return {"success": True, "name": name, "id": avatar_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_avatar(name: str = "") -> dict[str, Any]:
    """Delete an avatar from the scene by name. If name is empty, deletes ALL avatars.

    Useful to clear a neutral mannequin before loading a textured character template,
    or to start the scene over. Uses RScene.RemoveObject.
    """
    avatars = RLPy.RScene.GetAvatars()
    if not avatars:
        return {"success": False, "error": "No avatars in scene"}
    target = (name or "").strip()
    removed: list[str] = []
    try:
        RLPy.RGlobal.BeginAction("Delete Avatar")
        for avatar in list(avatars):
            aname = avatar.GetName()
            if not target or aname == target:
                RLPy.RScene.RemoveObject(avatar)
                removed.append(aname)
    finally:
        RLPy.RGlobal.EndAction()
    _invalidate_caches()
    if not removed:
        return {"success": False, "error": f"Avatar not found: {target}"}
    return {"success": True, "removed": removed}


def load_asset(file_path: str) -> dict[str, Any]:
    """Load a CC5 asset file (.iAvatar, .ccm, .ccShoes, .ccCloth, etc.)."""
    # Defense-in-depth: validate path even though TypeScript also validates.
    # Path-safety (traversal/null) via _validate_path; for the extension, accept the
    # explicit allowlist OR any CC5.1 / iClone content family (.cc*/.i*) — browse_content
    # returns .cc* content files (e.g. .ccShoes) that the legacy allowlist did not cover.
    decoded = urllib.parse.unquote(file_path)
    if "\x00" in file_path or "\x00" in decoded:
        return {"success": False, "error": "Path contains null byte"}
    if ".." in file_path or ".." in decoded:
        return {"success": False, "error": "Path traversal ('..') is not allowed"}
    ext = os.path.splitext(os.path.realpath(file_path))[1].lower()
    if ext not in _ALLOWED_LOAD_EXTENSIONS and not (ext.startswith(".cc") or ext.startswith(".i")):
        return {"success": False, "error": f"Disallowed file extension: {ext}"}

    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        result = RLPy.RFileIO.LoadFile(file_path)
        _invalidate_caches()
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _describe_rlpy_status(status: Any) -> tuple[bool | None, str]:
    """Interpret a return value from an RLPy call as (ok, description).

    RLPy file operations return an RStatus (IsError()/GetStatusCode()); some
    builds return a bool or None. ok is None when the value is not interpretable
    (so callers rely on checking the filesystem instead).
    """
    if status is None:
        return None, "None"
    if isinstance(status, bool):
        return status, f"bool({status})"
    if hasattr(status, "IsError"):
        try:
            is_err = bool(status.IsError())
        except Exception:
            return None, repr(status)
        code = ""
        try:
            code = f", code={status.GetStatusCode()}"
        except Exception:
            pass
        return (not is_err), f"RStatus(IsError={is_err}{code})"
    return None, repr(status)


def _export_failure_hints() -> str:
    """Best-effort, read-only explanation for a refused export (no UI is touched)."""
    parts: list[str] = []
    glob = getattr(RLPy, "RGlobal", None)
    trial_content = None
    for name in ("IsTrialContentMode", "IsTrialVersion"):
        fn = getattr(glob, name, None) if glob is not None else None
        if fn is None:
            continue
        try:
            val = bool(fn())
        except Exception:
            continue
        parts.append(f"RGlobal.{name}()={val}")
        if name == "IsTrialContentMode":
            trial_content = val
    if trial_content:
        parts.append(
            "CAUSE: the project contains trial (unpurchased) content, so CC5 refuses to "
            "export ('This project contains trial content. Purchase the trial content ... "
            "in order to export it.'). Replace or remove the trial items, or purchase them; "
            "a person must decide. This tool never clicks any CC5 pop-up."
        )
    else:
        parts.append(
            "Cause unknown. Check CC5 for a pop-up (list_dialogs); a person must decide "
            "on it. This tool never clicks any CC5 pop-up."
        )
    return " ".join(parts)


def _verify_fbx_written(output_path: str, status: Any, notes: list[str],
                        started_at: float) -> dict[str, Any] | None:
    """Confirm an FBX export actually produced a file.

    Returns a failure dict if the export reported an error, or if no non-empty
    file exists at output_path that was written during this call. Returns None
    when the file is verified (size is appended to notes).
    """
    ok, desc = _describe_rlpy_status(status)
    notes.append(f"ExportFbxFile returned {desc}")
    if ok is False:
        hints = _export_failure_hints()
        return {"success": False,
                "error": f"CC5 reported an FBX export error: {desc}. {hints}",
                "notes": notes}
    try:
        st = os.stat(output_path)
    except OSError:
        st = None
    if st is None or st.st_size <= 0 or st.st_mtime < started_at - 2.0:
        reason = ("no file was created" if st is None
                  else "file is empty" if st.st_size <= 0
                  else "file was not updated by this export (stale file)")
        return {
            "success": False,
            "error": f"FBX export reported success but verification failed: {reason} at {output_path}",
            "path": output_path,
            "notes": notes,
        }
    notes.append(f"verified: {st.st_size} bytes written")
    return None



def export_fbx(
    output_path: str,
    options_flags: int = 0,
    target_tool: str = "",
    sub_d_level: int | None = None,
    include_current_pose: bool = False,
    delete_hidden_faces: bool = False,
    use_smooth_mesh: bool = False,
    remove_eyelash: bool = False,
    remove_tearline_occlusion: bool = False,
    embed_textures: bool = False,
    export_motion: bool = True,
    fps: int | None = None,
    motion_range: list | None = None,
    convert_image_format: bool = False,
    texture_size: int | None = None,
) -> dict[str, Any]:
    """Export the current avatar as FBX, mirroring the CC5 "Export FBX" dialog.

    Args:
        output_path: .fbx destination. A bare filename (no directory component)
            is resolved under CC5_EXPORT_DIR (default ``D:\\CC5Export``).
        options_flags: Raw EExportFbxOptions bitmask. If 0, defaults are computed from named flags.
        target_tool: "UE5" | "Default" | "Maya" | "Unity" — sets sensible base flag preset
        sub_d_level: 0|1|2. HD Character Subdivision Level. Applied via
            RExportFbxSetting.SetExportLevel (no scene mutation). Falls back to
            set_subdivision_level only on the flag-less 2-arg export path.
        include_current_pose: Keep the current pose (do NOT force T-pose on first motion frame)
        delete_hidden_faces: Add EExportFbxOptions_RemoveHiddenMesh
        use_smooth_mesh: Enable RExportFbxSetting.EnableBakeSubdivision (CC5 UI "Use Smooth Mesh")
                         — falls back to setting sub_d_level=1 if RExportFbxSetting variant fails.
        remove_eyelash: Add EExportFbxOptions_RemoveEyelash
        remove_tearline_occlusion: Add EExportFbxOptions_RemoveTearLineAndOcclusion
        embed_textures: "Embed Textures" — add EExportFbxOptions_EmbedTexture.
        export_motion: "Mesh and Motion" when True, "Mesh" (mesh only) when False.
        fps: "Frame Rate" for included motion (e.g. 30). Mapped to RLPy.RFps.Fps{n}.
        motion_range: [start, end] frame range. None/"all" leaves the dialog default ("All").
        convert_image_format: "Convert Image Format" — add EExportFbxOptions_ConvertTifToPNG.
        texture_size: "Max Texture Size" in pixels (0 = original).
    """
    # Defense-in-depth path validation
    _decoded_out = urllib.parse.unquote(output_path)
    if "\x00" in output_path or "\x00" in _decoded_out:
        return {"success": False, "error": "Path contains null byte"}
    if ".." in output_path or ".." in _decoded_out:
        return {"success": False, "error": "Path traversal ('..') is not allowed"}

    notes: list[str] = []

    # Resolve a bare filename (no directory component) under CC5_EXPORT_DIR.
    if os.path.dirname(output_path) == "":
        output_path = os.path.join(CC5_EXPORT_DIR, output_path)
        notes.append(f"bare filename resolved under CC5_EXPORT_DIR ({CC5_EXPORT_DIR})")

    resolved = os.path.realpath(output_path)
    if not resolved.lower().endswith(".fbx"):
        return {"success": False, "error": "Output path must end with .fbx"}

    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    # Subdivision is applied via RExportFbxSetting.SetExportLevel inside the
    # setting-object block below (no scene mutation). The set_subdivision_level
    # snapshot/rollback dance is only used on the flag-less 2-arg fallback path.
    _orig_subd = None

    # --- Build option flags ---
    _MISSING_FLAG = object()

    def _safe_flag(name: str) -> int:
        val = getattr(RLPy, name, _MISSING_FLAG)
        if val is _MISSING_FLAG:
            notes.append(f"WARNING: RLPy.{name} not found, flag skipped")
            return 0
        return val

    flags = int(options_flags) if options_flags else 0
    flags2 = 0
    flags3 = 0

    # Target tool presets (matches CC5 "Target Tool Preset" UI)
    target_upper = (target_tool or "").upper()
    if target_upper == "UE5" or target_upper == "UNREAL":
        flags |= _safe_flag("EExportFbxOptions_AutoSkinRigidMesh")
        flags |= _safe_flag("EExportFbxOptions_ExportRootMotion")
        flags |= _safe_flag("EExportFbxOptions_RemoveAllUnused")
        flags2 |= _safe_flag("EExportFbxOptions2_UnrealPreset")
        flags2 |= _safe_flag("EExportFbxOptions2_UnrealEngine4BoneAxis")
        flags2 |= _safe_flag("EExportFbxOptions2_YUp")
        # The UI's "Unreal Engine" preset also writes the Auto Setup companion
        # .json manifest. Without it, UE's CC Auto Setup importer (UCCFbxFactory)
        # crashes with "Array index out of bounds" (verified 2026-07-02).
        flags3 |= _safe_flag("EExportFbxOptions3_ExportJson")
        # Characters whose body shape is driven by bone scaling export an FBX
        # whose bind-pose matrices don't match the node transforms unless the
        # exporter re-bakes them — UE then force-enables T0-as-ref-pose and hits
        # a deterministic engine crash in morph import (verified 2026-07-02:
        # 11/14 meshes invalid without these; 14/14 valid at 1e-6 with them).
        flags2 |= _safe_flag("EExportFbxOptions2_ResetSkinPose")
        flags2 |= _safe_flag("EExportFbxOptions2_ResetBoneScale")
        notes.append("target_tool=UE5 preset applied (incl. ExportJson + ResetSkinPose/ResetBoneScale)")
    elif target_upper == "UNITY":
        flags |= _safe_flag("EExportFbxOptions_AutoSkinRigidMesh")
        flags2 |= _safe_flag("EExportFbxOptions2_UnityPreset")
        flags2 |= _safe_flag("EExportFbxOptions2_YUp")
        notes.append("target_tool=Unity preset applied")
    elif target_upper == "MAYA":
        flags |= _safe_flag("EExportFbxOptions_AutoSkinRigidMesh")
        flags |= _safe_flag("EExportFbxOptions_MayaAdjustMaterial")
        notes.append("target_tool=Maya preset applied")
    elif flags == 0:
        # Default fallback (preserve old behavior)
        flags = _safe_flag("EExportFbxOptions_AutoSkinRigidMesh") | _safe_flag("EExportFbxOptions_ExportRootMotion")

    # Pose handling
    if not include_current_pose:
        flags |= _safe_flag("EExportFbxOptions_TPoseOnMotionFirstFrame")
    else:
        # Explicitly clear T-pose bit
        tpose_bit = _safe_flag("EExportFbxOptions_TPoseOnMotionFirstFrame")
        if tpose_bit:
            flags &= ~tpose_bit

    if delete_hidden_faces:
        flags |= _safe_flag("EExportFbxOptions_RemoveHiddenMesh")
    if remove_eyelash:
        flags |= _safe_flag("EExportFbxOptions_RemoveEyelash")
    if remove_tearline_occlusion:
        flags |= _safe_flag("EExportFbxOptions_RemoveTearLineAndOcclusion")

    # Texture Settings (CC5 dialog)
    if embed_textures:
        flags |= _safe_flag("EExportFbxOptions_EmbedTexture")  # "Embed Textures"
    if convert_image_format:
        flags |= _safe_flag("EExportFbxOptions_ConvertTifToPNG")  # "Convert Image Format"

    # Honest-reporting trackers for the RExportFbxSetting-only options. Each is
    # set to the actually-applied value only after its setter succeeds.
    applied_export_level: int | None = None
    applied_export_motion: bool | None = None
    applied_fps: int | None = None
    applied_motion_range: list | None = None
    applied_texture_size: int | None = None
    export_status: Any = None
    export_started = time.time()

    try:
        dir_path = os.path.dirname(output_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # --- Always use RExportFbxSetting object path (UR-16).
        # Passing a bare int as the 3rd arg to ExportFbxFile can crash CC5.
        # Fall back to the 2-arg call only if RExportFbxSetting is unavailable.
        used_setting_object = False
        applied_flags2 = False
        applied_flags3 = False
        if hasattr(RLPy, "RExportFbxSetting"):
            try:
                setting = RLPy.RExportFbxSetting()
                setting.SetOption(flags)
                if flags2:
                    try:
                        setting.SetOption2(flags2)
                        applied_flags2 = True
                    except Exception as e:
                        notes.append(f"WARNING: SetOption2 failed, flags2 NOT applied: {e}")
                if flags3:
                    try:
                        setting.SetOption3(flags3)
                        applied_flags3 = True
                    except Exception as e:
                        notes.append(f"WARNING: SetOption3 failed, flags3 NOT applied: {e}")
                if use_smooth_mesh and hasattr(setting, "EnableBakeSubdivision"):
                    setting.EnableBakeSubdivision(True)
                    notes.append("use_smooth_mesh: EnableBakeSubdivision(True) on RExportFbxSetting")

                # HD Character Subdivision Level — SetExportLevel does NOT mutate
                # the scene (unlike set_subdivision_level).
                if sub_d_level is not None:
                    try:
                        setting.SetExportLevel(int(sub_d_level))
                        applied_export_level = int(sub_d_level)
                        notes.append(f"SetExportLevel({int(sub_d_level)}) applied")
                    except Exception as e:
                        notes.append(f"WARNING: SetExportLevel failed: {e}")

                # FBX Options: "Mesh and Motion" (True) vs "Mesh" only (False).
                try:
                    setting.EnableExportMotion(bool(export_motion))
                    applied_export_motion = bool(export_motion)
                except Exception as e:
                    notes.append(f"WARNING: EnableExportMotion failed: {e}")

                # Include Motion — Frame Rate. RFps values are attributes (RLPy.RFps.Fps30).
                if fps is not None:
                    fps_attr = getattr(RLPy.RFps, f"Fps{int(fps)}", None) if hasattr(RLPy, "RFps") else None
                    if fps_attr is None:
                        notes.append(f"WARNING: RLPy.RFps.Fps{int(fps)} not found, fps skipped")
                    else:
                        try:
                            setting.SetExportMotionFps(fps_attr)
                            applied_fps = int(fps)
                        except Exception as e:
                            notes.append(f"WARNING: SetExportMotionFps failed: {e}")

                # Include Motion — frame range. None/"all" leaves the default ("All").
                if motion_range is not None:
                    if isinstance(motion_range, (list, tuple)) and len(motion_range) == 2:
                        try:
                            start_f, end_f = int(motion_range[0]), int(motion_range[1])
                            setting.SetExportMotionRange(RLPy.RRangePair(start_f, end_f))
                            applied_motion_range = [start_f, end_f]
                        except Exception as e:
                            notes.append(f"WARNING: SetExportMotionRange failed: {e}")
                    else:
                        notes.append("WARNING: motion_range must be [start, end]; left default (All)")

                # Texture Settings — "Max Texture Size" (0 = original).
                if texture_size is not None:
                    try:
                        setting.SetTextureSize(int(texture_size))
                        applied_texture_size = int(texture_size)
                    except Exception as e:
                        notes.append(f"WARNING: SetTextureSize failed: {e}")

                export_status = RLPy.RFileIO.ExportFbxFile(avatar, output_path, setting)
                used_setting_object = True
            except Exception as e:
                notes.append(f"RExportFbxSetting overload failed ({e}); falling back to 2-arg export")

        if not used_setting_object:
            if flags or flags2 or flags3:
                notes.append(
                    "WARNING: option flags (target-tool preset / axis / etc.) were NOT "
                    "applied — used the flag-less 2-arg ExportFbxFile fallback."
                )
            if export_motion is False:
                notes.append("WARNING: export_motion=False NOT applied (RExportFbxSetting unavailable)")
            if fps is not None or motion_range is not None or texture_size is not None or embed_textures or convert_image_format:
                notes.append("WARNING: motion/texture options NOT applied (RExportFbxSetting unavailable)")
            # 2-arg fallback can only honor subdivision via the scene-mutating
            # set_subdivision_level (snapshot for rollback on failure).
            if sub_d_level is not None:
                try:
                    if hasattr(avatar, "GetSubdivMeshLevel"):
                        _orig_subd = int(avatar.GetSubdivMeshLevel())
                except Exception:
                    _orig_subd = None
                try:
                    sub_result = set_subdivision_level(int(sub_d_level))
                    if sub_result.get("success", False):
                        applied_export_level = int(sub_d_level)
                        notes.append(f"sub_d_level={sub_d_level} applied via set_subdivision_level (2-arg fallback)")
                    else:
                        notes.append(f"set_subdivision_level failed: {sub_result.get('error')}")
                except Exception as e:
                    notes.append(f"set_subdivision_level exception: {e}")
            if use_smooth_mesh:
                notes.append("use_smooth_mesh: CC5 UI exclusive — emulated via sub_d_level/flags (RExportFbxSetting unavailable or failed)")
                # Best effort: ensure subdivision is on
                if sub_d_level is None:
                    # Snapshot for rollback (only None here means we didn't snapshot earlier).
                    try:
                        if _orig_subd is None and hasattr(avatar, "GetSubdivMeshLevel"):
                            _orig_subd = int(avatar.GetSubdivMeshLevel())
                    except Exception:
                        _orig_subd = None
                    try:
                        set_subdivision_level(1)
                        notes.append("auto sub_d_level=1 to approximate smooth mesh")
                    except Exception:
                        pass
            # 2-arg fallback — avoids passing bare int as 3rd arg
            export_status = RLPy.RFileIO.ExportFbxFile(avatar, output_path)

        # Never trust the return value alone: confirm the file really exists.
        failure = _verify_fbx_written(output_path, export_status, notes, export_started)
        if failure is not None:
            return failure

        # Honest reporting: echo flags/options only when actually applied.
        result: dict[str, Any] = {
            "success": True,
            "path": output_path,
            "flags_applied": used_setting_object,
            "flags": flags if used_setting_object else 0,
            "flags2": flags2 if applied_flags2 else 0,
            "flags3": flags3 if applied_flags3 else 0,
            "notes": notes,
            "target_tool": target_tool or "default",
        }
        if applied_export_level is not None:
            result["export_level"] = applied_export_level
        if applied_export_motion is not None:
            result["export_motion"] = applied_export_motion
        if applied_fps is not None:
            result["fps"] = applied_fps
        if applied_motion_range is not None:
            result["motion_range"] = applied_motion_range
        if applied_texture_size is not None:
            result["texture_size"] = applied_texture_size
        if embed_textures and used_setting_object:
            result["embed_textures"] = True
        if convert_image_format and used_setting_object:
            result["convert_image_format"] = True
        return result
    except Exception as e:
        # Roll back the subdivision change if we made one and the export failed.
        if _orig_subd is not None:
            try:
                set_subdivision_level(_orig_subd)
                notes.append(f"restored sub_d_level to {_orig_subd} after export failure")
            except Exception:
                pass
        return {"success": False, "error": str(e), "notes": notes}


def get_avatar_info() -> dict[str, Any] | None:
    """Get detailed information about the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return None

    shaping_comp = avatar.GetAvatarShapingComponent()
    current_morphs: dict[str, float] = {}

    if shaping_comp:
        categories = shaping_comp.GetShapingMorphCatergoryNames()
        for cat in categories:
            ids = shaping_comp.GetShapingMorphIDs(cat)
            for morph_id in ids:
                weight = shaping_comp.GetShapingMorphWeight(morph_id)
                if abs(weight) > 1e-6:
                    current_morphs[morph_id] = weight

    return {
        "name": avatar.GetName(),
        "id": avatar.GetID(),
        "active_morphs": current_morphs,
    }


def _capture_window_screenshot(output_path: str) -> None:
    """Fallback: capture CC5 window only via PowerShell + GetWindowRect."""
    import subprocess
    # The output path reaches PowerShell only through an environment variable.
    # Never put it on the command line: with -Command, PowerShell joins every
    # argument after it into one script, so a path such as "a;<command>;b.png"
    # would run <command> (a bound "-OutputPath" parameter does not work there).
    ps_script = """
$OutputPath = $env:CC5_CAPTURE_OUTPUT_PATH
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
'@
$proc = Get-Process -Name "CharacterCreator*" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc -or $proc.MainWindowHandle -eq [IntPtr]::Zero) {
    Add-Type -AssemblyName System.Windows.Forms
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
    $bitmap.Save($OutputPath)
    $graphics.Dispose()
    $bitmap.Dispose()
    exit
}
$rect = New-Object Win32+RECT
[Win32]::GetWindowRect($proc.MainWindowHandle, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
if ($w -le 0 -or $h -le 0) { exit 1 }
$bitmap = New-Object System.Drawing.Bitmap($w, $h)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bitmap.Save($OutputPath)
$graphics.Dispose()
$bitmap.Dispose()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True, timeout=10,
        env={**os.environ, "CC5_CAPTURE_OUTPUT_PATH": output_path},
    )
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"PowerShell screenshot failed (rc={result.returncode}): {stderr_text[:200]}"
        )


def _set_render_resolution(width: int, height: int) -> None:
    """Set RenderImage output size. The default RenderImage output is uselessly
    small (~100x32), making captures unusable for visual verification. Setting
    RExportImageParameter.kCommon.nOutputSizeWidth/Height fixes it (verified live).
    """
    try:
        g = RLPy.RGlobal
        if hasattr(g, "GetRenderExportImageParameter") and hasattr(g, "SetRenderExportParameter"):
            p = g.GetRenderExportImageParameter()
            if hasattr(p, "kCommon"):
                p.kCommon.nOutputSizeWidth = max(16, int(width))
                p.kCommon.nOutputSizeHeight = max(16, int(height))
                g.SetRenderExportParameter(p)
    except Exception as e:
        print(f"[CC5 MCP Bridge] _set_render_resolution failed: {e}")


def capture_viewport(output_path: str = "", width: int = 1280, height: int = 720) -> dict[str, Any]:
    """Capture the CC5 viewport as a PNG image at width x height (default 1280x720).

    NOTE: RenderImage's native default is ~100x32 px (unusable), so we set the
    render-export resolution first via _set_render_resolution (re-instated after
    UR-09, which wrongly assumed the size field was dead — it is wired via
    GetRenderExportImageParameter/SetRenderExportParameter, not the old kCommon arg).
    """
    try:
        if not output_path:
            output_path = os.path.join(tempfile.gettempdir(), "cc5_viewport.png")

        # Path validation via shared helper (UR-03): decodes %2e%2e and enforces .png
        _path_error = _validate_path(output_path, {".png"})
        if _path_error:
            return {"success": False, "error": _path_error}

        dir_path = os.path.dirname(output_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        if os.path.exists(output_path):
            os.remove(output_path)

        # Render at a usable resolution (RenderImage default is ~100x32).
        _set_render_resolution(width, height)

        # Try RenderImage first (skip if known broken after .ccProject load, UR-13)
        global _render_image_broken
        if not _render_image_broken:
            try:
                RLPy.RGlobal.RenderImage(output_path)
            except Exception as e:
                print(f"[CC5 MCP Bridge] RenderImage attempt 1 failed: {e}")

        # If RenderImage didn't create a file, try ForceViewportUpdate + retry
        if not _render_image_broken and not os.path.exists(output_path):
            if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                RLPy.RGlobal.ForceViewportUpdate()
            try:
                RLPy.RGlobal.RenderImage(output_path)
            except Exception as e:
                print(f"[CC5 MCP Bridge] RenderImage attempt 2 failed: {e}")
            if not os.path.exists(output_path):
                # Second failure: mark as broken so future calls skip these attempts
                _render_image_broken = True

        # Fallback: Windows screenshot of CC5 viewport
        if not os.path.exists(output_path):
            try:
                _capture_window_screenshot(output_path)
            except Exception as e:
                print(f"[CC5 MCP Bridge] _capture_window_screenshot failed: {e}")

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > MAX_IMAGE_BYTES:
                return {
                    "success": True,
                    "path": output_path,
                    "warning": f"Image too large to embed ({file_size} bytes). Read from path directly.",
                }
            with open(output_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            return {"success": True, "path": output_path, "base64": image_data}

        return {"success": False, "error": f"RenderImage did not create file at {output_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_subdivision_level(level: int) -> dict[str, Any]:
    """Set HD subdivision level (0-2) for the current avatar.

    Uses the RIAvatar subdivision-mesh API (CC4/CC5):
      - GetMaxSubdivMeshLevel() -> highest level the mesh supports
      - GetSubdivMeshLevel()    -> current level
      - SwitchSubdivMeshLevel(n)-> switch to level n
    Falls back to legacy method names on older builds.
    """
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    level = max(0, min(2, level))

    # --- Preferred: RIAvatar.SwitchSubdivMeshLevel (CC5/CC4) ---
    # UR-24: SwitchSubdivMeshLevel / GetSubdivMeshLevel / GetMaxSubdivMeshLevel are the
    # empirically-confirmed CC5.1 (5.10.x) methods (verified live against a running CC5
    # instance). SetHDSubdivisionLevel below is a legacy fallback NOT in the public
    # RLPy reference and is kept only for older builds.
    if hasattr(avatar, "SwitchSubdivMeshLevel"):
        try:
            max_level = None
            if hasattr(avatar, "GetMaxSubdivMeshLevel"):
                try:
                    max_level = int(avatar.GetMaxSubdivMeshLevel())
                except Exception:
                    max_level = None
            if max_level is not None and level > max_level:
                return {
                    "success": False,
                    "error": (
                        f"Requested level {level} exceeds the mesh's max subdivision "
                        f"level {max_level}. This character/mesh does not support that "
                        f"level of HD subdivision."
                    ),
                    "max_level": max_level,
                }
            avatar.SwitchSubdivMeshLevel(level)
            try:
                RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
            current = None
            if hasattr(avatar, "GetSubdivMeshLevel"):
                try:
                    current = int(avatar.GetSubdivMeshLevel())
                except Exception:
                    current = None
            return {
                "success": True,
                "level": level,
                "current_level": current,
                "max_level": max_level,
            }
        except Exception as e:
            return {"success": False, "error": f"SwitchSubdivMeshLevel failed: {e}"}

    # --- Legacy fallbacks (older builds) ---
    try:
        if hasattr(avatar, "SetSubdivisionLevel"):
            avatar.SetSubdivisionLevel(level)
        elif hasattr(RLPy, "RScene") and hasattr(RLPy.RScene, "SetHDSubdivisionLevel"):
            RLPy.RScene.SetHDSubdivisionLevel(level)
        else:
            return {"success": False, "error": "Subdivision API not available in this CC5 version"}
        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        return {"success": True, "level": level}
    except AttributeError:
        return {"success": False, "error": "Subdivision API not available in this CC5 version"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Undo / Redo ---

def _active_morph_count() -> int:
    """Count non-zero morph sliders on the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return 0
    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return 0
    count = 0
    categories = shaping_comp.GetShapingMorphCatergoryNames()
    for cat in categories:
        ids = shaping_comp.GetShapingMorphIDs(cat)
        for morph_id in ids:
            weight = shaping_comp.GetShapingMorphWeight(morph_id)
            if abs(weight) > 1e-6:
                count += 1
    return count


def undo() -> dict[str, Any]:
    """Undo the last action in CC5."""
    try:
        RLPy.RGlobal.Undo()
        avatar = get_first_avatar()
        if avatar:
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
            RLPy.RGlobal.ForceViewportUpdate()
        return {"success": True, "active_morph_count": _active_morph_count()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def redo() -> dict[str, Any]:
    """Redo the last undone action in CC5."""
    try:
        RLPy.RGlobal.Redo()
        avatar = get_first_avatar()
        if avatar:
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
            RLPy.RGlobal.ForceViewportUpdate()
        return {"success": True, "active_morph_count": _active_morph_count()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Camera Control ---

def get_camera_info() -> dict[str, Any]:
    """Get current camera position and focal length."""
    camera = RLPy.RScene.GetCurrentCamera()
    if not camera:
        return {"success": False, "error": "No camera"}
    transform = camera.WorldTransform()
    pos = transform.T()
    rot = transform.R()
    focal = camera.GetFocalLength(RLPy.RGlobal.GetTime())
    return {
        "name": camera.GetName(),
        "position": {"x": pos.x, "y": pos.y, "z": pos.z},
        "focal_length": focal,
    }


def set_camera_focal_length(focal_length: float) -> dict[str, Any]:
    """Set the focal length of the current camera.
    Note: CC5's 'Preview Camera' does not support focal length changes via API.
    This works only on user-created cameras.
    """
    camera = RLPy.RScene.GetCurrentCamera()
    if not camera:
        return {"success": False, "error": "No camera"}
    time = RLPy.RGlobal.GetTime()
    before = camera.GetFocalLength(time)
    try:
        RLPy.RGlobal.BeginAction("Set Camera Focal Length")
        camera.SetFocalLength(time, focal_length)
        RLPy.RGlobal.ObjectModified(camera, RLPy.EObjectModifiedType_Attribute)
        if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
            RLPy.RGlobal.ForceViewportUpdate()
    finally:
        RLPy.RGlobal.EndAction()
    actual = camera.GetFocalLength(time)
    if abs(actual - before) < 0.01 and abs(focal_length - before) > 0.01:
        return {
            "success": False,
            "error": f"Camera '{camera.GetName()}' does not support focal length changes (Preview Camera limitation). Create a new camera in CC5 to use this feature.",
            "focal_length": actual,
        }
    return {"success": True, "focal_length": actual}


_CAMERA_VIEWS = {
    "face": "ECameraLocationType_Face",
    "front": "ECameraLocationType_Front",
    "back": "ECameraLocationType_Back",
    "left": "ECameraLocationType_Left",
    "right": "ECameraLocationType_Right",
    "top": "ECameraLocationType_Top",
    "bottom": "ECameraLocationType_Bottom",
    "home": "ECameraLocationType_Home",
    "all": "ECameraLocationType_All",
    "focus": "ECameraLocationType_Focus",
}


def frame_camera(view: str = "face") -> dict[str, Any]:
    """Move the current camera to a preset view (face/front/home/all/back/left/right/top/
    bottom/focus). Enables face-level visual verification (eye/lip/skin color, facial
    morphs) that a full-body shot is too small to show. Found needed via tutorial runs.
    """
    cam = RLPy.RScene.GetCurrentCamera()
    if not cam:
        return {"success": False, "error": "No camera in scene"}
    key = (view or "").strip().lower()
    enum_name = _CAMERA_VIEWS.get(key)
    if not enum_name:
        return {"success": False, "error": f"Unknown view '{view}'. Valid: {', '.join(sorted(_CAMERA_VIEWS))}"}
    loc = getattr(RLPy, enum_name, None)
    if loc is None:
        return {"success": False, "error": f"Camera view '{view}' not available in this CC5 version"}
    try:
        cam.SetCameraLocation(loc)
        if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
            RLPy.RGlobal.ForceViewportUpdate()
        return {"success": True, "view": key, "camera": cam.GetName()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Light Control ---

def get_lights() -> list[dict[str, Any]]:
    """List all lights in the scene (deduplicated by ID)."""
    seen_ids: set[int] = set()
    result: list[dict[str, Any]] = []
    type_names = {
        RLPy.EObjectType_SpotLight: "SpotLight",
        RLPy.EObjectType_PointLight: "PointLight",
        RLPy.EObjectType_DirectionalLight: "DirectionalLight",
    }
    for light_type, type_name in type_names.items():
        objects = RLPy.RScene.FindObjects(light_type)
        for obj in objects:
            obj_id = obj.GetID()
            if obj_id not in seen_ids:
                seen_ids.add(obj_id)
                result.append({
                    "name": obj.GetName(),
                    "id": obj_id,
                    "type": type_name,
                })
    return result


def set_light_color(light_name: str, r: float, g: float, b: float) -> dict[str, Any]:
    """Set light color by name."""
    # UR-21: use shared _find_light helper to avoid duplicating the type-scan loop
    light, _ = _find_light(light_name)
    if not light:
        return {"success": False, "error": f"Light not found: {light_name}"}
    try:
        RLPy.RGlobal.BeginAction("Set Light Color")
        color = RLPy.RRgb(r, g, b)
        light.SetColor(RLPy.RGlobal.GetTime(), color)
        RLPy.RGlobal.ObjectModified(light, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "light": light_name}


def _find_light(light_name: str):
    """Find a light object by name across all light types. Returns (light, type_name) or (None, None)."""
    for light_type, type_name in [
        (RLPy.EObjectType_SpotLight, "SpotLight"),
        (RLPy.EObjectType_PointLight, "PointLight"),
        (RLPy.EObjectType_DirectionalLight, "DirectionalLight"),
    ]:
        light = RLPy.RScene.FindObject(light_type, light_name)
        if light:
            return light, type_name
    return None, None


def get_light_info(light_name: str) -> dict[str, Any]:
    """Get color and multiplier for a named light."""
    light, type_name = _find_light(light_name)
    if not light:
        return {"success": False, "error": f"Light not found: {light_name}"}

    time = RLPy.RGlobal.GetTime()
    result: dict[str, Any] = {"name": light_name, "type": type_name}
    try:
        color = light.GetColor()
        result["color"] = {"r": color.Red() / 255.0, "g": color.Green() / 255.0, "b": color.Blue() / 255.0}
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_light_info GetColor failed: {e}")
        result["color"] = None
    try:
        result["multiplier"] = light.GetMultiplier()
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_light_info GetMultiplier failed: {e}")
        result["multiplier"] = None
    # Lighting-guide additions: on/off + shadow shaping state (all best-effort)
    try:
        result["active"] = bool(light.GetActive())
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_light_info GetActive failed: {e}")
        result["active"] = None
    try:
        result["cast_shadow"] = bool(light.IsCastShadow())
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_light_info IsCastShadow failed: {e}")
        result["cast_shadow"] = None
    try:
        result["darken_shadow_strength"] = float(light.GetDarkenShadowStrength())
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_light_info GetDarkenShadowStrength failed: {e}")
        result["darken_shadow_strength"] = None
    try:
        result["range"] = float(light.GetRange())
    except Exception:
        # Directional lights have no range — not an error worth logging loudly
        result["range"] = None
    return result


def set_light_multiplier(light_name: str, multiplier: float) -> dict[str, Any]:
    """Set the intensity multiplier of a light by name."""
    if multiplier < 0:
        return {"success": False, "error": "Multiplier must be >= 0"}
    light, _ = _find_light(light_name)
    if not light:
        return {"success": False, "error": f"Light not found: {light_name}"}

    try:
        RLPy.RGlobal.BeginAction("Set Light Multiplier")
        light.SetMultiplier(RLPy.RGlobal.GetTime(), multiplier)
        RLPy.RGlobal.ObjectModified(light, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "light": light_name, "multiplier": multiplier}


def set_light_active(light_name: str, active: bool) -> dict[str, Any]:
    """Turn a light on or off by name (lighting-guide: toggle lights to shape a scene).

    Uses the keyable SetActive(time, bool); reads back GetActive() to confirm.
    """
    light, _ = _find_light(light_name)
    if not light:
        return {"success": False, "error": f"Light not found: {light_name}"}
    active = bool(active)
    try:
        RLPy.RGlobal.BeginAction("Set Light Active")
        light.SetActive(RLPy.RGlobal.GetTime(), active)
        RLPy.RGlobal.ObjectModified(light, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    try:
        confirmed = bool(light.GetActive())
    except Exception:
        confirmed = active
    return {"success": True, "light": light_name, "active": confirmed}


def set_light_shadow(
    light_name: str,
    cast_shadow: bool | None = None,
    darken_strength: float | None = None,
) -> dict[str, Any]:
    """Control a light's shadow casting and darkness (lighting-guide: soften/tune shadows).

    - cast_shadow: enable/disable shadow casting — SetCastShadow(bool), 1-arg.
    - darken_strength: 0.0-1.0 shadow darkness — SetDarkenShadowStrength(time, float), keyable.

    At least one of the two must be provided. Both are applied if given.
    """
    if cast_shadow is None and darken_strength is None:
        return {"success": False, "error": "Provide cast_shadow and/or darken_strength"}
    if darken_strength is not None and not (0.0 <= darken_strength <= 1.0):
        return {"success": False, "error": "darken_strength must be 0.0-1.0"}
    light, _ = _find_light(light_name)
    if not light:
        return {"success": False, "error": f"Light not found: {light_name}"}

    applied: dict[str, Any] = {}
    try:
        RLPy.RGlobal.BeginAction("Set Light Shadow")
        if cast_shadow is not None:
            light.SetCastShadow(bool(cast_shadow))
            applied["cast_shadow"] = bool(cast_shadow)
        if darken_strength is not None:
            light.SetDarkenShadowStrength(RLPy.RGlobal.GetTime(), float(darken_strength))
            applied["darken_shadow_strength"] = float(darken_strength)
        RLPy.RGlobal.ObjectModified(light, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "light": light_name, **applied}


# --- Environment / Visual Settings (ambient + IBL/HDRI) ---

_IBL_EXTENSIONS = {".hdr", ".exr", ".png", ".jpg", ".jpeg", ".hdri"}


def get_visual_settings() -> dict[str, Any]:
    """Get global environment lighting: ambient color (0-1) and IBL/HDRI state."""
    if not hasattr(RLPy.RGlobal, "GetVisualSettingComponent"):
        return {"success": False, "error": "Visual settings not available in this CC5 version"}
    vs = RLPy.RGlobal.GetVisualSettingComponent()
    if not vs:
        return {"success": False, "error": "No visual setting component"}
    result: dict[str, Any] = {"success": True}
    try:
        amb = vs.GetAmbientColor()
        result["ambient"] = {"r": amb.Red() / 255.0, "g": amb.Green() / 255.0, "b": amb.Blue() / 255.0}
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_visual_settings ambient failed: {e}")
        result["ambient"] = None
    try:
        result["ibl_enabled"] = bool(vs.IsIBLEnable())
    except Exception:
        result["ibl_enabled"] = None
    return result


def set_ambient(r: float, g: float, b: float) -> dict[str, Any]:
    """Set the scene ambient (fill) light color. RGB are floats 0.0-1.0."""
    if not hasattr(RLPy.RGlobal, "GetVisualSettingComponent"):
        return {"success": False, "error": "Visual settings not available in this CC5 version"}
    vs = RLPy.RGlobal.GetVisualSettingComponent()
    if not vs:
        return {"success": False, "error": "No visual setting component"}
    r = max(0.0, min(1.0, float(r)))
    g = max(0.0, min(1.0, float(g)))
    b = max(0.0, min(1.0, float(b)))
    try:
        RLPy.RGlobal.BeginAction("Set Ambient Color")
        vs.SetAmbientColor(RLPy.RRgb(r, g, b))
    finally:
        RLPy.RGlobal.EndAction()
    try:
        amb = vs.GetAmbientColor()
        applied = {"r": amb.Red() / 255.0, "g": amb.Green() / 255.0, "b": amb.Blue() / 255.0}
    except Exception:
        applied = {"r": r, "g": g, "b": b}
    return {"success": True, "ambient": applied}


def set_ibl(image_path: str = "", enable: bool = True) -> dict[str, Any]:
    """Enable/disable image-based lighting (IBL/HDRI), optionally loading an HDRI.

    image_path: path to an .hdr/.exr/.png/.jpg environment image. If omitted, only
    the enable flag is toggled (keeping any currently-loaded image).
    """
    if not hasattr(RLPy.RGlobal, "GetVisualSettingComponent"):
        return {"success": False, "error": "Visual settings not available in this CC5 version"}
    vs = RLPy.RGlobal.GetVisualSettingComponent()
    if not vs:
        return {"success": False, "error": "No visual setting component"}

    loaded = None
    if image_path:
        path_error = _validate_path(image_path, _IBL_EXTENSIONS)
        if path_error:
            return {"success": False, "error": path_error}
        if not os.path.isfile(image_path):
            return {"success": False, "error": f"IBL image not found: {image_path}"}
        try:
            RLPy.RGlobal.BeginAction("Load IBL")
            vs.LoadIBLImage(image_path)
            loaded = image_path
        except Exception as e:
            RLPy.RGlobal.EndAction()
            return {"success": False, "error": f"Failed to load IBL image: {e}"}
        else:
            RLPy.RGlobal.EndAction()

    try:
        vs.SetIBLEnable(bool(enable))
    except Exception as e:
        return {"success": False, "error": f"Failed to set IBL enable: {e}"}
    try:
        enabled = bool(vs.IsIBLEnable())
    except Exception:
        enabled = bool(enable)
    return {"success": True, "ibl_enabled": enabled, "loaded_image": loaded}


# --- Expression Control ---

def _facial_profile_type_map() -> dict[int, str]:
    """Map EFacialProfile enum ints -> readable labels (built dynamically so it
    never breaks if Reallusion renumbers the enum)."""
    mapping: dict[int, str] = {}
    for attr, label in (
        ("EFacialProfile__None", "None"),
        ("EFacialProfile_CC5MetaHuman", "CC5MetaHuman"),
        ("EFacialProfile_CC4Extended", "CC4Extended"),
        ("EFacialProfile_CC4Standard", "CC4Standard"),
        ("EFacialProfile_Traditional", "Traditional"),
    ):
        val = getattr(RLPy, attr, None)
        if val is None:
            continue
        try:
            mapping[int(val)] = label
        except (TypeError, ValueError):
            pass
    return mapping


def _classify_facial_profile(uid: str, total_sliders: int) -> str:
    """Heuristic ExPlus/HD/MetaHuman/Traditional label from the expression-set UID
    and slider count. Reference thresholds (Reallusion courses): CC4 Standard=60,
    CC4 Extended=140, ExPlus=63 (ARKit52 + tongue), CC5 Extended~160, CC5 HD/
    MetaHuman~390 (262 expression + 128 corrective)."""
    u = (uid or "").lower()
    if "metahuman" in u:
        return "CC5 MetaHuman (HD)"
    if "explus" in u or "ex plus" in u or "ex+" in u:
        return "ExPlus (ARKit52)"
    if "extended" in u:
        return "Extended"
    if "traditional" in u:
        return "Traditional"
    if "standard" in u:
        return "Standard"
    # Fall back to slider-count buckets when the UID string is unrecognised.
    if total_sliders >= 300:
        return "CC5 HD / MetaHuman (~390)"
    if total_sliders >= 150:
        return "CC5 Extended (~160)"
    if total_sliders >= 120:
        return "CC4 Extended (~140)"
    if total_sliders >= 60:
        return "ExPlus / CC4 Standard (~60-63)"
    return "unknown"


def get_facial_profile() -> dict[str, Any]:
    """Detect the current avatar's facial (expression) profile. Read-only.

    Returns the authoritative RLPy profile type (GetProfileType) + expression-set
    UID (GetExpressionSetUid), a per-category slider-count breakdown, and a
    heuristic ExPlus/HD/MetaHuman/Traditional class. Does NOT modify the scene.
    """
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar"}

    try:
        fp = avatar.GetFacialProfileComponent()
    except Exception as e:
        return {"success": False, "error": f"No facial profile component: {e}"}
    if not fp:
        return {"success": False, "error": "No facial profile component"}

    result: dict[str, Any] = {"success": True, "avatar": avatar.GetName()}

    # Authoritative profile type (enum int -> label).
    try:
        pt_int = int(fp.GetProfileType())
        result["profile_type_id"] = pt_int
        result["profile_type"] = _facial_profile_type_map().get(pt_int, f"Unknown({pt_int})")
    except Exception as e:
        result["profile_type_error"] = str(e)

    # Expression-set UID string (e.g. "CC5 MetaHuman", "Traditional", "ExPlus").
    uid = ""
    face_comp = avatar.GetFaceComponent()
    if face_comp:
        try:
            uid = str(face_comp.GetExpressionSetUid())
        except Exception as e:
            result["expression_set_uid_error"] = str(e)
    result["expression_set_uid"] = uid

    # Per-category slider counts.
    category_counts: dict[str, int] = {}
    total = 0
    try:
        for cat in fp.GetExpressionCategoryNames():
            try:
                sliders = fp.GetExpressionSliderNames(cat)
                n = len(sliders) if sliders else 0
            except Exception:
                n = 0
            category_counts[cat] = n
            total += n
    except Exception as e:
        result["category_error"] = str(e)
    result["category_slider_counts"] = category_counts
    result["total_sliders"] = total
    result["category_count"] = len(category_counts)

    result["heuristic_class"] = _classify_facial_profile(uid, total)
    result["arkit_capable"] = (
        any(k in (uid or "").lower() for k in ("metahuman", "explus", "arkit"))
        or total >= 150
    )
    return result


def _facial_profile_summary(info: Any) -> dict[str, Any]:
    """Small before/after summary extracted from a get_facial_profile() result."""
    if not isinstance(info, dict):
        return {}
    return {
        "profile_type": info.get("profile_type"),
        "expression_set_uid": info.get("expression_set_uid"),
        "total_sliders": info.get("total_sliders"),
    }


def convert_facial_profile(
    target_profile_path: str = "",
    dry_run: bool = True,
    backup_current_to: str = "",
) -> dict[str, Any]:
    """Swap the current avatar's facial profile by LOADING a target profile asset.

    RLPy scope (verified 2026-07-12): Reallusion's RLPy exposes NO direct
    profile-type conversion, and NO equivalent of the F8 "Edit Expression ->
    Corrective enable" one-click ExPlus upgrade. The only programmatic way to
    change the active facial profile is RIFacialProfileComponent.LoadProfile(path)
    with a pre-built .ccFacialProfile asset (same-topology constraint). This tool
    wraps that operation.

    Intended workflow — temporary switch for export, then restore:
      1) get_facial_profile            (record current type)
      2) convert_facial_profile(target, dry_run=false, backup_current_to=<save>)
      3) export_fbx(...)
      4) convert_facial_profile(<backup>, dry_run=false)   (restore original)

    Safety: dry_run defaults to True. In dry-run NOTHING changes — the tool only
    inspects the current profile and validates the target path.
    """
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar"}
    try:
        fp = avatar.GetFacialProfileComponent()
    except Exception as e:
        return {"success": False, "error": f"No facial profile component: {e}"}
    if not fp:
        return {"success": False, "error": "No facial profile component"}

    current_summary = _facial_profile_summary(get_facial_profile())
    notes = [
        "RLPy has no direct profile-type / ExPlus-upgrade API; this LOADS a target "
        ".ccFacialProfile via RIFacialProfileComponent.LoadProfile (same-topology).",
        "Recommended: pass backup_current_to to save the current profile, switch "
        "only for export, then convert back to the backup to restore the original.",
    ]

    path_error = None
    if target_profile_path:
        if not os.path.isabs(target_profile_path):
            path_error = "target_profile_path must be an absolute path"
        elif not os.path.exists(target_profile_path):
            path_error = f"target_profile_path not found: {target_profile_path}"

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "applied": False,
            "current_profile": current_summary,
            "target_profile_path": target_profile_path,
            "target_path_valid": bool(target_profile_path) and path_error is None,
            "path_error": path_error,
            "backup_current_to": backup_current_to,
            "notes": notes,
        }

    # --- Real apply path (scene-modifying) ---
    if not target_profile_path:
        return {"success": False, "error": "target_profile_path is required when dry_run=false"}
    if path_error:
        return {"success": False, "error": path_error}
    if not hasattr(fp, "LoadProfile"):
        return {"success": False, "error": "RIFacialProfileComponent.LoadProfile unavailable in this RLPy build"}
    if backup_current_to and not os.path.isabs(backup_current_to):
        return {"success": False, "error": "backup_current_to must be an absolute path"}

    saved_backup = None
    try:
        RLPy.RGlobal.BeginAction("Convert Facial Profile")
        try:
            if backup_current_to:
                backup_dir = os.path.dirname(backup_current_to)
                if backup_dir:
                    os.makedirs(backup_dir, exist_ok=True)
                fp.SaveProfile(backup_current_to)
                saved_backup = backup_current_to
            fp.LoadProfile(target_profile_path)
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Transform)
        finally:
            RLPy.RGlobal.EndAction()
    except Exception as e:
        return {"success": False, "error": f"LoadProfile failed: {e}", "backup_saved_to": saved_backup}

    _invalidate_caches()
    return {
        "success": True,
        "dry_run": False,
        "applied": True,
        "before": current_summary,
        "after": _facial_profile_summary(get_facial_profile()),
        "backup_saved_to": saved_backup,
        "target_profile_path": target_profile_path,
        "notes": notes,
    }


def get_expression_info() -> dict[str, Any]:
    """Get available expression groups and names for the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar"}
    face_comp = avatar.GetFaceComponent()
    if not face_comp:
        return {"success": False, "error": "No face component"}

    result: dict[str, list[str]] = {}
    try:
        groups = face_comp.GetExpressionGroups()
        for group in groups:
            names = face_comp.GetExpressionNames(group)
            result[group] = list(names) if names else []
    except Exception as e:
        return {"success": False, "error": f"Failed to get expressions: {e}"}

    # Return the bare group->names map (like get_lights/get_avatars). The TS tool
    # (expression.ts) does Object.keys(info); a {success, expressions} wrapper broke it
    # (EXPR-ENVELOPE). Failure paths above still return {success:False} -> HTTP 400.
    return result


def _collect_expression_names(face_comp) -> set[str]:
    """Build the set of all valid expression slider names for the avatar's face."""
    valid: set[str] = set()
    for group in face_comp.GetExpressionGroups():
        names = face_comp.GetExpressionNames(group)
        for n in (names or []):
            valid.add(n)
    return valid


def set_expression(expressions: list[dict[str, Any]]) -> dict[str, Any]:
    """Set one or more facial expression sliders by name (weights 0.0-1.0).

    expressions: [{"name": "Brow_Raise_Inner_L", "weight": 0.8}, ...]
    Names are validated against the avatar's expression set (use get_expression_info
    to discover them). Unknown names are skipped and reported, not silently dropped.
    Expressions are keyed via AddExpressionKeys(time, names, weights, interval=0).
    """
    if not isinstance(expressions, list) or not expressions:
        return {"success": False, "error": "expressions must be a non-empty list of {name, weight}"}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar"}
    face_comp = avatar.GetFaceComponent()
    if not face_comp:
        return {"success": False, "error": "No face component"}

    try:
        valid = _collect_expression_names(face_comp)
    except Exception as e:
        return {"success": False, "error": f"Failed to read expression names: {e}"}

    names: list[str] = []
    weights: list[float] = []
    skipped: list[str] = []
    for entry in expressions:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if name not in valid:
            skipped.append(name)
            continue
        try:
            weight = max(0.0, min(1.0, float(entry.get("weight", 0.0))))
        except (TypeError, ValueError):
            skipped.append(name)
            continue
        names.append(name)
        weights.append(weight)

    if not names:
        return {"success": False, "error": "No valid expression names", "skipped": skipped}

    time = RLPy.RGlobal.GetTime()
    try:
        RLPy.RGlobal.BeginAction("Set Expression")
        face_comp.BeginKeyEditing()
        try:
            face_comp.AddExpressionKeys(time, names, weights, RLPy.RTime_FromValue(0))
        finally:
            face_comp.EndKeyEditing()
        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Transform)
    finally:
        RLPy.RGlobal.EndAction()

    try:
        applied_weights = list(face_comp.GetExpressionWeights(time, names))
    except Exception:
        applied_weights = weights
    applied = [{"name": n, "weight": w} for n, w in zip(names, applied_weights)]
    return {"success": True, "applied": applied, "skipped": skipped}


def reset_expression() -> dict[str, Any]:
    """Reset all facial expression sliders to 0 (neutral face)."""
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar"}
    face_comp = avatar.GetFaceComponent()
    if not face_comp:
        return {"success": False, "error": "No face component"}

    try:
        names = list(_collect_expression_names(face_comp))
    except Exception as e:
        return {"success": False, "error": f"Failed to read expression names: {e}"}
    if not names:
        return {"success": True, "reset_count": 0}

    weights = [0.0] * len(names)
    time = RLPy.RGlobal.GetTime()
    try:
        RLPy.RGlobal.BeginAction("Reset Expression")
        face_comp.BeginKeyEditing()
        try:
            face_comp.AddExpressionKeys(time, names, weights, RLPy.RTime_FromValue(0))
        finally:
            face_comp.EndKeyEditing()
        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Transform)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "reset_count": len(names)}


# --- Material / Texture Control ---

def get_material_info(avatar_name: str = "") -> dict[str, Any]:
    """Get mesh names and material names for the current avatar."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        error = f"Avatar not found: {avatar_name}" if avatar_name else "No avatar in scene"
        return {"success": False, "error": error}

    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return {"success": False, "error": "No material component"}

    result: dict[str, list[str]] = {}
    try:
        # GetMeshNames is on RIObject (the avatar), not RIMaterialComponent
        meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
        for mesh in meshes:
            try:
                materials = mat_comp.GetMaterialNames(mesh)
                result[mesh] = list(materials) if materials else []
            except AttributeError:
                result[mesh] = []
            except Exception as e:
                print(f"[CC5 MCP Bridge] GetMaterialNames failed for '{mesh}': {e}")
                result[mesh] = []
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "meshes": result}


MAX_MATERIAL_NAME_LENGTH = 256


def _validate_material_names(mesh_name: str, material_name: str) -> str | None:
    """Validate mesh and material name lengths. Returns error message or None."""
    if len(mesh_name) > MAX_MATERIAL_NAME_LENGTH:
        return f"Mesh name too long ({len(mesh_name)} chars, max {MAX_MATERIAL_NAME_LENGTH})"
    if len(material_name) > MAX_MATERIAL_NAME_LENGTH:
        return f"Material name too long ({len(material_name)} chars, max {MAX_MATERIAL_NAME_LENGTH})"
    return None


def _get_valid_mesh_material(avatar, mesh_name: str, material_name: str) -> tuple[Any, str | None]:
    """Validate mesh/material names exist on the avatar. Returns (mat_comp, error)."""
    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return None, "No material component"

    # Verify mesh exists
    try:
        meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
        if meshes and mesh_name not in meshes:
            return None, f"Mesh not found: {mesh_name}. Available: {list(meshes)[:10]}"
    except AttributeError:
        pass  # API not available in this CC5 version
    except Exception as e:
        return None, f"Failed to enumerate meshes: {e}"

    # Verify material exists on this mesh
    try:
        materials = mat_comp.GetMaterialNames(mesh_name)
        if materials and material_name not in materials:
            return None, f"Material not found: {material_name}. Available on '{mesh_name}': {list(materials)[:10]}"
    except AttributeError:
        pass  # API not available
    except Exception as e:
        return None, f"Failed to enumerate materials: {e}"

    return mat_comp, None


def get_diffuse_color(mesh_name: str, material_name: str) -> dict[str, Any]:
    """Get the diffuse color of a material."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        color = mat_comp.GetDiffuseColor(mesh_name, material_name)
        return {"success": True, "r": color.Red() / 255.0, "g": color.Green() / 255.0, "b": color.Blue() / 255.0}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_diffuse_color(mesh_name: str, material_name: str, r: float, g: float, b: float) -> dict[str, Any]:
    """Set the diffuse color of a material (for skin tone, clothing color, etc.)."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        time = RLPy.RGlobal.GetTime()
        key = RLPy.RKey()
        key.SetTime(time)
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))
        color = RLPy.RRgb(r, g, b)
        try:
            RLPy.RGlobal.BeginAction("Set Diffuse Color")
            mat_comp.AddDiffuseKey(key, mesh_name, material_name, color)
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Material Properties (Opacity, Glossiness, Specular) ---


def get_material_properties(mesh_name: str, material_name: str) -> dict[str, Any]:
    """Get opacity, glossiness, and specular for a material."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        result: dict[str, Any] = {"success": True, "mesh": mesh_name, "material": material_name}
        if hasattr(mat_comp, "GetOpacity"):
            result["opacity"] = mat_comp.GetOpacity(mesh_name, material_name)
        if hasattr(mat_comp, "GetGlossinessWeight"):
            result["glossiness"] = mat_comp.GetGlossinessWeight(mesh_name, material_name)
        if hasattr(mat_comp, "GetSpecularWeight"):
            result["specular"] = mat_comp.GetSpecularWeight(mesh_name, material_name)
        elif hasattr(mat_comp, "GetSpecular"):
            result["specular"] = mat_comp.GetSpecular(mesh_name, material_name)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_material_opacity(mesh_name: str, material_name: str, opacity: float) -> dict[str, Any]:
    """Set the opacity of a material (0.0 = transparent, 1.0 = opaque)."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    opacity = max(0.0, min(1.0, opacity))
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        time = RLPy.RGlobal.GetTime()
        key = RLPy.RKey()
        key.SetTime(time)
        try:
            RLPy.RGlobal.BeginAction("Set Material Opacity")
            mat_comp.AddOpacityKey(key, mesh_name, material_name, opacity)
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "opacity": opacity}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_material_glossiness(mesh_name: str, material_name: str, glossiness: float) -> dict[str, Any]:
    """Set the glossiness of a material (0.0 = matte, 1.0 = glossy)."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    glossiness = max(0.0, min(1.0, glossiness))
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        time = RLPy.RGlobal.GetTime()
        key = RLPy.RKey()
        key.SetTime(time)
        try:
            RLPy.RGlobal.BeginAction("Set Material Glossiness")
            mat_comp.AddGlossinessKey(key, mesh_name, material_name, glossiness)
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "glossiness": glossiness}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_material_specular(mesh_name: str, material_name: str, specular: float) -> dict[str, Any]:
    """Set the specular weight of a material (0.0 = no specular, 1.0 = full specular)."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    specular = max(0.0, min(1.0, specular))
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    try:
        time = RLPy.RGlobal.GetTime()
        key = RLPy.RKey()
        key.SetTime(time)
        try:
            RLPy.RGlobal.BeginAction("Set Material Specular")
            mat_comp.AddSpecularKey(key, mesh_name, material_name, specular)
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "specular": specular}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- PBR Shader Parameters (Digital Human Shader: roughness, SSS, micronormal) ---

def get_shader_parameters(mesh_name: str, material_name: str) -> dict[str, Any]:
    """Get the shader name and all numeric shader parameters for a material.

    Exposes the Digital Human Shader controls (skin roughness scales, SSS radius/
    falloff/IOR, micronormal strength, specular, etc.). Each value is a list of
    floats (most are length 1). Use set_shader_parameter to change one.
    """
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    if not hasattr(mat_comp, "GetShaderParameterNames"):
        return {"success": False, "error": "Shader parameter API not available in this CC5 build"}

    try:
        shader = mat_comp.GetShader(mesh_name, material_name) if hasattr(mat_comp, "GetShader") else None
        names = mat_comp.GetShaderParameterNames(mesh_name, material_name)
        params: dict[str, list[float]] = {}
        for name in (names or []):
            try:
                value = mat_comp.GetShaderParameter(mesh_name, material_name, name)
                params[name] = [float(v) for v in value]
            except Exception:
                # skip non-numeric / unreadable params rather than failing the whole call
                continue
        return {
            "success": True,
            "mesh": mesh_name,
            "material": material_name,
            "shader": shader,
            "parameters": params,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_shader_parameter(
    mesh_name: str, material_name: str, parameter_name: str, values: list[float]
) -> dict[str, Any]:
    """Set a single Digital Human Shader parameter (e.g. 'Micro Roughness Scale',
    'SSS Radius', '_Specular') to a list of float values.

    The parameter name is validated against the material's actual shader parameters
    (use get_shader_parameters to discover them), and the value count must match the
    parameter's existing length — both guard against passing bad data to the SWIG layer.
    """
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    if not parameter_name or not isinstance(parameter_name, str):
        return {"success": False, "error": "parameter_name is required"}
    if not isinstance(values, list) or not values:
        return {"success": False, "error": "values must be a non-empty list of numbers"}
    try:
        values = [float(v) for v in values]
    except (TypeError, ValueError):
        return {"success": False, "error": "values must all be numbers"}

    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    if not hasattr(mat_comp, "SetShaderParameter"):
        return {"success": False, "error": "Shader parameter API not available in this CC5 build"}

    try:
        valid_names = list(mat_comp.GetShaderParameterNames(mesh_name, material_name) or [])
    except Exception as e:
        return {"success": False, "error": f"Failed to read shader parameters: {e}"}
    if parameter_name not in valid_names:
        return {"success": False, "error": f"Unknown shader parameter: {parameter_name}"}

    # Length must match the existing parameter (passing the wrong arity can crash SWIG)
    try:
        current = list(mat_comp.GetShaderParameter(mesh_name, material_name, parameter_name))
    except Exception as e:
        return {"success": False, "error": f"Failed to read current value: {e}"}
    if len(values) != len(current):
        return {
            "success": False,
            "error": f"'{parameter_name}' expects {len(current)} value(s), got {len(values)}",
        }

    try:
        RLPy.RGlobal.BeginAction("Set Shader Parameter")
        mat_comp.SetShaderParameter(mesh_name, material_name, parameter_name, values)
        RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
    finally:
        RLPy.RGlobal.EndAction()

    try:
        applied = [float(v) for v in mat_comp.GetShaderParameter(mesh_name, material_name, parameter_name)]
    except Exception:
        applied = values
    return {
        "success": True,
        "mesh": mesh_name,
        "material": material_name,
        "parameter": parameter_name,
        "values": applied,
    }


# --- Content Management (Clothes, Hair, Accessories) ---

def list_clothes() -> list[dict[str, Any]]:
    """List all clothing items on the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return []
    try:
        clothes = avatar.GetClothes()
        return [
            {
                "name": c.GetName(),
                "id": c.GetID(),
                "type": str(c.GetClotheType()) if hasattr(c, "GetClotheType") else "unknown",
            }
            for c in clothes
        ]
    except Exception as e:
        print(f"[CC5 MCP Bridge] list_clothes failed: {e}")
        return []


def list_hair() -> list[dict[str, Any]]:
    """List all hair items on the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return []
    try:
        hairs = avatar.GetHairs()
        return [
            {
                "name": h.GetName(),
                "id": h.GetID(),
                "type": str(h.GetHairType()) if hasattr(h, "GetHairType") else "unknown",
            }
            for h in hairs
        ]
    except Exception as e:
        print(f"[CC5 MCP Bridge] list_hair failed: {e}")
        return []


def list_accessories() -> list[dict[str, Any]]:
    """List all accessories on the current avatar."""
    avatar = get_first_avatar()
    if not avatar:
        return []
    try:
        accessories = avatar.GetAccessories(True)
        return [
            {"name": a.GetName(), "id": a.GetID()}
            for a in accessories
        ]
    except Exception as e:
        print(f"[CC5 MCP Bridge] list_accessories failed: {e}")
        return []


MAX_ITEM_NAME_LENGTH = 256


def remove_scene_item(item_name: str) -> dict[str, Any]:
    """Remove a clothing, hair, or accessory item by name."""
    if not item_name or len(item_name) > MAX_ITEM_NAME_LENGTH:
        return {"success": False, "error": "Invalid item name"}
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    getters = [
        avatar.GetClothes,
        avatar.GetHairs,
        lambda: avatar.GetAccessories(True),
    ]
    for getter in getters:
        try:
            items = getter()
            for item in items:
                if item.GetName() == item_name:
                    RLPy.RGlobal.BeginAction("Remove Item")
                    try:
                        RLPy.RScene.RemoveObject(item)
                        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
                        if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                            RLPy.RGlobal.ForceViewportUpdate()
                    finally:
                        RLPy.RGlobal.EndAction()
                    return {"success": True, "removed": item_name}
        except Exception as e:
            print(f"[CC5 MCP Bridge] remove_scene_item getter failed: {e}")
    return {"success": False, "error": f"Item not found: {item_name}"}


def browse_content(folder_type: str = "cloth_upper") -> list[str]:
    """Browse available content files by category. Returns file paths.

    CC5.1 API: RContentManager is gone. We resolve a '$/...' folder string via
    RApplication.GetDefaultContentFolder(enum) (falling back to
    GetCustomContentFolder) and then list files with
    RApplication.GetContentFilesInFolder(folderString). The enum is NEVER passed
    to GetContentFilesInFolder (that raises a SWIG std::wstring TypeError).
    """
    # Map advertised folder-type keys to valid CC5.1 EContentRootFolder enum names.
    # Only enums that actually exist in this build are kept (hasattr-guarded below).
    enum_candidates = {
        "cloth_upper": "EContentRootFolder_Upper",
        "cloth_lower": "EContentRootFolder_Lower",
        "shoes": "EContentRootFolder_Shoes",
        # No _AccessoryHead / _AccessoryBody enum exists — both map to the only
        # accessory folder enum CC5.1 exposes.
        "accessory_head": "EContentRootFolder_AccessoryOthers",
        "accessory_body": "EContentRootFolder_AccessoryOthers",
        # 'cloth' is an alias for the full-body clothing folder.
        "cloth": "EContentRootFolder_FullBody",
        # Animation / scene content — all loadable via load_asset (.cc*/.i*).
        # pose/motion may be empty on a base install (no pose packs) but resolve
        # correctly and will list files once content is installed.
        "pose": "EContentRootFolder_Pose",
        "motion": "EContentRootFolder_Motion",
        "expression": "EContentRootFolder_Expression",
        "props": "EContentRootFolder_Props",
        "light": "EContentRootFolder_Light",
        "camera": "EContentRootFolder_Camera",
        "character": "EContentRootFolder_Character",
    }
    folder_map: dict[str, Any] = {}
    for key, attr_name in enum_candidates.items():
        if hasattr(RLPy, attr_name):
            folder_map[key] = getattr(RLPy, attr_name)

    if folder_type not in folder_map:
        available = list(folder_map.keys()) if folder_map else list(enum_candidates.keys())
        return [f"Unknown folder type: {folder_type}. Available: {', '.join(available)}"]

    if not hasattr(RLPy, "RApplication") or not hasattr(RLPy.RApplication, "GetContentFilesInFolder"):
        return [f"Content browsing not available for '{folder_type}' in this CC5 version"]

    try:
        root_folder = folder_map[folder_type]

        # Collect candidate '$/...' folder STRINGS: bundled templates + user custom.
        # (Never pass the enum to GetContentFilesInFolder — it expects the string.)
        folder_strs: list[str] = []
        for getter in ("GetDefaultContentFolder", "GetCustomContentFolder"):
            if hasattr(RLPy.RApplication, getter):
                try:
                    fs = getattr(RLPy.RApplication, getter)(root_folder)
                    if fs:
                        folder_strs.append(fs)
                except Exception:
                    pass

        if not folder_strs:
            return [f"No content folder resolved for '{folder_type}'"]

        # CC5.1 content files use .cc* extensions (e.g. .ccShoes, .ccCloth, .ccUpper);
        # legacy CC3/iClone content uses .i* (e.g. .iAvatar, .iShoe). Accept both.
        # (_ALLOWED_LOAD_EXTENSIONS is for load_asset and excludes .cc* content files.)
        results: list[str] = []
        seen: set[str] = set()
        for fs in folder_strs:
            try:
                files = RLPy.RApplication.GetContentFilesInFolder(fs)
            except Exception:
                files = None
            for f in (files or []):
                ext = os.path.splitext(f)[1].lower()
                if (ext.startswith(".cc") or ext.startswith(".i")) and f not in seen:
                    seen.add(f)
                    results.append(f)
                    if len(results) >= 200:
                        return results
        return results
    except Exception as e:
        return [f"Error browsing content: {e}"]


# --- Convenience Color Shortcuts ---

# Known mesh/material names for CC5 standard avatars
_EYE_TARGETS = [
    ("CC_Base_Eye", "Std_Eye_R"),
    ("CC_Base_Eye", "Std_Eye_L"),
    ("CC_Base_Eye", "Eye_R"),
    ("CC_Base_Eye", "Eye_L"),
]

_HAIR_MESH_PREFIXES = ["CC_Base_Hair", "Hair", "hair"]

# Lip color must target a DEDICATED lip/mouth material only. The CC3+ base shares the
# whole face with Std_Skin_Head, so falling back to it paints the ENTIRE head the lip
# color (found via tutorial run). set_lip_color now relies solely on a name-based
# 'lip'/'mouth' material search and fails cleanly when none exists.
_LIP_TARGETS: list[tuple[str, str]] = []


def _find_materials_by_prefix(avatar, mesh_prefixes: list[str]) -> list[tuple[str, str, Any]]:
    """Find all mesh/material pairs where mesh name starts with one of the prefixes."""
    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return []
    results: list[tuple[str, str, Any]] = []
    try:
        meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
        for mesh in meshes:
            for prefix in mesh_prefixes:
                if mesh.startswith(prefix) or mesh.lower().startswith(prefix.lower()):
                    try:
                        materials = mat_comp.GetMaterialNames(mesh)
                        for mat_name in (materials or []):
                            results.append((mesh, mat_name, mat_comp))
                    except Exception as e:
                        print(f"[CC5 MCP Bridge] _find_materials_by_prefix GetMaterialNames failed: {e}")
                    break
    except Exception as e:
        print(f"[CC5 MCP Bridge] _find_materials_by_prefix GetMeshNames failed: {e}")
    return results


def _apply_diffuse_color_to_targets(
    mat_comp: Any,
    targets: list[tuple[str, str]],
    key: Any,
    color: Any,
) -> list[str]:
    """Apply diffuse color to a list of (mesh, material) pairs. Returns applied labels."""
    applied: list[str] = []
    for mesh_name, material_name in targets:
        try:
            mat_comp.AddDiffuseKey(key, mesh_name, material_name, color)
            applied.append(f"{mesh_name}/{material_name}")
        except Exception as e:
            print(f"[CC5 MCP Bridge] AddDiffuseKey failed for {mesh_name}/{material_name}: {e}")
    return applied

def set_eye_color(r: float, g: float, b: float) -> dict[str, Any]:
    """Set eye color (convenience shortcut). RGB 0.0-1.0."""
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return {"success": False, "error": "No material component"}
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    color = RLPy.RRgb(r, g, b)
    time = RLPy.RGlobal.GetTime()
    key = RLPy.RKey()
    key.SetTime(time)
    applied: list[str] = []
    try:
        RLPy.RGlobal.BeginAction("Set Eye Color")
        applied = _apply_diffuse_color_to_targets(mat_comp, _EYE_TARGETS, key, color)
        if applied:
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
    finally:
        RLPy.RGlobal.EndAction()
    if applied:
        return {"success": True, "applied_to": applied}
    return {"success": False, "error": "Could not find eye materials. Use get_material_info to discover mesh/material names."}


def set_skin_color(r: float, g: float, b: float) -> dict[str, Any]:
    """Set skin tone across ALL skin materials (Std_Skin_Head/Body/Arm/Leg, etc.)
    of the avatar's body (convenience shortcut). RGB 0.0-1.0.

    Found via tutorial run: setting one skin material leaves arms/legs the wrong
    color because CC body skin is split across several materials.
    """
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return {"success": False, "error": "No material component"}
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    color = RLPy.RRgb(r, g, b)
    key = RLPy.RKey()
    key.SetTime(RLPy.RGlobal.GetTime())
    # Discover skin materials dynamically: name contains 'skin' but not 'eyelash'.
    targets: list[tuple[str, str]] = []
    try:
        meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
        for mesh in meshes:
            try:
                for mat_name in (mat_comp.GetMaterialNames(mesh) or []):
                    low = mat_name.lower()
                    if "skin" in low and "eyelash" not in low:
                        targets.append((mesh, mat_name))
            except Exception as e:
                print(f"[CC5 MCP Bridge] set_skin_color GetMaterialNames failed for {mesh}: {e}")
    except Exception as e:
        print(f"[CC5 MCP Bridge] set_skin_color GetMeshNames failed: {e}")
    applied: list[str] = []
    try:
        RLPy.RGlobal.BeginAction("Set Skin Color")
        applied = _apply_diffuse_color_to_targets(mat_comp, targets, key, color)
        if applied:
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
    finally:
        RLPy.RGlobal.EndAction()
    if applied:
        return {"success": True, "applied_to": applied}
    return {"success": False, "error": "Could not find skin materials. Use get_material_info to discover mesh/material names."}


def set_hair_color(r: float, g: float, b: float) -> dict[str, Any]:
    """Set hair color on all hair materials (convenience shortcut). RGB 0.0-1.0."""
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    color = RLPy.RRgb(r, g, b)
    time = RLPy.RGlobal.GetTime()
    key = RLPy.RKey()
    key.SetTime(time)

    targets = _find_materials_by_prefix(avatar, _HAIR_MESH_PREFIXES)
    # Also check hair items directly
    try:
        hairs = avatar.GetHairs()
        for hair_item in hairs:
            hair_mat_comp = hair_item.GetMaterialComponent() if hasattr(hair_item, "GetMaterialComponent") else None
            if hair_mat_comp:
                try:
                    hair_meshes = hair_item.GetMeshNames(True) if hasattr(hair_item, "GetMeshNames") else []
                    for hm in hair_meshes:
                        try:
                            mats = hair_mat_comp.GetMaterialNames(hm)
                            for mat_name in (mats or []):
                                targets.append((hm, mat_name, hair_mat_comp))
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pass

    applied: list[str] = []
    try:
        RLPy.RGlobal.BeginAction("Set Hair Color")
        for mesh_name, material_name, mat_comp in targets:
            try:
                mat_comp.AddDiffuseKey(key, mesh_name, material_name, color)
                applied.append(f"{mesh_name}/{material_name}")
            except Exception as e:
                print(f"[CC5 MCP Bridge] AddDiffuseKey failed for {mesh_name}/{material_name}: {e}")
        if applied:
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
    finally:
        RLPy.RGlobal.EndAction()

    if applied:
        return {"success": True, "applied_to": applied}
    return {"success": False, "error": "Could not find hair materials. Use get_material_info to discover mesh/material names."}


def set_lip_color(r: float, g: float, b: float) -> dict[str, Any]:
    """Set lip color (convenience shortcut). RGB 0.0-1.0.
    Note: This sets the diffuse color of the head/skin material which affects the entire face.
    For lip-only color, use set_diffuse_color with specific lip material if available."""
    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return {"success": False, "error": "No material component"}

    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))
    color = RLPy.RRgb(r, g, b)
    time = RLPy.RGlobal.GetTime()
    key = RLPy.RKey()
    key.SetTime(time)

    applied: list[str] = []
    try:
        RLPy.RGlobal.BeginAction("Set Lip Color")
        # Try known lip/mouth material targets (UR-21: shared helper)
        applied = _apply_diffuse_color_to_targets(mat_comp, _LIP_TARGETS, key, color)
        # Also search for Lip-specific materials
        try:
            meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
            for mesh in meshes:
                try:
                    materials = mat_comp.GetMaterialNames(mesh)
                    for mat_name in (materials or []):
                        if "lip" in mat_name.lower() or "mouth" in mat_name.lower():
                            try:
                                mat_comp.AddDiffuseKey(key, mesh, mat_name, color)
                                label = f"{mesh}/{mat_name}"
                                if label not in applied:
                                    applied.append(label)
                            except Exception as e:
                                print(f"[CC5 MCP Bridge] AddDiffuseKey failed for {mesh}/{mat_name}: {e}")
                except Exception:
                    pass
        except Exception:
            pass
        if applied:
            RLPy.RGlobal.ObjectModified(avatar, _EOMTYPE_MATERIAL)
    finally:
        RLPy.RGlobal.EndAction()

    if applied:
        return {"success": True, "applied_to": applied}
    return {
        "success": False,
        "error": "No dedicated lip/mouth material on this character — lips share the head "
                 "skin (Std_Skin_Head), so lip color cannot be set independently without "
                 "tinting the whole face. Use a character with a separate lip material, or "
                 "apply makeup in CC5.",
    }


# --- Visibility & Scene ---

def set_item_visible(item_name: str, visible: bool) -> dict[str, Any]:
    """Set visibility of a scene item (clothing, hair, accessory, prop) by name."""
    if not item_name or len(item_name) > MAX_ITEM_NAME_LENGTH:
        return {"success": False, "error": "Invalid item name"}

    # Search across all object types
    avatar = get_first_avatar()
    if avatar:
        getters = [
            avatar.GetClothes,
            avatar.GetHairs,
            lambda: avatar.GetAccessories(True),
        ]
        for getter in getters:
            try:
                items = getter()
                for item in items:
                    if item.GetName() == item_name:
                        RLPy.RGlobal.BeginAction("Set Item Visible")
                        try:
                            # RICloth/RIHair have NO SetVisible; RScene.Show/Hide is generic.
                            (RLPy.RScene.Show if visible else RLPy.RScene.Hide)(item)
                            RLPy.RGlobal.ObjectModified(item, RLPy.EObjectModifiedType_Attribute)
                        finally:
                            RLPy.RGlobal.EndAction()
                        return {"success": True, "item": item_name, "visible": visible}
            except Exception as e:
                print(f"[CC5 MCP Bridge] set_item_visible getter failed: {e}")

    # UR-27 assessment: RLPy.RScene.FindObject(type, name) is name-based.
    # The FindObjects(type)+linear-scan fallback below is technically redundant
    # but kept for compatibility with older CC5 builds where FindObject may
    # not be available for all object types. Mark: partial.
    # Search props and other scene objects using both FindObject and FindObjects
    search_types = [
        RLPy.EObjectType_Prop,
        RLPy.EObjectType_SpotLight,
        RLPy.EObjectType_PointLight,
        RLPy.EObjectType_DirectionalLight,
        RLPy.EObjectType_Camera,
    ]
    for obj_type in search_types:
        # Try FindObject (single, by name) first
        try:
            obj = RLPy.RScene.FindObject(obj_type, item_name)
            if obj:
                RLPy.RGlobal.BeginAction("Set Item Visible")
                try:
                    (RLPy.RScene.Show if visible else RLPy.RScene.Hide)(obj)
                    RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
                finally:
                    RLPy.RGlobal.EndAction()
                return {"success": True, "item": item_name, "visible": visible}
        except Exception as e:
            print(f"[CC5 MCP Bridge] set_item_visible FindObject failed: {e}")
        # Fallback: iterate FindObjects results
        try:
            objects = RLPy.RScene.FindObjects(obj_type)
            for obj in objects:
                if obj.GetName() == item_name:
                    RLPy.RGlobal.BeginAction("Set Item Visible")
                    try:
                        (RLPy.RScene.Show if visible else RLPy.RScene.Hide)(obj)
                        RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
                    finally:
                        RLPy.RGlobal.EndAction()
                    return {"success": True, "item": item_name, "visible": visible}
        except Exception as e:
            print(f"[CC5 MCP Bridge] set_item_visible FindObjects scan failed: {e}")

    return {"success": False, "error": f"Item not found: {item_name}"}


def get_scene_objects() -> list[dict[str, Any]]:
    """List all objects in the scene: avatars, props, lights, cameras."""
    result: list[dict[str, Any]] = []

    # Avatars
    try:
        avatars = RLPy.RScene.GetAvatars()
        for a in avatars:
            result.append({"name": a.GetName(), "id": a.GetID(), "type": "Avatar"})
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_scene_objects avatars failed: {e}")

    # Props
    try:
        props = RLPy.RScene.FindObjects(RLPy.EObjectType_Prop)
        for p in props:
            result.append({"name": p.GetName(), "id": p.GetID(), "type": "Prop"})
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_scene_objects props failed: {e}")

    # Lights
    type_names = {
        RLPy.EObjectType_SpotLight: "SpotLight",
        RLPy.EObjectType_PointLight: "PointLight",
        RLPy.EObjectType_DirectionalLight: "DirectionalLight",
    }
    seen_ids: set[int] = set()
    for light_type, type_name in type_names.items():
        try:
            objects = RLPy.RScene.FindObjects(light_type)
            for obj in objects:
                obj_id = obj.GetID()
                if obj_id not in seen_ids:
                    seen_ids.add(obj_id)
                    result.append({"name": obj.GetName(), "id": obj_id, "type": type_name})
        except Exception as e:
            print(f"[CC5 MCP Bridge] get_scene_objects lights failed: {e}")

    # Cameras
    try:
        cameras = RLPy.RScene.FindObjects(RLPy.EObjectType_Camera)
        for cam in cameras:
            result.append({"name": cam.GetName(), "id": cam.GetID(), "type": "Camera"})
    except Exception as e:
        print(f"[CC5 MCP Bridge] get_scene_objects cameras failed: {e}")

    return result


# --- Reset Morphs ---

def reset_all_morphs(avatar_name: str = "") -> dict[str, Any]:
    """Reset all morph sliders to zero for an avatar."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        error = f"Avatar not found: {avatar_name}" if avatar_name else "No avatar in scene"
        return {"success": False, "error": error}
    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component"}
    categories = shaping_comp.GetShapingMorphCatergoryNames()
    count = 0
    try:
        RLPy.RGlobal.BeginAction("Reset All Morphs")
        for cat in categories:
            ids = shaping_comp.GetShapingMorphIDs(cat)
            for morph_id in ids:
                weight = shaping_comp.GetShapingMorphWeight(morph_id)
                if abs(weight) > 1e-6:
                    shaping_comp.SetShapingMorphWeight(morph_id, 0.0)
                    count += 1
        RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()
    return {"success": True, "reset_count": count}


# --- Opt-in gate for code execution and silent UI automation ---
#
# exec_python and the silent Export Head steps are refused unless CC5_ALLOW_EXEC
# is set (1 / true / yes). CC5_DEV_MODE and CC5_RELOAD_SECRET do NOT enable them:
# running code must always be an explicit opt-in. server.py checks the same thing
# per route; it is repeated here because cc5_api is hot-reloaded on its own, so
# the gate must hold even when an older server.py is the one that is loaded.

def _exec_allowed() -> bool:
    return os.environ.get("CC5_ALLOW_EXEC", "").strip().lower() in ("1", "true", "yes")


def _exec_gate(action: str) -> dict[str, Any] | None:
    """Return a refusal result when CC5_ALLOW_EXEC is off, else None."""
    if _exec_allowed():
        return None
    return {
        "success": False,
        "error": (
            f"'{action}' is disabled. It can run arbitrary code or drive CC5's UI "
            "without confirmation, so it is off by default. To enable it, set the "
            "environment variable CC5_ALLOW_EXEC=1 for Character Creator 5 (for "
            "example run 'setx CC5_ALLOW_EXEC 1', then restart CC5) and in the MCP "
            "server's env. See the Security section of the README."
        ),
    }


# --- Python Script Execution ---

def exec_python(code: str) -> dict[str, Any]:
    """Execute arbitrary Python code inside CC5's RLPy environment.
    The code has access to RLPy module and the running CC5 scene.
    Off unless CC5_ALLOW_EXEC is set (see _exec_gate).
    Returns: {"success": True, "output": "<captured stdout>", "result": "<last expression>"}
    """
    refused = _exec_gate("exec_python")
    if refused:
        return refused

    if not isinstance(code, str):
        return {"success": False, "error": "code must be a string"}
    if not code or not code.strip():
        return {"success": False, "error": "No code provided"}

    import io
    import contextlib

    # Provide useful globals for the script
    script_globals = {
        "RLPy": RLPy,
        "get_first_avatar": get_first_avatar,
        "get_avatar_by_name": get_avatar_by_name,
        "get_avatars": get_avatars,
        "get_avatar_info": get_avatar_info,
        "get_morph_catalog": get_morph_catalog,
        "search_morphs": search_morphs,
        "get_lights": get_lights,
        "get_material_info": get_material_info,
        "capture_viewport": capture_viewport,
    }

    stdout_capture = io.StringIO()
    result_value = None

    try:
        # Try as expression first (returns a value)
        try:
            compiled = compile(code, "<mcp_exec>", "eval")
            with contextlib.redirect_stdout(stdout_capture):
                result_value = eval(compiled, script_globals)
        except SyntaxError:
            # Not an expression — execute as statements
            compiled = compile(code, "<mcp_exec>", "exec")
            with contextlib.redirect_stdout(stdout_capture):
                exec(compiled, script_globals)
            result_value = script_globals.get("result", None)

        output = stdout_capture.getvalue()
        response: dict[str, Any] = {"success": True}
        if output:
            response["output"] = output[:10000]  # Cap output size
        if result_value is not None:
            response["result"] = str(result_value)[:10000]
        return response

    except Exception as e:
        # Return only the exception message — never the full traceback.
        return {
            "success": False,
            "error": str(e),
            "output": stdout_capture.getvalue()[:5000],
        }


# --- Skin Texture Baking (Mesh-to-MetaHuman prep) ---

def _resolution_to_enum(resolution: int) -> Any:
    """Map an integer resolution to RLPy EExportTextureSize_* enum (best effort)."""
    mapping = {
        256:  "EExportTextureSize_Size_256",
        512:  "EExportTextureSize_Size_512",
        1024: "EExportTextureSize_Size_1024",
        2048: "EExportTextureSize_Size_2048",
        4096: "EExportTextureSize_Size_4096",
    }
    name = mapping.get(int(resolution))
    if name is None:
        return None
    return getattr(RLPy, name, None)


def bake_skin_textures(resolution: int = 4096) -> dict[str, Any]:
    """Trigger CC5's Skin editor -> Bake Textures workflow.

    The Skin Editor / SkinGen "Bake" button is a UI-only operation in CC5.
    There is no direct stable RLPy entry point in this CC5 build, so this
    function does its best to drive the Qt UI:
      1. Find CC5 main window via QApplication
      2. Search QActions for "Bake" / "Skin Gen" related entries
      3. trigger() the action

    If automation fails, returns a structured response telling the caller
    to bake manually.
    """
    notes: list[str] = []
    res_enum = _resolution_to_enum(resolution)
    if res_enum is None:
        return {
            "success": False,
            "error": f"Unsupported resolution: {resolution}. Allowed: 256, 512, 1024, 2048, 4096",
        }
    notes.append(f"requested resolution={resolution} (enum={res_enum})")

    # --- Step 1: Try to set export texture size on default export settings ---
    try:
        if hasattr(RLPy, "RExportFbxSetting"):
            setting = RLPy.RExportFbxSetting()
            if hasattr(setting, "SetTextureSize"):
                setting.SetTextureSize(res_enum)
                notes.append("RExportFbxSetting.SetTextureSize succeeded (affects future FBX exports)")
    except Exception as e:
        notes.append(f"RExportFbxSetting.SetTextureSize failed: {e}")

    # --- Step 2: Drive the Qt UI to trigger Skin Editor Bake ---
    try:
        from PySide2 import QtWidgets  # type: ignore
        app = QtWidgets.QApplication.instance()
        if app is None:
            return {
                "success": False,
                "manual_step_required": True,
                "error": "QApplication.instance() returned None",
                "instructions": (
                    "Open CC5 -> Modify panel -> Skin Editor -> set Texture Size = "
                    f"{resolution} -> click Apply / Bake."
                ),
                "notes": notes,
            }

        candidates: list[QtWidgets.QAction] = []
        # Search all QActions in any widget
        for w in app.allWidgets():
            try:
                for action in w.actions():
                    text = (action.text() or "").strip()
                    obj = (action.objectName() or "").strip()
                    blob = f"{text} {obj}".lower()
                    # Reject destructive opposites
                    if any(neg in blob for neg in ["remove skingen", "remove skin gen", "delete skin"]):
                        continue
                    if any(k in blob for k in [
                        "bake skin", "bake texture", "bake textures",
                        "apply skin", "apply skingen", "apply skin gen",
                        "skin editor", "skin gen", "skingen",
                    ]):
                        candidates.append(action)
            except Exception:
                continue

        # Prefer "Bake" > "Apply" > "Skin Editor" > "Skin Gen"
        def _bake_score(a: QtWidgets.QAction) -> int:
            t = (a.text() or "").lower()
            o = (a.objectName() or "").lower()
            b = f"{t} {o}"
            if "bake" in b:
                return 0
            if "apply" in b:
                return 1
            if "skin editor" in b:
                return 2
            return 3

        if not candidates:
            return {
                "success": False,
                "manual_step_required": True,
                "error": "Could not locate Skin Editor / Bake QAction in CC5 UI",
                "instructions": (
                    "Open CC5 -> Modify panel -> Skin Editor -> set Texture Size = "
                    f"{resolution} -> click Apply / Bake."
                ),
                "notes": notes,
                "candidates_inspected": [
                    {"text": (a.text() or ""), "objectName": (a.objectName() or "")}
                    for a in candidates[:20]
                ],
            }

        candidates.sort(key=_bake_score)
        chosen = candidates[0]
        notes.append(
            "candidates considered: " + ", ".join(
                f"'{(a.text() or '').strip()}'" for a in candidates[:10]
            )
        )
        # Async trigger to avoid bridge deadlock if a modal opens
        try:
            from PySide2 import QtCore  # type: ignore
            QtCore.QTimer.singleShot(50, chosen.trigger)
            notes.append("Scheduled trigger() via QTimer.singleShot(50ms)")
        except Exception:
            chosen.trigger()
        notes.append(f"Triggered QAction: text='{chosen.text()}' objectName='{chosen.objectName()}'")

        return {
            "success": True,
            "resolution": resolution,
            "triggered_action": chosen.text(),
            "manual_step_required": True,
            "instructions": (
                "Skin Editor / Skin Gen panel was opened. CC5 does not expose a "
                f"one-shot Bake API — set Texture Size = {resolution} and click "
                "Apply / Bake in the Skin Editor panel."
            ),
            "notes": notes,
        }
    except ImportError as e:
        return {
            "success": False,
            "manual_step_required": True,
            "error": f"PySide2 not available: {e}",
            "instructions": (
                "Open CC5 -> Modify panel -> Skin Editor -> set Texture Size = "
                f"{resolution} -> click Apply / Bake."
            ),
            "notes": notes,
        }
    except Exception as e:
        return {
            "success": False,
            "manual_step_required": True,
            "error": str(e),
            "instructions": (
                "Open CC5 -> Modify panel -> Skin Editor -> set Texture Size = "
                f"{resolution} -> click Apply / Bake."
            ),
            "notes": notes,
        }


# --- Mesh-to-MetaHuman Head Export ---

_MH_ALLOWED_GENDERS = {"male", "female", "m", "f"}


def export_head_metahuman(
    output_dir: str,
    character_name: str,
    gender: str = "Female",
) -> dict[str, Any]:
    """Trigger CC5's File -> Export -> Export Head -> Mesh to MetaHuman pipeline.

    Strategy:
      1. Validate inputs and ensure output_dir exists
      2. Try a direct RLPy entry point (CC5MetaHuman facial profile related)
      3. Fall back to Qt menu navigation: File -> Export -> Export Head
    """
    if "\x00" in output_dir or "\x00" in character_name:
        return {"success": False, "error": "Null byte in path/name"}
    if ".." in output_dir:
        return {"success": False, "error": "Path traversal not allowed in output_dir"}
    if not character_name or not character_name.strip():
        return {"success": False, "error": "character_name must not be empty"}
    gender_norm = (gender or "").strip().lower()
    if gender_norm not in _MH_ALLOWED_GENDERS:
        return {
            "success": False,
            "error": f"gender must be one of {sorted(_MH_ALLOWED_GENDERS)}, got: {gender!r}",
        }
    gender_label = "Female" if gender_norm in ("female", "f") else "Male"

    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        return {"success": False, "error": f"Could not create output_dir: {e}"}

    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    notes: list[str] = []

    # --- Strategy 1: Direct RLPy facial profile (CC5MetaHuman) ---
    # NOTE: EFacialProfile_CC5MetaHuman exists in RLPy but a one-shot
    # "Export Head -> MH" function is not exposed. We record availability
    # so the caller knows.
    if hasattr(RLPy, "EFacialProfile_CC5MetaHuman"):
        notes.append("RLPy.EFacialProfile_CC5MetaHuman is available")
    else:
        notes.append("RLPy.EFacialProfile_CC5MetaHuman missing — CC5 too old?")

    # --- Strategy 2: Qt menu walk ---
    try:
        from PySide2 import QtWidgets  # type: ignore
        app = QtWidgets.QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication.instance() returned None")

        # Locate main window
        main_win = None
        for w in app.topLevelWidgets():
            try:
                if isinstance(w, QtWidgets.QMainWindow) and w.isVisible():
                    main_win = w
                    break
            except Exception:
                continue

        if main_win is None:
            raise RuntimeError("Could not find CC5 main QMainWindow")

        menubar = main_win.menuBar() if hasattr(main_win, "menuBar") else None
        if menubar is None:
            raise RuntimeError("Could not find QMenuBar on main window")

        # Reject any action that is clearly NOT "Export Head -> MH"
        _NEGATIVE = (
            "import", "animator", "csv", "remove", "delete",
            "load mha", "save mha", "open mha",
        )
        # Recursive search across all menus & submenus for "Export Head" or "Mesh to MetaHuman"
        def _walk_menu(menu: Any, depth: int = 0) -> list[Any]:
            found: list[Any] = []
            if depth > 6 or menu is None:
                return found
            try:
                for act in menu.actions():
                    text = (act.text() or "").replace("&", "").strip().lower()
                    obj = (act.objectName() or "").lower() if hasattr(act, "objectName") else ""
                    blob = f"{text} {obj}"
                    if any(neg in blob for neg in _NEGATIVE):
                        sub = act.menu()
                        if sub is not None:
                            found.extend(_walk_menu(sub, depth + 1))
                        continue
                    if any(k in text for k in [
                        "mesh to metahuman", "mesh-to-metahuman", "export head", "export mesh to"
                    ]):
                        found.append(act)
                    sub = act.menu()
                    if sub is not None:
                        found.extend(_walk_menu(sub, depth + 1))
            except Exception:
                pass
            return found

        matches = _walk_menu(menubar)
        notes.append(f"Found {len(matches)} candidate menu actions in menu bar")

        if not matches:
            # Last-ditch: search all QActions in the application
            for w in app.allWidgets():
                try:
                    for act in w.actions():
                        text = (act.text() or "").replace("&", "").strip().lower()
                        obj = (act.objectName() or "").lower() if hasattr(act, "objectName") else ""
                        blob = f"{text} {obj}"
                        if any(neg in blob for neg in _NEGATIVE):
                            continue
                        if "mesh to metahuman" in text or "export head" in text:
                            matches.append(act)
                except Exception:
                    continue
            notes.append(f"Fallback widget scan found {len(matches)} candidates")

        if not matches:
            return {
                "success": False,
                "manual_step_required": True,
                "error": "Could not locate 'Export Head' / 'Mesh to MetaHuman' menu",
                "instructions": (
                    f"File -> Export -> Export Head -> 'Mesh to MetaHuman {gender_label}' "
                    f"and save to {output_dir} as {character_name}"
                ),
                "notes": notes,
                "output_dir": output_dir,
                "character_name": character_name,
                "gender": gender_label,
            }

        # Prefer the most specific match
        def _score(act: Any) -> int:
            t = (act.text() or "").lower()
            s = 0
            if "mesh to metahuman" in t:
                s += 8
            if gender_label.lower() in t:
                s += 4
            if "export head" in t:
                s += 2
            if "metahuman" in t:
                s += 1
            return -s  # negative for ascending sort

        matches.sort(key=_score)
        chosen = matches[0]
        notes.append(
            f"Triggering action: text='{chosen.text()}' "
            f"objectName='{chosen.objectName() if hasattr(chosen, 'objectName') else ''}'"
        )
        # IMPORTANT: trigger() can block on a modal dialog. Schedule it
        # asynchronously via QTimer.singleShot so the bridge thread returns
        # the response immediately and the user can interact with the dialog.
        try:
            from PySide2 import QtCore  # type: ignore
            QtCore.QTimer.singleShot(50, chosen.trigger)
            notes.append("Scheduled trigger() via QTimer.singleShot(50ms) to avoid bridge deadlock")
        except Exception as e:
            notes.append(f"QTimer.singleShot unavailable ({e}); calling trigger() synchronously (may block)")
            chosen.trigger()

        return {
            "success": True,
            "manual_step_required": True,
            "triggered_action": chosen.text(),
            "instructions": (
                "Export Head dialog has been opened. In the dialog:\n"
                f"  1. Choose 'Mesh to MetaHuman {gender_label}'\n"
                f"  2. Set output folder to: {output_dir}\n"
                f"  3. Set file name to: {character_name}\n"
                "  4. Click OK / Export."
            ),
            "output_dir": output_dir,
            "character_name": character_name,
            "gender": gender_label,
            "notes": notes,
        }
    except ImportError as e:
        return {
            "success": False,
            "manual_step_required": True,
            "error": f"PySide2 not available: {e}",
            "instructions": (
                f"File -> Export -> Export Head -> 'Mesh to MetaHuman {gender_label}' "
                f"-> {output_dir}\\{character_name}"
            ),
            "output_dir": output_dir,
            "character_name": character_name,
            "gender": gender_label,
            "notes": notes,
        }
    except Exception as e:
        return {
            "success": False,
            "manual_step_required": True,
            "error": str(e),
            "instructions": (
                f"File -> Export -> Export Head -> 'Mesh to MetaHuman {gender_label}' "
                f"-> {output_dir}\\{character_name}"
            ),
            "output_dir": output_dir,
            "character_name": character_name,
            "gender": gender_label,
            "notes": notes,
        }


# --- Silent Export Head (no user interaction) ---
#
# CC5's Export Head normally opens TWO modal dialogs in sequence:
#   1. ExportHeadDialog (QDialog) — pipeline selection + texture size
#   2. Native Windows Save File dialog — output path
#
# To fully automate without any user click, we:
#   (a) Install a global QApplication event filter that catches any QFileDialog
#       Show event, sets the filename via selectFile(), forces non-native, then
#       calls accept() on it via QTimer.
#   (b) Trigger the File→Export→Export Head menu action via QTimer chain.
#   (c) When the ExportHeadDialog appears, set Pipeline / MaxTextureSize, then
#       click qtExportPushButton via another QTimer.
#   (d) The button's C++ slot opens the native file dialog → filter intercepts
#       and accepts it with our path → export proceeds with progress dialog.
#   (e) State is tracked in _SILENT_EXPORT_STATE for /export/head_mh/status.

_SILENT_EXPORT_STATE: dict[str, Any] = {
    "phase": "idle",        # idle | menu | configuring | exporting | done | error
    "output_dir": "",
    "character_name": "",
    "gender": "",
    "fbx_path": "",
    "error": "",
    "started_at": 0.0,
    "finished_at": 0.0,
    "notes": [],
}


def _silent_export_install_filter(output_dir: str, character_name: str) -> Any:
    """Install a QApplication event filter that auto-accepts QFileDialogs.

    The CC5 Save File flow shows the dialog TWICE:
      (1) initial Show event with native backend
      (2) WindowActivate after Qt rebuilds non-native (triggered by our setOption)
    Both fires must succeed: (1) flips to non-native, (2) accepts the path.
    We track per-dialog state by id() to avoid re-processing the same dialog
    after it has been accepted (or to skip unrelated dialogs after we're done).
    """
    from PySide2.QtCore import QObject, QEvent, QTimer
    from PySide2.QtWidgets import QApplication, QFileDialog

    target_file = output_dir.rstrip("/\\") + "/" + character_name

    class _FileDialogAutoAccept(QObject):
        def __init__(self):
            super().__init__()
            self.fired_count = 0
            self.accepted_ids: set[int] = set()
            self.done = False

        def eventFilter(self, obj, event):
            if self.done:
                return False
            try:
                if (
                    isinstance(obj, QFileDialog)
                    and event.type() in (QEvent.Show, QEvent.WindowActivate)
                ):
                    # Only intercept SAVE dialogs (not Open dialogs that
                    # might appear for asset browsing etc.)
                    try:
                        mode_ok = obj.acceptMode() == QFileDialog.AcceptSave
                    except Exception:
                        mode_ok = True
                    if not mode_ok:
                        return False
                    # Skip dialogs we've already accepted
                    if id(obj) in self.accepted_ids:
                        return False
                    obj.setDirectory(output_dir)
                    obj.selectFile(target_file)
                    obj.setOption(QFileDialog.DontUseNativeDialog, True)
                    QTimer.singleShot(150, obj.accept)
                    self.fired_count += 1
                    # If this was the non-native fire, mark as accepted (one-shot)
                    try:
                        is_native = not bool(obj.options() & QFileDialog.DontUseNativeDialog)
                    except Exception:
                        is_native = False
                    if not is_native:
                        self.accepted_ids.add(id(obj))
                        # After non-native accept, disarm the filter to avoid
                        # intercepting any later save dialog (e.g. logs, autosave)
                        self.done = True
            except Exception as e:
                _SILENT_EXPORT_STATE["phase"] = "error"
                _SILENT_EXPORT_STATE["error"] = f"eventFilter exception: {e}"
            return False

    flt = _FileDialogAutoAccept()
    QApplication.instance().installEventFilter(flt)
    # Keep alive on cc5_api module
    sys.modules["cc5_api"]._silent_export_filter = flt  # type: ignore[attr-defined]
    return flt


def _silent_export_remove_filter() -> None:
    from PySide2.QtWidgets import QApplication

    flt = getattr(sys.modules["cc5_api"], "_silent_export_filter", None)
    if flt is not None:
        try:
            QApplication.instance().removeEventFilter(flt)
        except Exception:
            pass
        try:
            del sys.modules["cc5_api"]._silent_export_filter  # type: ignore[attr-defined]
        except Exception:
            pass


def _silent_export_find_action() -> Any:
    """Find the best 'Export Head → Mesh to MetaHuman' QAction in the menu bar."""
    from PySide2.QtWidgets import QApplication, QMainWindow

    app = QApplication.instance()
    if app is None:
        return None

    main_win = None
    for w in app.topLevelWidgets():
        try:
            if isinstance(w, QMainWindow) and w.isVisible():
                main_win = w
                break
        except Exception:
            continue
    if main_win is None or not hasattr(main_win, "menuBar"):
        return None

    _NEGATIVE = ("import", "animator", "csv", "remove", "delete",
                 "load mha", "save mha", "open mha")

    def _walk(menu, depth=0):
        found = []
        if depth > 6 or menu is None:
            return found
        try:
            for act in menu.actions():
                text = (act.text() or "").replace("&", "").strip().lower()
                if any(neg in text for neg in _NEGATIVE):
                    sub = act.menu()
                    if sub:
                        found.extend(_walk(sub, depth + 1))
                    continue
                if any(k in text for k in [
                    "mesh to metahuman", "mesh-to-metahuman",
                    "export head", "export mesh to",
                ]):
                    found.append(act)
                sub = act.menu()
                if sub:
                    found.extend(_walk(sub, depth + 1))
        except Exception:
            pass
        return found

    matches = _walk(main_win.menuBar())
    if not matches:
        return None

    def _score(act):
        t = (act.text() or "").lower()
        s = 0
        if "mesh to metahuman" in t: s += 8
        if "export head" in t: s += 4
        if "metahuman" in t: s += 1
        return -s

    matches.sort(key=_score)
    return matches[0]


def _silent_export_find_dialog() -> Any:
    """Find the visible ExportHeadDialog QDialog instance."""
    from PySide2.QtWidgets import QApplication, QDialog
    for w in QApplication.allWidgets():
        try:
            if ("ExportHeadDialog" in w.objectName()
                    and isinstance(w, QDialog) and w.isVisible()):
                return w
        except Exception:
            continue
    return None


def silent_install_filter(output_dir: str, character_name: str) -> dict[str, Any]:
    """Step 1 of silent Export Head: spawn a background OS-level SendKeys handler.

    NOTE: Despite the legacy name, this function no longer uses a Qt event
    filter (which caused CC5 to crash on multiple test runs — the native
    Windows Save dialog backend cannot survive setOption(DontUseNativeDialog)
    being called from a Python event filter while C++ is mid-COM-call).

    Instead, this spawns a daemon thread that polls Win32 EnumWindows for the
    native save dialog matching CC5's process, then SendInput's the path +
    Enter. Pure OS-level — no Qt or C++ touch.
    """
    refused = _exec_gate("silent_install_filter")
    if refused:
        return refused
    import time, threading

    if "\x00" in output_dir or "\x00" in character_name:
        return {"success": False, "error": "Null byte in path/name"}
    if ".." in output_dir:
        return {"success": False, "error": "Path traversal not allowed"}
    if not character_name or not character_name.strip():
        return {"success": False, "error": "character_name required"}
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        return {"success": False, "error": f"Could not create output_dir: {e}"}

    # Cancel any prior handler
    prior = getattr(sys.modules["cc5_api"], "_silent_send_handler_stop", None)
    if prior is not None:
        try:
            prior.set()
        except Exception:
            pass

    stop_event = threading.Event()
    sys.modules["cc5_api"]._silent_send_handler_stop = stop_event  # type: ignore[attr-defined]

    # Full path to type into the save dialog's filename field.
    # CC5's save dialog accepts an ABSOLUTE path; backslashes work best.
    full_path = (output_dir.rstrip("/\\") + "\\" + character_name).replace("/", "\\")

    handler_log: list[str] = []
    sys.modules["cc5_api"]._silent_send_handler_log = handler_log  # type: ignore[attr-defined]

    def _handler():
        """Background OS-level handler — waits for save dialog, types path + Enter."""
        import ctypes, ctypes.wintypes as wt

        u32 = ctypes.windll.user32
        WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        u32.GetWindowTextW.restype = ctypes.c_int
        u32.GetClassNameW.restype = ctypes.c_int

        # Get CC5's PID for filtering
        cc_pid = 0
        try:
            import subprocess
            r = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq CharacterCreator.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            line = r.stdout.strip().splitlines()[0] if r.stdout else ""
            cc_pid = int(line.split(",")[1].strip('"')) if "," in line else 0
        except Exception as e:
            handler_log.append(f"PID lookup failed: {e}")

        VK_RETURN = 0x0D
        KEYEVENTF_KEYUP = 0x0002

        # SendInput structures
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wt.WORD),
                ("wScan", wt.WORD),
                ("dwFlags", wt.DWORD),
                ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wt.ULONG)),
            ]
        class _INPUTunion(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        class INPUT(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = [("type", wt.DWORD), ("u", _INPUTunion)]
        INPUT_KEYBOARD = 1
        KEYEVENTF_UNICODE = 0x0004

        def send_char(ch: str) -> None:
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE, 0, None)
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
            u32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
            u32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))

        def send_enter() -> None:
            inp_down = INPUT(type=INPUT_KEYBOARD)
            inp_down.ki = KEYBDINPUT(VK_RETURN, 0, 0, 0, None)
            inp_up = INPUT(type=INPUT_KEYBOARD)
            inp_up.ki = KEYBDINPUT(VK_RETURN, 0, KEYEVENTF_KEYUP, 0, None)
            u32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
            u32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))

        def send_ctrl_a() -> None:
            VK_CONTROL = 0x11
            VK_A = 0x41
            for vk, flags in [(VK_CONTROL, 0), (VK_A, 0), (VK_A, KEYEVENTF_KEYUP), (VK_CONTROL, KEYEVENTF_KEYUP)]:
                inp = INPUT(type=INPUT_KEYBOARD)
                inp.ki = KEYBDINPUT(vk, 0, flags, 0, None)
                u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

        target_hwnd: list[int] = []

        def cb(hwnd, _lp):
            if not u32.IsWindowVisible(hwnd):
                return True
            cls_buf = ctypes.create_unicode_buffer(256)
            u32.GetClassNameW(hwnd, cls_buf, 256)
            cls = cls_buf.value
            length = u32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            txt_buf = ctypes.create_unicode_buffer(length + 1)
            u32.GetWindowTextW(hwnd, txt_buf, length + 1)
            title = txt_buf.value
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            # The CC5 native save dialog has class "#32770" and title containing
            # "Save" or "Export". Confirm process matches CC5.
            if cls == "#32770" and (cc_pid == 0 or pid.value == cc_pid):
                low = title.lower()
                if "save" in low or "export" in low or "保存" in title:
                    target_hwnd.append(hwnd)
                    return False
            return True

        deadline = time.time() + 30.0
        while not stop_event.is_set() and time.time() < deadline:
            target_hwnd.clear()
            try:
                u32.EnumWindows(WNDENUMPROC(cb), 0)
            except Exception as e:
                handler_log.append(f"EnumWindows error: {e}")
            if target_hwnd:
                hwnd = target_hwnd[0]
                handler_log.append(f"Found dialog hwnd={hwnd}")
                # Bring to foreground + give it a moment to settle
                u32.SetForegroundWindow(hwnd)
                time.sleep(0.4)
                # Clear current filename field (Ctrl+A then type)
                send_ctrl_a()
                time.sleep(0.1)
                # Type the full path char-by-char
                for ch in full_path:
                    send_char(ch)
                    time.sleep(0.005)
                time.sleep(0.2)
                send_enter()
                handler_log.append(f"Typed '{full_path}' + Enter")
                break
            time.sleep(0.25)
        if not target_hwnd:
            handler_log.append("Save dialog never appeared within 30s")
            _SILENT_EXPORT_STATE["phase"] = "error"
            _SILENT_EXPORT_STATE["error"] = "Save dialog never appeared within 30s"

    thread = threading.Thread(target=_handler, daemon=True)
    thread.start()
    sys.modules["cc5_api"]._silent_send_handler_thread = thread  # type: ignore[attr-defined]

    _SILENT_EXPORT_STATE.update({
        "phase": "handler_armed",
        "output_dir": output_dir,
        "character_name": character_name,
        "gender": "",
        "fbx_path": output_dir.rstrip("/\\") + "/" + character_name + ".fbx",
        "error": "",
        "started_at": time.time(),
        "finished_at": 0.0,
        "notes": ["Win32 SendKeys handler armed (background thread)"],
    })
    return {
        "success": True,
        "phase": "handler_armed",
        "method": "Win32 SendKeys (background thread)",
        "output_dir": output_dir,
        "character_name": character_name,
        "expected_path": full_path,
    }


def silent_trigger_dialog() -> dict[str, Any]:
    """Step 2 of silent Export Head: trigger File → Export → Export Head menu.

    The dialog opens via QTimer.singleShot so this returns immediately.
    Wait ~1 second, then call silent_configure_and_click.
    """
    refused = _exec_gate("silent_trigger_dialog")
    if refused:
        return refused
    if _SILENT_EXPORT_STATE.get("phase") not in ("filter_installed", "handler_armed", "menu_triggered"):
        return {"success": False, "error": f"Wrong phase: {_SILENT_EXPORT_STATE.get('phase')}. Call silent_install_filter first."}
    chosen = _silent_export_find_action()
    if chosen is None:
        return {"success": False, "error": "Could not find Export Head menu action"}
    from PySide2.QtCore import QTimer
    QTimer.singleShot(50, chosen.trigger)
    _SILENT_EXPORT_STATE["phase"] = "menu_triggered"
    _SILENT_EXPORT_STATE["notes"].append(f"Menu scheduled: {chosen.text()}")
    return {"success": True, "phase": "menu_triggered", "action_text": chosen.text()}


def silent_configure_and_click(gender: str = "Female", max_texture_size: int = 4096) -> dict[str, Any]:
    """Step 3 of silent Export Head: find dialog, configure fields, click Export.

    The Export click opens the native save dialog which the previously installed
    filter will intercept and auto-accept. Returns once Export is clicked. The
    actual export+texture writing runs asynchronously inside CC5 (poll
    get_export_status to know when done).
    """
    refused = _exec_gate("silent_configure_and_click")
    if refused:
        return refused
    from PySide2.QtWidgets import QComboBox, QCheckBox, QPushButton, QApplication
    from PySide2.QtCore import QTimer

    gender_norm = (gender or "").strip().lower()
    if gender_norm not in _MH_ALLOWED_GENDERS:
        return {"success": False, "error": f"gender must be Male/Female, got: {gender!r}"}
    gender_label = "Female" if gender_norm in ("female", "f") else "Male"
    if max_texture_size not in (256, 512, 1024, 2048, 4096):
        return {"success": False, "error": f"max_texture_size must be 256/512/1024/2048/4096"}

    dialog = _silent_export_find_dialog()
    if dialog is None:
        return {"success": False, "error": "ExportHeadDialog not visible yet — wait longer after silent_trigger_dialog"}

    notes = []
    p = dialog.findChild(QComboBox, "qtPipelineSelectionComboBox")
    if p:
        idx = p.findText(f"Mesh to MetaHuman_{gender_label}")
        if idx < 0:
            idx = p.findText(f"Mesh to MetaHuman {gender_label}")
        if idx >= 0:
            p.setCurrentIndex(idx)
            notes.append(f"Pipeline: {p.currentText()}")

    chk = dialog.findChild(QCheckBox, "qtMaxTextureSizeCheckBox")
    if chk and not chk.isChecked():
        chk.click()
        notes.append("Checkbox toggled on")

    sz = dialog.findChild(QComboBox, "qtMaxTextureSizeComboBox")
    if sz:
        idx = sz.findText(str(max_texture_size))
        if idx >= 0:
            sz.setCurrentIndex(idx)
            notes.append(f"MaxTextureSize: {sz.currentText()}")

    btn = dialog.findChild(QPushButton, "qtExportPushButton")
    if btn is None:
        return {"success": False, "error": "qtExportPushButton not found"}

    _SILENT_EXPORT_STATE["gender"] = gender_label
    _SILENT_EXPORT_STATE["phase"] = "exporting"
    _SILENT_EXPORT_STATE["notes"].extend(notes)
    _SILENT_EXPORT_STATE["notes"].append("Export clicked (deferred via QTimer)")

    # Defer click so this bridge command can return before the modal opens
    QTimer.singleShot(100, btn.click)
    return {
        "success": True,
        "phase": "exporting",
        "gender": gender_label,
        "max_texture_size": max_texture_size,
        "expected_fbx": _SILENT_EXPORT_STATE["fbx_path"],
        "notes": notes,
        "estimated_seconds": 60,
        "poll_endpoint": "GET /export/head_mh/status",
    }


def silent_finalize() -> dict[str, Any]:
    """Step 4 (cleanup) of silent Export Head: remove filter + close stale dialog.

    Call this after the export progress completes (get_export_status shows done).
    """
    refused = _exec_gate("silent_finalize")
    if refused:
        return refused
    from PySide2.QtCore import QTimer
    _silent_export_remove_filter()
    try:
        dlg = _silent_export_find_dialog()
        if dlg is not None:
            QTimer.singleShot(50, dlg.reject)
    except Exception:
        pass
    _SILENT_EXPORT_STATE["phase"] = "done" if os.path.exists(_SILENT_EXPORT_STATE.get("fbx_path", "")) else "cleanup_done"
    import time
    _SILENT_EXPORT_STATE["finished_at"] = time.time()
    return {"success": True, "phase": _SILENT_EXPORT_STATE["phase"]}


def get_export_status() -> dict[str, Any]:
    """Return the current state of the silent export job."""
    state = dict(_SILENT_EXPORT_STATE)
    # Add elapsed
    import time
    if state["started_at"] > 0:
        end = state["finished_at"] if state["finished_at"] > 0 else time.time()
        state["elapsed_seconds"] = round(end - state["started_at"], 1)
    else:
        state["elapsed_seconds"] = 0
    # Check FBX exists
    if state["fbx_path"]:
        state["fbx_exists"] = os.path.exists(state["fbx_path"])
        if state["fbx_exists"]:
            state["fbx_size"] = os.path.getsize(state["fbx_path"])
    return state


# =====================================================================
# ActorMIXER PRO: Create Mixer Assets (.ccMixerPreset generation)
# =====================================================================
#
# Drives CC5's native ActorMIXER PRO "Create Mixer Assets" dialog in-process
# via PySide2 + shiboken2. The dialog uses modal exec loops, so EVERY trigger
# (menu action, message box dismiss, Create/Cancel click) is scheduled through
# QTimer.singleShot — calling .trigger()/.click() synchronously would block the
# bridge thread inside the modal loop and deadlock the HTTP server.
#
# Flow (all async, polled across multiple bridge calls is NOT needed — this
# single call schedules the whole chain and returns immediately after Create/
# Cancel is scheduled):
#   1. Snapshot the ActorMIXER/Character presets dir (for diffing new files).
#   2. Locate QAction objectName 'qtCreateMixerSliderAction' by walking the
#      menu bar; schedule act.trigger() via singleShot.
#   3. A trial-content QMessageBox (OK) may appear first — dismiss it via
#      singleShot OK click.
#   4. Poll (via singleShot chain) for the 'CreateMixerSliderDlg' dialog in
#      QApplication.allWidgets(); once found, set fields.
#   5. Click Create (qtCreatePushButton) if confirm_create, else Cancel
#      (qtCancelPushButton) for a dry-run.
#   6. _invalidate_caches() only on a real successful create.

# Default head-part checkboxes (all checked by default in the native dialog).
_MIXER_HEAD_PART_CHECKBOXES = {
    "eyes":       "qtEyeCheckBox",
    "forehead":   "qtBrowCheckBox",
    "chin":       "qtChinCheckBox",
    "mouth":      "qtMouthCheckBox",
    "ears":       "qtEarCheckBox",
    "nose":       "qtNoseCheckBox",
    "head_shape": "qtHeadAdjustCheckBox",
}

# Body checkboxes (unchecked by default).
_MIXER_BODY_CHECKBOXES = {
    "body":  "qtUserBodyAdjustCheckBox",
    "torso": "qtTorsoCheckBox",
}

# Save Presets group ('Save Presets' groupbox children).
_MIXER_SAVE_PRESET_CHECKBOXES = {
    "character":  "qtFullBodyPresetCheckBox",
    "head":       "qtHeadPresetCheckBox",
    "head_parts": "qtHeadPartsPresetCheckBox",
    "body":       "qtBodyPresetCheckBox",
    "body_parts": "qtBodyPartsPresetCheckBox",
}

# Defaults for the head_parts option object (native dialog: all checked).
_MIXER_HEAD_PART_DEFAULTS = {k: True for k in _MIXER_HEAD_PART_CHECKBOXES}
# Body parts default OFF.
_MIXER_BODY_PART_DEFAULTS = {k: False for k in _MIXER_BODY_CHECKBOXES}
# Save Presets: enabled with character/head/head_parts/body on, body_parts off.
_MIXER_SAVE_PRESET_DEFAULTS = {
    "enabled": True, "character": True, "head": True,
    "head_parts": True, "body": True, "body_parts": False,
}

# Shared state for the async dialog driver (single in-flight create at a time).
_MIXER_STATE: dict[str, Any] = {
    "phase": "idle",          # idle | scheduled | dialog_open | created | cancelled | error
    "morph_name": "",
    "created": False,
    "dry_run": True,
    "presets_dir": "",
    "presets_before": [],
    "new_presets": [],
    "error": "",
    "notes": [],
}


def _mixer_is_trial_content() -> bool:
    """Return True if the open avatar contains TRIAL content.

    The ActorMIXER plugin REFUSES to generate mixer presets from trial content:
    it shows the trial QMessageBox and then ABORTS — CreateMixerSliderDlg never
    appears, so we must detect this up front instead of polling until timeout.
    hasattr-guarded because IsTrialContentMode may not exist in every CC5 build.
    """
    try:
        if hasattr(RLPy, "RGlobal") and hasattr(RLPy.RGlobal, "IsTrialContentMode"):
            return bool(RLPy.RGlobal.IsTrialContentMode())
    except Exception:
        pass
    return False


def _mixer_presets_dir() -> str:
    """Resolve the directory where new mixer presets (.ccMixerPreset) land.

    Prefers RApplication.GetCustomContentFolder(EContentRootFolder_Character)
    so we can diff the user's content folder for newly created assets. Falls
    back to <CC5 root>/.../ActorMIXER if the API path is unavailable.
    """
    for attr_name in ("EContentRootFolder_Character", "EContentRootFolder_FullBody"):
        if not hasattr(RLPy, attr_name):
            continue
        enum = getattr(RLPy, attr_name)
        for getter in ("GetCustomContentFolder", "GetDefaultContentFolder"):
            if hasattr(RLPy, "RApplication") and hasattr(RLPy.RApplication, getter):
                try:
                    folder = getattr(RLPy.RApplication, getter)(enum)
                    if folder and os.path.isdir(folder):
                        return folder
                except Exception:
                    pass
    # Fallback: best-effort directory under CC5 root.
    return os.path.join(_get_cc5_root(), "Custom", "ActorMIXER")


def _mixer_snapshot_presets(presets_dir: str) -> list[str]:
    """List existing .ccMixerPreset files under presets_dir (recursive)."""
    found: list[str] = []
    if not presets_dir or not os.path.isdir(presets_dir):
        return found
    try:
        for root, _dirs, files in os.walk(presets_dir):
            for fname in files:
                if fname.lower().endswith(".ccmixerpreset"):
                    found.append(os.path.join(root, fname))
    except Exception:
        pass
    return found


def _mixer_find_main_window() -> Any:
    """Wrap CC5's main window as a QMainWindow via shiboken2, or None."""
    try:
        import shiboken2
        from PySide2 import QtWidgets
    except Exception:
        return None
    try:
        ptr = RLPy.RUi.GetMainWindow()
        if not ptr:
            return None
        return shiboken2.wrapInstance(int(ptr), QtWidgets.QMainWindow)
    except Exception:
        return None


def _mixer_find_action(main_win: Any) -> Any:
    """Walk the menu bar to find QAction objectName 'qtCreateMixerSliderAction'."""
    if main_win is None or not hasattr(main_win, "menuBar"):
        return None
    menubar = main_win.menuBar()
    if menubar is None:
        return None

    def _walk(menu: Any, depth: int = 0) -> Any:
        if menu is None or depth > 6:
            return None
        try:
            for act in menu.actions():
                try:
                    obj = act.objectName() if hasattr(act, "objectName") else ""
                except Exception:
                    obj = ""
                if obj == "qtCreateMixerSliderAction":
                    return act
                sub = act.menu()
                if sub is not None:
                    hit = _walk(sub, depth + 1)
                    if hit is not None:
                        return hit
        except Exception:
            pass
        return None

    return _walk(menubar)


def _mixer_find_dialog() -> Any:
    """Find the visible 'CreateMixerSliderDlg' dialog, or None."""
    try:
        from PySide2.QtWidgets import QApplication
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    for w in app.allWidgets():
        try:
            if w.objectName() == "CreateMixerSliderDlg" and w.isVisible():
                return w
        except Exception:
            continue
    return None


def _mixer_dismiss_trial_msgbox() -> None:
    """Dismiss a trial-content QMessageBox (click OK) if one is showing."""
    try:
        from PySide2.QtWidgets import QApplication, QMessageBox, QPushButton, QDialogButtonBox
        from PySide2.QtCore import QTimer
    except Exception:
        return
    app = QApplication.instance()
    if app is None:
        return
    for w in app.allWidgets():
        try:
            if isinstance(w, QMessageBox) and w.isVisible():
                ok_btn = w.button(QMessageBox.Ok)
                if ok_btn is None:
                    bb = w.findChild(QDialogButtonBox)
                    if bb is not None:
                        ok_btn = bb.button(QDialogButtonBox.Ok)
                if ok_btn is None:
                    ok_btn = w.findChild(QPushButton)
                if ok_btn is not None:
                    QTimer.singleShot(0, ok_btn.click)
                return
        except Exception:
            continue


def _mixer_set_checkbox(dialog: Any, object_name: str, desired: bool, notes: list[str]) -> None:
    """Set a QCheckBox in the dialog to `desired` (click only if state differs)."""
    try:
        from PySide2.QtWidgets import QCheckBox
    except Exception:
        return
    chk = dialog.findChild(QCheckBox, object_name)
    if chk is None:
        notes.append(f"checkbox not found: {object_name}")
        return
    try:
        if bool(chk.isChecked()) != bool(desired):
            chk.setChecked(bool(desired))
        notes.append(f"{object_name}={desired}")
    except Exception as e:
        notes.append(f"{object_name} set failed: {e}")


def _mixer_apply_fields(dialog: Any, opts: dict[str, Any], notes: list[str]) -> None:
    """Set all line-edit and checkbox fields on the CreateMixerSliderDlg."""
    try:
        from PySide2.QtWidgets import QLineEdit
    except Exception:
        notes.append("PySide2 QLineEdit unavailable; fields not applied")
        return

    morph_name = opts.get("morph_name") or ""
    if morph_name:
        name_edit = dialog.findChild(QLineEdit, "qtSliderNameLineEdit")
        if name_edit is not None:
            name_edit.setText(str(morph_name))
            notes.append(f"name={morph_name}")

    slider_path = opts.get("slider_path") or ""
    if slider_path:
        path_edit = dialog.findChild(QLineEdit, "qtSliderPathLineEdit")
        if path_edit is not None:
            path_edit.setText(str(slider_path))
            notes.append(f"path={slider_path}")

    _mixer_set_checkbox(
        dialog, "qtUseUnderPartFolderCheckBox",
        bool(opts.get("use_parts_folder", False)), notes,
    )

    head_parts = dict(_MIXER_HEAD_PART_DEFAULTS)
    head_parts.update(opts.get("head_parts") or {})
    for key, object_name in _MIXER_HEAD_PART_CHECKBOXES.items():
        _mixer_set_checkbox(dialog, object_name, bool(head_parts.get(key, True)), notes)

    body_parts = dict(_MIXER_BODY_PART_DEFAULTS)
    body_parts.update(opts.get("body_parts") or {})
    for key, object_name in _MIXER_BODY_CHECKBOXES.items():
        _mixer_set_checkbox(dialog, object_name, bool(body_parts.get(key, False)), notes)

    save_presets = dict(_MIXER_SAVE_PRESET_DEFAULTS)
    save_presets.update(opts.get("save_presets") or {})
    _mixer_set_groupbox(dialog, "qtSavePresetGroupBox", bool(save_presets.get("enabled", True)), notes)
    for key, object_name in _MIXER_SAVE_PRESET_CHECKBOXES.items():
        _mixer_set_checkbox(dialog, object_name, bool(save_presets.get(key, False)), notes)

    # Save Avatar Presets (whole group) — default disabled.
    save_avatar = dict(opts.get("save_avatar_presets") or {})
    _mixer_set_groupbox(
        dialog, "qtSaveAvatarPresetGroupBox",
        bool(save_avatar.get("enabled", False)), notes,
    )


def _mixer_set_groupbox(dialog: Any, object_name: str, desired: bool, notes: list[str]) -> None:
    """Set a checkable QGroupBox to `desired` if it is checkable."""
    try:
        from PySide2.QtWidgets import QGroupBox
    except Exception:
        return
    gb = dialog.findChild(QGroupBox, object_name)
    if gb is None:
        notes.append(f"groupbox not found: {object_name}")
        return
    try:
        if gb.isCheckable() and bool(gb.isChecked()) != bool(desired):
            gb.setChecked(bool(desired))
        notes.append(f"{object_name}={desired}")
    except Exception as e:
        notes.append(f"{object_name} set failed: {e}")


def create_actor_mixer(params: dict[str, Any]) -> dict[str, Any]:
    """Drive the ActorMIXER PRO 'Create Mixer Assets' dialog to generate mixer
    presets (.ccMixerPreset) from the currently open avatar.

    confirm_create is a safety gate:
      - False (default): set every field, then CANCEL the dialog (dry-run; no
        files written). Lets callers preview exactly what would be created.
      - True: set fields then click Create once.

    Because the dialog runs a modal exec loop, the whole chain (menu trigger,
    trial-msgbox dismiss, field config, Create/Cancel) is scheduled via
    QTimer.singleShot and this function returns immediately after scheduling.

    Returns: {success, morph_name, created, dry_run, new_presets, presets_dir, error?}
    """
    try:
        from PySide2.QtCore import QTimer
        from PySide2.QtWidgets import QApplication
    except Exception as e:
        return {
            "success": False,
            "error": f"PySide2 unavailable ({e}); ActorMIXER automation requires the CC5 Qt UI",
            "created": False,
            "dry_run": True,
            "new_presets": [],
            "presets_dir": "",
        }

    if params is None:
        params = {}

    # Single in-flight job: refuse a new request while a prior chain is still
    # polling for / configuring the dialog (otherwise the still-pending _finish
    # closure would write stale snapshots into the shared _MIXER_STATE).
    _IN_FLIGHT = ("scheduled", "dialog_open")
    if _MIXER_STATE.get("phase") in _IN_FLIGHT:
        return {
            "success": False,
            "error": f"Create Mixer Assets already in-flight (phase={_MIXER_STATE.get('phase')}); "
                     f"poll GET /actor_mixer/status and retry once idle/created/cancelled.",
            "created": False,
            "dry_run": True,
            "new_presets": [],
            "presets_dir": _MIXER_STATE.get("presets_dir", ""),
        }

    # Trial-content precondition: the ActorMIXER plugin shows the trial message
    # box and ABORTS (CreateMixerSliderDlg never appears) when the avatar holds
    # trial content. Detect and fail fast — do NOT open or schedule anything,
    # otherwise the dialog-poll chain would hang until its ~4s timeout.
    if _mixer_is_trial_content():
        return {
            "success": False,
            "error": (
                "Cannot create ActorMIXER assets: the current avatar contains "
                "TRIAL content (IsTrialContentMode is true). The plugin refuses "
                "to generate mixer presets from trial content. Replace the trial "
                "asset(s) with owned/purchased equivalents, or load a non-trial "
                "avatar, then retry."
            ),
            "trial_content": True,
            "created": False,
            "dry_run": True,
            "new_presets": [],
            "presets_dir": "",
        }

    confirm_create = bool(params.get("confirm_create", False))
    dry_run = not confirm_create

    # Default morph_name to the open avatar's name.
    morph_name = (params.get("morph_name") or "").strip()
    avatar = get_first_avatar()
    if not morph_name and avatar is not None:
        try:
            morph_name = avatar.GetName()
        except Exception:
            morph_name = ""

    presets_dir = _mixer_presets_dir()
    presets_before = _mixer_snapshot_presets(presets_dir)

    opts = {
        "morph_name": morph_name,
        "slider_path": params.get("slider_path") or "",
        "use_parts_folder": bool(params.get("use_parts_folder", False)),
        "head_parts": params.get("head_parts") or {},
        "body_parts": params.get("body_parts") or {},
        "save_presets": params.get("save_presets") or {},
        "save_avatar_presets": params.get("save_avatar_presets") or {},
    }

    main_win = _mixer_find_main_window()
    if main_win is None:
        return {
            "success": False,
            "error": "Could not resolve CC5 main window (RUi.GetMainWindow / shiboken2)",
            "morph_name": morph_name,
            "created": False,
            "dry_run": dry_run,
            "new_presets": [],
            "presets_dir": presets_dir,
        }

    action = _mixer_find_action(main_win)
    if action is None:
        return {
            "success": False,
            "error": "Could not find 'qtCreateMixerSliderAction' (ActorMIXER PRO required)",
            "morph_name": morph_name,
            "created": False,
            "dry_run": dry_run,
            "new_presets": [],
            "presets_dir": presets_dir,
        }

    notes: list[str] = []
    _MIXER_STATE.update({
        "phase": "scheduled",
        "morph_name": morph_name,
        "created": False,
        "dry_run": dry_run,
        "presets_dir": presets_dir,
        "presets_before": presets_before,
        "new_presets": [],
        "error": "",
        "notes": notes,
    })

    # Schedule the async chain. Each step re-arms the next via singleShot so the
    # bridge thread never blocks inside the modal exec loop.
    def _on_dialog_ready(attempt: int = 0) -> None:
        # First, clear any trial-content message box that pre-empts the dialog.
        _mixer_dismiss_trial_msgbox()
        dialog = _mixer_find_dialog()
        if dialog is None:
            if attempt >= 40:  # ~4s budget at 100ms steps
                _MIXER_STATE["phase"] = "error"
                _MIXER_STATE["error"] = "CreateMixerSliderDlg never appeared"
                return
            QTimer.singleShot(100, lambda: _on_dialog_ready(attempt + 1))
            return

        _MIXER_STATE["phase"] = "dialog_open"
        try:
            _mixer_apply_fields(dialog, opts, notes)
        except Exception as e:
            notes.append(f"apply_fields error: {e}")

        # Defer the final action so field edits settle in the event loop.
        QTimer.singleShot(50, lambda: _finish(dialog))

    def _post_create() -> None:
        # Runs ~2.5s after Create is clicked, giving CC5 time to flush the
        # .ccMixerPreset file(s) to disk before we diff. Only NOW is it safe to
        # diff and invalidate caches (the inline diff inside _finish would race
        # the still-pending file write and report an empty new_presets list).
        try:
            after = _mixer_snapshot_presets(presets_dir)
            before_set = set(presets_before)
            _MIXER_STATE["new_presets"] = [p for p in after if p not in before_set]
            _invalidate_caches()
        except Exception as e:
            notes.append(f"post_create diff error: {e}")

    def _finish(dialog: Any) -> None:
        try:
            from PySide2.QtWidgets import QPushButton
        except Exception as e:
            _MIXER_STATE["phase"] = "error"
            _MIXER_STATE["error"] = f"PySide2 QPushButton unavailable: {e}"
            return
        try:
            if confirm_create:
                btn = dialog.findChild(QPushButton, "qtCreatePushButton")
                if btn is None:
                    _MIXER_STATE["phase"] = "error"
                    _MIXER_STATE["error"] = "qtCreatePushButton not found"
                    return
                btn.click()
                _MIXER_STATE["phase"] = "created"
                _MIXER_STATE["created"] = True
                _MIXER_STATE["new_presets"] = []
                # Defer the presets diff + cache invalidation: the file is not
                # on disk yet when btn.click() returns (async CC5 work).
                QTimer.singleShot(2500, _post_create)
            else:
                btn = dialog.findChild(QPushButton, "qtCancelPushButton")
                if btn is not None:
                    btn.click()
                else:
                    dialog.reject()
                _MIXER_STATE["phase"] = "cancelled"
        except Exception as e:
            _MIXER_STATE["phase"] = "error"
            _MIXER_STATE["error"] = str(e)

    QTimer.singleShot(0, action.trigger)
    QTimer.singleShot(300, _on_dialog_ready)

    return {
        "success": True,
        "morph_name": morph_name,
        "created": False,          # async — created flips true in _finish; poll get_mixer_status
        "dry_run": dry_run,
        "new_presets": [],
        "presets_dir": presets_dir,
        "scheduled": True,
        "notes": list(notes),      # snapshot copy — callbacks keep mutating _MIXER_STATE["notes"]
        "poll_endpoint": "/actor_mixer/status",
    }


def get_mixer_status() -> dict[str, Any]:
    """Return the current state of the async Create Mixer Assets job.

    On a completed create, re-diff the presets dir from disk so a poll picks up
    files CC5 wrote after _finish returned. Short-circuit once new_presets is
    populated to avoid re-walking the filesystem on every subsequent poll.
    """
    state = dict(_MIXER_STATE)
    if (
        state.get("phase") == "created"
        and state.get("presets_dir")
        and not state.get("new_presets")
    ):
        after = _mixer_snapshot_presets(state["presets_dir"])
        before_set = set(state.get("presets_before") or [])
        state["new_presets"] = [p for p in after if p not in before_set]
    return {
        "success": state.get("phase") != "error",
        "phase": state.get("phase", "idle"),
        "morph_name": state.get("morph_name", ""),
        "created": bool(state.get("created", False)),
        "dry_run": bool(state.get("dry_run", True)),
        "new_presets": state.get("new_presets", []),
        "presets_dir": state.get("presets_dir", ""),
        # Surface trial mode up front so callers can check before attempting a
        # create that the plugin would refuse (see _mixer_is_trial_content).
        "trial_content": _mixer_is_trial_content(),
        "error": state.get("error", ""),
        "notes": list(state.get("notes", [])),
    }


# --- Workflow routes (see docs/contract_workflow_routes.md) ---
#
# Calling convention: the bridge dispatches with handler(params), so every
# route takes an optional body dict as its first positional argument, plus
# keyword overrides for direct callers:
#     wf_set_visible({"item_name": "Hat", "visible": False})
#     wf_set_visible(item_name="Hat", visible=False)
# That also lets the plain function object be registered in ACTION_MAP.

# RLPy does not document the exact TransferSkinWeight template strings, so we
# guess title-case names ("Default", "Dress", "Gloves", "Shoes", "Cloak",
# "Other").
_WF_TRANSFER_TEMPLATES = {
    "default": "Default",
    "dress": "Dress",
    "gloves": "Gloves",
    "shoes": "Shoes",
    "cloak": "Cloak",
    "other": "Other",
}

# (enum attribute name, is face hair). The eyelash types have no matching
# EHairType_/EFaceHairType_ constant in the exposed constants list, so they
# cannot be mapped and are reported as GUI-only.
_WF_HAIR_ENUM_NAMES = {
    "top": ("EHairType_Hair_Top", False),
    "base_all": ("EHairType_Hair_Base", False),
    "rear": ("EHairType_Hair_Rear", False),
    "bangs": ("EHairType_Hair_Bangs", False),
    "accessory": ("EHairType_Hair_Accessory", False),
    "brows": ("EFaceHairType_Eyebrows", True),
    "upper_lash": (None, True),
    "lower_lash": (None, True),
}

_WF_LIGHT_TYPE_NAMES = (
    "EObjectType_SpotLight",
    "EObjectType_PointLight",
    "EObjectType_DirectionalLight",
)

_WF_TYPE_KINDS = (
    ("EObjectType_Avatar", "avatar"),
    ("EObjectType_Cloth", "cloth"),
    ("EObjectType_Accessory", "accessory"),
    ("EObjectType_Hair", "hair"),
    ("EObjectType_Prop", "prop"),
    ("EObjectType_Camera", "camera"),
    ("EObjectType_SpotLight", "light"),
    ("EObjectType_PointLight", "light"),
    ("EObjectType_DirectionalLight", "light"),
    ("EObjectType_Light", "light"),
)

_WF_VIEW4_ORDER = ("front", "side", "top", "persp")

# Guesses: "Right" for the +X side view; "Home" for the perspective view
# (SetCameraLocation has no way to request an exact 45 deg yaw / 25 deg pitch).
_WF_VIEW4_CAMERA = {
    "front": "ECameraLocationType_Front",
    "side": "ECameraLocationType_Right",
    "top": "ECameraLocationType_Top",
    "persp": "ECameraLocationType_Home",
}


def _wf_params(body: Any, extra: dict[str, Any]) -> dict[str, Any]:
    """Merge the positional body dict with keyword overrides (None means unset)."""
    params: dict[str, Any] = dict(body) if isinstance(body, dict) else {}
    for key, value in extra.items():
        if value is not None:
            params[key] = value
    return params


def _wf_obj_name(obj) -> str:
    try:
        return obj.GetName()
    except Exception:
        return ""


def _wf_obj_id(obj) -> Any:
    try:
        return obj.GetID()
    except Exception:
        return None


def _wf_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


def _wf_visible(obj) -> bool | None:
    """Visibility where the object exposes IsVisible; cloth/hair have no getter."""
    try:
        if hasattr(obj, "IsVisible"):
            return bool(obj.IsVisible(RLPy.RGlobal.GetTime()))
    except Exception:
        pass
    return None


def _wf_parent_name(obj) -> str | None:
    try:
        parent = obj.GetParent()
    except Exception:
        return None
    if parent is None:
        return None
    return _wf_obj_name(parent) or None


def _wf_kind_from_type(obj) -> str | None:
    try:
        obj_type = obj.GetType()
    except Exception:
        return None
    for const_name, kind in _WF_TYPE_KINDS:
        enum = getattr(RLPy, const_name, None)
        if enum is None:
            continue
        try:
            if obj_type == enum:
                return kind
        except Exception:
            continue
    return None


def _wf_kind_of(obj) -> str:
    """Best-effort kind for an object (avatar/cloth/accessory/hair/prop/light/camera)."""
    oid = _wf_obj_id(obj)
    try:
        avatars = RLPy.RScene.GetAvatars()
    except Exception:
        avatars = []
    for avatar in avatars or []:
        if _wf_obj_id(avatar) == oid:
            return "avatar"
        for getter, kind in (
            (avatar.GetClothes, "cloth"),
            (lambda a=avatar: a.GetAccessories(True), "accessory"),
            (avatar.GetHairs, "hair"),
        ):
            try:
                items = getter()
            except Exception:
                continue
            for item in items or []:
                if _wf_obj_id(item) == oid:
                    return kind
    return _wf_kind_from_type(obj) or "prop"


def _wf_owner_avatar(obj):
    """Return the avatar that owns obj (the avatar itself, or its parent avatar)."""
    oid = _wf_obj_id(obj)
    try:
        avatars = RLPy.RScene.GetAvatars()
    except Exception:
        return None
    for avatar in avatars or []:
        if _wf_obj_id(avatar) == oid:
            return avatar
    for avatar in avatars or []:
        for getter in (
            avatar.GetClothes,
            lambda a=avatar: a.GetAccessories(True),
            avatar.GetHairs,
        ):
            try:
                items = getter()
            except Exception:
                continue
            for item in items or []:
                if _wf_obj_id(item) == oid:
                    return avatar
    return None


def _wf_scan() -> list[tuple[Any, dict[str, Any]]]:
    """All scene items as (object, entry) pairs, deduplicated by object id."""
    found: list[tuple[Any, dict[str, Any]]] = []
    seen: set[Any] = set()

    def add(obj, kind: str) -> None:
        oid = _wf_obj_id(obj)
        if oid is not None and oid in seen:
            return
        seen.add(oid)
        entry: dict[str, Any] = {
            "name": _wf_obj_name(obj),
            "id": oid,
            "kind": kind,
            "visible": _wf_visible(obj),
            "parent": _wf_parent_name(obj),
        }
        if kind == "cloth":
            try:
                entry["cloth_type"] = str(obj.GetClotheType())
            except Exception:
                entry["cloth_type"] = None
        elif kind == "hair":
            try:
                entry["hair_type"] = str(obj.GetHairType())
            except Exception:
                entry["hair_type"] = None
        found.append((obj, entry))

    try:
        avatars = RLPy.RScene.GetAvatars()
    except Exception as e:
        print(f"[CC5 MCP Bridge] _wf_scan avatars failed: {e}")
        avatars = []
    for avatar in avatars or []:
        add(avatar, "avatar")
        for getter, kind in (
            (avatar.GetClothes, "cloth"),
            (lambda a=avatar: a.GetAccessories(True), "accessory"),
            (avatar.GetHairs, "hair"),
        ):
            try:
                items = getter()
            except Exception as e:
                print(f"[CC5 MCP Bridge] _wf_scan {kind} failed: {e}")
                continue
            for item in items or []:
                add(item, kind)

    try:
        props = RLPy.RScene.GetProps()
    except Exception as e:
        print(f"[CC5 MCP Bridge] _wf_scan props failed: {e}")
        props = []
    for prop in props or []:
        add(prop, "prop")

    for type_name in _WF_LIGHT_TYPE_NAMES:
        enum = getattr(RLPy, type_name, None)
        if enum is None:
            continue
        try:
            lights = RLPy.RScene.FindObjects(enum)
        except Exception as e:
            print(f"[CC5 MCP Bridge] _wf_scan {type_name} failed: {e}")
            continue
        for light in lights or []:
            add(light, "light")

    try:
        cameras = RLPy.RScene.GetCameras()
    except Exception as e:
        print(f"[CC5 MCP Bridge] _wf_scan cameras failed: {e}")
        cameras = []
    for camera in cameras or []:
        add(camera, "camera")

    return found


def _wf_resolve(item_name: str | None = None, item_id: Any = None):
    """Resolve an item selector. Returns (object, kind, error_dict_or_None)."""
    if item_id is None and not item_name:
        return None, None, {"success": False, "error": "item_name or item_id is required"}

    scan = _wf_scan()
    if item_id is not None and str(item_id) != "":
        # Only ids from the current scan are used. Never pass an unknown id to
        # RScene.QueryObjectByID: ids change when a project is reopened, and a stale id
        # crashed CC5 twice (access violation, live 10-22). The scan also yields the
        # typed object (RIAccessory/RICloth/...) that QueryObjectByID would not.
        typed = [(o, e) for o, e in scan if str(e["id"]) == str(item_id)]
        if len(typed) == 1:
            return typed[0][0], typed[0][1]["kind"], None

    if item_id is not None and str(item_id) != "":
        wanted = str(item_id)
        matches = [(o, e) for o, e in scan if str(e["id"]) == wanted]
        label = f"id {item_id}"
    else:
        matches = [(o, e) for o, e in scan if e["name"] == item_name]
        label = f"name {item_name!r}"

    if not matches:
        return None, None, {"success": False, "error": f"Item not found: {label}"}
    if len(matches) > 1:
        return None, None, {
            "success": False,
            "error": "ambiguous name",
            "matches": [
                {"name": e["name"], "id": e["id"], "kind": e["kind"]} for _, e in matches
            ],
        }
    obj, entry = matches[0]
    return obj, entry["kind"], None


# --- Routines shared by several routes ---

def _wf_current_project_path() -> str:
    """Best-effort lookup of the open project path (not part of the documented API)."""
    app = getattr(RLPy, "RApplication", None)
    if app is None:
        return ""
    for name in ("GetCurrentProjectPath", "GetCurrentProjectFilePath", "GetProjectPath"):
        getter = getattr(app, name, None)
        if getter is None:
            continue
        try:
            value = getter()
        except Exception:
            continue
        if isinstance(value, str) and value.lower().endswith(".ccproject"):
            return value
    return ""


def _wf_conform_get(obj, key: str) -> Any:
    try:
        return _wf_jsonable(obj.GetClothConformValue(key))
    except Exception:
        return None


# Conform panel labels (title case) and lower_snake guesses, in probe order.
_WF_CONFORM_KEYS = (
    "Increase Size", "increase_size",
    "Iteration", "iteration",
    "Subdivision Level", "subdivision_level",
    "Margin", "margin",
    "Close-fitting", "close_fitting",
    "Smooth", "smooth",
)


def _wf_conform_candidates() -> list[str]:
    """Unique conform key spellings to probe with GetClothConformValue."""
    seen: set[str] = set()
    ordered: list[str] = []
    for key in _WF_CONFORM_KEYS:
        if key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def _wf_conform_norm(key: str) -> str:
    """Normalise a conform key for matching (case/underscore/hyphen insensitive)."""
    text = key.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


def _wf_vec3(value) -> list[float] | None:
    if value is None:
        return None
    try:
        return [float(value.x), float(value.y), float(value.z)]
    except Exception:
        try:
            return [float(c) for c in list(value)[:3]]
        except Exception:
            return None


def _wf_vector3(values: list[float]):
    vector3 = getattr(RLPy, "RVector3", None)
    if vector3 is None:
        return None
    try:
        return vector3(float(values[0]), float(values[1]), float(values[2]))
    except Exception:
        return None


def _wf_read_transform(obj) -> dict[str, Any]:
    """Read the object's local transform as raw T/R/S values."""
    transform = obj.LocalTransform()
    return {
        "move": _wf_vec3(transform.T()),
        "rotate": _wf_vec3(transform.R()),
        "scale": _wf_vec3(transform.S()),
    }


def _wf_make_transform(move, rotate, scale):
    """Build an RTransform from T/R/S value lists. Returns (transform, error)."""
    transform = RLPy.RTransform()
    for method_name, values in (("T", move), ("R", rotate), ("S", scale)):
        if values is None:
            continue
        vector = _wf_vector3(values)
        if vector is None:
            return None, f"Could not build an RVector3 for {method_name}()"
        getattr(transform, method_name)(vector)
    return transform, None


def _wf_shoes_items(avatar) -> list[Any]:
    """Cloth items on the avatar whose cloth type is Shoes."""
    if avatar is None:
        return []
    shoes_enum = getattr(RLPy, "EClotheType_Shoes", None)
    result: list[Any] = []
    try:
        clothes = avatar.GetClothes()
    except Exception:
        return []
    for cloth in clothes or []:
        try:
            cloth_type = cloth.GetClotheType()
        except Exception:
            continue
        if shoes_enum is not None:
            try:
                if cloth_type == shoes_enum:
                    result.append(cloth)
                    continue
            except Exception:
                pass
        if "Shoes" in str(cloth_type):
            result.append(cloth)
    return result


def _wf_floor_contact_types() -> list[tuple[str, Any]]:
    """Constants named EFloorContact* exposed by this RLPy build (name, enum)."""
    types: list[tuple[str, Any]] = []
    for name in dir(RLPy):
        if not name.startswith("EFloorContact"):
            continue
        try:
            types.append((name, getattr(RLPy, name)))
        except Exception:
            continue
    return sorted(types, key=lambda item: item[0])


def _wf_render_png(file_path: str) -> str | None:
    """Render the viewport to file_path with no UI interaction. Error string or None."""
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    # RenderImage's native default is ~100x32 px, so raise the export size first.
    try:
        _set_render_resolution(1280, 720)
    except Exception as e:
        print(f"[CC5 MCP Bridge] _wf_render_png resolution failed: {e}")

    try:
        RLPy.RGlobal.RenderImage(file_path)
    except Exception as e:
        return f"RenderImage failed: {e}"

    if not os.path.exists(file_path) and hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
        try:
            RLPy.RGlobal.ForceViewportUpdate()
            RLPy.RGlobal.RenderImage(file_path)
        except Exception as e:
            return f"RenderImage failed: {e}"

    if not os.path.exists(file_path):
        return (
            f"RenderImage did not create {file_path}; no silent render path is "
            "available (refusing to click the UI)"
        )
    return None


_WF_CAMERA_CONTROL_KEYS = (
    "Transform", "KT_Transform", "LocalTransform", "WorldTransform", "GlobalTransform",
)


def _wf_camera_find_control(camera) -> tuple[Any, str]:
    """The first readable/writable transform control on the camera, or (None, "")."""
    get_control = getattr(camera, "GetControl", None)
    if get_control is None:
        return None, ""
    for key in _WF_CAMERA_CONTROL_KEYS:
        try:
            control = get_control(key)
        except Exception:
            control = None
        if control is None:
            continue
        if hasattr(control, "SetValue") and hasattr(control, "GetValue"):
            return control, key
    return None, ""


def _wf_camera_save(camera) -> dict[str, Any]:
    """Snapshot the camera's transform control value (plus WorldTransform fallback)."""
    saved: dict[str, Any] = {
        "control": None,
        "control_key": "",
        "value": None,
        "world": None,
    }
    try:
        saved["world"] = camera.WorldTransform()
    except Exception as e:
        print(f"[CC5 MCP Bridge] camera WorldTransform not readable: {e}")
    control, key = _wf_camera_find_control(camera)
    if control is not None:
        try:
            value = RLPy.RTransform()
            got = control.GetValue(RLPy.RGlobal.GetTime(), value)
            if got is not None and hasattr(got, "T"):
                value = got
            saved["control"] = control
            saved["control_key"] = key
            saved["value"] = value
        except Exception as e:
            print(f"[CC5 MCP Bridge] camera control {key} GetValue failed: {e}")
    if saved["value"] is None:
        saved["value"] = saved["world"]
    elif saved["world"] is not None:
        # A binding that does not fill the out-parameter leaves an identity
        # RTransform behind; fall back to the world transform in that case.
        try:
            unusable = bool(saved["value"].IsIdentity()) and not bool(saved["world"].IsIdentity())
        except Exception:
            unusable = False
        if unusable:
            print("[CC5 MCP Bridge] camera control GetValue gave identity; using WorldTransform")
            saved["value"] = saved["world"]
    return saved


def _wf_transform_close(a, b, move_tol: float = 0.5, rotate_tol: float = 0.02) -> bool:
    """True when two RTransforms agree on translation and rotation."""
    try:
        ta, tb = _wf_vec3(a.T()), _wf_vec3(b.T())
        ra, rb = _wf_vec3(a.R()), _wf_vec3(b.R())
        if ta is None or tb is None:
            return False
        if not all(abs(x - y) <= move_tol for x, y in zip(ta, tb)):
            return False
        if ra is not None and rb is not None:
            if not all(abs(x - y) <= rotate_tol for x, y in zip(ra, rb)):
                return False
        return True
    except Exception:
        return False


def _wf_camera_apply(camera, transform) -> tuple[bool, str]:
    """Write a camera transform. Returns (applied, method) — RIObject has no setter."""
    control, key = _wf_camera_find_control(camera)
    if control is not None:
        try:
            control.SetValue(RLPy.RGlobal.GetTime(), transform)
            return True, f"control:{key}"
        except Exception as e:
            print(f"[CC5 MCP Bridge] camera control {key} SetValue failed: {e}")
    for name in ("SetWorldTransform", "SetLocalTransform"):
        setter = getattr(camera, name, None)
        if setter is None:
            continue
        try:
            setter(transform)
            return True, name
        except Exception as e:
            print(f"[CC5 MCP Bridge] camera {name} failed: {e}")
    return False, ""


def _wf_restore_camera(camera, saved: dict[str, Any] | None) -> bool:
    """Put the camera back after a multi-view capture. False if it did not stick."""
    restored = False
    target = (saved or {}).get("value")
    if target is not None:
        applied = False
        control = (saved or {}).get("control")
        if control is None:
            control, _key = _wf_camera_find_control(camera)
        if control is not None and hasattr(control, "SetValue"):
            try:
                control.SetValue(RLPy.RGlobal.GetTime(), target)
                applied = True
            except Exception as e:
                print(f"[CC5 MCP Bridge] camera control restore failed: {e}")
        if not applied:
            for name in ("SetWorldTransform", "SetLocalTransform"):
                setter = getattr(camera, name, None)
                if setter is None:
                    continue
                try:
                    setter(target)
                    applied = True
                    break
                except Exception as e:
                    print(f"[CC5 MCP Bridge] camera {name} restore failed: {e}")
        if applied:
            readbacks: list[Any] = []
            if control is not None and hasattr(control, "GetValue"):
                try:
                    value = RLPy.RTransform()
                    got = control.GetValue(RLPy.RGlobal.GetTime(), value)
                    readbacks.append(got if (got is not None and hasattr(got, "T")) else value)
                except Exception:
                    pass
            try:
                readbacks.append(camera.WorldTransform())
            except Exception:
                pass
            restored = any(
                readback is not None and _wf_transform_close(target, readback)
                for readback in readbacks
            )
    try:
        RLPy.RScene.SetCurrentCamera(camera)
    except Exception as e:
        print(f"[CC5 MCP Bridge] SetCurrentCamera restore failed: {e}")
    if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
        try:
            RLPy.RGlobal.ForceViewportUpdate()
        except Exception:
            pass
    return restored


# --- Routes ---

def list_scene_items(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route /workflow/items: every scene item with kind/visible/parent."""
    try:
        return {"success": True, "items": [entry for _, entry in _wf_scan()]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_set_visible(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/visible."""
    params = _wf_params(body, kwargs)
    try:
        if params.get("visible") is None:
            return {"success": False, "error": "visible is required"}
        visible = bool(params.get("visible"))
        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        RLPy.RGlobal.BeginAction("wf_set_visible")
        try:
            (RLPy.RScene.Show if visible else RLPy.RScene.Hide)(obj)
            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
            if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                RLPy.RGlobal.ForceViewportUpdate()
        finally:
            RLPy.RGlobal.EndAction()
        return {
            "success": True,
            "name": _wf_obj_name(obj),
            "id": _wf_obj_id(obj),
            "visible": visible,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_remove_item(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/remove."""
    params = _wf_params(body, kwargs)
    try:
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        removed = {"name": _wf_obj_name(obj), "id": _wf_obj_id(obj), "kind": kind}
        avatar = _wf_owner_avatar(obj)
        RLPy.RGlobal.BeginAction("wf_remove_item")
        try:
            RLPy.RScene.RemoveObject(obj)
            if avatar is not None:
                try:
                    RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
                except Exception:
                    pass
            if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                RLPy.RGlobal.ForceViewportUpdate()
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "removed": removed}
    except Exception as e:
        return {"success": False, "error": str(e)}


_WF_IMPORT_FBX_TIMEOUT = 60.0

_WF_IMPORT_FBX_STATE: dict[str, Any] = {
    "phase": "idle",  # idle | file_dialog | prop_dialog | settings_dialog | settling | done | error
    "file_path": "",
    "error": "",
    "notes": [],
    "before_ids": [],
    "result": None,
    "started_at": 0.0,
    "finished_at": 0.0,
    "deadline": 0.0,
    "timer": None,
    "dialogs": [],
    "accepted": [],
    "file_dialog_seen_at": 0.0,
    "file_dialog_retry": False,
    "non_native_dialog": False,
    "prior_attr": None,
    "prior_attr_set": False,
    "steps": {},
}


# Dialog titles the import flow may touch. Anything else is never clicked; a visible
# title from _WF_IMPORT_FBX_DENY aborts the import (10-22: a stray "Convert" in the main
# window opened the irreversible "Game Base UVs" conversion).
_WF_IMPORT_FBX_PROP_TITLES = ("import fbx",)
_WF_IMPORT_FBX_SETTINGS_TITLES = ("import settings",)
_WF_IMPORT_FBX_DENY = ("game base", "convert to game", "subdivision", "export")


def _wf_import_trace(message: str) -> None:
    """Append one line to %TEMP%/cc5_import_trace.log (flushed), so a silent exit still leaves the last step."""
    try:
        path = os.path.join(os.environ.get("TEMP", "."), "cc5_import_trace.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(time.strftime("%H:%M:%S ") + message + "\n")
            fh.flush()
    except Exception:
        pass


def _wf_qt_valid(obj: Any) -> bool:
    """True while the C++ side of a PySide2 wrapper still exists."""
    if obj is None:
        return False
    try:
        import shiboken2  # type: ignore[import-not-found]
        return bool(shiboken2.isValid(obj))
    except Exception:
        try:
            obj.objectName()
            return True
        except Exception:
            return False


def _wf_qt_later(obj: Any, method: str, delay_ms: int = 100) -> None:
    """Call obj.method() after delay_ms, only if obj is still alive (no dangling calls)."""
    from PySide2.QtCore import QTimer

    def _run() -> None:
        try:
            if _wf_qt_valid(obj):
                _wf_import_trace(f"deferred {method} on {type(obj).__name__} '{_wf_import_fbx_text(obj) or _wf_dialog_title(obj)}'")
                getattr(obj, method)()
                _wf_import_trace(f"deferred {method} returned")
        except Exception as e:
            print(f"[CC5 MCP Bridge] deferred {method} failed: {e}")

    QTimer.singleShot(delay_ms, _run)


def _wf_dialog_title(widget: Any) -> str:
    try:
        win = widget.window()
        return (win.windowTitle() or "").strip().lower()
    except Exception:
        return ""


def _wf_import_fbx_denied_dialog() -> str:
    """Title of a visible dialog the import must never continue past, else ''."""
    for dlg in _wf_import_fbx_visible_dialogs():
        title = _wf_dialog_title(dlg)
        if any(word in title for word in _WF_IMPORT_FBX_DENY):
            return title
    return ""


def _wf_import_fbx_text(widget: Any) -> str:
    try:
        return (widget.text() or "").replace("&", "").replace("…", "...").strip().lower()
    except Exception:
        return ""


def _wf_import_fbx_find_action() -> Any:
    """QAction for File > Import... (text search of the menu tree)."""
    try:
        from PySide2.QtWidgets import QApplication, QMainWindow
    except Exception:
        return None
    app = QApplication.instance()
    main_win = None
    if app is not None:
        for w in app.topLevelWidgets():
            try:
                if isinstance(w, QMainWindow) and w.isVisible():
                    main_win = w
                    break
            except Exception:
                continue
    if main_win is None:
        main_win = _mixer_find_main_window()
    if main_win is None or not hasattr(main_win, "menuBar"):
        return None

    matches: list[tuple[int, Any]] = []

    def _walk(menu: Any, depth: int = 0) -> None:
        if menu is None or depth > 6:
            return
        try:
            for act in menu.actions():
                text = _wf_import_fbx_text(act)
                sub = act.menu()
                if sub is not None:
                    # "Import..." in File is only a submenu header (live 10-22); its leaf
                    # "Import" item is the one that opens the file dialog.
                    _walk(sub, depth + 1)
                    continue
                if text == "import":
                    matches.append((0, act))
                elif text == "import...":
                    matches.append((1, act))
                elif text.startswith("import") and "fbx" not in text:
                    matches.append((2, act))
        except Exception:
            pass

    _walk(main_win.menuBar())
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def _wf_import_fbx_force_non_native() -> bool:
    """Ask Qt not to use the native Windows file dialog, if the app allows it."""
    try:
        from PySide2.QtWidgets import QApplication
        from PySide2.QtCore import Qt
    except Exception:
        return False
    app = QApplication.instance()
    attr = getattr(Qt, "AA_DontUseNativeDialogs", None)
    if app is None or attr is None:
        return False
    try:
        prior = bool(app.testAttribute(attr))
        app.setAttribute(attr, True)
        _WF_IMPORT_FBX_STATE["prior_attr"] = prior
        _WF_IMPORT_FBX_STATE["prior_attr_set"] = True
        return True
    except Exception as e:
        print(f"[CC5 MCP Bridge] AA_DontUseNativeDialogs failed: {e}")
        return False


def _wf_import_fbx_restore_attr() -> None:
    state = _WF_IMPORT_FBX_STATE
    if not state.get("prior_attr_set"):
        return
    state["prior_attr_set"] = False
    try:
        from PySide2.QtWidgets import QApplication
        from PySide2.QtCore import Qt
    except Exception:
        return
    app = QApplication.instance()
    attr = getattr(Qt, "AA_DontUseNativeDialogs", None)
    if app is None or attr is None:
        return
    try:
        app.setAttribute(attr, bool(state.get("prior_attr")))
    except Exception:
        pass


def _wf_import_fbx_install_filter(file_path: str) -> Any:
    """Auto-accept the (non-native) QFileDialog opened by File > Import."""
    from PySide2.QtCore import QObject, QEvent, QTimer
    from PySide2.QtWidgets import QApplication, QFileDialog

    state = _WF_IMPORT_FBX_STATE

    class _ImportFileDialogAccept(QObject):
        def __init__(self) -> None:
            super().__init__()
            self.done = False

        def eventFilter(self, obj, event):
            if self.done:
                return False
            try:
                if (
                    isinstance(obj, QFileDialog)
                    and event.type() in (QEvent.Show, QEvent.WindowActivate)
                    and id(obj) not in state["accepted"]
                ):
                    try:
                        mode_ok = obj.acceptMode() == QFileDialog.AcceptOpen
                    except Exception:
                        mode_ok = True
                    if not mode_ok:
                        return False
                    if not state["non_native_dialog"]:
                        # Only when the app-level attribute was unavailable.
                        obj.setOption(QFileDialog.DontUseNativeDialog, True)
                    obj.selectFile(file_path)
                    state["accepted"].append(id(obj))
                    if obj not in state["dialogs"]:
                        state["dialogs"].append(obj)
                    state["notes"].append("File dialog filled through Qt (event filter)")
                    _wf_qt_later(obj, "accept", 150)
            except Exception as e:
                print(f"[CC5 MCP Bridge] import file filter failed: {e}")
            return False

    flt = _ImportFileDialogAccept()
    QApplication.instance().installEventFilter(flt)
    sys.modules["cc5_api"]._wf_import_fbx_filter = flt  # type: ignore[attr-defined]
    return flt


def _wf_import_fbx_remove_filter() -> None:
    from PySide2.QtWidgets import QApplication

    flt = getattr(sys.modules["cc5_api"], "_wf_import_fbx_filter", None)
    if flt is None:
        return
    try:
        flt.done = True
    except Exception:
        pass
    try:
        QApplication.instance().removeEventFilter(flt)
    except Exception:
        pass
    try:
        del sys.modules["cc5_api"]._wf_import_fbx_filter  # type: ignore[attr-defined]
    except Exception:
        pass


def _wf_import_fbx_visible_file_dialog() -> Any:
    try:
        from PySide2.QtWidgets import QApplication, QFileDialog
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    for w in app.allWidgets():
        try:
            if isinstance(w, QFileDialog) and w.isVisible():
                return w
        except Exception:
            continue
    return None


def _wf_import_fbx_is_file_dialog_button(button: Any) -> bool:
    try:
        from PySide2.QtWidgets import QFileDialog
        parent = button.parentWidget()
        while parent is not None:
            if isinstance(parent, QFileDialog):
                return True
            parent = parent.parentWidget()
    except Exception:
        pass
    return False


def _wf_import_fbx_find_button(kind: str) -> Any:
    """Visible Prop / Convert button belonging to the import dialogs."""
    try:
        from PySide2.QtWidgets import QAbstractButton, QApplication
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None

    best = None
    best_score = -1
    for w in app.allWidgets():
        try:
            if not isinstance(w, QAbstractButton) or not w.isVisible():
                continue
            if _wf_import_fbx_is_file_dialog_button(w):
                continue
            title = _wf_dialog_title(w)
            wanted = _WF_IMPORT_FBX_PROP_TITLES if kind == "prop" else _WF_IMPORT_FBX_SETTINGS_TITLES
            if title not in wanted:
                continue                    # never a button of the main window or another dialog
            text = _wf_import_fbx_text(w)
            try:
                obj_name = (w.objectName() or "").strip().lower()
            except Exception:
                obj_name = ""
            score = -1
            if kind == "prop":
                if text == "prop":
                    score = 4
                elif "prop" in obj_name:
                    score = 3
                elif text.startswith("prop"):
                    score = 2
            else:  # settings: "Convert All" first, then OK
                if "convert" in text:
                    score = 4 if "all" in text else 3
                elif "convert" in obj_name:
                    score = 2
                elif text in ("ok", "okay"):
                    score = 1
                elif "ok" in obj_name:
                    score = 1
            if score > best_score:
                best = w
                best_score = score
        except Exception:
            continue
    return best if best_score >= 0 else None


def _wf_import_fbx_visible_dialogs() -> list[Any]:
    try:
        from PySide2.QtWidgets import QApplication, QDialog, QFileDialog
    except Exception:
        return []
    app = QApplication.instance()
    if app is None:
        return []
    found = []
    for w in app.topLevelWidgets():
        try:
            if isinstance(w, QDialog) and not isinstance(w, QFileDialog) and w.isVisible():
                found.append(w)
        except Exception:
            continue
    return found


def _wf_dialog_text(dlg: Any) -> str:
    """All label text of a dialog, joined (for spotting questions like the sub-prop one)."""
    try:
        from PySide2.QtWidgets import QLabel
        parts = [(l.text() or "").strip() for l in dlg.findChildren(QLabel) if l.isVisible()]
        return " ".join(p for p in parts if p)
    except Exception:
        return ""


def open_dialog_summary() -> list[dict[str, str]]:
    """Visible CC dialogs other than the main window and the dock panels: title, text, buttons."""
    from PySide2.QtWidgets import QAbstractButton, QApplication, QDialog, QMainWindow
    out = []
    app = QApplication.instance()
    if app is None:
        return out
    for w in app.topLevelWidgets():
        try:
            if not w.isVisible() or isinstance(w, QMainWindow) or not isinstance(w, QDialog):
                continue
            title = (w.windowTitle() or "").strip()
            text = _wf_dialog_text(w)
            buttons = [_wf_import_fbx_text(b) for b in w.findChildren(QAbstractButton)
                       if b.isVisible() and _wf_import_fbx_text(b)]
            if text or buttons:
                out.append({"title": title, "text": text[:300], "buttons": ", ".join(buttons[:8])})
        except Exception:
            continue
    return out


def _wf_import_fbx_answer_subprops(state: dict) -> bool:
    """Answer CC's "break up the meshes into sub-props?" question (No by default).

    Returns True when it clicked. A multi-mesh FBX (e.g. a corset with ruffles) shows it
    after the Import Settings dialog; unanswered, the import hangs until the timeout.
    """
    from PySide2.QtCore import QMetaObject, Qt
    from PySide2.QtWidgets import QAbstractButton
    for dlg in _wf_import_fbx_visible_dialogs():
        text = _wf_dialog_text(dlg).lower()
        if "sub-prop" not in text:
            continue
        want = "yes" if state.get("split_sub_props") else "no"
        for b in dlg.findChildren(QAbstractButton):
            if b.isVisible() and _wf_import_fbx_text(b) == want:
                QMetaObject.invokeMethod(b, "click", Qt.QueuedConnection)
                state["notes"].append("Sub-props question answered: " + want)
                return True
    return False


def _wf_import_fbx_diff() -> list[dict[str, Any]]:
    before = set(_WF_IMPORT_FBX_STATE["before_ids"])
    new_items = []
    for _obj, entry in _wf_scan():
        if str(entry["id"]) in before:
            continue
        # Lights/cameras get new ids on a reload; they are not the import result.
        if entry.get("kind") in ("light", "camera"):
            continue
        new_items.append({
            "name": entry["name"],
            "id": entry["id"],
            "kind": entry["kind"],
        })
    return new_items


def _wf_import_fbx_cleanup() -> None:
    state = _WF_IMPORT_FBX_STATE
    timer = state.get("timer")
    state["timer"] = None
    if timer is not None:
        try:
            timer.stop()
        except Exception:
            pass
        try:
            timer.deleteLater()
        except Exception:
            pass
    _wf_import_fbx_remove_filter()
    # Never leave a modal dialog we opened (file / Prop / Import Settings).
    try:
        from PySide2.QtCore import QTimer
    except Exception:
        QTimer = None  # type: ignore[assignment]
    seen = set()
    for dlg in state.get("dialogs", []):
        if dlg is None or id(dlg) in seen:
            continue
        seen.add(id(dlg))
        try:
            if _wf_qt_valid(dlg) and dlg.isVisible():
                dlg.reject()
        except Exception:
            pass
    _wf_import_fbx_restore_attr()


def _wf_import_fbx_fail(message: str) -> None:
    state = _WF_IMPORT_FBX_STATE
    if state["phase"] in ("done", "error"):
        return
    state["phase"] = "error"
    state["error"] = message
    state["finished_at"] = time.time()
    state["notes"].append(message)
    _wf_import_fbx_cleanup()


def _wf_import_fbx_finish(new_items: list[dict[str, Any]]) -> None:
    state = _WF_IMPORT_FBX_STATE
    props = [item for item in new_items if item.get("kind") == "prop"]
    chosen = (props or new_items)[-1]
    state["result"] = {"item": chosen, "new_items": new_items}
    state["phase"] = "done"
    state["finished_at"] = time.time()
    state["notes"].append(f"Imported: {chosen['name']} ({chosen['kind']})")
    _wf_import_fbx_cleanup()


def wf_import_fbx_tick() -> None:
    """QTimer step of the GUI import: file -> Prop -> Convert All -> diff."""
    from PySide2.QtCore import QTimer
    from PySide2.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QLineEdit

    def _wf_qt_later_done(obj: Any, delay_ms: int = 200) -> None:
        """Defer obj.done(QDialog.Accepted); _wf_qt_later cannot pass arguments."""

        def _run() -> None:
            try:
                if _wf_qt_valid(obj):
                    obj.done(QDialog.Accepted)
            except Exception as e:
                print(f"[CC5 MCP Bridge] deferred done(Accepted) failed: {e}")

        QTimer.singleShot(delay_ms, _run)

    state = _WF_IMPORT_FBX_STATE
    if state["phase"] in ("done", "error", "idle"):
        _wf_import_fbx_cleanup()
        return
    if state.get("_last_traced_notes", 0) != len(state["notes"]):
        for note in state["notes"][state.get("_last_traced_notes", 0):]:
            _wf_import_trace("note: " + note)
        state["_last_traced_notes"] = len(state["notes"])
    if time.time() > state["deadline"]:
        phase = state["phase"]
        if phase == "file_dialog" and not state["accepted"]:
            if state["non_native_dialog"]:
                _wf_import_fbx_fail("needs GUI: import file dialog (timeout)")
            else:
                _wf_import_fbx_fail("needs GUI: native file dialog")
        elif phase == "prop_dialog":
            _wf_import_fbx_fail("needs GUI: Import Fbx Character/Prop dialog")
        elif phase == "settings_dialog":
            _wf_import_fbx_fail("needs GUI: Import Settings dialog")
        else:
            open_dialogs = [t for t in (_wf_dialog_text(d) for d in _wf_import_fbx_visible_dialogs()) if t]
            _wf_import_fbx_fail("needs GUI: imported item did not appear"
                                + (" (open dialog: " + " | ".join(open_dialogs)[:300] + ")" if open_dialogs else ""))
        return

    try:
        denied = _wf_import_fbx_denied_dialog()
        if denied:
            _wf_import_fbx_fail(f"needs GUI: unexpected dialog '{denied}' (nothing clicked)")
            return
        if _wf_import_fbx_answer_subprops(state):
            return
        if state["phase"] == "file_dialog":
            dlg = _wf_import_fbx_visible_file_dialog()
            if dlg is not None:
                if id(dlg) not in state["accepted"]:
                    if not state["non_native_dialog"]:
                        try:
                            dlg.setOption(QFileDialog.DontUseNativeDialog, True)
                        except Exception:
                            pass
                    path = state["file_path"]
                    try:
                        dlg.setDirectory(os.path.dirname(path))
                    except Exception:
                        pass
                    # selectFile alone does not reach the file-name line edit of an
                    # already-visible dialog (live 10-22), so fill the edit directly.
                    dlg.selectFile(os.path.basename(path))
                    edit = None
                    try:
                        edit = dlg.findChild(QLineEdit, "fileNameEdit")
                        if edit is None:
                            for candidate in dlg.findChildren(QLineEdit):
                                try:
                                    if candidate.isVisible():
                                        edit = candidate
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        edit = None
                    if edit is not None:
                        try:
                            edit.setText(path)
                        except Exception:
                            edit = None
                    # Click the Open / Accept button; accept() would re-validate the edit.
                    btn = None
                    btn_text = ""
                    try:
                        box = dlg.findChild(QDialogButtonBox)
                        if box is not None:
                            try:
                                btn = box.button(QDialogButtonBox.Open)
                            except Exception:
                                btn = None
                            if btn is None:
                                for candidate in box.buttons():
                                    try:
                                        if box.buttonRole(candidate) == QDialogButtonBox.AcceptRole:
                                            btn = candidate
                                            break
                                    except Exception:
                                        continue
                    except Exception:
                        btn = None
                    if btn is not None:
                        btn_text = _wf_import_fbx_text(btn)
                        _wf_qt_later(btn, "click", 200)
                    else:
                        _wf_qt_later(dlg, "accept", 200)
                    state["notes"].append(
                        f"File dialog filled: line edit {'yes' if edit is not None else 'no'}, "
                        f"button '{btn_text or 'accept()'}'"
                    )
                    state["accepted"].append(id(dlg))
                    if dlg not in state["dialogs"]:
                        state["dialogs"].append(dlg)
                    state["file_dialog_seen_at"] = time.time()
                    return
                # Same dialog still up 2.5 s after we filled it: the click did not
                # take. Record what it holds, then force done(Accepted) once.
                if (
                    not state["file_dialog_retry"]
                    and state["file_dialog_seen_at"]
                    and time.time() - state["file_dialog_seen_at"] > 2.5
                ):
                    state["file_dialog_retry"] = True
                    text = ""
                    try:
                        edit = dlg.findChild(QLineEdit, "fileNameEdit")
                        if edit is not None:
                            text = edit.text() or ""
                    except Exception:
                        text = ""
                    try:
                        selected = [str(p) for p in dlg.selectedFiles()]
                    except Exception:
                        selected = []
                    state["notes"].append(f"File dialog retry: text='{text}' selected={selected}")
                    _wf_qt_later_done(dlg)
                return
            if state["accepted"]:
                state["phase"] = "prop_dialog"
            return

        if state["phase"] == "prop_dialog":
            prop_btn = _wf_import_fbx_find_button("prop")
            if prop_btn is not None:
                for dlg in _wf_import_fbx_visible_dialogs():
                    if dlg not in state["dialogs"]:
                        state["dialogs"].append(dlg)
                state["notes"].append("Prop button clicked")
                _wf_qt_later(prop_btn, "click", 100)
                state["phase"] = "settings_dialog"
                return
            # Some FBX builds go straight to Import Settings.
            convert_btn = _wf_import_fbx_find_button("settings")
            if convert_btn is not None:
                for dlg in _wf_import_fbx_visible_dialogs():
                    if dlg not in state["dialogs"]:
                        state["dialogs"].append(dlg)
                state["notes"].append("No Prop choice; Convert clicked")
                _wf_qt_later(convert_btn, "click", 100)
                state["phase"] = "settling"
            return

        if state["phase"] == "settings_dialog":
            convert_btn = _wf_import_fbx_find_button("settings")
            if convert_btn is not None:
                for dlg in _wf_import_fbx_visible_dialogs():
                    if dlg not in state["dialogs"]:
                        state["dialogs"].append(dlg)
                state["notes"].append("Import Settings: Convert clicked")
                _wf_qt_later(convert_btn, "click", 100)
                state["phase"] = "settling"
            return

        if state["phase"] == "settling":
            new_items = _wf_import_fbx_diff()
            if new_items and not _wf_import_fbx_visible_dialogs():
                _wf_import_fbx_finish(new_items)
    except Exception as e:
        _wf_import_fbx_fail(f"import_fbx tick failed: {e}")


def wf_import_fbx_begin(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/import_fbx: start CC5's own File > Import GUI flow, no mouse.

    Async: this arms a QTimer state machine and triggers the menu action; poll
    GET /workflow/import_fbx/status for progress and the new prop.
    """
    params = _wf_params(body, kwargs)
    try:
        state = _WF_IMPORT_FBX_STATE
        if state["phase"] not in ("idle", "done", "error"):
            return {
                "success": False,
                "error": f"An import is already running (phase {state['phase']}). Poll /workflow/import_fbx/status.",
            }
        file_path = os.path.abspath((params.get("file_path") or "").strip())
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        path_error = _validate_path(file_path, {".fbx", ".obj"})
        if path_error:
            return {"success": False, "error": path_error}
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        action = _wf_import_fbx_find_action()
        if action is None:
            return {"success": False, "error": "needs GUI: File > Import menu action not found"}

        from PySide2.QtCore import QTimer

        now = time.time()
        state.update({
            "phase": "file_dialog",
            "split_sub_props": bool(params.get("split_sub_props", False)),
            "file_path": file_path,
            "error": "",
            "notes": [],
            "before_ids": [str(entry["id"]) for _obj, entry in _wf_scan()],
            "result": None,
            "started_at": now,
            "finished_at": 0.0,
            "deadline": now + _WF_IMPORT_FBX_TIMEOUT,
            "timer": None,
            "dialogs": [],
            "accepted": [],
            "file_dialog_seen_at": 0.0,
            "file_dialog_retry": False,
            "non_native_dialog": False,
            "prior_attr": None,
            "prior_attr_set": False,
            "steps": {},
        })
        state["non_native_dialog"] = _wf_import_fbx_force_non_native()
        # The app-wide event filter that filled the dialog on Show crashed Qt5Widgets
        # on 10-22; the 200 ms timer below fills it instead.

        timer = QTimer()
        timer.setInterval(200)
        timer.timeout.connect(wf_import_fbx_tick)
        timer.start()
        state["timer"] = timer
        state["notes"].append(f"Menu scheduled: {action.text()}")
        try:
            parent_menu = action.parentWidget()
            parent_title = parent_menu.title() if hasattr(parent_menu, "title") else type(parent_menu).__name__
        except Exception:
            parent_title = "?"
        _wf_import_trace(f"begin {file_path} action='{action.text()}' in '{parent_title}'")
        _wf_qt_later(action, "trigger", 50)

        return {
            "success": True,
            "phase": "file_dialog",
            "file_path": file_path,
            "action_text": action.text(),
            "non_native_dialog": state["non_native_dialog"],
            "poll_endpoint": "/workflow/import_fbx/status",
            "timeout_seconds": _WF_IMPORT_FBX_TIMEOUT,
        }
    except Exception as e:
        _wf_import_fbx_fail(f"import_fbx begin failed: {e}")
        return {"success": False, "error": str(e)}


def wf_import_fbx(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/import_fbx (alias for wf_import_fbx_begin)."""
    return wf_import_fbx_begin(body, **kwargs)


def wf_import_fbx_status(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/import_fbx/status: progress or the imported prop."""
    _wf_params(body, kwargs)  # status takes no parameters; keep the body shape uniform
    state = _WF_IMPORT_FBX_STATE
    payload: dict[str, Any] = {
        "success": state["phase"] != "error",
        "phase": state["phase"],
        "file_path": state["file_path"],
        "error": state["error"],
        "notes": list(state["notes"]),
        "started_at": state["started_at"],
        "finished_at": state["finished_at"],
        "non_native_dialog": state["non_native_dialog"],
    }
    if state["result"]:
        payload["item"] = state["result"]["item"]
        payload["new_items"] = state["result"]["new_items"]
    return payload


def wf_attach_to_bone(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/attach: parent/link an item to a skin bone."""
    params = _wf_params(body, kwargs)
    try:
        bone_name = (params.get("bone_name") or "").strip()
        if not bone_name:
            return {"success": False, "error": "bone_name is required"}
        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error

        avatar = _wf_owner_avatar(obj) or get_first_avatar()
        if not avatar:
            return {"success": False, "error": "No avatar in scene (needed for the skeleton)"}
        skeleton = None
        try:
            skeleton = avatar.GetSkeletonComponent()
        except Exception as e:
            return {"success": False, "error": f"GetSkeletonComponent failed: {e}"}
        if skeleton is None:
            return {"success": False, "error": "Avatar has no skeleton component"}

        bone_by_name: dict[str, Any] = {}
        try:
            bones = skeleton.GetSkinBones() or []
        except Exception as e:
            return {"success": False, "error": f"GetSkinBones failed: {e}"}
        for bone in bones:
            try:
                bone_by_name[bone.GetName()] = bone
            except Exception:
                continue

        target = bone_by_name.get(bone_name)
        if target is None:
            lowered = bone_name.lower()
            hits = [name for name in bone_by_name if lowered in name.lower()]
            candidates = hits or list(bone_by_name)
            return {
                "success": False,
                "error": f"Unknown bone: {bone_name}",
                "bones": candidates[:40],
            }

        RLPy.RGlobal.BeginAction("wf_attach_to_bone")
        try:
            attached = False
            last_error: Exception | None = None
            # LinkTo(*args) is undocumented: try the plausible arities in order.
            attempts = (
                lambda: obj.LinkTo(target),
                lambda: obj.LinkTo(RLPy.RGlobal.GetTime(), target),
                lambda: obj.SetParent(target),
            )
            for attempt in attempts:
                try:
                    attempt()
                    attached = True
                    break
                except Exception as exc:
                    last_error = exc
            if not attached:
                raise last_error or RuntimeError("No attach method succeeded")
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "name": _wf_obj_name(obj), "bone": bone_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_transfer_skin_weights(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/transfer_weights."""
    params = _wf_params(body, kwargs)
    try:
        key = (params.get("template") or "default").strip().lower()
        template = _WF_TRANSFER_TEMPLATES.get(key)
        if template is None:
            return {
                "success": False,
                "error": (
                    f"Unknown template: {params.get('template')}. "
                    f"Valid: {', '.join(sorted(_WF_TRANSFER_TEMPLATES))}"
                ),
            }
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        if not hasattr(obj, "TransferSkinWeight"):
            return {
                "success": False,
                "error": f"A {kind} item cannot transfer skin weights",
            }

        if key == "shoes":
            avatar = _wf_owner_avatar(obj) or get_first_avatar()
            existing = _wf_shoes_items(avatar)
            if existing:
                if not bool(params.get("replace")):
                    names = ", ".join(_wf_obj_name(item) for item in existing)
                    return {
                        "success": False,
                        "error": (
                            f"Avatar already has a shoes item ({names}); "
                            'pass "replace": true to remove it first'
                        ),
                    }
                RLPy.RGlobal.BeginAction("wf_transfer_skin_weights_replace_shoes")
                try:
                    for item in existing:
                        RLPy.RScene.RemoveObject(item)
                finally:
                    RLPy.RGlobal.EndAction()

        RLPy.RGlobal.BeginAction("wf_transfer_skin_weights")
        try:
            obj.TransferSkinWeight(template)
            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()

        try:
            kind_after = _wf_kind_of(obj)
        except Exception:
            kind_after = kind
        return {
            "success": True,
            "name": _wf_obj_name(obj),
            "template": key,
            "kind_after": kind_after,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_convert_to_hair(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/convert_hair."""
    params = _wf_params(body, kwargs)
    try:
        key = (params.get("template") or "").strip().lower()
        if key not in _WF_HAIR_ENUM_NAMES:
            return {
                "success": False,
                "error": (
                    f"Unknown template: {params.get('template')}. "
                    f"Valid: {', '.join(sorted(_WF_HAIR_ENUM_NAMES))}"
                ),
            }
        enum_name, is_face_hair = _WF_HAIR_ENUM_NAMES[key]
        if enum_name is None:
            return {
                "success": False,
                "error": (
                    f"needs GUI: no EHairType_/EFaceHairType_ constant for '{key}' "
                    "eyelashes is exposed in this CC5 build"
                ),
            }
        hair_enum = getattr(RLPy, enum_name, None)
        if hair_enum is None:
            return {
                "success": False,
                "error": f"{enum_name} is not available in this CC5 build",
            }

        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        if is_face_hair:
            if not hasattr(obj, "ConvertToFaceHair"):
                return {
                    "success": False,
                    "error": f"A {kind} item cannot convert to face hair",
                }
            convert = obj.ConvertToFaceHair
        else:
            if not hasattr(obj, "ConvertToHair"):
                return {"success": False, "error": f"A {kind} item cannot convert to hair"}
            convert = obj.ConvertToHair

        RLPy.RGlobal.BeginAction("wf_convert_to_hair")
        try:
            convert(hair_enum)
            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "name": _wf_obj_name(obj), "template": key}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_cloth_to_accessory(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/cloth_to_accessory."""
    params = _wf_params(body, kwargs)
    try:
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        if not hasattr(obj, "ConvertToAccessory"):
            return {
                "success": False,
                "error": f"A {kind} item cannot convert to an accessory (needs cloth)",
            }
        keep_shape = bool(params.get("keep_current_shape", True))
        RLPy.RGlobal.BeginAction("wf_cloth_to_accessory")
        try:
            obj.ConvertToAccessory(keep_shape)
            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "name": _wf_obj_name(obj)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_conform_cloth(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/conform."""
    params = _wf_params(body, kwargs)
    try:
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        if not (hasattr(obj, "SetClothConformValue") and hasattr(obj, "GetClothConformValue")):
            return {"success": False, "error": f"A {kind} item has no cloth conform values"}

        try:
            iterations = int(params.get("iterations", 1))
        except (TypeError, ValueError):
            return {"success": False, "error": "iterations must be an integer 1..10"}
        iterations = max(1, min(10, iterations))

        raw_values = params.get("values") or {}
        if not isinstance(raw_values, dict):
            return {
                "success": False,
                "error": 'values must be an object of {"<conform key>": number}',
            }
        values: dict[str, float] = {}
        for key, raw in raw_values.items():
            if not isinstance(key, str) or not key:
                return {"success": False, "error": "conform keys must be non-empty strings"}
            try:
                values[key] = float(raw)
            except (TypeError, ValueError):
                return {"success": False, "error": f"Conform value for {key!r} is not a number"}

        # The conform key strings are undocumented: probe the CC5 Conform panel
        # labels and their lower_snake variants, and keep the ones that read a number.
        available: list[dict[str, Any]] = []
        working: dict[str, str] = {}
        for candidate in _wf_conform_candidates():
            try:
                raw_value = obj.GetClothConformValue(candidate)
            except Exception:
                continue
            raw_value = _wf_jsonable(raw_value)
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                continue
            available.append({"key": candidate, "value": raw_value})
            working.setdefault(_wf_conform_norm(candidate), candidate)

        applied: dict[str, float] = {}
        skipped: dict[str, str] = {}
        for key, value in values.items():
            actual = working.get(_wf_conform_norm(key))
            if actual is None:
                skipped[key] = "key does not read a number via GetClothConformValue"
            else:
                applied[actual] = value

        before = {key: _wf_conform_get(obj, key) for key in applied}
        RLPy.RGlobal.BeginAction("wf_conform_cloth")
        try:
            for key, value in applied.items():
                obj.SetClothConformValue(key, value)
            for _ in range(iterations):
                obj.CalculateCollision()
            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()
        after = {key: _wf_conform_get(obj, key) for key in applied}

        result: dict[str, Any] = {
            "success": True,
            "name": _wf_obj_name(obj),
            "before": before,
            "after": after,
            "available_keys": available,
            "applied_keys": sorted(applied),
            "skipped_values": skipped,
        }
        if not available:
            result["warning"] = "no conform key read a number via GetClothConformValue"
        elif values and not applied:
            result["warning"] = "none of the requested values matched a readable conform key"
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wf_find_skin_bone(avatar: Any, name: str) -> Any:
    """Skin bone of the avatar with exactly this name, or None."""
    skeleton = avatar.GetSkeletonComponent()
    for bone in skeleton.GetSkinBones() or []:
        try:
            if bone.GetName() == name:
                return bone
        except Exception:
            continue
    return None


def _wf_bone_rotation_deg(block: Any, time: Any) -> list[float]:
    out = []
    for axis in "XYZ":
        value = block.GetData("Rotation/Rotation" + axis, time)
        out.append(round(math.degrees(value.ToFloat()), 4))
    return out


def wf_bone_rotation(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/bone/rotation: read, and optionally set, bone local rotations at frame 0.

    Body: {"bones": {"CC_Base_L_Foot": [x, y, z] | null, ...}} in degrees. null only reads.
    This is the pose CC's shoe guide uses to fit feet to high-heel shoes (rotate Foot/ToeBase
    at frame 0, then transfer skin weights).
    """
    params = _wf_params(body, kwargs)
    try:
        bones = params.get("bones")
        if not isinstance(bones, dict) or not bones:
            return {"success": False, "error": "bones must be an object of bone name -> [x,y,z] or null"}
        parsed: dict[str, list[float] | None] = {}
        for name, rot in bones.items():
            if rot is None:
                parsed[str(name)] = None
                continue
            if not isinstance(rot, (list, tuple)) or len(rot) != 3:
                return {"success": False, "error": f"{name}: rotation must be 3 numbers (degrees)"}
            try:
                parsed[str(name)] = [float(v) for v in rot]
            except (TypeError, ValueError):
                return {"success": False, "error": f"{name}: rotation must be 3 numbers (degrees)"}
        avatar = get_first_avatar()
        if avatar is None:
            return {"success": False, "error": "No avatar in the scene"}
        time = RLPy.RTime.FromValue(0)
        result: dict[str, Any] = {}
        missing = [n for n in parsed if _wf_find_skin_bone(avatar, n) is None]
        if missing:
            return {"success": False, "error": "Unknown bone(s): " + ", ".join(missing)}
        skeleton = avatar.GetSkeletonComponent()
        if skeleton.GetClipCount() == 0:
            skeleton.AddClip(time)
        clip = skeleton.GetClip(0)
        RLPy.RGlobal.BeginAction("wf_bone_rotation")
        try:
            for name, rot in parsed.items():
                block = clip.GetControl("Layer", _wf_find_skin_bone(avatar, name)).GetDataBlock()
                before = _wf_bone_rotation_deg(block, time)
                if rot is not None:
                    for axis, deg in zip("XYZ", rot):
                        block.SetData("Rotation/Rotation" + axis, time, RLPy.RVariant(math.radians(deg)))
                result[name] = {"before": before, "after": _wf_bone_rotation_deg(block, time)}
        finally:
            RLPy.RGlobal.EndAction()
        try:
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Transform)
        except Exception:
            pass
        return {"success": True, "frame": 0, "bones": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- High Heels (GUI only: no RLPy API for the heel height) ---

def _wf_high_heels_dialog() -> Any:
    """Visible top-level dialog titled "High Heels", or None.

    CC5 opens it from the Modify > Attribute button of the same name. It has no
    objectName and no RLPy handle, so the window title is the only stable selector.
    """
    try:
        from PySide2.QtWidgets import QApplication
    except Exception:
        return None
    app = QApplication.instance()
    if app is None:
        return None
    for w in app.topLevelWidgets():
        try:
            if w.isVisible() and (w.windowTitle() or "").strip().lower() == "high heels":
                return w
        except Exception:
            continue
    return None


def _wf_high_heels_spins(dlg: Any) -> list[Any]:
    """Spin boxes of the High Heels dialog (QDoubleSpinBox is not a QSpinBox)."""
    try:
        from PySide2.QtWidgets import QDoubleSpinBox, QSpinBox
    except Exception:
        return []
    found: list[Any] = []
    for klass in (QSpinBox, QDoubleSpinBox):
        try:
            found.extend(dlg.findChildren(klass))
        except Exception:
            continue
    return found


def _wf_high_heels_read(dlg: Any) -> dict[str, Any]:
    """Spin-box and slider readings of the High Heels dialog."""
    try:
        from PySide2.QtWidgets import QSlider
    except Exception:
        return {"spin_boxes": [], "slider": None}
    spins: list[dict[str, Any]] = []
    for spin in _wf_high_heels_spins(dlg):
        try:
            spins.append({
                "value": spin.value(),
                "minimum": spin.minimum(),
                "maximum": spin.maximum(),
            })
        except Exception:
            continue
    slider = None
    try:
        sliders = dlg.findChildren(QSlider)
        if sliders:
            first = sliders[0]
            slider = {
                "value": first.value(),
                "minimum": first.minimum(),
                "maximum": first.maximum(),
            }
    except Exception:
        slider = None
    return {"spin_boxes": spins, "slider": slider}


def wf_high_heels_open(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/high_heels/open: select the shoes, click Modify > Attribute > High Heels.

    Body: {"item_name"|"item_id"} for the shoes. The dialog appears a moment after the
    click; poll /workflow/high_heels/state, then drive /workflow/high_heels/set.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtWidgets import QAbstractButton, QApplication, QMainWindow

        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        RLPy.RScene.ClearSelectObjects()
        RLPy.RScene.SelectObject(obj)

        not_visible = {
            "success": False,
            "error": "High Heels button not visible (open Modify > Attribute with the shoes selected)",
        }
        app = QApplication.instance()
        if app is None:
            return not_visible
        main_win = None
        for w in app.topLevelWidgets():
            try:
                if isinstance(w, QMainWindow) and w.isVisible():
                    main_win = w
                    break
            except Exception:
                continue
        if main_win is None:
            main_win = _mixer_find_main_window()
        if main_win is None:
            return not_visible

        btn = None
        for candidate in main_win.findChildren(QAbstractButton):
            try:
                if not candidate.isVisible() or _wf_import_fbx_text(candidate) != "high heels":
                    continue
                # The "High Heels" dialog carries a button of the same name; only the
                # Modify > Attribute one is a child of the QMainWindow, never a dialog.
                win = candidate.window()
                if not isinstance(win, QMainWindow) or win is not main_win:
                    continue
                btn = candidate
                break
            except Exception:
                continue
        if btn is None:
            return not_visible

        _wf_qt_later(btn, "click", 150)
        return {"success": True, "clicked": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_high_heels_state(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/high_heels/state: heel-height spin box and slider of the open dialog."""
    try:
        dlg = _wf_high_heels_dialog()
        if dlg is None:
            return {"success": True, "open": False}
        return {"success": True, "open": True, **_wf_high_heels_read(dlg)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_high_heels_set(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/high_heels/set: drive the High Heels dialog, then Ok or Cancel.

    Body: {"value": number, "press": "ok" | "cancel" | null}. The value is clamped to the
    spin box range; only buttons inside the "High Heels" dialog are ever clicked.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtWidgets import QAbstractButton, QSpinBox

        raw_value = params.get("value")
        if raw_value is None:
            return {"success": False, "error": "value is required"}
        try:
            wanted = float(raw_value)
        except (TypeError, ValueError):
            return {"success": False, "error": "value must be a number"}
        press = params.get("press")
        if press is not None:
            press = str(press).strip().lower() or None
        if press is not None and press not in ("ok", "cancel"):
            return {"success": False, "error": 'press must be "ok", "cancel" or null'}

        dlg = _wf_high_heels_dialog()
        if dlg is None:
            return {
                "success": False,
                "error": 'The "High Heels" dialog is not open (run /workflow/high_heels/open first)',
            }

        spins = _wf_high_heels_spins(dlg)
        if not spins:
            return {"success": False, "error": 'The "High Heels" dialog has no spin box'}
        spin = spins[0]
        try:
            low, high = float(spin.minimum()), float(spin.maximum())
            clamped = max(low, min(high, wanted))
            # QSpinBox takes ints only; QDoubleSpinBox takes the float as is.
            spin.setValue(int(round(clamped)) if isinstance(spin, QSpinBox) else clamped)
        except Exception as e:
            return {"success": False, "error": f"could not set the heel value: {e}"}

        # The panel applies the height on editingFinished (slider drag end) and Ok;
        # setValue alone can leave the result untouched.
        try:
            spin.editingFinished.emit()
        except Exception:
            pass

        set_value = spin.value()
        pressed = None
        if press:
            btn = None
            for candidate in dlg.findChildren(QAbstractButton):
                try:
                    if _wf_import_fbx_text(candidate) == press:
                        btn = candidate
                        break
                except Exception:
                    continue
            if btn is None:
                return {
                    "success": False,
                    "error": f'"{press}" button not found in the "High Heels" dialog',
                    "value": set_value,
                    "state": _wf_high_heels_read(dlg),
                }
            _wf_qt_later(btn, "click", 200)
            pressed = press

        return {
            "success": True,
            "value": set_value,
            "clamped": set_value != wanted,
            "pressed": pressed,
            "state": _wf_high_heels_read(dlg),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_menu_find(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/menu/find: list main-window menu actions whose text contains `text` (read-only)."""
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtWidgets import QApplication, QMainWindow
        needle = (params.get("text") or "").strip().lower()
        app = QApplication.instance()
        main_win = next((w for w in app.topLevelWidgets() if isinstance(w, QMainWindow) and w.isVisible()), None)
        if main_win is None:
            return {"success": False, "error": "main window not found"}
        found: list[dict[str, Any]] = []

        def _walk(menu: Any, path: list[str], depth: int = 0) -> None:
            if menu is None or depth > 6:
                return
            for act in menu.actions():
                text = (act.text() or "").replace("&", "")
                sub = act.menu()
                if sub is not None:
                    _walk(sub, path + [text], depth + 1)
                    continue
                if text and (not needle or needle in text.lower()):
                    found.append({"path": " > ".join(path + [text]), "enabled": act.isEnabled(),
                                  "checkable": act.isCheckable(), "checked": act.isChecked()})

        _walk(main_win.menuBar(), [])
        return {"success": True, "count": len(found), "actions": found[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


_WF_MENU_DENY = ("exit", "delete", "remove", "game base", "convert", "buy", "pack", "purchase",
                 "new project", "open", "reset", "clear")


def wf_menu_trigger(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/menu/trigger: trigger one main-window menu action by its exact path.

    Body: {"path": "Character > Pose Offset"}. Actions whose text contains a word from
    _WF_MENU_DENY are refused, so destructive or purchase items are never fired from here.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtWidgets import QApplication, QMainWindow
        want = [p.strip().lower() for p in (params.get("path") or "").split(">") if p.strip()]
        if not want:
            return {"success": False, "error": "path is required, e.g. 'Character > Pose Offset'"}
        if any(word in want[-1] for word in _WF_MENU_DENY):
            return {"success": False, "error": f"refused: '{want[-1]}' is on the deny list"}
        app = QApplication.instance()
        main_win = next((w for w in app.topLevelWidgets() if isinstance(w, QMainWindow) and w.isVisible()), None)
        if main_win is None:
            return {"success": False, "error": "main window not found"}
        menu = main_win.menuBar()
        action = None
        for depth, name in enumerate(want):
            match = None
            for act in menu.actions():
                if (act.text() or "").replace("&", "").strip().lower() == name:
                    match = act
                    break
            if match is None:
                return {"success": False, "error": f"menu item not found: {name}"}
            if depth == len(want) - 1:
                action = match
            else:
                menu = match.menu()
                if menu is None:
                    return {"success": False, "error": f"not a submenu: {name}"}
        if action is None or action.menu() is not None:
            return {"success": False, "error": "path does not end at an action"}
        _wf_qt_later(action, "trigger", 50)
        return {"success": True, "triggered": " > ".join(want)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_create_morph_slider(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/morph/create: make a morph slider from a source and a target OBJ.

    Body: {"name", "target_obj", "source_obj" (optional; else the current shape),
    "category": "head"|"body", "axis": "yup"|"zup", "min": 0, "max": 1,
    "output": path of the slider file to write, "apply": true}.
    The same thing as Create > Morph Slider Editor with an OBJ target.
    """
    params = _wf_params(body, kwargs)
    try:
        name = (params.get("name") or "").strip()
        target = os.path.abspath((params.get("target_obj") or "").strip())
        if not name or not os.path.isfile(target):
            return {"success": False, "error": "name and an existing target_obj are required"}
        source = (params.get("source_obj") or "").strip()
        output = os.path.abspath((params.get("output") or "").strip() or
                                 os.path.splitext(target)[0] + "_slider.ccSlider")
        avatar = get_first_avatar()
        if avatar is None:
            return {"success": False, "error": "No avatar in the scene"}
        st = RLPy.RMorphSliderSetting()
        st.SetMorphName(name)
        st.SetCategory(RLPy.ESetCategory_Head if (params.get("category") or "head") == "head"
                       else RLPy.ESetCategory_Body)
        st.SetMorphValueRange(float(params.get("min", 0.0)), float(params.get("max", 1.0)))
        if params.get("slider_path"):
            st.SetSliderPath(str(params["slider_path"]))
        if source:
            st.SetSourceBaseType(RLPy.EChooseBase_File)
            st.SetSourceFilePath(os.path.abspath(source))
        else:
            st.SetSourceBaseType(RLPy.EChooseBase_Current)
        st.SetTargetFilePath(target)
        st.SetAxisSettingForObj(RLPy.EAxisSetting_ZUp if (params.get("axis") or "zup") == "zup"
                                else RLPy.EAxisSetting_YUp)
        st.SetAdjustBonesToFitMorph(False)
        st.SetAutoApplyToCurrentCharacter(bool(params.get("apply", True)))
        RLPy.RGlobal.BeginAction("wf_create_morph_slider")
        try:
            status = avatar.GetAvatarShapingComponent().CreateSlider(st, output)
        finally:
            RLPy.RGlobal.EndAction()
        # CreateSlider returns [RStatus, written path]
        st_obj = status[0] if isinstance(status, (list, tuple)) and status else status
        written = status[1] if isinstance(status, (list, tuple)) and len(status) > 1 else output
        ok, code = True, None
        try:
            ok = not st_obj.IsError()
            code = st_obj.GetStatusCode()
        except Exception:
            pass
        # Look for the new slider among the shaping morphs, by display name
        found = []
        try:
            comp = avatar.GetAvatarShapingComponent()
            for cat in comp.GetShapingMorphCatergoryNames():
                for mid, disp in zip(comp.GetShapingMorphIDs(cat), comp.GetShapingMorphDisplayNames(cat)):
                    if disp == name:
                        found.append({"category": cat, "id": mid,
                                      "weight": comp.GetShapingMorphWeight(mid)})
        except Exception as e:
            found = [{"error": str(e)}]
        file_written = os.path.isfile(str(written))
        return {"success": ok and (file_written or bool(found)), "name": name,
                "output": str(written), "status_code": str(code),
                "file_written": file_written, "found": found}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_load_texture(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/material/load_texture: load an image into one texture channel.

    Body: {"mesh": "CC_Base_Body", "material": "Std_Skin_Head",
    "channel": "diffuse"|"normal"|"roughness"|"ao"|..., "path": image file}.
    """
    params = _wf_params(body, kwargs)
    try:
        mesh = (params.get("mesh") or "").strip()
        mat = (params.get("material") or "").strip()
        path = os.path.abspath((params.get("path") or "").strip())
        chan = (params.get("channel") or "diffuse").strip().lower()
        if not mesh or not mat or not os.path.isfile(path):
            return {"success": False, "error": "mesh, material and an existing path are required"}
        names = {"diffuse": "Diffuse", "normal": "Normal", "roughness": "Roughness",
                 "ao": "AmbientOcclusion", "metallic": "Metallic", "opacity": "Opacity",
                 "specular": "Specular", "glow": "Glow", "bump": "Bump"}
        if chan not in names:
            return {"success": False, "error": "unknown channel: %s" % chan}
        enum = getattr(RLPy, "EMaterialTextureChannel_" + names[chan])
        avatar = get_first_avatar()
        if avatar is None:
            return {"success": False, "error": "No avatar in the scene"}
        comp = avatar.GetMaterialComponent()
        if mat not in list(comp.GetMaterialNames(mesh)):
            return {"success": False, "error": "material %s not on mesh %s" % (mat, mesh)}
        RLPy.RGlobal.BeginAction("wf_load_texture")
        try:
            status = comp.LoadImageToTexture(mesh, mat, enum, path)
        finally:
            RLPy.RGlobal.EndAction()
        ok = True
        try:
            ok = not status.IsError()
        except Exception:
            pass
        return {"success": ok, "mesh": mesh, "material": mat, "channel": chan, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wf_morph_editor() -> Any:
    """The open, visible "Morph Slider Editor" window, else None."""
    from PySide2.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return None
    for w in app.topLevelWidgets():
        try:
            if w.isVisible() and _wf_dialog_title(w) == "morph slider editor":
                return w
        except Exception:
            continue
    return None


def _wf_morph_editor_parts(dlg: Any) -> dict[str, list]:
    """Line edits, radio buttons, check boxes and push buttons, top to bottom."""
    from PySide2.QtWidgets import QCheckBox, QLineEdit, QPushButton, QRadioButton

    def ordered(cls: Any) -> list:
        items = [w for w in dlg.findChildren(cls) if w.isVisible()]
        return sorted(items, key=lambda w: (w.mapTo(dlg, w.rect().topLeft()).y(),
                                            w.mapTo(dlg, w.rect().topLeft()).x()))
    return {"edits": ordered(QLineEdit), "radios": ordered(QRadioButton),
            "checks": ordered(QCheckBox), "buttons": ordered(QPushButton)}


def _wf_morph_editor_all_buttons(dlg: Any) -> list:
    """Every visible button of the panel with its place, class and tool tip (for browse)."""
    from PySide2.QtWidgets import QAbstractButton
    out = []
    for b in dlg.findChildren(QAbstractButton):
        try:
            if not b.isVisible():
                continue
            pos = b.mapTo(dlg, b.rect().topLeft())
            out.append({"x": pos.x(), "y": pos.y(), "cls": type(b).__name__,
                        "name": b.objectName(), "text": b.text(), "tip": b.toolTip(),
                        "enabled": b.isEnabled()})
        except Exception:
            continue
    return sorted(out, key=lambda d: (d["y"], d["x"]))


def wf_morph_editor(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/morph/editor: read or fill Create > Morph Slider Editor from inside CC.

    Body: {"action": "inspect"} lists the widgets. {"action": "fill", "name",
    "source_obj" (optional; else Current Morph), "target_obj", "axis": "zup"|"yup",
    "auto_apply": true, "press": "ok"|null} fills the panel; only the panel's own
    widgets are touched (no keyboard input reaches the main window).
    """
    params = _wf_params(body, kwargs)
    try:
        dlg = _wf_morph_editor()
        if dlg is None:
            return {"success": False, "error": "Morph Slider Editor is not open"}
        parts = _wf_morph_editor_parts(dlg)
        action = (params.get("action") or "inspect").strip().lower()

        def y(w: Any) -> int:
            return int(w.mapTo(dlg, w.rect().topLeft()).y())

        if action == "inspect":
            return {"success": True,
                    "edits": [{"y": y(w), "text": w.text(), "read_only": w.isReadOnly(),
                               "enabled": w.isEnabled()} for w in parts["edits"]],
                    "radios": [{"y": y(w), "text": w.text(), "checked": w.isChecked(),
                                "enabled": w.isEnabled()} for w in parts["radios"]],
                    "checks": [{"y": y(w), "text": w.text(), "checked": w.isChecked()}
                               for w in parts["checks"]],
                    "buttons": [{"y": y(w), "text": w.text()} for w in parts["buttons"]],
                    "all_buttons": _wf_morph_editor_all_buttons(dlg)}
        if action == "browse":
            # Click the "Open Path" button of the source or target box (by object name).
            # The file dialog opens modally a moment later; fill it with
            # /workflow/dialog/file_fill (set /workflow/dialog/native false first).
            from PySide2.QtWidgets import QToolButton
            which = "Source" if (params.get("which") or "target") == "source" else "Target"
            btn = dlg.findChild(QToolButton, "qt%sOpenFilePathToolButton" % which)
            if btn is None or not btn.isVisible():
                return {"success": False, "error": "browse button not found"}
            if not btn.isEnabled():
                return {"success": False, "error": "browse button is disabled"}
            # Queued: the click opens a modal dialog, which must not run inside this call.
            from PySide2.QtCore import QMetaObject, Qt
            ok = QMetaObject.invokeMethod(btn, "click", Qt.QueuedConnection)
            _wf_import_trace("queued click on browse %s: %s" % (which.lower(), ok))
            return {"success": bool(ok), "clicked": "browse " + which.lower()}
        if action != "fill":
            return {"success": False, "error": "action must be inspect, browse or fill"}

        edits, radios = parts["edits"], parts["radios"]
        files = [r for r in radios if _wf_import_fbx_text(r) == "file"]
        current = [r for r in radios if _wf_import_fbx_text(r) == "current morph"]
        if len(files) < 2 or len(current) < 2 or len(edits) < 4:
            return {"success": False, "error": "unexpected panel layout (run inspect)"}
        name_edit = edits[0]
        name_edit.setText(str(params.get("name") or "Custom Morph"))
        name_edit.editingFinished.emit()
        source = (params.get("source_obj") or "").strip()
        target = os.path.abspath((params.get("target_obj") or "").strip())
        if not os.path.isfile(target):
            return {"success": False, "error": "target_obj not found"}

        def path_edit_below(radio: Any) -> Any:
            below = [e for e in edits if y(e) > y(radio)]
            return below[0] if below else None

        if source:
            files[0].click()
            e = path_edit_below(files[0])
            e.setText(os.path.abspath(source)); e.editingFinished.emit()
        else:
            current[0].click()
        files[1].click()
        after = [x for x in edits if y(x) > y(files[1])]
        after[0].setText(target); after[0].editingFinished.emit()
        # the target's .ObjKey (checksum) sits in the next path box
        key = (params.get("objkey") or "").strip() or os.path.splitext(target)[0] + ".ObjKey"
        if len(after) > 1 and os.path.isfile(key):
            after[1].setText(os.path.abspath(key)); after[1].editingFinished.emit()
        axis = "z-up" if (params.get("axis") or "zup") == "zup" else "y-up"
        for r in radios:
            if _wf_import_fbx_text(r) == axis:
                r.click()
        want_apply = bool(params.get("auto_apply", True))
        for c in parts["checks"]:
            if "auto apply" in _wf_import_fbx_text(c) and c.isChecked() != want_apply:
                c.click()
        state = wf_morph_editor({"action": "inspect"})
        if (params.get("press") or "").lower() == "ok":
            ok = [b for b in parts["buttons"] if _wf_import_fbx_text(b) == "ok"]
            if not ok:
                return {"success": False, "error": "no OK button", "state": state}
            from PySide2.QtCore import QMetaObject, Qt
            state["pressed"] = "ok" if QMetaObject.invokeMethod(ok[0], "click", Qt.QueuedConnection) else "failed"
        return state
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_file_dialog_native(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/dialog/native: {"enable": false} makes CC open Qt's own file dialogs.

    Qt's own dialog has a file-name line edit that /workflow/dialog/file_fill can fill;
    the Windows one only takes "/"-joined paths, which Windows rejects. Set it back to
    true when done.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtCore import Qt
        from PySide2.QtWidgets import QApplication
        app = QApplication.instance()
        if "enable" in params:
            app.setAttribute(Qt.AA_DontUseNativeDialogs, not bool(params["enable"]))
        return {"success": True, "native": not app.testAttribute(Qt.AA_DontUseNativeDialogs)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_file_dialog_fill(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/dialog/file_fill: fill the open Qt file dialog of CC and press Open.

    Body: {"path": file to choose, "save": false, "press": true}; "save": true allows a
    new file name in an existing folder (never an existing file). Only a QFileDialog that is already
    open is touched; nothing is typed through the keyboard.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtWidgets import QDialogButtonBox, QLineEdit
        dlg = _wf_import_fbx_visible_file_dialog()
        if dlg is None:
            return {"success": True, "open": False}
        path = os.path.abspath((params.get("path") or "").strip())
        info = {"success": True, "open": True, "title": _wf_dialog_title(dlg)}
        if not params.get("path"):
            return info
        if params.get("save"):
            if not os.path.isdir(os.path.dirname(path)):
                return {"success": False, "error": "folder not found", **info}
            if os.path.exists(path):
                return {"success": False, "error": "file exists (choose a new name)", **info}
        elif not os.path.isfile(path):
            return {"success": False, "error": "path not found", **info}
        try:
            dlg.setDirectory(os.path.dirname(path))
        except Exception:
            pass
        edit = dlg.findChild(QLineEdit, "fileNameEdit")
        if edit is not None:
            dlg.selectFile(os.path.basename(path))
            edit.setText(path)
        else:
            # A native dialog: a full path reaches Windows with "/" separators and is
            # rejected ("file name is not valid"); press its Save button by UIA.
            # setDirectory above already moved it to the folder, so give the bare name.
            dlg.selectFile(os.path.basename(path))
            info["native"] = True
        info["line_edit"] = edit is not None
        if params.get("press", True) and edit is not None:
            btn = None
            box = dlg.findChild(QDialogButtonBox)
            if box is not None:
                btn = box.button(QDialogButtonBox.Open)
                if btn is None:
                    for b in box.buttons():
                        if box.buttonRole(b) == QDialogButtonBox.AcceptRole:
                            btn = b
                            break
            # Queued calls: _wf_qt_later's timer did not fire while a modal dialog ran (10-22).
            from PySide2.QtCore import QMetaObject, Qt
            if btn is not None:
                QMetaObject.invokeMethod(btn, "click", Qt.QueuedConnection)
                info["pressed"] = _wf_import_fbx_text(btn) or "accept button"
            else:
                QMetaObject.invokeMethod(dlg, "accept", Qt.QueuedConnection)
                info["pressed"] = "accept()"
        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_timeline(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/timeline: {"action": "state"|"pause"|"set", "frame": n}.

    "pause" stops playback where it is; "set" pauses and moves to a frame, so
    captures for before/after comparisons show the same pose.
    """
    params = _wf_params(body, kwargs)
    try:
        action = (params.get("action") or "state").strip().lower()
        fps = RLPy.RGlobal.GetFps()                      # RFps: frames by index, not a number
        if action in ("pause", "set") and RLPy.RGlobal.IsPlaying():
            RLPy.RGlobal.Pause()
        if action == "set":
            RLPy.RGlobal.SetTime(fps.IndexedFrameTime(int(params.get("frame", 0))))
        now = RLPy.RGlobal.GetTime()
        return {"success": True, "playing": bool(RLPy.RGlobal.IsPlaying()),
                "time_ms": float(now.ToFloat()) if hasattr(now, "ToFloat") else None,
                "frame": int(fps.GetFrameIndex(now)),
                "end_frame": int(fps.GetFrameIndex(RLPy.RGlobal.GetEndTime()))}
    except Exception as e:
        return {"success": False, "error": str(e)}


_WF_BUTTON_DENY = ("delete", "remove", "buy", "purchase", "pack", "convert", "exit", "reset", "clear", "update")


def wf_buttons(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/buttons: list visible buttons whose tool tip / text / name contains `find`,
    or click the one with exactly that tool tip (queued), e.g. the Animation Player's Pause.

    Body: {"find": "pause"} or {"click_tip": "Pause"}. Words in _WF_BUTTON_DENY are never clicked.
    """
    params = _wf_params(body, kwargs)
    try:
        from PySide2.QtCore import QMetaObject, Qt
        from PySide2.QtWidgets import QAbstractButton, QApplication
        found = []
        for b in QApplication.instance().allWidgets():
            try:
                if not isinstance(b, QAbstractButton) or not b.isVisible():
                    continue
                tip, text, name = b.toolTip() or "", b.text() or "", b.objectName() or ""
                found.append((b, tip, text, name))
            except Exception:
                continue
        want = (params.get("click_tip") or "").strip().lower()
        if want:
            if any(w in want for w in _WF_BUTTON_DENY):
                return {"success": False, "error": "refused by the deny list"}
            hits = [f for f in found if f[1].strip().lower() == want]
            if len(hits) != 1:
                return {"success": False, "error": "%d buttons have that tool tip" % len(hits),
                        "candidates": [{"tip": h[1], "name": h[3]} for h in hits][:10]}
            ok = QMetaObject.invokeMethod(hits[0][0], "click", Qt.QueuedConnection)
            return {"success": bool(ok), "clicked": hits[0][1], "name": hits[0][3]}
        needle = (params.get("find") or "").strip().lower()
        rows = [{"tip": t, "text": x, "name": n, "window": _wf_dialog_title(b), "enabled": b.isEnabled()}
                for b, t, x, n in found if needle in (t + " " + x + " " + n).lower()]
        return {"success": True, "count": len(rows), "buttons": rows[:60]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_pivot(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/pivot: {"item_name"|"item_id", "action": "get"|"center"|"set", "position": [x,y,z]}.

    "center" moves the pivot to the middle of the item's bounding box, so the move gizmo
    shows on the item (a pivot far from the mesh puts the gizmo off screen). The mesh
    does not move.
    """
    params = _wf_params(body, kwargs)
    try:
        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        pos, ori = RLPy.RVector3(), RLPy.RVector3()   # orientation is a vector (Euler), not a quaternion
        obj.GetPivot(pos, ori)
        mx, ct, mn = RLPy.RVector3(), RLPy.RVector3(), RLPy.RVector3()
        obj.GetBounds(mx, ct, mn)
        v = lambda r: [round(r.x, 3), round(r.y, 3), round(r.z, 3)]
        out = {"success": True, "pivot": v(pos), "bounds_center": v(ct), "bounds_min": v(mn), "bounds_max": v(mx)}
        action = (params.get("action") or "get").lower()
        if action in ("center", "set"):
            if not hasattr(obj, "SetPivot"):
                return {"success": False, "error": "this item has no SetPivot (props and accessories only)", **out}
            target = ct if action == "center" else RLPy.RVector3(*[float(x) for x in params["position"]])
            RLPy.RGlobal.BeginAction("wf_pivot")
            try:
                obj.SetPivot(target, ori)
            finally:
                RLPy.RGlobal.EndAction()
            p2 = RLPy.RVector3()
            obj.GetPivot(p2, RLPy.RVector3())
            out["pivot_after"] = v(p2)
        return out
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_get_transform(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/transform/get."""
    params = _wf_params(body, kwargs)
    try:
        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        values = _wf_read_transform(obj)
        return {"success": True, "name": _wf_obj_name(obj), **values}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_set_transform(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/transform/set."""
    params = _wf_params(body, kwargs)
    try:
        obj, _kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        current = _wf_read_transform(obj)

        parsed: dict[str, list[float] | None] = {}
        for key in ("move", "rotate", "scale"):
            raw = params.get(key)
            if raw is None:
                parsed[key] = current[key]
                continue
            if not isinstance(raw, (list, tuple)) or len(raw) != 3:
                return {"success": False, "error": f"{key} must be a list of 3 numbers"}
            try:
                parsed[key] = [float(component) for component in raw]
            except (TypeError, ValueError):
                return {"success": False, "error": f"{key} must be a list of 3 numbers"}

        if any(parsed[key] is None for key in parsed):
            return {
                "success": False,
                "error": "Current transform is unreadable; pass move, rotate and scale explicitly",
            }

        # Write the values through the Transform control's data block (the documented
        # RLPy way for props). RTransform.T()/R()/S() are getters only, so building an
        # RTransform from lists fails ("RTransform_T expected at most 1 arguments", 10-22).
        given = {key: parsed[key] for key in ("move", "rotate", "scale") if params.get(key) is not None}
        if given:
            try:
                block = obj.GetControl("Transform").GetDataBlock()
                now = RLPy.RGlobal.GetTime()
                RLPy.RGlobal.BeginAction("wf_set_transform")
                try:
                    for key, prefix, conv in (("move", "Position/Position", float),
                                              ("rotate", "Rotation/Rotation", math.radians),
                                              ("scale", "Scale/Scale", lambda v: float(v) / 100.0)):
                        if key not in given:
                            continue
                        for axis, value in zip("XYZ", given[key]):
                            block.SetData(prefix + axis, now, RLPy.RVariant(conv(value)))
                finally:
                    RLPy.RGlobal.EndAction()
                try:
                    RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Transform)
                except Exception:
                    pass
                return {"success": True, "name": _wf_obj_name(obj), "method": "data block",
                        **_wf_read_transform(obj)}
            except Exception as exc:
                print(f"[CC5 MCP Bridge] data-block transform failed, trying RTransform: {exc}")

        transform, build_error = _wf_make_transform(
            parsed["move"], parsed["rotate"], parsed["scale"]
        )
        if build_error:
            return {"success": False, "error": build_error}

        # RIObject has no documented transform setter, so try, in order:
        #  1. the object's transform control (GetControl + RTransformControl.SetValue);
        #  2. an undocumented Set*Transform method if this build has one;
        #  3. mutating the RTransform returned by LocalTransform() in place.
        # The read-back below decides whether anything actually took effect.
        now = RLPy.RGlobal.GetTime()
        applied = False
        RLPy.RGlobal.BeginAction("wf_set_transform")
        try:
            get_control = getattr(obj, "GetControl", None)
            if get_control is not None:
                for key in ("Transform", "KT_Transform"):
                    try:
                        control = get_control(key)
                    except Exception:
                        control = None
                    if control is None or not hasattr(control, "SetValue"):
                        continue
                    try:
                        control.SetValue(now, transform)
                        applied = True
                        break
                    except Exception as exc:
                        print(f"[CC5 MCP Bridge] control {key} SetValue failed: {exc}")

            if not applied:
                for name in ("SetLocalTransform", "SetWorldTransform", "SetTransform"):
                    candidate = getattr(obj, name, None)
                    if candidate is None:
                        continue
                    try:
                        candidate(transform)
                        applied = True
                        break
                    except Exception as exc:
                        print(f"[CC5 MCP Bridge] {name} failed: {exc}")

            if not applied:
                try:
                    local = obj.LocalTransform()
                    for method_name, values in (
                        ("T", parsed["move"]),
                        ("R", parsed["rotate"]),
                        ("S", parsed["scale"]),
                    ):
                        vector = _wf_vector3(values)
                        if vector is not None:
                            getattr(local, method_name)(vector)
                    applied = True
                except Exception as exc:
                    print(f"[CC5 MCP Bridge] LocalTransform in-place set failed: {exc}")

            try:
                RLPy.RGlobal.ObjectModified(obj, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
            if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                RLPy.RGlobal.ForceViewportUpdate()
        finally:
            RLPy.RGlobal.EndAction()

        values = _wf_read_transform(obj)

        def _close(a, b) -> bool:
            return (
                a is not None
                and b is not None
                and len(a) == 3
                and len(b) == 3
                and all(abs(float(x) - float(y)) <= 1e-3 for x, y in zip(a, b))
            )

        if not applied or not all(
            _close(values[key], parsed[key]) for key in ("move", "rotate", "scale")
        ):
            return {
                "success": False,
                "error": (
                    "needs GUI: the transform change did not stick through the "
                    "available RLPy calls (LocalTransform/GetControl only); "
                    "change it in the CC5 UI"
                ),
                "move": values["move"],
                "rotate": values["rotate"],
                "scale": values["scale"],
            }
        return {"success": True, "name": _wf_obj_name(obj), **values}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_save_project(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/save."""
    params = _wf_params(body, kwargs)
    try:
        file_path = (params.get("file_path") or "").strip()
        if not file_path:
            file_path = _wf_current_project_path()
            if not file_path:
                return {
                    "success": False,
                    "error": (
                        "file_path is required: the current project path is not "
                        "readable through the RLPy API used here"
                    ),
                }
        path_error = _validate_path(file_path, {".ccproject"})
        if path_error:
            return {"success": False, "error": path_error}
        if os.path.basename(file_path).lower().endswith("_hs_ok.ccproject"):
            return {
                "success": False,
                "error": "Refusing to overwrite a *_hs_ok.ccProject safety copy",
            }

        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        RLPy.RGlobal.BeginAction("wf_save_project")
        try:
            saved = False
            save_error: Exception | None = None
            try:
                RLPy.RFileIO.SaveProject(file_path)
                saved = True
            except Exception as exc:
                save_error = exc
            if not saved:
                avatar = get_first_avatar()
                if avatar is not None:
                    try:
                        RLPy.RFileIO.SaveFile(
                            avatar, RLPy.ESaveFileType_Project, file_path
                        )
                        saved = True
                    except Exception as exc:
                        save_error = exc
            if not saved:
                raise save_error or RuntimeError("SaveProject failed")
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_export_obj(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/export_obj."""
    params = _wf_params(body, kwargs)
    try:
        file_path = (params.get("file_path") or "").strip()
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        path_error = _validate_path(file_path, {".obj"})
        if path_error:
            return {"success": False, "error": path_error}
        current_pose = bool(params.get("current_pose", True))
        with_materials = bool(params.get("with_materials", True))

        obj = None
        if params.get("item_name") or params.get("item_id"):
            obj, _kind, error = _wf_resolve(
                params.get("item_name"), params.get("item_id")
            )
            if error:
                return error
        if obj is None:
            obj = get_first_avatar()
        if obj is None:
            return {
                "success": False,
                "error": "No item selected and no avatar in the scene",
            }

        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        if os.path.exists(file_path):
            os.remove(file_path)

        RLPy.RGlobal.BeginAction("wf_export_obj")
        try:
            exported = False
            export_error: Exception | None = None
            # ExportObjFile(*args) is undocumented: try the plausible arities.
            for args in (
                (obj, file_path, current_pose, with_materials),
                (obj, file_path, current_pose),
                (obj, file_path),
            ):
                try:
                    RLPy.RFileIO.ExportObjFile(*args)
                except Exception as exc:
                    export_error = exc
                    continue
                if os.path.exists(file_path):
                    exported = True
                    break
            if not exported:
                raise export_error or RuntimeError(
                    f"ExportObjFile did not create {file_path}"
                )
        finally:
            RLPy.RGlobal.EndAction()
        return {
            "success": True,
            "path": file_path,
            "bytes": os.path.getsize(file_path),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_get_floor_contact(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/floor_contact/get."""
    try:
        avatar = get_first_avatar()
        if not avatar:
            return {"success": False, "error": "No avatar in scene"}
        if not hasattr(avatar, "GetFloorContactValue"):
            return {
                "success": False,
                "error": "GetFloorContactValue is not available in this CC5 build",
            }

        types = _wf_floor_contact_types()
        if not types:
            try:
                return {
                    "success": True,
                    "value": _wf_jsonable(avatar.GetFloorContactValue()),
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": (
                        "needs GUI: the floor-contact type enum (EFloorContact*) is "
                        f"not exposed through RLPy ({e})"
                    ),
                }

        values: dict[str, Any] = {}
        for name, enum in types:
            if name.endswith("_All"):
                # EFloorContactType_All is a set-only aggregate, not a channel.
                continue
            try:
                values[name] = _wf_jsonable(avatar.GetFloorContactValue(enum))
            except Exception as e:
                print(f"[CC5 MCP Bridge] GetFloorContactValue({name}) failed: {e}")
                values[name] = None
        return {"success": True, "value": values}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_set_floor_contact(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/floor_contact/set (value: an object as returned by get)."""
    params = _wf_params(body, kwargs)
    try:
        value = params.get("value")
        if value is None:
            return {"success": False, "error": "value is required"}
        avatar = get_first_avatar()
        if not avatar:
            return {"success": False, "error": "No avatar in scene"}
        if not hasattr(avatar, "SetFloorContactValue"):
            return {
                "success": False,
                "error": "SetFloorContactValue is not available in this CC5 build",
            }

        types = _wf_floor_contact_types()
        type_map = dict(types)
        updates: list[tuple[str, Any, float]] = []

        if isinstance(value, dict):
            for key, raw in value.items():
                enum = type_map.get(key)
                if enum is None:
                    return {
                        "success": False,
                        "error": (
                            f"Unknown floor-contact type: {key}. "
                            f"Valid: {', '.join(sorted(type_map)) or 'none exposed'}"
                        ),
                    }
                try:
                    updates.append((key, enum, float(raw)))
                except (TypeError, ValueError):
                    return {
                        "success": False,
                        "error": f"Floor-contact value for {key!r} is not a number",
                    }
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if len(types) != 1:
                return {
                    "success": False,
                    "error": (
                        "value must be an object keyed by floor-contact type "
                        f"(this build exposes {len(types)} types)"
                    ),
                }
            name, enum = types[0]
            updates.append((name, enum, float(value)))
        elif isinstance(value, (list, tuple)):
            if len(value) != len(types):
                return {
                    "success": False,
                    "error": (
                        f"value must have {len(types)} entries "
                        f"({', '.join(name for name, _ in types)})"
                    ),
                }
            for (name, enum), raw in zip(types, value):
                try:
                    updates.append((name, enum, float(raw)))
                except (TypeError, ValueError):
                    return {
                        "success": False,
                        "error": f"Floor-contact value for {name!r} is not a number",
                    }
        else:
            return {
                "success": False,
                "error": "value must be an object as returned by /workflow/floor_contact/get",
            }

        RLPy.RGlobal.BeginAction("wf_set_floor_contact")
        try:
            for _name, enum, number in updates:
                avatar.SetFloorContactValue(enum, number)
            try:
                RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_auto_adjust_foot_height(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/foot_auto."""
    try:
        avatar = get_first_avatar()
        if not avatar:
            return {"success": False, "error": "No avatar in scene"}
        if not hasattr(avatar, "AutoAdjustFootHeight"):
            return {
                "success": False,
                "error": "AutoAdjustFootHeight is not available in this CC5 build",
            }
        RLPy.RGlobal.BeginAction("wf_auto_adjust_foot_height")
        try:
            avatar.AutoAdjustFootHeight()
            try:
                RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
            except Exception:
                pass
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_render_viewport(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/render (silent RenderImage only; never clicks)."""
    params = _wf_params(body, kwargs)
    try:
        file_path = (params.get("file_path") or "").strip()
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        path_error = _validate_path(file_path, {".png"})
        if path_error:
            return {"success": False, "error": path_error}
        render_error = _wf_render_png(file_path)
        if render_error:
            return {"success": False, "error": render_error}
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wf_bounds_center_size(obj) -> tuple[list[float], list[float]] | None:
    """(center, size) from RIObject.GetBounds(), tolerant of the binding shape."""
    get_bounds = getattr(obj, "GetBounds", None)
    if get_bounds is None:
        return None

    max_v: list[float] | None = None
    center: list[float] | None = None
    min_v: list[float] | None = None

    points = None
    try:
        points = get_bounds()
    except Exception as e:
        print(f"[CC5 MCP Bridge] GetBounds() failed: {e}")

    if isinstance(points, (list, tuple)) and len(points) >= 3:
        triple = (points[0], points[1], points[2])
        if all(isinstance(p, (int, float)) for p in points[:9]) and len(points) >= 9:
            nums = [float(p) for p in points[:9]]
            max_v, center, min_v = nums[0:3], nums[3:6], nums[6:9]
        else:
            max_v = _wf_vec3(triple[0])
            center = _wf_vec3(triple[1])
            min_v = _wf_vec3(triple[2])
    else:
        # The reference signature uses out-parameters; fill RVector3 instances.
        vector3 = getattr(RLPy, "RVector3", None)
        if vector3 is not None:
            try:
                out_max = vector3(0.0, 0.0, 0.0)
                out_center = vector3(0.0, 0.0, 0.0)
                out_min = vector3(0.0, 0.0, 0.0)
                got = get_bounds(out_max, out_center, out_min)
                if isinstance(got, (list, tuple)) and len(got) >= 3:
                    out_max, out_center, out_min = got[0], got[1], got[2]
                max_v = _wf_vec3(out_max)
                center = _wf_vec3(out_center)
                min_v = _wf_vec3(out_min)
            except Exception as e:
                print(f"[CC5 MCP Bridge] GetBounds(out...) failed: {e}")

    if max_v is None or min_v is None:
        return None
    if center is None:
        center = [(max_v[i] + min_v[i]) * 0.5 for i in range(3)]
    size = [abs(max_v[i] - min_v[i]) for i in range(3)]
    if max(size) <= 1e-6:
        return None
    return center, size


def _wf_target_bounds(target) -> tuple[list[float], list[float]] | None:
    """Bounds of the requested item, else the first avatar's bounds."""
    if target is not None:
        bounds = _wf_bounds_center_size(target)
        if bounds is not None:
            return bounds
    try:
        avatars = RLPy.RScene.GetAvatars()
    except Exception as e:
        print(f"[CC5 MCP Bridge] GetAvatars for framing failed: {e}")
        avatars = []
    for avatar in avatars or []:
        bounds = _wf_bounds_center_size(avatar)
        if bounds is not None:
            return bounds
    return None


def _wf_v_sub(a: list[float], b: list[float]) -> list[float]:
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _wf_v_norm(v: list[float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _wf_v_unit(v: list[float], fallback: list[float]) -> list[float]:
    n = _wf_v_norm(v)
    if n <= 1e-6:
        return list(fallback)
    return [v[0] / n, v[1] / n, v[2] / n]


def _wf_camera_fov_degrees(camera) -> float:
    """Vertical-ish angle of view in degrees; tolerant of radians/defaults."""
    fov = None
    try:
        fov = float(camera.GetAngleOfView(RLPy.RGlobal.GetTime()))
    except Exception as e:
        print(f"[CC5 MCP Bridge] GetAngleOfView failed: {e}")
    if fov is None or fov != fov or fov <= 0.0:
        fov = 30.0
    if fov <= 3.2:  # radians
        fov = math.degrees(fov)
    return min(120.0, max(5.0, fov))


def _wf_framing_distance(camera, frame_height: float, fill: float = 0.8) -> float:
    """Distance so `frame_height` fills `fill` of a 1280x720 frame height."""
    frame_height = max(float(frame_height), 1e-3)
    half = math.radians(_wf_camera_fov_degrees(camera)) * 0.5
    distance = (frame_height * 0.5) / max(fill * math.tan(half), 1e-6)
    return max(distance, frame_height * 0.25)


def _wf_view_frame_height(size: list[float], key: str) -> float:
    # CC scenes are Z-up: the vertical extent in front/side is Z.
    if key == "top":
        return max(size[0], size[1])
    return size[2]


def _wf_camera_pose_at(camera, position: list[float]) -> Any:
    """Copy the camera's current pose, moved to `position`. None on failure."""
    try:
        transform = camera.WorldTransform()
        vector = _wf_vector3(position)
        if vector is None:
            return None
        transform.T(vector)
        return transform
    except Exception as e:
        print(f"[CC5 MCP Bridge] camera pose build failed: {e}")
        return None


def _wf_camera_persp_pose(
    base: Any,
    position: list[float],
    yaw_deg: float,
    pitch_deg: float,
    look_at: list[float],
) -> Any:
    """Front pose rotated by yaw (Z) / pitch (X), then aimed at `look_at`."""
    try:
        matrix = base.Matrix()
        rz = RLPy.RMatrix4()
        rz.MakeIdentity()
        rz.RotationZ(math.radians(yaw_deg))
        rx = RLPy.RMatrix4()
        rx.MakeIdentity()
        rx.RotationX(math.radians(pitch_deg))
        matrix = rz * rx * matrix
        # The Front preset looks at the scene origin; carry that view direction
        # through the same rotation, then take out the residual angle to the
        # requested centre so the shot really looks at the target.
        try:
            base_pos = _wf_vec3(base.T())
            if base_pos is not None:
                forward = _wf_v_unit([-base_pos[0], -base_pos[1], -base_pos[2]], [0.0, 1.0, 0.0])
                p, y = math.radians(pitch_deg), math.radians(yaw_deg)
                fy = forward[1] * math.cos(p) - forward[2] * math.sin(p)
                fz = forward[1] * math.sin(p) + forward[2] * math.cos(p)
                fx = forward[0]
                turned = [
                    fx * math.cos(y) - fy * math.sin(y),
                    fx * math.sin(y) + fy * math.cos(y),
                    fz,
                ]
                desired = _wf_v_unit(_wf_v_sub(look_at, position), turned)
                dot = max(-1.0, min(1.0,
                    turned[0] * desired[0] + turned[1] * desired[1] + turned[2] * desired[2]))
                axis = [
                    turned[1] * desired[2] - turned[2] * desired[1],
                    turned[2] * desired[0] - turned[0] * desired[2],
                    turned[0] * desired[1] - turned[1] * desired[0],
                ]
                axis_norm = _wf_v_norm(axis)
                if axis_norm > 1e-6 and dot < 0.999999:
                    vec = _wf_vector3([c / axis_norm for c in axis])
                    if vec is not None:
                        correction = RLPy.RMatrix4()
                        correction.MakeIdentity()
                        correction.RotateAxisAngle(vec, math.acos(dot))
                        matrix = correction * matrix
        except Exception as e:
            print(f"[CC5 MCP Bridge] persp look-at correction skipped: {e}")
        vector = _wf_vector3(position)
        if vector is None:
            return None
        matrix.SetTranslate(vector)
        transform = RLPy.RTransform()
        transform.From(matrix)
        return transform
    except Exception as e:
        print(f"[CC5 MCP Bridge] perspective pose build failed: {e}")
        # Last resort: keep the front orientation, only move the camera.
        try:
            transform = base
            vector = _wf_vector3(position)
            if vector is not None:
                transform.T(vector)
            return transform
        except Exception:
            return None


def wf_capture_views4(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/views4: front, side, top and a 45/25 perspective image."""
    params = _wf_params(body, kwargs)
    try:
        folder = (params.get("folder") or "").strip()
        prefix = (params.get("prefix") or "").strip()
        if not folder:
            return {"success": False, "error": "folder is required"}
        if not prefix:
            return {"success": False, "error": "prefix is required"}
        if "\x00" in folder or ".." in folder or "\x00" in prefix or "/" in prefix or "\\" in prefix:
            return {"success": False, "error": "Invalid folder or prefix"}

        target = None
        if params.get("item_name") or params.get("item_id"):
            target, _kind, error = _wf_resolve(
                params.get("item_name"), params.get("item_id")
            )
            if error:
                return error

        camera = RLPy.RScene.GetCurrentCamera()
        if camera is None:
            return {"success": False, "error": "No camera in scene"}
        saved = _wf_camera_save(camera)

        bounds = _wf_target_bounds(target)
        framing = "target bounds, 80% of frame height" if bounds is not None else "camera presets"
        if bounds is not None:
            center, size = bounds
        else:
            center, size = [0.0, 0.0, 0.0], None

        os.makedirs(folder, exist_ok=True)
        files: dict[str, str] = {}
        views: dict[str, Any] = {}
        restored = False
        RLPy.RGlobal.BeginAction("wf_capture_views4")
        try:
            if target is not None:
                try:
                    RLPy.RScene.SelectObject(target)
                except Exception as e:
                    print(f"[CC5 MCP Bridge] SelectObject failed: {e}")

            front_enum = getattr(RLPy, _WF_VIEW4_CAMERA["front"], None)
            for key in _WF_VIEW4_ORDER:
                if key == "persp":
                    # Perspective: 45 deg yaw around Z, tilted 25 deg down,
                    # aimed at the target center (never the Top preset).
                    try:
                        if front_enum is not None:
                            camera.SetCameraLocation(front_enum)
                        front_pose = camera.WorldTransform()
                        front_pos = _wf_vec3(front_pose.T())
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Perspective base pose failed: {e}",
                        }
                    if front_pos is None:
                        return {"success": False, "error": "Perspective: camera pose unreadable"}
                    horizontal = [front_pos[0] - center[0], front_pos[1] - center[1], 0.0]
                    direction = _wf_v_unit(horizontal, [0.0, -1.0, 0.0])
                    yaw = math.radians(45.0)
                    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
                    direction = [
                        direction[0] * cos_yaw - direction[1] * sin_yaw,
                        direction[0] * sin_yaw + direction[1] * cos_yaw,
                        0.0,
                    ]
                    if size is not None:
                        distance = _wf_framing_distance(
                            camera, _wf_view_frame_height(size, "front")
                        )
                    else:
                        distance = max(_wf_v_norm(_wf_v_sub(front_pos, center)), 10.0)
                    tilt = math.radians(25.0)
                    position = [
                        center[0] + direction[0] * distance * math.cos(tilt),
                        center[1] + direction[1] * distance * math.cos(tilt),
                        center[2] + distance * math.sin(tilt),
                    ]
                    transform = _wf_camera_persp_pose(
                        front_pose, position, 45.0, -25.0, center
                    )
                    applied, method = (False, "")
                    if transform is not None:
                        applied, method = _wf_camera_apply(camera, transform)
                    if applied:
                        views[key] = {
                            "yaw_deg": 45.0,
                            "pitch_deg": 25.0,
                            "method": method,
                            "position": [round(v, 3) for v in position],
                        }
                    else:
                        # The camera transform is not writable on this build (live 10-22):
                        # fall back to the Back preset so the 4th image is still a new angle.
                        back_enum = getattr(RLPy, "ECameraLocationType_Back", None)
                        if back_enum is not None:
                            camera.SetCameraLocation(back_enum)
                        views[key] = {"method": "preset Back (camera transform not writable)"}
                else:
                    enum_name = _WF_VIEW4_CAMERA[key]
                    enum = getattr(RLPy, enum_name, None)
                    if enum is None:
                        return {
                            "success": False,
                            "error": f"Camera view '{key}' is not available in this CC5 version",
                        }
                    try:
                        camera.SetCameraLocation(enum)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"SetCameraLocation failed for the {key} view: {e}",
                        }
                    if size is not None:
                        try:
                            preset_pose = camera.WorldTransform()
                            preset_pos = _wf_vec3(preset_pose.T())
                        except Exception:
                            preset_pos = None
                        if preset_pos is not None:
                            direction = _wf_v_unit(
                                _wf_v_sub(preset_pos, center),
                                [0.0, 0.0, 1.0] if key == "top" else [0.0, -1.0, 0.0],
                            )
                            distance = _wf_framing_distance(
                                camera, _wf_view_frame_height(size, key)
                            )
                            position = [
                                center[i] + direction[i] * distance for i in range(3)
                            ]
                            transform = _wf_camera_pose_at(camera, position)
                            if transform is not None:
                                applied, method = _wf_camera_apply(camera, transform)
                                if applied:
                                    views[key] = {
                                        "method": method,
                                        "position": [round(v, 3) for v in position],
                                    }
                                else:
                                    camera.SetCameraLocation(enum)   # keep the plain preset view
                    views.setdefault(key, {"method": "preset"})

                if hasattr(RLPy.RGlobal, "ForceViewportUpdate"):
                    RLPy.RGlobal.ForceViewportUpdate()
                out_path = os.path.join(folder, f"{prefix}_{key}.png")
                path_error = _validate_path(out_path, {".png"})
                if path_error:
                    return {"success": False, "error": path_error}
                render_error = _wf_render_png(out_path)
                if render_error:
                    return {"success": False, "error": f"{key} view: {render_error}"}
                files[key] = out_path
        finally:
            restored = _wf_restore_camera(camera, saved)
            if target is not None:
                try:
                    RLPy.RScene.ClearSelectObjects()
                except Exception as e:
                    print(f"[CC5 MCP Bridge] ClearSelectObjects failed: {e}")
            RLPy.RGlobal.EndAction()

        result: dict[str, Any] = {
            "success": True,
            "files": [files[key] for key in _WF_VIEW4_ORDER],
            "camera_restored": restored,
            "framing": framing,
            "views": views,
        }
        if not restored:
            result["warning"] = "Camera could not be restored to its previous transform"
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}



def wf_open_project(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/open_project: open a saved .ccProject (replaces the current scene)."""
    params = _wf_params(body, kwargs)
    try:
        file_path = (params.get("file_path") or "").strip()
        path_error = _validate_path(file_path, {".ccproject"})
        if path_error:
            return {"success": False, "error": path_error}
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"No such project file: {file_path}"}
        RLPy.RFileIO.LoadProject(file_path)
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_load_cloth_fbx(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/load_cloth_fbx: import an FBX directly as cloth on the first avatar (RFileIO.LoadClotheFromFbx)."""
    params = _wf_params(body, kwargs)
    try:
        file_path = (params.get("file_path") or "").strip()
        path_error = _validate_path(file_path, {".fbx"})
        if path_error:
            return {"success": False, "error": path_error}
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        avatar = get_first_avatar()
        if avatar is None:
            return {"success": False, "error": "No avatar in scene"}
        before = {str(entry["id"]) for _, entry in _wf_scan()}
        failed: list[Any] = []
        RLPy.RGlobal.BeginAction("wf_load_cloth_fbx")
        try:
            result = RLPy.RFileIO.LoadClotheFromFbx(avatar, file_path, failed)
        finally:
            RLPy.RGlobal.EndAction()
        new_items = [entry for _, entry in _wf_scan() if str(entry["id"]) not in before]
        # LoadClotheFromFbx returns [RStatus, failedMeshList]; report the status
        # instead of only stringifying it (the live test saw [RStatus, ()]).
        status = None
        failed_meshes = [str(f) for f in failed]
        if isinstance(result, (list, tuple)) and result:
            status = result[0]
            if len(result) > 1:
                try:
                    failed_meshes = [str(f) for f in (result[1] or [])]
                except Exception:
                    pass
        status_error = None
        status_code = None
        if status is not None:
            try:
                status_error = bool(status.IsError())
            except Exception as e:
                print(f"[CC5 MCP Bridge] RStatus.IsError failed: {e}")
            try:
                status_code = _wf_jsonable(status.GetStatusCode())
            except Exception as e:
                print(f"[CC5 MCP Bridge] RStatus.GetStatusCode failed: {e}")
        return {
            "success": bool(new_items),
            "result": str(result),
            "status_error": status_error,
            "status_code": status_code,
            "failed_meshes": failed_meshes,
            "items": new_items,
            **({} if new_items else {"error": "nothing new appeared in the scene"}),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Physics (Soft Cloth) routes (see docs/contract_workflow_routes.md) ---
#
# Not tried in a live CC5 yet, so every RLPy call is guarded. Only methods that
# exist in CC5's RLPy.py are used:
#   RICloth / RIAccessory / RIHair / RIAvatar .GetPhysicsComponent()
#       (RIProp has no GetPhysicsComponent)
#   RIPhysicsComponent:
#     GetSoftPhysicsMeshNameList()
#     GetSoftPhysicsMaterialNameList(strMeshName)
#     IsActivatePhysicsEnable() / SetActivatePhysicsEnable(bActivate)
#         -- one switch for the whole item; there is no per-mesh/material switch
#     GetSoftPhysXProperty(strMeshName, strMaterialName, strPropertyName)
#     SetSoftPhysXProperty(strMeshName, strMaterialName, strPropertyName, fValue)
#     GetSoftPhysXCollisionEnable(strMeshName, strMaterialName, strCollisionName)
#     GetSoftPhysXCollisionValue(strMeshName, strMaterialName, strCollisionName)
#     SetSoftPhysXCollisionEnable(strMeshName, strMaterialName, strCollisionName, bEnable)
#     SetSoftPhysXCollisionValue(strMeshName, strMaterialName, strCollisionName, fValue)
#     SetPhysicsSoftColthWeightMap(*args)  -- overloads (_RLPy.pyd):
#         (wstring mesh, wstring material, wstring filePath) and
#         (wstring mesh, wstring material, RIImagePtr image)
#     GetPhysicsSoftColthWeightMap(strMeshName, strMaterialName)
#
# RLPy.py does not document the property names. This is the soft-cloth key
# table found in CharacterCreator.exe (CC5), in its order. SoftVsRigidCollision
# and SelfCollision are on/off switches; they are written as 1.0 / 0.0.
_WF_SOFT_PHYSX_PROPERTIES = (
    "Mass",
    "Friction",
    "SolverFrequency",
    "Damping",
    "TetherLimit",
    "Drag",
    "Elasticity",
    "Stretch",
    "Bending",
    "Inertia",
    "SoftVsRigidCollisionMargin",
    "SelfCollisionMargin",
    "SoftVsRigidCollision",
    "SelfCollision",
)

_WF_PHYSICS_GUI_HINT = (
    "Do it by hand in CC5 instead: select the item, then Modify panel > Physics."
)

_WF_WEIGHT_MAP_GUI_HINT = (
    "Load the weight map by hand in CC5 (画面で読み込む): select the item, open "
    "Modify panel > Physics > Weight Map, choose the mesh/material and load the PNG."
)


def _wf_physics_norm(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


_WF_SOFT_PHYSX_BY_NORM = {_wf_physics_norm(n): n for n in _WF_SOFT_PHYSX_PROPERTIES}


def _wf_physics_canonical(names: Any) -> tuple[list[str], list[str]]:
    """Map requested property names to RLPy keys. Returns (canonical, unknown)."""
    canonical: list[str] = []
    unknown: list[str] = []
    for name in names or []:
        key = _WF_SOFT_PHYSX_BY_NORM.get(_wf_physics_norm(name))
        if key is None:
            unknown.append(str(name))
        elif key not in canonical:
            canonical.append(key)
    return canonical, unknown


def _wf_physics_strs(value: Any) -> list[str]:
    try:
        return [str(v) for v in (value or [])]
    except Exception:
        return []


def _wf_physics_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == value  # not NaN
        and value not in (float("inf"), float("-inf"))
    )


def _wf_physics_component(obj, kind: str | None):
    """Return (RIPhysicsComponent, error_dict_or_None) for a resolved item."""
    name = _wf_obj_name(obj)
    getter = getattr(obj, "GetPhysicsComponent", None)
    if getter is None:
        hint = ""
        if kind == "prop":
            hint = (
                " Props have no physics component in RLPy; turn the prop into cloth or "
                "an accessory first (for example with transfer_skin_weights)."
            )
        return None, {
            "success": False,
            "error": (
                f"'{name}' ({kind}) has no GetPhysicsComponent in RLPy; only cloth, "
                f"accessory, hair and avatar items have one.{hint}"
            ),
        }
    try:
        comp = getter()
    except Exception as e:
        return None, {"success": False, "error": f"GetPhysicsComponent failed for '{name}': {e}"}
    if comp is None:
        return None, {
            "success": False,
            "error": f"'{name}' has no physics component (GetPhysicsComponent returned None)",
        }
    return comp, None


def _wf_physics_meshes(comp) -> tuple[dict[str, list[str]] | None, str | None]:
    """Soft-cloth mesh -> material names, or (None, reason) when unreadable."""
    if not hasattr(comp, "GetSoftPhysicsMeshNameList"):
        return None, "RLPy has no GetSoftPhysicsMeshNameList"
    try:
        meshes = _wf_physics_strs(comp.GetSoftPhysicsMeshNameList())
    except Exception as e:
        return None, f"GetSoftPhysicsMeshNameList failed: {e}"
    result: dict[str, list[str]] = {}
    for mesh in meshes:
        materials: list[str] = []
        if hasattr(comp, "GetSoftPhysicsMaterialNameList"):
            try:
                materials = _wf_physics_strs(comp.GetSoftPhysicsMaterialNameList(mesh))
            except Exception as e:
                print(f"[CC5 MCP Bridge] GetSoftPhysicsMaterialNameList({mesh!r}) failed: {e}")
        result[mesh] = materials
    return result, None


def _wf_physics_mesh_list(meshes: dict[str, list[str]] | None) -> list[dict[str, Any]]:
    return [{"mesh": m, "materials": list(mats)} for m, mats in (meshes or {}).items()]


def _wf_physics_target(params: dict[str, Any], strict: bool = True):
    """Resolve item + physics component + mesh/material.

    Returns (ctx, error). ctx has obj, name, comp, mesh, material, notes.
    With strict=False an unknown mesh/material is only noted (the weight-map
    load may be what turns soft cloth on for that material).
    """
    obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
    if error:
        return None, error
    name = _wf_obj_name(obj)
    comp, error = _wf_physics_component(obj, kind)
    if error:
        return None, error

    notes: list[str] = []
    mesh = str(params.get("mesh_name") or "").strip()
    material = str(params.get("material_name") or "").strip()
    meshes, list_error = _wf_physics_meshes(comp)

    if meshes is None:
        if not mesh or not material:
            return None, {
                "success": False,
                "error": (
                    "mesh_name and material_name are required (the soft-cloth mesh list "
                    f"could not be read: {list_error})"
                ),
            }
        notes.append(f"Soft-cloth mesh list unavailable ({list_error}); names were not checked.")
    else:
        listing = _wf_physics_mesh_list(meshes)
        if not mesh:
            if len(meshes) == 1:
                mesh = next(iter(meshes))
            elif not meshes:
                return None, {
                    "success": False,
                    "error": (
                        f"'{name}' has no soft-cloth meshes yet, so mesh_name and "
                        "material_name must be given (see get_material_info). Soft cloth "
                        "is set up per material by loading a weight map."
                    ),
                    "meshes": listing,
                }
            else:
                return None, {
                    "success": False,
                    "error": "mesh_name is required (the item has several soft-cloth meshes)",
                    "meshes": listing,
                }
        if mesh not in meshes:
            message = f"Mesh {mesh!r} has no soft-cloth physics on '{name}'"
            if strict:
                return None, {"success": False, "error": message, "meshes": listing}
            notes.append(message + " yet.")
        materials = meshes.get(mesh, [])
        if not material:
            if len(materials) == 1:
                material = materials[0]
            else:
                return None, {
                    "success": False,
                    "error": f"material_name is required for mesh {mesh!r}",
                    "meshes": listing,
                }
        if materials and material not in materials:
            message = f"Material {material!r} on mesh {mesh!r} has no soft-cloth physics"
            if strict:
                return None, {"success": False, "error": message, "meshes": listing}
            notes.append(message + " yet.")
        elif mesh in meshes and not materials:
            notes.append(f"No soft-cloth material list for mesh {mesh!r}; material name not checked.")

    return {
        "obj": obj,
        "name": name,
        "comp": comp,
        "mesh": mesh,
        "material": material,
        "notes": notes,
    }, None


def _wf_physics_activate_state(comp) -> bool | None:
    if not hasattr(comp, "IsActivatePhysicsEnable"):
        return None
    try:
        return bool(comp.IsActivatePhysicsEnable())
    except Exception as e:
        print(f"[CC5 MCP Bridge] IsActivatePhysicsEnable failed: {e}")
        return None


def _wf_physics_read_props(comp, mesh: str, material: str, names: list[str]):
    """Read SoftPhysX properties. Returns (values, unreadable)."""
    values: dict[str, Any] = {}
    unreadable: dict[str, str] = {}
    for key in names:
        try:
            raw = comp.GetSoftPhysXProperty(mesh, material, key)
        except Exception as e:
            unreadable[key] = str(e)
            continue
        if raw is None:
            unreadable[key] = "returned None"
            continue
        values[key] = _wf_jsonable(raw)
    return values, unreadable


def _wf_physics_probe(comp, mesh: str, material: str, name: str) -> dict[str, Any] | None:
    """Read one collision shape; None when neither getter gives a value."""
    entry: dict[str, Any] = {"name": name, "enabled": None, "value": None}
    found = False
    if hasattr(comp, "GetSoftPhysXCollisionEnable"):
        try:
            raw = comp.GetSoftPhysXCollisionEnable(mesh, material, name)
            if raw is not None:
                entry["enabled"] = bool(raw)
                found = True
        except Exception:
            pass
    if hasattr(comp, "GetSoftPhysXCollisionValue"):
        try:
            raw = comp.GetSoftPhysXCollisionValue(mesh, material, name)
            if raw is not None:
                entry["value"] = _wf_jsonable(raw)
                found = True
        except Exception:
            pass
    return entry if found else None


def _wf_physics_bone_names(obj) -> list[str]:
    """Skin bone names of the avatar that owns obj (default collision candidates)."""
    avatar = _wf_owner_avatar(obj)
    if avatar is None:
        try:
            avatar = get_first_avatar()
        except Exception:
            avatar = None
    if avatar is None:
        return []
    try:
        bones = avatar.GetSkeletonComponent().GetSkinBones() or []
    except Exception as e:
        print(f"[CC5 MCP Bridge] collision bone list failed: {e}")
        return []
    names: list[str] = []
    for bone in bones:
        try:
            bone_name = bone.GetName()
        except Exception:
            continue
        if bone_name and bone_name not in names:
            names.append(bone_name)
    return names


def _wf_physics_close(a: Any, b: Any) -> bool:
    try:
        a, b = float(a), float(b)
    except Exception:
        return False
    return abs(a - b) <= 1e-3 * max(1.0, abs(b))


def _wf_physics_reply(ctx: dict[str, Any], **extra: Any) -> dict[str, Any]:
    reply: dict[str, Any] = {
        "success": True,
        "name": ctx["name"],
        "mesh": ctx["mesh"],
        "material": ctx["material"],
    }
    reply.update(extra)
    if ctx["notes"]:
        reply["notes"] = list(ctx["notes"])
    return reply


def wf_physics_info(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/physics/info: Activate Physics state and soft-cloth meshes/materials."""
    params = _wf_params(body, kwargs)
    try:
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        comp, error = _wf_physics_component(obj, kind)
        if error:
            return error
        meshes, list_error = _wf_physics_meshes(comp)
        reply: dict[str, Any] = {
            "success": True,
            "name": _wf_obj_name(obj),
            "kind": kind,
            "activate": _wf_physics_activate_state(comp),
            "meshes": _wf_physics_mesh_list(meshes),
            "properties": list(_WF_SOFT_PHYSX_PROPERTIES),
            "weight_map_import": hasattr(comp, "SetPhysicsSoftColthWeightMap"),
        }
        if list_error:
            reply["notes"] = [list_error]
        return reply
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_activate(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/physics/activate: turn Activate Physics on/off for a whole item."""
    params = _wf_params(body, kwargs)
    try:
        enable = params.get("enable")
        if not isinstance(enable, bool):
            return {"success": False, "error": "enable (true or false) is required"}
        obj, kind, error = _wf_resolve(params.get("item_name"), params.get("item_id"))
        if error:
            return error
        comp, error = _wf_physics_component(obj, kind)
        if error:
            return error
        name = _wf_obj_name(obj)
        if not hasattr(comp, "SetActivatePhysicsEnable"):
            return {
                "success": False,
                "error": f"RLPy has no SetActivatePhysicsEnable. {_WF_PHYSICS_GUI_HINT}",
            }
        RLPy.RGlobal.BeginAction("wf_physics_activate")
        try:
            status = comp.SetActivatePhysicsEnable(enable)
        finally:
            RLPy.RGlobal.EndAction()
        ok, desc = _describe_rlpy_status(status)
        if ok is False:
            return {"success": False, "error": f"CC5 refused SetActivatePhysicsEnable ({desc})"}
        after = _wf_physics_activate_state(comp)
        if after is not None and after != enable:
            return {
                "success": False,
                "error": f"Activate Physics is still {after} after setting it to {enable}",
                "activate": after,
            }
        return {
            "success": True,
            "name": name,
            "activate": enable if after is None else after,
            "verified": after is not None,
            "notes": [
                "Activate Physics is one switch for the whole item; RLPy has no "
                "per-mesh or per-material switch."
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_load_weight_map(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/physics/weight_map: load a soft-cloth weight map PNG for one material."""
    params = _wf_params(body, kwargs)
    try:
        file_path = str(params.get("file_path") or "").strip()
        if not file_path:
            return {"success": False, "error": "file_path is required"}
        path_error = _validate_path(file_path, {".png"})
        if path_error:
            return {"success": False, "error": path_error}
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        ctx, error = _wf_physics_target(params, strict=False)
        if error:
            return error
        comp = ctx["comp"]
        setter = getattr(comp, "SetPhysicsSoftColthWeightMap", None)
        if setter is None:
            return {
                "success": False,
                "gui_only": True,
                "error": (
                    "This CC5 build's RLPy has no SetPhysicsSoftColthWeightMap, so the "
                    f"weight map cannot be loaded from a script. {_WF_WEIGHT_MAP_GUI_HINT}"
                ),
            }
        RLPy.RGlobal.BeginAction("wf_physics_load_weight_map")
        try:
            status = setter(ctx["mesh"], ctx["material"], file_path)
        except Exception as e:
            return {
                "success": False,
                "gui_only": True,
                "error": f"SetPhysicsSoftColthWeightMap failed: {e}. {_WF_WEIGHT_MAP_GUI_HINT}",
            }
        finally:
            RLPy.RGlobal.EndAction()
        ok, desc = _describe_rlpy_status(status)
        if ok is False:
            return {
                "success": False,
                "gui_only": True,
                "error": f"CC5 refused the weight map ({desc}). {_WF_WEIGHT_MAP_GUI_HINT}",
            }
        present = None
        if hasattr(comp, "GetPhysicsSoftColthWeightMap"):
            try:
                present = comp.GetPhysicsSoftColthWeightMap(ctx["mesh"], ctx["material"]) is not None
            except Exception as e:
                ctx["notes"].append(f"GetPhysicsSoftColthWeightMap failed: {e}")
        return _wf_physics_reply(
            ctx,
            path=file_path,
            status=desc,
            weight_map_present=present,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_get_params(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/physics/params/get: read Soft PhysX properties of one material."""
    params = _wf_params(body, kwargs)
    try:
        requested = params.get("names")
        if requested is not None and not isinstance(requested, list):
            return {"success": False, "error": "names must be a list of property names"}
        names, unknown = _wf_physics_canonical(requested or _WF_SOFT_PHYSX_PROPERTIES)
        if unknown:
            return {
                "success": False,
                "error": f"Unknown Soft PhysX property: {', '.join(unknown)}",
                "allowed": list(_WF_SOFT_PHYSX_PROPERTIES),
            }
        ctx, error = _wf_physics_target(params)
        if error:
            return error
        comp = ctx["comp"]
        if not hasattr(comp, "GetSoftPhysXProperty"):
            return {
                "success": False,
                "error": f"RLPy has no GetSoftPhysXProperty. {_WF_PHYSICS_GUI_HINT}",
            }
        values, unreadable = _wf_physics_read_props(comp, ctx["mesh"], ctx["material"], names)
        if not values and unreadable:
            return {
                "success": False,
                "error": "No Soft PhysX property could be read",
                "unreadable": unreadable,
            }
        reply = _wf_physics_reply(ctx, params=values)
        if unreadable:
            reply["unreadable"] = unreadable
        return reply
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_set_params(body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Route /workflow/physics/params/set: write Soft PhysX properties, then read them back."""
    params = _wf_params(body, kwargs)
    try:
        raw_values = params.get("values")
        if not isinstance(raw_values, dict) or not raw_values:
            return {"success": False, "error": "values must be a non-empty object {name: number}"}
        wanted: dict[str, float] = {}
        unknown: list[str] = []
        for raw_name, raw_value in raw_values.items():
            key = _WF_SOFT_PHYSX_BY_NORM.get(_wf_physics_norm(raw_name))
            if key is None:
                unknown.append(str(raw_name))
                continue
            if isinstance(raw_value, bool):
                wanted[key] = 1.0 if raw_value else 0.0
            elif _wf_physics_number(raw_value):
                wanted[key] = float(raw_value)
            else:
                return {"success": False, "error": f"Value for {raw_name} must be a number or boolean"}
        if unknown:
            return {
                "success": False,
                "error": f"Unknown Soft PhysX property: {', '.join(unknown)}",
                "allowed": list(_WF_SOFT_PHYSX_PROPERTIES),
            }
        ctx, error = _wf_physics_target(params)
        if error:
            return error
        comp = ctx["comp"]
        if not hasattr(comp, "SetSoftPhysXProperty"):
            return {
                "success": False,
                "error": f"RLPy has no SetSoftPhysXProperty. {_WF_PHYSICS_GUI_HINT}",
            }
        keys = list(wanted)
        can_read = hasattr(comp, "GetSoftPhysXProperty")
        before = _wf_physics_read_props(comp, ctx["mesh"], ctx["material"], keys)[0] if can_read else {}
        failures: dict[str, str] = {}
        RLPy.RGlobal.BeginAction("wf_physics_set_params")
        try:
            for key, value in wanted.items():
                try:
                    status = comp.SetSoftPhysXProperty(ctx["mesh"], ctx["material"], key, value)
                except Exception as e:
                    failures[key] = str(e)
                    continue
                ok, desc = _describe_rlpy_status(status)
                if ok is False:
                    failures[key] = f"refused ({desc})"
        finally:
            RLPy.RGlobal.EndAction()
        after: dict[str, Any] = {}
        if can_read:
            after = _wf_physics_read_props(comp, ctx["mesh"], ctx["material"], keys)[0]
        else:
            ctx["notes"].append("RLPy has no GetSoftPhysXProperty; values were not read back.")
        mismatched = {
            key: {"wanted": value, "got": after[key]}
            for key, value in wanted.items()
            if key not in failures and key in after and not _wf_physics_close(after[key], value)
        }
        reply = _wf_physics_reply(ctx, before=before, after=after)
        if failures or mismatched:
            problems = []
            if failures:
                problems.append("write failed for " + ", ".join(failures))
            if mismatched:
                problems.append("read-back differs for " + ", ".join(mismatched))
            reply["success"] = False
            reply["error"] = "; ".join(problems)
            if failures:
                reply["failures"] = failures
            if mismatched:
                reply["mismatched"] = mismatched
        return reply
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_get_collision(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/physics/collision/get: collision shapes for one soft-cloth material.

    RLPy has no call that lists collision shapes, so names are probed: the given
    collision_names, or every skin bone of the owning avatar.
    """
    params = _wf_params(body, kwargs)
    try:
        requested = params.get("collision_names")
        if requested is not None and not isinstance(requested, list):
            return {"success": False, "error": "collision_names must be a list of names"}
        ctx, error = _wf_physics_target(params)
        if error:
            return error
        comp = ctx["comp"]
        if not (
            hasattr(comp, "GetSoftPhysXCollisionEnable")
            or hasattr(comp, "GetSoftPhysXCollisionValue")
        ):
            return {
                "success": False,
                "error": f"RLPy has no GetSoftPhysXCollision* methods. {_WF_PHYSICS_GUI_HINT}",
            }
        explicit = bool(requested)
        names = [str(n) for n in requested] if explicit else _wf_physics_bone_names(ctx["obj"])
        if not names:
            return {
                "success": False,
                "error": "No collision names to check: give collision_names (no avatar bones found)",
            }
        shapes: list[dict[str, Any]] = []
        unknown: list[str] = []
        for collision_name in names:
            entry = _wf_physics_probe(comp, ctx["mesh"], ctx["material"], collision_name)
            if entry is None:
                unknown.append(collision_name)
            else:
                shapes.append(entry)
        reply = _wf_physics_reply(ctx, shapes=shapes, probed=len(names))
        if explicit and unknown:
            reply["unknown"] = unknown
        reply.setdefault("notes", []).append(
            "RLPy cannot list collision shapes; names were probed. 'value' is the number "
            "RLPy calls the collision value (most likely the margin)."
        )
        return reply
    except Exception as e:
        return {"success": False, "error": str(e)}


def wf_physics_set_collision(
    body: dict[str, Any] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Route /workflow/physics/collision/set: enable/disable shapes and set their value."""
    params = _wf_params(body, kwargs)
    try:
        shapes = params.get("shapes")
        if not isinstance(shapes, list) or not shapes:
            return {
                "success": False,
                "error": "shapes must be a non-empty list of {name, enabled?, value?}",
            }
        for shape in shapes:
            if not isinstance(shape, dict) or not str(shape.get("name") or "").strip():
                return {"success": False, "error": "every shape needs a name"}
            if "enabled" not in shape and "value" not in shape:
                return {
                    "success": False,
                    "error": f"shape {shape['name']!r} needs enabled and/or value",
                }
            if "enabled" in shape and not isinstance(shape["enabled"], bool):
                return {"success": False, "error": f"enabled for {shape['name']!r} must be true/false"}
            if "value" in shape and not _wf_physics_number(shape["value"]):
                return {"success": False, "error": f"value for {shape['name']!r} must be a number"}
        ctx, error = _wf_physics_target(params)
        if error:
            return error
        comp = ctx["comp"]
        mesh, material = ctx["mesh"], ctx["material"]
        needs_enable = any("enabled" in s for s in shapes)
        needs_value = any("value" in s for s in shapes)
        if needs_enable and not hasattr(comp, "SetSoftPhysXCollisionEnable"):
            return {
                "success": False,
                "error": f"RLPy has no SetSoftPhysXCollisionEnable. {_WF_PHYSICS_GUI_HINT}",
            }
        if needs_value and not hasattr(comp, "SetSoftPhysXCollisionValue"):
            return {
                "success": False,
                "error": f"RLPy has no SetSoftPhysXCollisionValue. {_WF_PHYSICS_GUI_HINT}",
            }

        results: list[dict[str, Any]] = []
        problems: list[str] = []
        RLPy.RGlobal.BeginAction("wf_physics_set_collision")
        try:
            for shape in shapes:
                collision_name = str(shape["name"]).strip()
                before = _wf_physics_probe(comp, mesh, material, collision_name)
                errors: list[str] = []
                if "enabled" in shape:
                    try:
                        status = comp.SetSoftPhysXCollisionEnable(
                            mesh, material, collision_name, shape["enabled"]
                        )
                        ok, desc = _describe_rlpy_status(status)
                        if ok is False:
                            errors.append(f"enable refused ({desc})")
                    except Exception as e:
                        errors.append(f"enable failed: {e}")
                if "value" in shape:
                    try:
                        status = comp.SetSoftPhysXCollisionValue(
                            mesh, material, collision_name, float(shape["value"])
                        )
                        ok, desc = _describe_rlpy_status(status)
                        if ok is False:
                            errors.append(f"value refused ({desc})")
                    except Exception as e:
                        errors.append(f"value failed: {e}")
                after = _wf_physics_probe(comp, mesh, material, collision_name)
                if after is not None:
                    if (
                        "enabled" in shape
                        and after.get("enabled") is not None
                        and after["enabled"] != shape["enabled"]
                    ):
                        errors.append(f"enabled reads back as {after['enabled']}")
                    if (
                        "value" in shape
                        and after.get("value") is not None
                        and not _wf_physics_close(after["value"], shape["value"])
                    ):
                        errors.append(f"value reads back as {after['value']}")
                entry: dict[str, Any] = {"name": collision_name, "before": before, "after": after}
                if errors:
                    entry["errors"] = errors
                    problems.append(f"{collision_name}: {'; '.join(errors)}")
                results.append(entry)
        finally:
            RLPy.RGlobal.EndAction()

        reply = _wf_physics_reply(ctx, shapes=results)
        if problems:
            reply["success"] = False
            reply["error"] = " | ".join(problems)
        return reply
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Auto-patch server ACTION_MAP on reload ---

def _auto_patch_server() -> None:
    """Update the running server's dispatch table when cc5_api is reloaded."""
    srv = sys.modules.get("server")
    if srv is None or not hasattr(srv, "ACTION_MAP"):
        return

    import cc5_api as _self
    srv.ACTION_MAP.update({
        "wf_open_project": wf_open_project,
        "wf_load_cloth_fbx": wf_load_cloth_fbx,
        "get_avatars":           lambda p: _self.get_avatars(),
        "get_avatar_info":       lambda p: _self.get_avatar_info(),
        "get_morph_catalog":     lambda p: _self.get_morph_catalog(),
        "search_morphs":         lambda p: _self.search_morphs(p["query"], p.get("category", "")),
        "get_morph_value":       lambda p: _self.get_morph_value(p["morph_id"]),
        "set_morph_value":       lambda p: _self.set_morph_value(p["morph_id"], float(p["value"])),
        "set_multiple_morphs":   lambda p: _self.set_multiple_morphs(p["morphs"]),
        "create_default_avatar": lambda p: _self.create_default_avatar(),
        "delete_avatar":         lambda p: _self.delete_avatar(p.get("name", "")),
        "load_asset":            lambda p: _self.load_asset(p["file_path"]),
        "export_fbx":            lambda p: _self.export_fbx(
            p["output_path"],
            int(p.get("options", 0)),
            target_tool=p.get("target_tool", ""),
            sub_d_level=(int(p["sub_d_level"]) if p.get("sub_d_level") is not None else None),
            include_current_pose=bool(p.get("include_current_pose", False)),
            delete_hidden_faces=bool(p.get("delete_hidden_faces", False)),
            use_smooth_mesh=bool(p.get("use_smooth_mesh", False)),
            remove_eyelash=bool(p.get("remove_eyelash", False)),
            remove_tearline_occlusion=bool(p.get("remove_tearline_occlusion", False)),
            embed_textures=bool(p.get("embed_textures", False)),
            export_motion=bool(p.get("export_motion", True)),
            fps=(int(p["fps"]) if p.get("fps") is not None else None),
            motion_range=p.get("motion_range"),
            convert_image_format=bool(p.get("convert_image_format", False)),
            texture_size=(int(p["texture_size"]) if p.get("texture_size") is not None else None),
        ),
        "capture_viewport":      lambda p: _self.capture_viewport(p.get("output_path", ""), int(p.get("width", 1280)), int(p.get("height", 720))),
        "set_subdivision_level": lambda p: _self.set_subdivision_level(int(p["level"])),
        "undo":                  lambda p: _self.undo(),
        "redo":                  lambda p: _self.redo(),
        "get_camera_info":       lambda p: _self.get_camera_info(),
        "set_camera_focal_length": lambda p: _self.set_camera_focal_length(float(p["focal_length"])),
        "frame_camera":          lambda p: _self.frame_camera(p.get("view", "face")),
        "get_lights":            lambda p: _self.get_lights(),
        "set_light_color":       lambda p: _self.set_light_color(p["light_name"], float(p["r"]), float(p["g"]), float(p["b"])),
        "get_light_info":        lambda p: _self.get_light_info(p["light_name"]),
        "set_light_multiplier":  lambda p: _self.set_light_multiplier(p["light_name"], float(p["multiplier"])),
        "set_light_active":      lambda p: _self.set_light_active(p["light_name"], bool(p["active"])),
        "set_light_shadow":      lambda p: _self.set_light_shadow(
            p["light_name"],
            (bool(p["cast_shadow"]) if p.get("cast_shadow") is not None else None),
            (float(p["darken_strength"]) if p.get("darken_strength") is not None else None),
        ),
        "get_visual_settings":   lambda p: _self.get_visual_settings(),
        "set_ambient":           lambda p: _self.set_ambient(float(p["r"]), float(p["g"]), float(p["b"])),
        "set_ibl":               lambda p: _self.set_ibl(p.get("image_path", ""), bool(p.get("enable", True))),
        "get_expression_info":   lambda p: _self.get_expression_info(),
        "get_facial_profile":    lambda p: _self.get_facial_profile(),
        "convert_facial_profile": lambda p: _self.convert_facial_profile(
            p.get("target_profile_path", ""),
            bool(p.get("dry_run", True)),
            p.get("backup_current_to", ""),
        ),
        "set_expression":        lambda p: _self.set_expression(p["expressions"]),
        "reset_expression":      lambda p: _self.reset_expression(),
        "reset_all_morphs":      lambda p: _self.reset_all_morphs(p.get("avatar_name", "")),
        "get_material_info":     lambda p: _self.get_material_info(p.get("avatar_name", "")),
        "get_diffuse_color":     lambda p: _self.get_diffuse_color(p["mesh_name"], p["material_name"]),
        "set_diffuse_color":     lambda p: _self.set_diffuse_color(p["mesh_name"], p["material_name"], float(p["r"]), float(p["g"]), float(p["b"])),
        "get_material_properties": lambda p: _self.get_material_properties(p["mesh_name"], p["material_name"]),
        "set_material_opacity":  lambda p: _self.set_material_opacity(p["mesh_name"], p["material_name"], float(p["opacity"])),
        "set_material_glossiness": lambda p: _self.set_material_glossiness(p["mesh_name"], p["material_name"], float(p["glossiness"])),
        "set_material_specular": lambda p: _self.set_material_specular(p["mesh_name"], p["material_name"], float(p["specular"])),
        "get_shader_parameters": lambda p: _self.get_shader_parameters(p["mesh_name"], p["material_name"]),
        "set_shader_parameter": lambda p: _self.set_shader_parameter(p["mesh_name"], p["material_name"], p["parameter_name"], list(p["values"])),
        # Tier 1: Content Management
        "list_clothes":          lambda p: _self.list_clothes(),
        "list_hair":             lambda p: _self.list_hair(),
        "list_accessories":      lambda p: _self.list_accessories(),
        "remove_scene_item":     lambda p: _self.remove_scene_item(p["item_name"]),
        "browse_content":        lambda p: _self.browse_content(p.get("folder_type", "cloth_upper")),
        # Tier 3: Convenience Color Shortcuts
        "set_eye_color":         lambda p: _self.set_eye_color(float(p["r"]), float(p["g"]), float(p["b"])),
        "set_hair_color":        lambda p: _self.set_hair_color(float(p["r"]), float(p["g"]), float(p["b"])),
        "set_lip_color":         lambda p: _self.set_lip_color(float(p["r"]), float(p["g"]), float(p["b"])),
        "set_skin_color":        lambda p: _self.set_skin_color(float(p["r"]), float(p["g"]), float(p["b"])),
        # Tier 4: Visibility & Scene
        "set_item_visible":      lambda p: _self.set_item_visible(p["item_name"], bool(p["visible"])),
        "get_scene_objects":     lambda p: _self.get_scene_objects(),
        "exec_python":           lambda p: _self.exec_python(p["code"]),
        # Mesh-to-MetaHuman pipeline helpers
        "bake_skin_textures":    lambda p: _self.bake_skin_textures(int(p.get("resolution", 4096))),
        "export_head_metahuman": lambda p: _self.export_head_metahuman(
            p["output_dir"], p["character_name"], p.get("gender", "Female"),
        ),
        "silent_install_filter": lambda p: _self.silent_install_filter(
            p["output_dir"], p["character_name"],
        ),
        "silent_trigger_dialog": lambda p: _self.silent_trigger_dialog(),
        "silent_configure_and_click": lambda p: _self.silent_configure_and_click(
            p.get("gender", "Female"), int(p.get("max_texture_size", 4096)),
        ),
        "silent_finalize": lambda p: _self.silent_finalize(),
        "get_export_status": lambda p: _self.get_export_status(),
        # ActorMIXER PRO: Create Mixer Assets
        "create_actor_mixer": lambda p: _self.create_actor_mixer(p),
        "get_mixer_status":   lambda p: _self.get_mixer_status(),
        # Workflow routes (docs/contract_workflow_routes.md). These are plain
        # functions: each takes the JSON body dict as its only positional arg.
        "list_scene_items":          list_scene_items,
        "wf_set_visible":            wf_set_visible,
        "wf_remove_item":            wf_remove_item,
        "wf_import_fbx":             wf_import_fbx,
        "wf_import_fbx_begin":       wf_import_fbx_begin,
        "wf_import_fbx_status":      wf_import_fbx_status,
        "wf_attach_to_bone":         wf_attach_to_bone,
        "wf_transfer_skin_weights":  wf_transfer_skin_weights,
        "wf_convert_to_hair":        wf_convert_to_hair,
        "wf_cloth_to_accessory":     wf_cloth_to_accessory,
        "wf_conform_cloth":          wf_conform_cloth,
        "wf_get_transform":          wf_get_transform,
        "wf_bone_rotation":          wf_bone_rotation,
        "wf_menu_find":              wf_menu_find,
        "wf_menu_trigger":           wf_menu_trigger,
        "wf_create_morph_slider":    wf_create_morph_slider,
        "wf_load_texture":           wf_load_texture,
        "wf_morph_editor":           wf_morph_editor,
        "wf_file_dialog_fill":       wf_file_dialog_fill,
        "wf_file_dialog_native":     wf_file_dialog_native,
        "wf_timeline":               wf_timeline,
        "wf_buttons":                wf_buttons,
        "wf_pivot":                  wf_pivot,
        "wf_high_heels_open":        wf_high_heels_open,
        "wf_high_heels_state":       wf_high_heels_state,
        "wf_high_heels_set":         wf_high_heels_set,
        "wf_set_transform":          wf_set_transform,
        "wf_save_project":           wf_save_project,
        "wf_export_obj":             wf_export_obj,
        "wf_get_floor_contact":      wf_get_floor_contact,
        "wf_set_floor_contact":      wf_set_floor_contact,
        "wf_auto_adjust_foot_height": wf_auto_adjust_foot_height,
        "wf_render_viewport":        wf_render_viewport,
        "wf_capture_views4":         wf_capture_views4,
        # Physics (Soft Cloth) routes
        "wf_physics_info":            wf_physics_info,
        "wf_physics_activate":        wf_physics_activate,
        "wf_physics_load_weight_map": wf_physics_load_weight_map,
        "wf_physics_get_params":      wf_physics_get_params,
        "wf_physics_set_params":      wf_physics_set_params,
        "wf_physics_get_collision":   wf_physics_get_collision,
        "wf_physics_set_collision":   wf_physics_set_collision,
    })

    # Also patch routes so new endpoints work after reload
    if hasattr(srv, "POST_ROUTES"):
        srv.POST_ROUTES.update({
            "/undo":             "undo",
            "/redo":             "redo",
            "/camera/focal":     "set_camera_focal_length",
            "/camera/frame":     "frame_camera",
            "/light/color":      "set_light_color",
            "/light/info":       "get_light_info",
            "/light/multiplier": "set_light_multiplier",
            "/light/active":     "set_light_active",
            "/light/shadow":     "set_light_shadow",
            "/visual/ambient":   "set_ambient",
            "/visual/ibl":       "set_ibl",
            "/avatar/delete":    "delete_avatar",
            "/expression/set":   "set_expression",
            "/expression/reset": "reset_expression",
            "/facial/profile/convert": "convert_facial_profile",
            "/morphs/reset":     "reset_all_morphs",
            "/morphs/search":    "search_morphs",
            "/material/info":    "get_material_info",
            "/material/color/get": "get_diffuse_color",
            "/material/color/set": "set_diffuse_color",
            "/material/properties": "get_material_properties",
            "/material/opacity":    "set_material_opacity",
            "/material/glossiness": "set_material_glossiness",
            "/material/specular":   "set_material_specular",
            "/material/shader/get": "get_shader_parameters",
            "/material/shader/set": "set_shader_parameter",
            # Tier 1: Content Management
            "/item/remove":      "remove_scene_item",
            "/content/browse":   "browse_content",
            # Tier 3: Convenience Color Shortcuts
            "/color/eye":        "set_eye_color",
            "/color/hair":       "set_hair_color",
            "/color/lip":        "set_lip_color",
            "/color/skin":       "set_skin_color",
            # Tier 4: Visibility & Scene
            "/item/visible":     "set_item_visible",
            "/exec/python":      "exec_python",
            # Mesh-to-MetaHuman pipeline helpers
            "/skin/bake":        "bake_skin_textures",
            "/export/head_mh":   "export_head_metahuman",
            "/export/head_mh/silent/install_filter":  "silent_install_filter",
            "/export/head_mh/silent/trigger_dialog":  "silent_trigger_dialog",
            "/export/head_mh/silent/configure_click": "silent_configure_and_click",
            "/export/head_mh/silent/finalize":        "silent_finalize",
            # ActorMIXER PRO: Create Mixer Assets
            "/actor_mixer/create":                    "create_actor_mixer",
            # Workflow routes (docs/contract_workflow_routes.md)
            "/workflow/items":              "list_scene_items",
            "/workflow/open_project":       "wf_open_project",
            "/workflow/load_cloth_fbx":     "wf_load_cloth_fbx",
            "/workflow/visible":            "wf_set_visible",
            "/workflow/remove":             "wf_remove_item",
            "/workflow/import_fbx":         "wf_import_fbx_begin",
            "/workflow/attach":             "wf_attach_to_bone",
            "/workflow/transfer_weights":   "wf_transfer_skin_weights",
            "/workflow/convert_hair":       "wf_convert_to_hair",
            "/workflow/cloth_to_accessory": "wf_cloth_to_accessory",
            "/workflow/conform":            "wf_conform_cloth",
            "/workflow/transform/get":      "wf_get_transform",
            "/workflow/bone/rotation":      "wf_bone_rotation",
            "/workflow/menu/find":          "wf_menu_find",
            "/workflow/menu/trigger":       "wf_menu_trigger",
            "/workflow/morph/create":       "wf_create_morph_slider",
            "/workflow/material/load_texture": "wf_load_texture",
            "/workflow/morph/editor":       "wf_morph_editor",
            "/workflow/dialog/file_fill":   "wf_file_dialog_fill",
            "/workflow/dialog/native":      "wf_file_dialog_native",
            "/workflow/timeline":           "wf_timeline",
            "/workflow/buttons":            "wf_buttons",
            "/workflow/pivot":              "wf_pivot",
            "/workflow/high_heels/open":    "wf_high_heels_open",
            "/workflow/high_heels/state":   "wf_high_heels_state",
            "/workflow/high_heels/set":     "wf_high_heels_set",
            "/workflow/transform/set":      "wf_set_transform",
            "/workflow/save":               "wf_save_project",
            "/workflow/export_obj":         "wf_export_obj",
            "/workflow/floor_contact/get":  "wf_get_floor_contact",
            "/workflow/floor_contact/set":  "wf_set_floor_contact",
            "/workflow/foot_auto":          "wf_auto_adjust_foot_height",
            "/workflow/render":             "wf_render_viewport",
            "/workflow/views4":             "wf_capture_views4",
            "/workflow/physics/info":           "wf_physics_info",
            "/workflow/physics/activate":       "wf_physics_activate",
            "/workflow/physics/weight_map":     "wf_physics_load_weight_map",
            "/workflow/physics/params/get":     "wf_physics_get_params",
            "/workflow/physics/params/set":     "wf_physics_set_params",
            "/workflow/physics/collision/get":  "wf_physics_get_collision",
            "/workflow/physics/collision/set":  "wf_physics_set_collision",
        })
    if hasattr(srv, "GET_ROUTES"):
        srv.GET_ROUTES.update({
            "/camera/info":      "get_camera_info",
            "/lights":           "get_lights",
            "/visual/settings":  "get_visual_settings",
            "/expressions":      "get_expression_info",
            "/facial/profile":   "get_facial_profile",
            "/material/info":    "get_material_info",
            # Tier 1: Content Management
            "/clothes":          "list_clothes",
            "/hair":             "list_hair",
            "/accessories":      "list_accessories",
            # Tier 4: Scene
            "/scene/objects":    "get_scene_objects",
            # Silent export polling
            "/export/head_mh/status": "get_export_status",
            # GUI import polling (File > Import flow, no mouse)
            "/workflow/import_fbx/status": "wf_import_fbx_status",
            # ActorMIXER PRO: Create Mixer Assets polling
            "/actor_mixer/status": "get_mixer_status",
        })
    if hasattr(srv, "REQUIRED_PARAMS"):
        srv.REQUIRED_PARAMS.update({
            "set_camera_focal_length": ["focal_length"],
            "set_light_color":         ["light_name", "r", "g", "b"],
            "get_light_info":          ["light_name"],
            "set_light_multiplier":    ["light_name", "multiplier"],
            "set_light_active":        ["light_name", "active"],
            "set_light_shadow":        ["light_name"],
            "set_ambient":             ["r", "g", "b"],
            "set_expression":          ["expressions"],
            "get_diffuse_color":       ["mesh_name", "material_name"],
            "set_diffuse_color":       ["mesh_name", "material_name", "r", "g", "b"],
            "get_material_properties": ["mesh_name", "material_name"],
            "set_material_opacity":    ["mesh_name", "material_name", "opacity"],
            "set_material_glossiness": ["mesh_name", "material_name", "glossiness"],
            "set_material_specular":   ["mesh_name", "material_name", "specular"],
            "get_shader_parameters":   ["mesh_name", "material_name"],
            "set_shader_parameter":    ["mesh_name", "material_name", "parameter_name", "values"],
            # Tier 1: Content Management
            "remove_scene_item":       ["item_name"],
            # Tier 3: Convenience Color Shortcuts
            "set_eye_color":           ["r", "g", "b"],
            "set_hair_color":          ["r", "g", "b"],
            "set_lip_color":           ["r", "g", "b"],
            "set_skin_color":          ["r", "g", "b"],
            # Tier 4: Visibility
            "set_item_visible":        ["item_name", "visible"],
            # Mesh-to-MetaHuman pipeline helpers
            "export_head_metahuman":   ["output_dir", "character_name"],
            "silent_install_filter": ["output_dir", "character_name"],
            # ActorMIXER PRO: Create Mixer Assets (safety gate)
            "create_actor_mixer":      ["confirm_create"],
        })

    print("[CC5 MCP Bridge] Auto-patched ACTION_MAP + routes")


_auto_patch_server()
