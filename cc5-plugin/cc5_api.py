"""
CC5 RLPy API wrapper functions.

Provides a clean interface over RLPy for character manipulation.
All functions MUST be called from the main thread (via QTimer queue).
"""

from __future__ import annotations

import os
import sys
import base64
import tempfile
import urllib.parse
from typing import Any

import RLPy

# --- Path validation (defense-in-depth, mirrors TypeScript validation) ---

_ALLOWED_LOAD_EXTENSIONS = {
    ".iavatar", ".ccavatar", ".ccm", ".iclothes", ".ihair", ".iprop",
    ".ccfbx", ".iclothing", ".ishoe", ".iaccessory", ".ibody", ".iskin",
    ".ccproject",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

MAX_MORPH_ID_LENGTH = 256

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
    """Load the CC5 neutral base avatar into the scene (additive, does not clear scene)."""
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
) -> dict[str, Any]:
    """Export the current avatar as FBX with optional Mesh-to-MetaHuman friendly settings.

    Args:
        output_path: Absolute .fbx destination
        options_flags: Raw EExportFbxOptions bitmask. If 0, defaults are computed from named flags.
        target_tool: "UE5" | "Default" | "Maya" | "Unity" — sets sensible base flag preset
        sub_d_level: 0|1|2, calls set_subdivision_level before export
        include_current_pose: Keep the current pose (do NOT force T-pose on first motion frame)
        delete_hidden_faces: Add EExportFbxOptions_RemoveHiddenMesh
        use_smooth_mesh: Enable RExportFbxSetting.EnableBakeSubdivision (CC5 UI "Use Smooth Mesh")
                         — falls back to setting sub_d_level=1 if RExportFbxSetting variant fails.
        remove_eyelash: Add EExportFbxOptions_RemoveEyelash
        remove_tearline_occlusion: Add EExportFbxOptions_RemoveTearLineAndOcclusion
    """
    # Defense-in-depth path validation
    _decoded_out = urllib.parse.unquote(output_path)
    if "\x00" in output_path or "\x00" in _decoded_out:
        return {"success": False, "error": "Path contains null byte"}
    if ".." in output_path or ".." in _decoded_out:
        return {"success": False, "error": "Path traversal ('..') is not allowed"}
    resolved = os.path.realpath(output_path)
    if not resolved.lower().endswith(".fbx"):
        return {"success": False, "error": "Output path must end with .fbx"}

    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    notes: list[str] = []

    # --- Apply subdivision level first if requested (snapshot for rollback) ---
    _orig_subd = None
    if sub_d_level is not None:
        try:
            if hasattr(avatar, "GetSubdivMeshLevel"):
                _orig_subd = int(avatar.GetSubdivMeshLevel())
        except Exception:
            _orig_subd = None
        try:
            sub_result = set_subdivision_level(int(sub_d_level))
            if not sub_result.get("success", False):
                notes.append(f"set_subdivision_level failed: {sub_result.get('error')}")
            else:
                notes.append(f"sub_d_level={sub_d_level} applied")
        except Exception as e:
            notes.append(f"set_subdivision_level exception: {e}")

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
        notes.append("target_tool=UE5 preset applied")
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
                RLPy.RFileIO.ExportFbxFile(avatar, output_path, setting)
                used_setting_object = True
            except Exception as e:
                notes.append(f"RExportFbxSetting overload failed ({e}); falling back to 2-arg export")

        if not used_setting_object:
            if flags or flags2 or flags3:
                notes.append(
                    "WARNING: option flags (target-tool preset / axis / etc.) were NOT "
                    "applied — used the flag-less 2-arg ExportFbxFile fallback."
                )
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
            RLPy.RFileIO.ExportFbxFile(avatar, output_path)

        # Honest reporting: echo flags only when actually applied.
        return {
            "success": True,
            "path": output_path,
            "flags_applied": used_setting_object,
            "flags": flags if used_setting_object else 0,
            "flags2": flags2 if applied_flags2 else 0,
            "flags3": flags3 if applied_flags3 else 0,
            "notes": notes,
            "target_tool": target_tool or "default",
        }
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
    # Pass the output path as a bound PowerShell parameter instead of
    # interpolating it into the script body — prevents PS command injection
    # via single-quote / paren breakout in caller-influenced paths.
    ps_script = """
param([string]$OutputPath)
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
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    Add-Type -AssemblyName System.Windows.Forms
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
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script,
         "-OutputPath", output_path],
        capture_output=True, timeout=10,
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


# --- Expression Control ---

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


# --- Python Script Execution ---

def exec_python(code: str) -> dict[str, Any]:
    """Execute arbitrary Python code inside CC5's RLPy environment.
    The code has access to RLPy module and the running CC5 scene.
    Returns: {"success": True, "output": "<captured stdout>", "result": "<last expression>"}
    """
    # --- Production safety gate (hot-reloadable; mirrors server-side DEV_MODE) ---
    # Disabled when dev mode is off unless an explicit exec opt-in / reload secret
    # is present. Keeps arbitrary code execution off by default in production.
    # NOTE: deliberately NOT gated on CC5_RELOAD_SECRET — exec must not be enabled
    # as a side effect of securing /reload. Gate only on dev mode / explicit exec opt-in.
    dev_mode = os.environ.get("CC5_DEV_MODE", "1").strip().lower() not in ("0", "false", "no", "")
    allow_exec = os.environ.get("CC5_ALLOW_EXEC", "").strip().lower() in ("1", "true", "yes")
    if not dev_mode and not allow_exec:
        return {
            "success": False,
            "error": "/exec/python disabled. Set CC5_DEV_MODE=1 or CC5_ALLOW_EXEC=1.",
        }

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


# --- Auto-patch server ACTION_MAP on reload ---

def _auto_patch_server() -> None:
    """Update the running server's dispatch table when cc5_api is reloaded."""
    srv = sys.modules.get("server")
    if srv is None or not hasattr(srv, "ACTION_MAP"):
        return

    import cc5_api as _self
    srv.ACTION_MAP.update({
        "get_avatars":           lambda p: _self.get_avatars(),
        "get_avatar_info":       lambda p: _self.get_avatar_info(),
        "get_morph_catalog":     lambda p: _self.get_morph_catalog(),
        "search_morphs":         lambda p: _self.search_morphs(p["query"], p.get("category", "")),
        "get_morph_value":       lambda p: _self.get_morph_value(p["morph_id"]),
        "set_morph_value":       lambda p: _self.set_morph_value(p["morph_id"], float(p["value"])),
        "set_multiple_morphs":   lambda p: _self.set_multiple_morphs(p["morphs"]),
        "create_default_avatar": lambda p: _self.create_default_avatar(),
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
        "get_expression_info":   lambda p: _self.get_expression_info(),
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
            "/expression/set":   "set_expression",
            "/expression/reset": "reset_expression",
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
        })
    if hasattr(srv, "GET_ROUTES"):
        srv.GET_ROUTES.update({
            "/camera/info":      "get_camera_info",
            "/lights":           "get_lights",
            "/expressions":      "get_expression_info",
            "/material/info":    "get_material_info",
            # Tier 1: Content Management
            "/clothes":          "list_clothes",
            "/hair":             "list_hair",
            "/accessories":      "list_accessories",
            # Tier 4: Scene
            "/scene/objects":    "get_scene_objects",
            # Silent export polling
            "/export/head_mh/status": "get_export_status",
        })
    if hasattr(srv, "REQUIRED_PARAMS"):
        srv.REQUIRED_PARAMS.update({
            "set_camera_focal_length": ["focal_length"],
            "set_light_color":         ["light_name", "r", "g", "b"],
            "get_light_info":          ["light_name"],
            "set_light_multiplier":    ["light_name", "multiplier"],
            "set_light_active":        ["light_name", "active"],
            "set_light_shadow":        ["light_name"],
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
        })

    print("[CC5 MCP Bridge] Auto-patched ACTION_MAP + routes")


_auto_patch_server()
