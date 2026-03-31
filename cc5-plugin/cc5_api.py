"""
CC5 RLPy API wrapper functions.

Provides a clean interface over RLPy for character manipulation.
All functions MUST be called from the main thread (via QTimer queue).
"""

import json
from typing import Any

import RLPy


def get_avatars() -> list[dict[str, Any]]:
    """Get all avatars in the current scene."""
    avatars = RLPy.RScene.GetAvatars()
    result = []
    for avatar in avatars:
        result.append({
            "name": avatar.GetName(),
            "id": avatar.GetID(),
            "type": str(avatar.GetType()),
        })
    return result


def get_selected_avatar():
    """Get the first avatar in the scene (or None)."""
    avatars = RLPy.RScene.GetAvatars()
    if not avatars:
        return None
    return avatars[0]


def get_morph_catalog() -> dict[str, list[dict[str, str]]]:
    """
    Enumerate all available shaping morph IDs, grouped by category.
    Returns: { "category_name": [{"id": "...", "display_name": "..."}] }
    """
    avatar = get_selected_avatar()
    if not avatar:
        return {}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {}

    catalog: dict[str, list[dict[str, str]]] = {}
    # Note: Reallusion has a typo in their API - "Catergory" instead of "Category"
    categories = shaping_comp.GetShapingMorphCatergoryNames()

    for cat in categories:
        ids = shaping_comp.GetShapingMorphIDs(cat)
        names = shaping_comp.GetShapingMorphDisplayNames(cat)
        entries = []
        for i in range(len(ids)):
            entries.append({
                "id": ids[i],
                "display_name": names[i] if i < len(names) else ids[i],
            })
        catalog[cat] = entries

    return catalog


def get_morph_value(morph_id: str) -> float | None:
    """Get current value of a shaping morph slider."""
    avatar = get_selected_avatar()
    if not avatar:
        return None

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return None

    return shaping_comp.GetShapingMorphWeight(morph_id)


def set_morph_value(morph_id: str, value: float) -> dict[str, Any]:
    """Set a shaping morph slider value (0.0 - 1.0)."""
    avatar = get_selected_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component found"}

    value = max(0.0, min(1.0, value))
    shaping_comp.SetShapingMorphWeight(morph_id, value)
    RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)

    return {"success": True, "morph_id": morph_id, "value": value}


def set_multiple_morphs(morphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Set multiple morph values at once. Each entry: {"id": str, "value": float}."""
    avatar = get_selected_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    shaping_comp = avatar.GetAvatarShapingComponent()
    if not shaping_comp:
        return {"success": False, "error": "No shaping component found"}

    results = []
    for morph in morphs:
        morph_id = morph["id"]
        value = max(0.0, min(1.0, float(morph["value"])))
        shaping_comp.SetShapingMorphWeight(morph_id, value)
        results.append({"id": morph_id, "value": value})

    RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    return {"success": True, "applied": results}


def load_asset(file_path: str) -> dict[str, Any]:
    """Load a CC5 asset file (.iAvatar, .ccm, .iClothes, etc.)."""
    try:
        result = RLPy.RFileIO.LoadFile(file_path)
        return {"success": True, "path": file_path, "result": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_fbx(output_path: str, options_flags: int = 0) -> dict[str, Any]:
    """Export the current avatar as FBX."""
    avatar = get_selected_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    try:
        if options_flags == 0:
            options_flags = (
                RLPy.EExportFbxOptions_AutoSkinRigidMesh
                | RLPy.EExportFbxOptions_ExportRootMotion
            )
        result = RLPy.RFileIO.ExportFbxFile(avatar, output_path, options_flags)
        return {"success": True, "path": output_path, "result": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_avatar_info() -> dict[str, Any] | None:
    """Get detailed information about the current avatar."""
    avatar = get_selected_avatar()
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
                if weight != 0.0:
                    current_morphs[morph_id] = weight

    return {
        "name": avatar.GetName(),
        "id": avatar.GetID(),
        "active_morphs": current_morphs,
    }


def set_subdivision_level(level: int) -> dict[str, Any]:
    """Set HD subdivision level (0-2) for the current avatar."""
    avatar = get_selected_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    level = max(0, min(2, level))
    avatar.SetSubdivisionLevel(level)
    RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    return {"success": True, "level": level}
