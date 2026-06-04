# Implementation Plan: Missing Character Customization Features

## Overview

Add 21 new tools to the CC5 MCP Server across 5 tiers. Each feature requires changes in 4 layers:

1. **cc5_api.py** -- Python function wrapping RLPy calls
2. **server.py** -- HTTP route + dispatch registration
3. **cc5-bridge.ts** -- TypeScript HTTP client method
4. **src/tools/*.ts** -- MCP tool definition with Zod schema

New tool registration files: `src/tools/content.ts`, `src/tools/visibility.ts`, `src/tools/project.ts`

---

## Tier 1: Content Management (8 tools)

### 1.1 `list_clothes`

List all clothing currently on avatar.

**RLPy API:** `RIAvatar.GetClothes()` returns `ClothVector`. Each `RICloth` has `.GetName()`, `.GetID()`, `.GetClotheType()`.

**cc5_api.py:**
```python
def list_clothes(avatar_name: str = "") -> list[dict[str, Any]]:
    """List all clothing items on the avatar."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return []
    clothes = avatar.GetClothes()
    clothe_type_names = {
        RLPy.EClotheType_Upper: "Upper",
        RLPy.EClotheType_Lower: "Lower",
        RLPy.EClotheType_Shoes: "Shoes",
        RLPy.EClotheType_Gloves: "Gloves",
        RLPy.EClotheType_Accessory: "Accessory",
    }
    return [
        {
            "name": c.GetName(),
            "id": c.GetID(),
            "type": clothe_type_names.get(c.GetClotheType(), "Unknown"),
        }
        for c in clothes
    ]
```

**server.py:**
- Route: `GET /clothes` -> `"list_clothes"`
- ACTION_MAP: `"list_clothes": lambda p: cc5_api.list_clothes(p.get("avatar_name", ""))`
- REQUIRED_PARAMS: (none)

**cc5-bridge.ts:**
```typescript
async listClothes(avatarName?: string): Promise<ClothItem[]> {
  return this.request<ClothItem[]>("/clothes", "POST", { avatar_name: avatarName ?? "" });
}
```

**Tool (src/tools/content.ts):**
- Name: `list_clothes`
- Schema: `{ avatar_name?: string }`
- Description: "List all clothing items currently worn by the avatar (tops, bottoms, shoes, gloves)."

---

### 1.2 `list_hair`

List all hair pieces on avatar.

**RLPy API:** `RIAvatar.GetHairs()` returns `HairVector`. Each `RIHair` has `.GetName()`, `.GetID()`, `.GetHairType()`.

**cc5_api.py:**
```python
def list_hair(avatar_name: str = "") -> list[dict[str, Any]]:
    """List all hair items on the avatar."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return []
    hairs = avatar.GetHairs()
    return [
        {
            "name": h.GetName(),
            "id": h.GetID(),
            "type": str(h.GetHairType()) if hasattr(h, "GetHairType") else "Unknown",
        }
        for h in hairs
    ]
```

**server.py:**
- Route: `GET /hair` -> `"list_hair"`
- ACTION_MAP: `"list_hair": lambda p: cc5_api.list_hair(p.get("avatar_name", ""))`

**cc5-bridge.ts:**
```typescript
async listHair(avatarName?: string): Promise<HairItem[]> {
  return this.request<HairItem[]>("/hair", "POST", { avatar_name: avatarName ?? "" });
}
```

**Tool:** Name: `list_hair`, Schema: `{ avatar_name?: string }`

---

### 1.3 `list_accessories`

List all accessories (glasses, jewelry, etc.).

**RLPy API:** `RIAvatar.GetAccessories(bAll=True)` returns `AccessoryVector`. Each `RIAccessory` has `.GetName()`, `.GetID()`.

**cc5_api.py:**
```python
def list_accessories(avatar_name: str = "") -> list[dict[str, Any]]:
    """List all accessories on the avatar."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return []
    accessories = avatar.GetAccessories(True)
    return [
        {"name": a.GetName(), "id": a.GetID()}
        for a in accessories
    ]
```

**server.py:**
- Route: `GET /accessories` -> `"list_accessories"`
- ACTION_MAP: `"list_accessories": lambda p: cc5_api.list_accessories(p.get("avatar_name", ""))`

**cc5-bridge.ts:**
```typescript
async listAccessories(avatarName?: string): Promise<AccessoryItem[]> {
  return this.request<AccessoryItem[]>("/accessories", "POST", { avatar_name: avatarName ?? "" });
}
```

**Tool:** Name: `list_accessories`, Schema: `{ avatar_name?: string }`

---

### 1.4 `remove_item`

Remove a specific clothing/hair/accessory by name.

**RLPy API:** `RScene.RemoveObject(spObject)`. Find object by searching clothes, hairs, accessories by name.

**cc5_api.py:**
```python
def remove_item(item_name: str, avatar_name: str = "") -> dict[str, Any]:
    """Remove a clothing, hair, or accessory item by name."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}

    # Search clothes, hairs, accessories
    for getter in [avatar.GetClothes, avatar.GetHairs, lambda: avatar.GetAccessories(True)]:
        items = getter()
        for item in items:
            if item.GetName() == item_name:
                RLPy.RGlobal.BeginAction("Remove Item")
                RLPy.RScene.RemoveObject(item)
                RLPy.RGlobal.EndAction()
                _invalidate_caches()
                return {"success": True, "removed": item_name}

    return {"success": False, "error": f"Item not found: {item_name}"}
```

**server.py:**
- Route: `POST /item/remove` -> `"remove_item"`
- REQUIRED_PARAMS: `["item_name"]`
- ACTION_MAP: `"remove_item": lambda p: cc5_api.remove_item(p["item_name"], p.get("avatar_name", ""))`

**cc5-bridge.ts:**
```typescript
async removeItem(itemName: string, avatarName?: string): Promise<OperationResult> {
  return this.request<OperationResult>("/item/remove", "POST", {
    item_name: itemName,
    avatar_name: avatarName ?? "",
  });
}
```

**Tool:** Name: `remove_item`, Schema: `{ item_name: string, avatar_name?: string }`

---

### 1.5 `load_clothing`

Load .iClothes file onto avatar.

**RLPy API:** `RFileIO.LoadFile(filePath)` -- same as existing `load_asset`, but specialized with validation for `.iclothes`/`.iclothing` extensions only.

**cc5_api.py:**
```python
_CLOTHING_EXTENSIONS = {".iclothes", ".iclothing", ".ishoe"}

def load_clothing(file_path: str) -> dict[str, Any]:
    """Load a clothing file onto the current avatar."""
    error = _validate_path(file_path, _CLOTHING_EXTENSIONS)
    if error:
        return {"success": False, "error": error}
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        RLPy.RFileIO.LoadFile(file_path)
        _invalidate_caches()
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /clothing/load` -> `"load_clothing"`
- REQUIRED_PARAMS: `["file_path"]`

**cc5-bridge.ts:**
```typescript
async loadClothing(filePath: string): Promise<OperationResult> {
  return this.request<OperationResult>("/clothing/load", "POST", { file_path: filePath });
}
```

**Tool:** Name: `load_clothing`, Schema: `{ file_path: string }`, validates `.iclothes`/`.iclothing`/`.ishoe`

---

### 1.6 `load_hair`

Load .iHair file onto avatar.

**RLPy API:** `RFileIO.LoadFile(filePath)` with `.ihair` extension validation.

**cc5_api.py:**
```python
_HAIR_EXTENSIONS = {".ihair"}

def load_hair(file_path: str) -> dict[str, Any]:
    """Load a hair file onto the current avatar."""
    error = _validate_path(file_path, _HAIR_EXTENSIONS)
    if error:
        return {"success": False, "error": error}
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        RLPy.RFileIO.LoadFile(file_path)
        _invalidate_caches()
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /hair/load` -> `"load_hair"`
- REQUIRED_PARAMS: `["file_path"]`

**cc5-bridge.ts:**
```typescript
async loadHair(filePath: string): Promise<OperationResult> {
  return this.request<OperationResult>("/hair/load", "POST", { file_path: filePath });
}
```

**Tool:** Name: `load_hair`, Schema: `{ file_path: string }`, validates `.ihair`

---

### 1.7 `load_accessory`

Load .iAccessory file onto avatar.

**RLPy API:** `RFileIO.LoadFile(filePath)` with `.iaccessory` extension validation.

**cc5_api.py:**
```python
_ACCESSORY_EXTENSIONS = {".iaccessory"}

def load_accessory(file_path: str) -> dict[str, Any]:
    """Load an accessory file onto the current avatar."""
    error = _validate_path(file_path, _ACCESSORY_EXTENSIONS)
    if error:
        return {"success": False, "error": error}
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        RLPy.RFileIO.LoadFile(file_path)
        _invalidate_caches()
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /accessory/load` -> `"load_accessory"`
- REQUIRED_PARAMS: `["file_path"]`

**cc5-bridge.ts:**
```typescript
async loadAccessory(filePath: string): Promise<OperationResult> {
  return this.request<OperationResult>("/accessory/load", "POST", { file_path: filePath });
}
```

**Tool:** Name: `load_accessory`, Schema: `{ file_path: string }`, validates `.iaccessory`

---

### 1.8 `browse_content`

List available content files in CC5 library folders.

**RLPy API:**
- `RApplication.GetDefaultContentFolder(eFolderType)` -- returns path to default content folder
- `RApplication.GetCustomContentFolder(eFolderType)` -- returns path to custom content folder
- `RApplication.GetContentFilesInFolder(strFolder)` -- lists files in a folder
- `RApplication.GetContentFoldersInFolder(strFolder)` -- lists subfolders

Uses `EContentRootFolder_*` enum values to select content type.

**cc5_api.py:**
```python
_CONTENT_FOLDER_MAP = {
    "character": "EContentRootFolder_Character",
    "upper": "EContentRootFolder_Upper",
    "lower": "EContentRootFolder_Lower",
    "hair": "EContentRootFolder_Hair",  # may not exist -- fallback to EContentRootFolder_Character
    "accessory": "EContentRootFolder_Accessory",  # same
    "project": "EContentRootFolder_Project",
}

MAX_BROWSE_RESULTS = 200

def browse_content(content_type: str = "", folder_path: str = "") -> dict[str, Any]:
    """List available content files in CC5 library folders."""
    try:
        if folder_path:
            # Direct folder listing
            files = RLPy.RApplication.GetContentFilesInFolder(folder_path)
            folders = RLPy.RApplication.GetContentFoldersInFolder(folder_path)
            return {
                "path": folder_path,
                "folders": list(folders)[:MAX_BROWSE_RESULTS] if folders else [],
                "files": list(files)[:MAX_BROWSE_RESULTS] if files else [],
            }

        # Get folder by content type
        enum_name = _CONTENT_FOLDER_MAP.get(content_type.lower(), "")
        if enum_name and hasattr(RLPy, enum_name):
            folder_enum = getattr(RLPy, enum_name)
            default_path = RLPy.RApplication.GetDefaultContentFolder(folder_enum)
            custom_path = RLPy.RApplication.GetCustomContentFolder(folder_enum)
            result: dict[str, Any] = {"content_type": content_type}
            if default_path:
                files = RLPy.RApplication.GetContentFilesInFolder(default_path)
                result["default_path"] = default_path
                result["default_files"] = list(files)[:MAX_BROWSE_RESULTS] if files else []
            if custom_path:
                files = RLPy.RApplication.GetContentFilesInFolder(custom_path)
                result["custom_path"] = custom_path
                result["custom_files"] = list(files)[:MAX_BROWSE_RESULTS] if files else []
            return result

        # Fallback: list template and custom root paths
        template_path = RLPy.RApplication.GetTemplateDataPath()
        custom_path = RLPy.RApplication.GetCustomDataPath()
        return {
            "template_root": template_path,
            "custom_root": custom_path,
            "available_types": list(_CONTENT_FOLDER_MAP.keys()),
        }
    except Exception as e:
        return {"error": str(e)}
```

**server.py:**
- Route: `POST /content/browse` -> `"browse_content"`
- ACTION_MAP: `"browse_content": lambda p: cc5_api.browse_content(p.get("content_type", ""), p.get("folder_path", ""))`

**cc5-bridge.ts:**
```typescript
async browseContent(contentType?: string, folderPath?: string): Promise<ContentBrowseResult> {
  return this.request<ContentBrowseResult>("/content/browse", "POST", {
    content_type: contentType ?? "",
    folder_path: folderPath ?? "",
  });
}
```

**Tool:** Name: `browse_content`, Schema: `{ content_type?: string, folder_path?: string }`

---

## Tier 2: Material Enhancement (4 tools)

All use `RIMaterialComponent` methods already proven in the existing `set_diffuse_color` implementation.

### 2.1 `set_opacity`

**RLPy API:** `RIMaterialComponent.AddOpacityKey(kKey, strMeshName, strMaterialName, fWeight)` and `.GetOpacity(strMeshName, strMaterialName)`

**cc5_api.py:**
```python
def set_opacity(mesh_name: str, material_name: str, opacity: float) -> dict[str, Any]:
    """Set material opacity (0.0 = fully transparent, 1.0 = fully opaque)."""
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
        opacity = max(0.0, min(1.0, opacity))
        key = RLPy.RKey()
        key.SetTime(RLPy.RGlobal.GetTime())
        RLPy.RGlobal.BeginAction("Set Opacity")
        try:
            mat_comp.AddOpacityKey(key, mesh_name, material_name, opacity)
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "opacity": opacity}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /material/opacity/set` -> `"set_opacity"`
- REQUIRED_PARAMS: `["mesh_name", "material_name", "opacity"]`

**cc5-bridge.ts:**
```typescript
async setOpacity(meshName: string, materialName: string, opacity: number): Promise<OperationResult> {
  return this.request<OperationResult>("/material/opacity/set", "POST", {
    mesh_name: meshName, material_name: materialName, opacity,
  });
}
```

**Tool:** Name: `set_opacity`, Schema: `{ mesh_name, material_name, opacity: 0.0-1.0 }`

---

### 2.2 `set_glossiness`

**RLPy API:** `RIMaterialComponent.AddGlossinessKey(kKey, strMeshName, strMaterialName, fWeight)` and `.GetGlossinessWeight(strMeshName, strMaterialName)`

**cc5_api.py:**
```python
def set_glossiness(mesh_name: str, material_name: str, glossiness: float) -> dict[str, Any]:
    """Set material glossiness/shininess (0.0 = matte, 1.0 = mirror-like)."""
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
        glossiness = max(0.0, min(1.0, glossiness))
        key = RLPy.RKey()
        key.SetTime(RLPy.RGlobal.GetTime())
        RLPy.RGlobal.BeginAction("Set Glossiness")
        try:
            mat_comp.AddGlossinessKey(key, mesh_name, material_name, glossiness)
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "glossiness": glossiness}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /material/glossiness/set` -> `"set_glossiness"`
- REQUIRED_PARAMS: `["mesh_name", "material_name", "glossiness"]`

**cc5-bridge.ts:**
```typescript
async setGlossiness(meshName: string, materialName: string, glossiness: number): Promise<OperationResult> {
  return this.request<OperationResult>("/material/glossiness/set", "POST", {
    mesh_name: meshName, material_name: materialName, glossiness,
  });
}
```

**Tool:** Name: `set_glossiness`, Schema: `{ mesh_name, material_name, glossiness: 0.0-1.0 }`

---

### 2.3 `set_specular`

**RLPy API:** `RIMaterialComponent.AddSpecularKey(kKey, strMeshName, strMaterialName, ...)` (overloaded -- accepts color or weight). Also `.GetSpecularColor()`, `.GetSpecularWeight()`.

**cc5_api.py:**
```python
def set_specular(mesh_name: str, material_name: str, weight: float,
                 r: float = -1.0, g: float = -1.0, b: float = -1.0) -> dict[str, Any]:
    """Set specular weight and optionally specular color."""
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
        weight = max(0.0, min(1.0, weight))
        key = RLPy.RKey()
        key.SetTime(RLPy.RGlobal.GetTime())
        RLPy.RGlobal.BeginAction("Set Specular")
        try:
            if r >= 0 and g >= 0 and b >= 0:
                color = RLPy.RRgb(max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)))
                mat_comp.AddSpecularKey(key, mesh_name, material_name, weight, color)
            else:
                mat_comp.AddSpecularKey(key, mesh_name, material_name, weight)
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "weight": weight}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /material/specular/set` -> `"set_specular"`
- REQUIRED_PARAMS: `["mesh_name", "material_name", "weight"]`

**cc5-bridge.ts:**
```typescript
async setSpecular(meshName: string, materialName: string, weight: number,
                  r?: number, g?: number, b?: number): Promise<OperationResult> {
  return this.request<OperationResult>("/material/specular/set", "POST", {
    mesh_name: meshName, material_name: materialName, weight,
    ...(r !== undefined && { r, g, b }),
  });
}
```

**Tool:** Name: `set_specular`, Schema: `{ mesh_name, material_name, weight: 0.0-1.0, r?, g?, b? }`

---

### 2.4 `load_texture`

Load an image texture to a material channel.

**RLPy API:** `RIMaterialComponent.LoadImageToTexture(strMeshName, strMaterialName, eChannel, strImagePath)`. Channel is `EMaterialTextureChannel_*` enum.

**cc5_api.py:**
```python
_TEXTURE_CHANNEL_MAP = {
    "diffuse": "EMaterialTextureChannel_Diffuse",
    "specular": "EMaterialTextureChannel_Specular",
    "normal": "EMaterialTextureChannel_Normal",
    "bump": "EMaterialTextureChannel_Bump",
    "opacity": "EMaterialTextureChannel_Opacity",
    "glow": "EMaterialTextureChannel_Glow",
    "displacement": "EMaterialTextureChannel_Displacement",
    "ao": "EMaterialTextureChannel_AmbientOcclusion",
    "roughness": "EMaterialTextureChannel_Roughness",
    "metallic": "EMaterialTextureChannel_Metallic",
    "reflection": "EMaterialTextureChannel_Reflection",
}

_TEXTURE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tif", ".tiff", ".exr"}

def load_texture(mesh_name: str, material_name: str, channel: str, image_path: str) -> dict[str, Any]:
    """Load an image texture to a material channel."""
    error = _validate_material_names(mesh_name, material_name)
    if error:
        return {"success": False, "error": error}

    # Validate image path
    if "\x00" in image_path or ".." in image_path:
        return {"success": False, "error": "Invalid image path"}
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in _TEXTURE_IMAGE_EXTENSIONS:
        return {"success": False, "error": f"Unsupported image format: {ext}"}
    if not os.path.exists(image_path):
        return {"success": False, "error": f"File not found: {image_path}"}

    # Resolve channel enum
    channel_key = channel.lower().replace(" ", "")
    enum_name = _TEXTURE_CHANNEL_MAP.get(channel_key)
    if not enum_name or not hasattr(RLPy, enum_name):
        return {"success": False, "error": f"Unknown channel: {channel}. Available: {list(_TEXTURE_CHANNEL_MAP.keys())}"}
    channel_enum = getattr(RLPy, enum_name)

    avatar = get_first_avatar()
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp, error = _get_valid_mesh_material(avatar, mesh_name, material_name)
    if error:
        return {"success": False, "error": error}
    try:
        RLPy.RGlobal.BeginAction("Load Texture")
        try:
            mat_comp.LoadImageToTexture(mesh_name, material_name, channel_enum, image_path)
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
        finally:
            RLPy.RGlobal.EndAction()
        return {"success": True, "mesh": mesh_name, "material": material_name, "channel": channel}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /material/texture/load` -> `"load_texture"`
- REQUIRED_PARAMS: `["mesh_name", "material_name", "channel", "image_path"]`

**cc5-bridge.ts:**
```typescript
async loadTexture(meshName: string, materialName: string,
                  channel: string, imagePath: string): Promise<OperationResult> {
  return this.request<OperationResult>("/material/texture/load", "POST", {
    mesh_name: meshName, material_name: materialName, channel, image_path: imagePath,
  });
}
```

**Tool:** Name: `load_texture`, Schema: `{ mesh_name, material_name, channel: string, image_path: string }`
Description mentions available channels: diffuse, specular, normal, bump, opacity, glow, displacement, ao, roughness, metallic, reflection.

---

## Tier 3: Advanced Appearance (4 tools)

These are convenience shortcuts that internally use `set_diffuse_color` on specific well-known mesh/material names.

### 3.1 `set_eye_color`

**RLPy API:** Uses `set_diffuse_color` on the eye iris material. Typical mesh: `"CC_Base_Eye"`, material: `"Std_Eye_R"` / `"Std_Eye_L"`. The function auto-discovers the correct mesh/material by searching for eye-related names.

**cc5_api.py:**
```python
_EYE_MATERIAL_HINTS = ["eye_r", "eye_l", "iris", "std_eye"]

def set_eye_color(r: float, g: float, b: float, avatar_name: str = "") -> dict[str, Any]:
    """Change iris/eye color by setting diffuse color on eye materials."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return {"success": False, "error": "No avatar in scene"}
    mat_comp = avatar.GetMaterialComponent()
    if not mat_comp:
        return {"success": False, "error": "No material component"}

    r, g, b = max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b))
    color = RLPy.RRgb(r, g, b)
    key = RLPy.RKey()
    key.SetTime(RLPy.RGlobal.GetTime())
    applied = []

    meshes = avatar.GetMeshNames(True) if hasattr(avatar, "GetMeshNames") else []
    RLPy.RGlobal.BeginAction("Set Eye Color")
    try:
        for mesh in meshes:
            materials = mat_comp.GetMaterialNames(mesh)
            for mat in (materials or []):
                mat_lower = mat.lower()
                if any(hint in mat_lower for hint in _EYE_MATERIAL_HINTS):
                    mat_comp.AddDiffuseKey(key, mesh, mat, color)
                    applied.append(f"{mesh}/{mat}")
        if applied:
            RLPy.RGlobal.ObjectModified(avatar, RLPy.EObjectModifiedType_Attribute)
    finally:
        RLPy.RGlobal.EndAction()

    if not applied:
        return {"success": False, "error": "No eye materials found. Use get_material_info to find eye material names."}
    return {"success": True, "applied_to": applied}
```

**server.py:**
- Route: `POST /appearance/eye_color` -> `"set_eye_color"`
- REQUIRED_PARAMS: `["r", "g", "b"]`

**cc5-bridge.ts:**
```typescript
async setEyeColor(r: number, g: number, b: number, avatarName?: string): Promise<OperationResult> {
  return this.request<OperationResult>("/appearance/eye_color", "POST", {
    r, g, b, avatar_name: avatarName ?? "",
  });
}
```

**Tool:** Name: `set_eye_color`, Schema: `{ r, g, b: 0.0-1.0, avatar_name?: string }`

---

### 3.2 `set_hair_color`

Same pattern as eye color but targets hair materials.

**cc5_api.py:**
```python
_HAIR_MATERIAL_HINTS = ["hair", "strand", "scalp"]

def set_hair_color(r: float, g: float, b: float, avatar_name: str = "") -> dict[str, Any]:
    """Change hair color by setting diffuse on hair materials."""
    # Same pattern: iterate meshes/materials, match hints, apply diffuse color
    # Also search on RIHair objects via avatar.GetHairs() -> each has GetMaterialComponent()
```

**server.py:** Route: `POST /appearance/hair_color`, REQUIRED_PARAMS: `["r", "g", "b"]`

---

### 3.3 `set_lip_color`

Targets lip materials (hints: `"lip"`, `"mouth"`, `"std_lip"`).

**cc5_api.py:**
```python
_LIP_MATERIAL_HINTS = ["lip", "mouth"]

def set_lip_color(r: float, g: float, b: float, avatar_name: str = "") -> dict[str, Any]:
    """Change lip color."""
    # Same pattern as set_eye_color
```

**server.py:** Route: `POST /appearance/lip_color`, REQUIRED_PARAMS: `["r", "g", "b"]`

---

### 3.4 `set_nail_color`

Targets nail materials (hints: `"nail"`, `"fingernail"`, `"toenail"`).

**cc5_api.py:**
```python
_NAIL_MATERIAL_HINTS = ["nail", "fingernail", "toenail"]

def set_nail_color(r: float, g: float, b: float, avatar_name: str = "") -> dict[str, Any]:
    """Change nail color."""
    # Same pattern as set_eye_color
```

**server.py:** Route: `POST /appearance/nail_color`, REQUIRED_PARAMS: `["r", "g", "b"]`

---

## Tier 4: Visibility & Scene (3 tools)

### 4.1 `set_visible`

Show/hide an object (avatar, prop, cloth, hair, etc.).

**RLPy API:**
- `RIAvatar.SetVisible(kTime, bVisible)` / `RIAvatar.IsVisible(kTime)`
- `RIProp.SetVisible(kTime, bVisible)` / `RIProp.IsVisible(kTime)`
- `RScene.Show(spObject)` / `RScene.Hide(spObject)` -- works on any object

**cc5_api.py:**
```python
def set_visible(object_name: str, visible: bool) -> dict[str, Any]:
    """Show or hide an object in the scene by name."""
    # Search across all object types
    for obj_type in [
        RLPy.EObjectType_Avatar, RLPy.EObjectType_Prop,
        RLPy.EObjectType_Hair, RLPy.EObjectType_Cloth,
        RLPy.EObjectType_Accessory,
    ]:
        obj = RLPy.RScene.FindObject(obj_type, object_name)
        if obj:
            RLPy.RGlobal.BeginAction("Set Visible")
            if visible:
                RLPy.RScene.Show(obj)
            else:
                RLPy.RScene.Hide(obj)
            RLPy.RGlobal.EndAction()
            return {"success": True, "object": object_name, "visible": visible}

    return {"success": False, "error": f"Object not found: {object_name}"}
```

**server.py:**
- Route: `POST /object/visible` -> `"set_visible"`
- REQUIRED_PARAMS: `["object_name", "visible"]`

**cc5-bridge.ts:**
```typescript
async setVisible(objectName: string, visible: boolean): Promise<OperationResult> {
  return this.request<OperationResult>("/object/visible", "POST", {
    object_name: objectName, visible,
  });
}
```

**Tool:** Name: `set_visible`, Schema: `{ object_name: string, visible: boolean }`

---

### 4.2 `get_scene_objects`

List all objects in the scene (not just avatars).

**RLPy API:** `RScene.FindObjects(eType)` for each `EObjectType_*`, or `RScene.GetAvatars()`, `RScene.GetProps()`, `RScene.GetCameras()`, etc.

**cc5_api.py:**
```python
def get_scene_objects() -> dict[str, list[dict[str, Any]]]:
    """List all objects in the scene, grouped by type."""
    result: dict[str, list[dict[str, Any]]] = {}
    type_map = {
        "avatars": RLPy.EObjectType_Avatar,
        "props": RLPy.EObjectType_Prop,
        "cameras": RLPy.EObjectType_Camera,
        "lights": RLPy.EObjectType_Light,
        "hair": RLPy.EObjectType_Hair,
        "clothes": RLPy.EObjectType_Cloth,
        "accessories": RLPy.EObjectType_Accessory,
        "particles": RLPy.EObjectType_Particle,
    }
    for type_name, obj_type in type_map.items():
        try:
            objects = RLPy.RScene.FindObjects(obj_type)
            if objects:
                result[type_name] = [
                    {"name": o.GetName(), "id": o.GetID()}
                    for o in objects
                ]
        except Exception:
            pass
    return result
```

**server.py:**
- Route: `GET /scene/objects` -> `"get_scene_objects"`
- ACTION_MAP: `"get_scene_objects": lambda p: cc5_api.get_scene_objects()`

**cc5-bridge.ts:**
```typescript
async getSceneObjects(): Promise<SceneObjects> {
  return this.request<SceneObjects>("/scene/objects");
}
```

**Tool:** Name: `get_scene_objects`, Schema: `{}`

---

### 4.3 `set_light_intensity`

Set light brightness/multiplier.

**RLPy API:** `RILight.SetMultiplier(kTime, fMultiplier)` and `.GetMultiplier()`

**cc5_api.py:**
```python
def set_light_intensity(light_name: str, multiplier: float) -> dict[str, Any]:
    """Set light brightness multiplier."""
    for light_type in [
        RLPy.EObjectType_SpotLight,
        RLPy.EObjectType_PointLight,
        RLPy.EObjectType_DirectionalLight,
    ]:
        light = RLPy.RScene.FindObject(light_type, light_name)
        if light:
            RLPy.RGlobal.BeginAction("Set Light Intensity")
            light.SetMultiplier(RLPy.RGlobal.GetTime(), multiplier)
            RLPy.RGlobal.ObjectModified(light, RLPy.EObjectModifiedType_Attribute)
            RLPy.RGlobal.EndAction()
            return {"success": True, "light": light_name, "multiplier": multiplier}
    return {"success": False, "error": f"Light not found: {light_name}"}
```

**server.py:**
- Route: `POST /light/intensity` -> `"set_light_intensity"`
- REQUIRED_PARAMS: `["light_name", "multiplier"]`

**cc5-bridge.ts:**
```typescript
async setLightIntensity(lightName: string, multiplier: number): Promise<OperationResult> {
  return this.request<OperationResult>("/light/intensity", "POST", {
    light_name: lightName, multiplier,
  });
}
```

**Tool:** Name: `set_light_intensity`, Schema: `{ light_name: string, multiplier: number (0.0-10.0) }`

---

## Tier 5: Quality of Life (2 tools)

### 5.1 `save_project`

**RLPy API:** `RFileIO.SaveProject(strSavePath)` -- saves the current project to the specified path.

**cc5_api.py:**
```python
def save_project(save_path: str = "") -> dict[str, Any]:
    """Save the current CC5 project."""
    try:
        if save_path:
            if "\x00" in save_path or ".." in save_path:
                return {"success": False, "error": "Invalid path"}
            if not save_path.lower().endswith(".ccproject"):
                return {"success": False, "error": "Save path must end with .ccProject"}
            dir_path = os.path.dirname(save_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            RLPy.RFileIO.SaveProject(save_path)
        else:
            # Save to current project path
            current_path = RLPy.RApplication.GetCurrentProjectPath()
            if not current_path:
                return {"success": False, "error": "No current project path. Provide save_path."}
            RLPy.RFileIO.SaveProject(current_path)
            save_path = current_path
        return {"success": True, "path": save_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**server.py:**
- Route: `POST /project/save` -> `"save_project"`
- ACTION_MAP: `"save_project": lambda p: cc5_api.save_project(p.get("save_path", ""))`

**cc5-bridge.ts:**
```typescript
async saveProject(savePath?: string): Promise<OperationResult> {
  return this.request<OperationResult>("/project/save", "POST", {
    save_path: savePath ?? "",
  });
}
```

**Tool:** Name: `save_project`, Schema: `{ save_path?: string }`

---

### 5.2 `describe_outfit`

Natural language description of current clothing/hair/accessories.

**RLPy API:** Combines results from `list_clothes()`, `list_hair()`, `list_accessories()`. No new RLPy calls needed -- this is a composition tool.

**cc5_api.py:**
```python
def describe_outfit(avatar_name: str = "") -> dict[str, Any]:
    """Get a structured description of the avatar's current outfit."""
    avatar = get_avatar_by_name(avatar_name)
    if not avatar:
        return {"error": "No avatar in scene"}

    clothes = list_clothes(avatar_name)
    hairs = list_hair(avatar_name)
    accessories = list_accessories(avatar_name)

    return {
        "avatar_name": avatar.GetName(),
        "clothes": clothes,
        "hair": hairs,
        "accessories": accessories,
        "summary": {
            "clothing_count": len(clothes),
            "hair_count": len(hairs),
            "accessory_count": len(accessories),
        },
    }
```

**server.py:**
- Route: `GET /outfit/describe` or `POST /outfit/describe` -> `"describe_outfit"`
- ACTION_MAP: `"describe_outfit": lambda p: cc5_api.describe_outfit(p.get("avatar_name", ""))`

**cc5-bridge.ts:**
```typescript
async describeOutfit(avatarName?: string): Promise<OutfitDescription> {
  return this.request<OutfitDescription>("/outfit/describe", "POST", {
    avatar_name: avatarName ?? "",
  });
}
```

**Tool:** Name: `describe_outfit`, Schema: `{ avatar_name?: string }`

---

## New TypeScript Type Definitions (types.ts additions)

```typescript
export interface ClothItem {
  name: string;
  id: number;
  type: string;
}

export interface HairItem {
  name: string;
  id: number;
  type: string;
}

export interface AccessoryItem {
  name: string;
  id: number;
}

export interface ContentBrowseResult {
  path?: string;
  content_type?: string;
  folders?: string[];
  files?: string[];
  default_path?: string;
  default_files?: string[];
  custom_path?: string;
  custom_files?: string[];
  template_root?: string;
  custom_root?: string;
  available_types?: string[];
  error?: string;
}

export interface SceneObjects {
  [typeName: string]: Array<{ name: string; id: number }>;
}

export interface OutfitDescription {
  avatar_name: string;
  clothes: ClothItem[];
  hair: HairItem[];
  accessories: AccessoryItem[];
  summary: {
    clothing_count: number;
    hair_count: number;
    accessory_count: number;
  };
  error?: string;
}
```

---

## New Tool Registration Files

### src/tools/content.ts
Registers: `list_clothes`, `list_hair`, `list_accessories`, `remove_item`, `load_clothing`, `load_hair`, `load_accessory`, `browse_content`, `describe_outfit`

### src/tools/visibility.ts
Registers: `set_visible`, `get_scene_objects`

### src/tools/project.ts
Registers: `save_project`

### Existing file modifications:
- **src/tools/material.ts** -- Add `set_opacity`, `set_glossiness`, `set_specular`, `load_texture`
- **src/tools/light.ts** -- Add `set_light_intensity`
- **src/tools/character.ts** -- Add `set_eye_color`, `set_hair_color`, `set_lip_color`, `set_nail_color`

### src/index.ts additions:
```typescript
import { registerContentTools } from "./tools/content.js";
import { registerVisibilityTools } from "./tools/visibility.js";
import { registerProjectTools } from "./tools/project.js";
// ... in main():
registerContentTools(server, bridge);
registerVisibilityTools(server, bridge);
registerProjectTools(server, bridge);
```

---

## Implementation Checklist

### Phase 1: Python API Layer (cc5_api.py)

- [ ] 1.1 `list_clothes()` -- uses `avatar.GetClothes()`
- [ ] 1.2 `list_hair()` -- uses `avatar.GetHairs()`
- [ ] 1.3 `list_accessories()` -- uses `avatar.GetAccessories(True)`
- [ ] 1.4 `remove_item()` -- uses `RScene.RemoveObject()`
- [ ] 1.5 `load_clothing()` -- uses `RFileIO.LoadFile()` with `.iclothes` validation
- [ ] 1.6 `load_hair()` -- uses `RFileIO.LoadFile()` with `.ihair` validation
- [ ] 1.7 `load_accessory()` -- uses `RFileIO.LoadFile()` with `.iaccessory` validation
- [ ] 1.8 `browse_content()` -- uses `RApplication.GetDefaultContentFolder()`, `GetContentFilesInFolder()`
- [ ] 2.1 `set_opacity()` -- uses `mat_comp.AddOpacityKey()`
- [ ] 2.2 `set_glossiness()` -- uses `mat_comp.AddGlossinessKey()`
- [ ] 2.3 `set_specular()` -- uses `mat_comp.AddSpecularKey()`
- [ ] 2.4 `load_texture()` -- uses `mat_comp.LoadImageToTexture()`
- [ ] 3.1 `set_eye_color()` -- uses `mat_comp.AddDiffuseKey()` on eye materials
- [ ] 3.2 `set_hair_color()` -- uses `mat_comp.AddDiffuseKey()` on hair materials
- [ ] 3.3 `set_lip_color()` -- uses `mat_comp.AddDiffuseKey()` on lip materials
- [ ] 3.4 `set_nail_color()` -- uses `mat_comp.AddDiffuseKey()` on nail materials
- [ ] 4.1 `set_visible()` -- uses `RScene.Show()`/`RScene.Hide()`
- [ ] 4.2 `get_scene_objects()` -- uses `RScene.FindObjects()` per type
- [ ] 4.3 `set_light_intensity()` -- uses `light.SetMultiplier()`
- [ ] 5.1 `save_project()` -- uses `RFileIO.SaveProject()`
- [ ] 5.2 `describe_outfit()` -- composes list_clothes/hair/accessories

### Phase 2: HTTP Bridge (server.py)

- [ ] Add all 21 entries to `ACTION_MAP`
- [ ] Add 14 POST routes to `POST_ROUTES`
- [ ] Add 3 GET routes to `GET_ROUTES`
- [ ] Add 12 entries to `REQUIRED_PARAMS`
- [ ] Update `_auto_patch_server()` in cc5_api.py

### Phase 3: TypeScript Bridge (cc5-bridge.ts)

- [ ] Add 21 new methods to `CC5Bridge` class
- [ ] Add new type interfaces to `types.ts`

### Phase 4: MCP Tool Definitions

- [ ] Create `src/tools/content.ts` (9 tools)
- [ ] Create `src/tools/visibility.ts` (2 tools)
- [ ] Create `src/tools/project.ts` (1 tool)
- [ ] Extend `src/tools/material.ts` (+4 tools)
- [ ] Extend `src/tools/light.ts` (+1 tool)
- [ ] Extend `src/tools/character.ts` (+4 tools)
- [ ] Update `src/index.ts` to register new tool files

### Phase 5: Integration & Testing

- [ ] Build: `npm run build`
- [ ] Verify bridge connectivity: `check_cc5_connection`
- [ ] Test each new tool via MCP client
- [ ] Test error paths (missing avatar, bad file paths, unknown materials)
- [ ] Update CLAUDE.md tool count and table

---

## Route Summary (all 21 new endpoints)

| Method | Route | Action | Required Params |
|--------|-------|--------|-----------------|
| POST | /clothes | list_clothes | -- |
| POST | /hair | list_hair | -- |
| POST | /accessories | list_accessories | -- |
| POST | /item/remove | remove_item | item_name |
| POST | /clothing/load | load_clothing | file_path |
| POST | /hair/load | load_hair | file_path |
| POST | /accessory/load | load_accessory | file_path |
| POST | /content/browse | browse_content | -- |
| POST | /material/opacity/set | set_opacity | mesh_name, material_name, opacity |
| POST | /material/glossiness/set | set_glossiness | mesh_name, material_name, glossiness |
| POST | /material/specular/set | set_specular | mesh_name, material_name, weight |
| POST | /material/texture/load | load_texture | mesh_name, material_name, channel, image_path |
| POST | /appearance/eye_color | set_eye_color | r, g, b |
| POST | /appearance/hair_color | set_hair_color | r, g, b |
| POST | /appearance/lip_color | set_lip_color | r, g, b |
| POST | /appearance/nail_color | set_nail_color | r, g, b |
| POST | /object/visible | set_visible | object_name, visible |
| GET | /scene/objects | get_scene_objects | -- |
| POST | /light/intensity | set_light_intensity | light_name, multiplier |
| POST | /project/save | save_project | -- |
| POST | /outfit/describe | describe_outfit | -- |

---

## Risk Notes

1. **Content folder enumeration** -- `EContentRootFolder_*` enum values for "Hair" and "Accessory" may not exist in CC5 (they exist for Upper/Lower/Character). Fallback to `GetTemplateDataPath()` + manual subfolder search if needed.
2. **Hair material access** -- Hair objects (`RIHair`) have their own `GetMaterialComponent()`, separate from the avatar's. `set_hair_color` must check both the avatar's mesh materials AND each hair object's material component.
3. **AddSpecularKey overload** -- The RLPy wrapper shows `*args` for this method. Test both (weight-only) and (weight+color) signatures; one may fail in some CC5 versions.
4. **RScene.Show/Hide** -- These are documented but may behave differently from `SetVisible(kTime, bVisible)`. Test both approaches.
5. **SaveProject path** -- May trigger a file dialog in CC5 if the path is empty. Always provide an explicit path or use `GetCurrentProjectPath()`.
