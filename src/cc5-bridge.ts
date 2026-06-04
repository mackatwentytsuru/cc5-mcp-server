/**
 * HTTP client for communicating with the CC5 Python bridge plugin.
 */

import type {
  CC5Avatar,
  CC5Response,
  MorphCatalog,
  AvatarInfo,
  OperationResult,
  CreateAvatarResult,
  CaptureResult,
  MorphSetRequest,
  CameraInfo,
  FocalLengthResult,
  LightInfo,
  LightColorResult,
  LightDetailInfo,
  LightMultiplierResult,
  ExpressionInfo,
  ResetMorphsResult,
  MaterialInfo,
  DiffuseColor,
  SetDiffuseColorResult,
  MaterialProperties,
  SetMaterialPropertyResult,
  ClothingItem,
  HairItem,
  AccessoryItem,
  RemoveItemResult,
  ColorResult,
  SetVisibleResult,
  SceneObject,
  ExportFbxOptions,
  ExportFbxResult,
  BakeSkinResult,
  ExportHeadMetaHumanResult,
} from "./types.js";

const DEFAULT_BASE_URL = "http://127.0.0.1:5101";
const _rawTimeout = parseInt(process.env.CC5_REQUEST_TIMEOUT_MS ?? "30000", 10);
const REQUEST_TIMEOUT_MS = Number.isFinite(_rawTimeout) && _rawTimeout > 0 && _rawTimeout <= 300_000
  ? _rawTimeout
  : 30_000;

export class CC5Bridge {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    const url = baseUrl ?? process.env.CC5_BRIDGE_URL ?? DEFAULT_BASE_URL;
    try {
      const parsed = new URL(url);
      if (!["127.0.0.1", "localhost", "::1", "[::1]"].includes(parsed.hostname)) {
        throw new Error(`CC5_BRIDGE_URL must point to localhost, got: ${parsed.hostname}`);
      }
    } catch (e) {
      if (e instanceof TypeError) {
        throw new Error(`Invalid CC5_BRIDGE_URL: ${url}`);
      }
      throw e;
    }
    this.baseUrl = url;
  }

  private async request<T>(
    path: string,
    method: "GET" | "POST" = "GET",
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const options: RequestInit = {
        method,
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
      };

      if (body !== undefined) {
        options.body = JSON.stringify(body);
      }

      const response = await fetch(`${this.baseUrl}${path}`, options);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(
          `CC5 bridge error (${response.status}): ${errorBody}`
        );
      }

      const data = (await response.json()) as CC5Response<T>;

      if (data.error) {
        throw new Error(`CC5 error: ${data.error}`);
      }

      if (data.result === undefined) {
        throw new Error("CC5 bridge returned empty result");
      }

      return data.result;
    } finally {
      clearTimeout(timeout);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.request<{ status: string }>("/health");
      return true;
    } catch (err) {
      console.error("[CC5 Bridge] healthCheck failed:", err);
      return false;
    }
  }

  async getAvatars(): Promise<CC5Avatar[]> {
    return this.request<CC5Avatar[]>("/avatars");
  }

  async getAvatarInfo(): Promise<AvatarInfo | null> {
    return this.request<AvatarInfo | null>("/avatar/info");
  }

  async searchMorphs(query: string, category?: string): Promise<Array<{ id: string; display_name: string; category: string }>> {
    return this.request<Array<{ id: string; display_name: string; category: string }>>("/morphs/search", "POST", {
      query,
      category: category ?? "",
    });
  }

  async getMorphCatalog(): Promise<MorphCatalog> {
    return this.request<MorphCatalog>("/morphs/catalog");
  }

  async getMorphValue(
    morphId: string,
  ): Promise<{ success: boolean; morph_id?: string; value?: number; error?: string }> {
    return this.request("/morph/get", "POST", {
      morph_id: morphId,
    });
  }

  async setMorph(morphId: string, value: number): Promise<OperationResult> {
    return this.request<OperationResult>("/morph/set", "POST", {
      morph_id: morphId,
      value,
    });
  }

  async setMultipleMorphs(
    morphs: MorphSetRequest[]
  ): Promise<OperationResult> {
    return this.request<OperationResult>("/morphs/set", "POST", { morphs });
  }

  async createDefaultAvatar(): Promise<CreateAvatarResult> {
    return this.request<CreateAvatarResult>("/avatar/create", "POST", {});
  }

  async loadAsset(filePath: string): Promise<OperationResult> {
    return this.request<OperationResult>("/asset/load", "POST", {
      file_path: filePath,
    });
  }

  async exportFbx(
    outputPath: string,
    options: number = 0,
    extra: ExportFbxOptions = {},
  ): Promise<ExportFbxResult> {
    const body: Record<string, unknown> = {
      output_path: outputPath,
      options,
    };
    if (extra.target_tool !== undefined) body.target_tool = extra.target_tool;
    if (extra.sub_d_level !== undefined) body.sub_d_level = extra.sub_d_level;
    if (extra.include_current_pose !== undefined) body.include_current_pose = extra.include_current_pose;
    if (extra.delete_hidden_faces !== undefined) body.delete_hidden_faces = extra.delete_hidden_faces;
    if (extra.use_smooth_mesh !== undefined) body.use_smooth_mesh = extra.use_smooth_mesh;
    if (extra.remove_eyelash !== undefined) body.remove_eyelash = extra.remove_eyelash;
    if (extra.remove_tearline_occlusion !== undefined) body.remove_tearline_occlusion = extra.remove_tearline_occlusion;
    return this.request<ExportFbxResult>("/export/fbx", "POST", body);
  }

  // --- Mesh-to-MetaHuman pipeline ---

  async bakeSkinTextures(resolution: number = 4096): Promise<BakeSkinResult> {
    return this.request<BakeSkinResult>("/skin/bake", "POST", { resolution });
  }

  async exportHeadMetaHuman(
    outputDir: string,
    characterName: string,
    gender: "Male" | "Female" = "Female",
  ): Promise<ExportHeadMetaHumanResult> {
    return this.request<ExportHeadMetaHumanResult>("/export/head_mh", "POST", {
      output_dir: outputDir,
      character_name: characterName,
      gender,
    });
  }

  async captureViewport(outputPath?: string, width?: number, height?: number): Promise<CaptureResult> {
    const body: Record<string, unknown> = {};
    if (outputPath) body.output_path = outputPath;
    if (width !== undefined) body.width = width;
    if (height !== undefined) body.height = height;
    return this.request<CaptureResult>("/viewport/capture", "POST", body);
  }

  async setSubdivisionLevel(level: number): Promise<OperationResult> {
    return this.request<OperationResult>("/subdivision", "POST", { level });
  }

  // --- Undo / Redo ---

  async undo(): Promise<OperationResult> {
    return this.request<OperationResult>("/undo", "POST", {});
  }

  async redo(): Promise<OperationResult> {
    return this.request<OperationResult>("/redo", "POST", {});
  }

  // --- Camera ---

  async getCameraInfo(): Promise<CameraInfo> {
    return this.request<CameraInfo>("/camera/info");
  }

  async setCameraFocalLength(focalLength: number): Promise<FocalLengthResult> {
    return this.request<FocalLengthResult>("/camera/focal", "POST", {
      focal_length: focalLength,
    });
  }

  // --- Lights ---

  async getLights(): Promise<LightInfo[]> {
    return this.request<LightInfo[]>("/lights");
  }

  async setLightColor(
    lightName: string,
    r: number,
    g: number,
    b: number
  ): Promise<LightColorResult> {
    return this.request<LightColorResult>("/light/color", "POST", {
      light_name: lightName,
      r,
      g,
      b,
    });
  }

  async getLightInfo(lightName: string): Promise<LightDetailInfo> {
    return this.request<LightDetailInfo>("/light/info", "POST", {
      light_name: lightName,
    });
  }

  async setLightMultiplier(
    lightName: string,
    multiplier: number
  ): Promise<LightMultiplierResult> {
    return this.request<LightMultiplierResult>("/light/multiplier", "POST", {
      light_name: lightName,
      multiplier,
    });
  }

  // --- Expressions ---

  async getExpressionInfo(): Promise<ExpressionInfo> {
    return this.request<ExpressionInfo>("/expressions");
  }

  // --- Reset Morphs ---

  async resetAllMorphs(avatarName?: string): Promise<ResetMorphsResult> {
    const body: Record<string, unknown> = {};
    if (avatarName) body.avatar_name = avatarName;
    return this.request<ResetMorphsResult>("/morphs/reset", "POST", body);
  }

  // --- Material / Texture ---

  async getMaterialInfo(avatarName?: string): Promise<MaterialInfo> {
    const body: Record<string, unknown> = {};
    if (avatarName) body.avatar_name = avatarName;
    return this.request<MaterialInfo>("/material/info", "POST", body);
  }

  async getDiffuseColor(meshName: string, materialName: string): Promise<DiffuseColor> {
    return this.request<DiffuseColor>("/material/color/get", "POST", {
      mesh_name: meshName,
      material_name: materialName,
    });
  }

  async setDiffuseColor(
    meshName: string,
    materialName: string,
    r: number,
    g: number,
    b: number
  ): Promise<SetDiffuseColorResult> {
    return this.request<SetDiffuseColorResult>("/material/color/set", "POST", {
      mesh_name: meshName,
      material_name: materialName,
      r,
      g,
      b,
    });
  }

  async getMaterialProperties(
    meshName: string,
    materialName: string
  ): Promise<MaterialProperties> {
    return this.request<MaterialProperties>("/material/properties", "POST", {
      mesh_name: meshName,
      material_name: materialName,
    });
  }

  async setMaterialOpacity(
    meshName: string,
    materialName: string,
    opacity: number
  ): Promise<SetMaterialPropertyResult> {
    return this.request<SetMaterialPropertyResult>("/material/opacity", "POST", {
      mesh_name: meshName,
      material_name: materialName,
      opacity,
    });
  }

  async setMaterialGlossiness(
    meshName: string,
    materialName: string,
    glossiness: number
  ): Promise<SetMaterialPropertyResult> {
    return this.request<SetMaterialPropertyResult>("/material/glossiness", "POST", {
      mesh_name: meshName,
      material_name: materialName,
      glossiness,
    });
  }

  async setMaterialSpecular(
    meshName: string,
    materialName: string,
    specular: number
  ): Promise<SetMaterialPropertyResult> {
    return this.request<SetMaterialPropertyResult>("/material/specular", "POST", {
      mesh_name: meshName,
      material_name: materialName,
      specular,
    });
  }

  // --- Content Management (Tier 1) ---

  async listClothes(): Promise<ClothingItem[]> {
    return this.request<ClothingItem[]>("/clothes");
  }

  async listHair(): Promise<HairItem[]> {
    return this.request<HairItem[]>("/hair");
  }

  async listAccessories(): Promise<AccessoryItem[]> {
    return this.request<AccessoryItem[]>("/accessories");
  }

  async removeSceneItem(itemName: string): Promise<RemoveItemResult> {
    return this.request<RemoveItemResult>("/item/remove", "POST", {
      item_name: itemName,
    });
  }

  async browseContent(folderType: string): Promise<string[]> {
    return this.request<string[]>("/content/browse", "POST", {
      folder_type: folderType,
    });
  }

  // --- Convenience Color Shortcuts (Tier 3) ---

  async setEyeColor(r: number, g: number, b: number): Promise<ColorResult> {
    return this.request<ColorResult>("/color/eye", "POST", { r, g, b });
  }

  async setHairColor(r: number, g: number, b: number): Promise<ColorResult> {
    return this.request<ColorResult>("/color/hair", "POST", { r, g, b });
  }

  async setLipColor(r: number, g: number, b: number): Promise<ColorResult> {
    return this.request<ColorResult>("/color/lip", "POST", { r, g, b });
  }

  async setSkinColor(r: number, g: number, b: number): Promise<ColorResult> {
    return this.request<ColorResult>("/color/skin", "POST", { r, g, b });
  }

  // --- Visibility & Scene (Tier 4) ---

  async setItemVisible(itemName: string, visible: boolean): Promise<SetVisibleResult> {
    return this.request<SetVisibleResult>("/item/visible", "POST", {
      item_name: itemName,
      visible,
    });
  }

  async getSceneObjects(): Promise<SceneObject[]> {
    return this.request<SceneObject[]>("/scene/objects");
  }

  async execPython(code: string): Promise<{ success: boolean; output?: string; result?: string; error?: string }> {
    return this.request<{ success: boolean; output?: string; result?: string; error?: string }>("/exec/python", "POST", { code });
  }
}
