/**
 * HTTP client for communicating with the CC5 Python bridge plugin.
 */

import type {
  CC5Health,
  CC5Avatar,
  CC5Response,
  MorphCatalog,
  AvatarInfo,
  OperationResult,
  CreateAvatarResult,
  DeleteAvatarResult,
  CaptureResult,
  MorphSetRequest,
  AvatarPartsResult,
  CameraInfo,
  CameraDollyResult,
  CameraListResult,
  RemoveAvatarPartResult,
  FocalLengthResult,
  LightInfo,
  LightColorResult,
  LightDetailInfo,
  LightMultiplierResult,
  LightActiveResult,
  LightShadowResult,
  VisualSettings,
  SetAmbientResult,
  SetIblResult,
  ExpressionInfo,
  ExpressionItem,
  ExpressionSetResult,
  ExpressionResetResult,
  FacialProfileInfo,
  ConvertFacialProfileResult,
  ResetMorphsResult,
  MaterialInfo,
  DiffuseColor,
  SetDiffuseColorResult,
  MaterialProperties,
  SetMaterialPropertyResult,
  ShaderParameters,
  SetShaderParameterResult,
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
  CreateActorMixerOptions,
  CreateActorMixerResult,
  WorkflowItemSelector,
  WorkflowListItemsResult,
  WorkflowSetVisibleResult,
  WorkflowRemoveItemResult,
  WorkflowImportFbxResult,
  WorkflowAttachResult,
  WorkflowWeightTemplate,
  WorkflowTransferWeightsResult,
  WorkflowHairTemplate,
  WorkflowConvertHairResult,
  WorkflowClothToAccessoryResult,
  WorkflowConformResult,
  WorkflowTransformResult,
  WorkflowTransformUpdate,
  WorkflowSaveResult,
  WorkflowExportObjResult,
  WorkflowFloorContactResult,
  WorkflowSimpleResult,
  WorkflowRenderResult,
  WorkflowViews4Result,
  PhysicsMaterialTarget,
  PhysicsInfoResult,
  PhysicsActivateResult,
  PhysicsWeightMapResult,
  PhysicsParamsResult,
  PhysicsCollisionGetResult,
  PhysicsCollisionSetResult,
  PhysicsCollisionUpdate,
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

  /**
   * Full health, including whether CC5's main thread is actually running.
   *
   * The bridge's HTTP server lives on its own thread, so /health answers even when
   * CC5 is frozen behind a modal dialog. In that state every queued RLPy call hangs
   * until the dialog is dismissed. `main_thread_blocked` is what distinguishes
   * "reachable" from "able to do work" -- always check it before reporting success.
   */
  async healthDetail(): Promise<CC5Health | null> {
    try {
      return await this.request<CC5Health>("/health");
    } catch (err) {
      console.error("[CC5 Bridge] healthDetail failed:", err);
      return null;
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

  async deleteAvatar(name: string): Promise<DeleteAvatarResult> {
    return this.request<DeleteAvatarResult>("/avatar/delete", "POST", { name });
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
    if (extra.embed_textures !== undefined) body.embed_textures = extra.embed_textures;
    if (extra.export_motion !== undefined) body.export_motion = extra.export_motion;
    if (extra.fps !== undefined) body.fps = extra.fps;
    if (extra.motion_range !== undefined) body.motion_range = extra.motion_range;
    if (extra.convert_image_format !== undefined) body.convert_image_format = extra.convert_image_format;
    if (extra.texture_size !== undefined) body.texture_size = extra.texture_size;
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

  async frameCamera(
    view: string,
  ): Promise<{ success: boolean; view?: string; camera?: string; error?: string }> {
    return this.request("/camera/frame", "POST", { view });
  }

  async listCameras(): Promise<CameraListResult> {
    return this.request<CameraListResult>("/camera/list");
  }

  async dollyCamera(notches: number): Promise<CameraDollyResult> {
    return this.request<CameraDollyResult>("/camera/dolly", "POST", { notches });
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

  async setLightActive(
    lightName: string,
    active: boolean
  ): Promise<LightActiveResult> {
    return this.request<LightActiveResult>("/light/active", "POST", {
      light_name: lightName,
      active,
    });
  }

  async setLightShadow(
    lightName: string,
    castShadow: boolean | null,
    darkenStrength: number | null
  ): Promise<LightShadowResult> {
    return this.request<LightShadowResult>("/light/shadow", "POST", {
      light_name: lightName,
      cast_shadow: castShadow,
      darken_strength: darkenStrength,
    });
  }

  // --- Environment / Visual Settings ---

  async getVisualSettings(): Promise<VisualSettings> {
    return this.request<VisualSettings>("/visual/settings");
  }

  async setAmbient(r: number, g: number, b: number): Promise<SetAmbientResult> {
    return this.request<SetAmbientResult>("/visual/ambient", "POST", { r, g, b });
  }

  async setIbl(imagePath: string, enable: boolean): Promise<SetIblResult> {
    return this.request<SetIblResult>("/visual/ibl", "POST", {
      image_path: imagePath,
      enable,
    });
  }

  // --- Expressions ---

  async getExpressionInfo(): Promise<ExpressionInfo> {
    return this.request<ExpressionInfo>("/expressions");
  }

  async setExpression(
    expressions: ExpressionItem[]
  ): Promise<ExpressionSetResult> {
    return this.request<ExpressionSetResult>("/expression/set", "POST", {
      expressions,
    });
  }

  async resetExpression(): Promise<ExpressionResetResult> {
    return this.request<ExpressionResetResult>("/expression/reset", "POST", {});
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

  async getShaderParameters(
    meshName: string,
    materialName: string
  ): Promise<ShaderParameters> {
    return this.request<ShaderParameters>("/material/shader/get", "POST", {
      mesh_name: meshName,
      material_name: materialName,
    });
  }

  async setShaderParameter(
    meshName: string,
    materialName: string,
    parameterName: string,
    values: number[]
  ): Promise<SetShaderParameterResult> {
    return this.request<SetShaderParameterResult>("/material/shader/set", "POST", {
      mesh_name: meshName,
      material_name: materialName,
      parameter_name: parameterName,
      values,
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

  async listAvatarParts(): Promise<AvatarPartsResult> {
    return this.request<AvatarPartsResult>("/avatar/parts");
  }

  async removeAvatarPart(name?: string, type?: string): Promise<RemoveAvatarPartResult> {
    return this.request<RemoveAvatarPartResult>("/avatar/part/remove", "POST", {
      ...(name ? { name } : {}),
      ...(type ? { type } : {}),
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

  // --- Facial profile ---

  async getFacialProfile(): Promise<FacialProfileInfo> {
    return this.request<FacialProfileInfo>("/facial/profile");
  }

  async convertFacialProfile(opts: {
    target_profile_path?: string;
    dry_run?: boolean;
    backup_current_to?: string;
  }): Promise<ConvertFacialProfileResult> {
    return this.request<ConvertFacialProfileResult>("/facial/profile/convert", "POST", {
      target_profile_path: opts.target_profile_path ?? "",
      dry_run: opts.dry_run ?? true,
      backup_current_to: opts.backup_current_to ?? "",
    });
  }

  // --- ActorMIXER PRO: Create Mixer Assets ---

  async createActorMixer(opts: CreateActorMixerOptions): Promise<CreateActorMixerResult> {
    const body: Record<string, unknown> = {
      confirm_create: opts.confirm_create ?? false,
    };
    if (opts.morph_name !== undefined) body.morph_name = opts.morph_name;
    if (opts.slider_path !== undefined) body.slider_path = opts.slider_path;
    if (opts.use_parts_folder !== undefined) body.use_parts_folder = opts.use_parts_folder;
    if (opts.head_parts !== undefined) body.head_parts = opts.head_parts;
    if (opts.body_parts !== undefined) body.body_parts = opts.body_parts;
    if (opts.save_presets !== undefined) body.save_presets = opts.save_presets;
    if (opts.save_avatar_presets !== undefined) body.save_avatar_presets = opts.save_avatar_presets;
    return this.request<CreateActorMixerResult>("/actor_mixer/create", "POST", body);
  }

  // --- Text-only workflow routes ---

  /** GET /workflow/items (sent as POST with an empty body per the contract). */
  async listSceneItems(): Promise<WorkflowListItemsResult> {
    return this.request<WorkflowListItemsResult>("/workflow/items", "POST", {});
  }

  async wfSetVisible(
    sel: WorkflowItemSelector,
    visible: boolean
  ): Promise<WorkflowSetVisibleResult> {
    return this.request<WorkflowSetVisibleResult>("/workflow/visible", "POST", {
      ...sel,
      visible,
    });
  }

  async wfRemoveItem(sel: WorkflowItemSelector): Promise<WorkflowRemoveItemResult> {
    return this.request<WorkflowRemoveItemResult>("/workflow/remove", "POST", { ...sel });
  }

  async wfImportFbx(filePath: string): Promise<WorkflowImportFbxResult> {
    return this.request<WorkflowImportFbxResult>("/workflow/import_fbx", "POST", {
      file_path: filePath,
    });
  }

  async wfAttachToBone(
    sel: WorkflowItemSelector,
    boneName: string
  ): Promise<WorkflowAttachResult> {
    return this.request<WorkflowAttachResult>("/workflow/attach", "POST", {
      ...sel,
      bone_name: boneName,
    });
  }

  async wfTransferSkinWeights(
    sel: WorkflowItemSelector,
    template: WorkflowWeightTemplate
  ): Promise<WorkflowTransferWeightsResult> {
    return this.request<WorkflowTransferWeightsResult>("/workflow/transfer_weights", "POST", {
      ...sel,
      template,
    });
  }

  async wfConvertToHair(
    sel: WorkflowItemSelector,
    template: WorkflowHairTemplate
  ): Promise<WorkflowConvertHairResult> {
    return this.request<WorkflowConvertHairResult>("/workflow/convert_hair", "POST", {
      ...sel,
      template,
    });
  }

  async wfClothToAccessory(
    sel: WorkflowItemSelector,
    keepCurrentShape: boolean = true
  ): Promise<WorkflowClothToAccessoryResult> {
    return this.request<WorkflowClothToAccessoryResult>("/workflow/cloth_to_accessory", "POST", {
      ...sel,
      keep_current_shape: keepCurrentShape,
    });
  }

  async wfConformCloth(
    sel: WorkflowItemSelector,
    iterations: number = 1,
    values?: Record<string, number>
  ): Promise<WorkflowConformResult> {
    const body: Record<string, unknown> = { ...sel, iterations };
    if (values !== undefined) body.values = values;
    return this.request<WorkflowConformResult>("/workflow/conform", "POST", body);
  }

  async wfGetTransform(sel: WorkflowItemSelector): Promise<WorkflowTransformResult> {
    return this.request<WorkflowTransformResult>("/workflow/transform/get", "POST", { ...sel });
  }

  async wfSetTransform(
    sel: WorkflowItemSelector,
    update: WorkflowTransformUpdate
  ): Promise<WorkflowTransformResult> {
    const body: Record<string, unknown> = { ...sel };
    if (update.move !== undefined) body.move = update.move;
    if (update.rotate !== undefined) body.rotate = update.rotate;
    if (update.scale !== undefined) body.scale = update.scale;
    return this.request<WorkflowTransformResult>("/workflow/transform/set", "POST", body);
  }

  async wfSaveProject(filePath?: string): Promise<WorkflowSaveResult> {
    const body: Record<string, unknown> = {};
    if (filePath !== undefined) body.file_path = filePath;
    return this.request<WorkflowSaveResult>("/workflow/save", "POST", body);
  }

  async wfExportObj(
    filePath: string,
    currentPose: boolean = true,
    withMaterials: boolean = true
  ): Promise<WorkflowExportObjResult> {
    return this.request<WorkflowExportObjResult>("/workflow/export_obj", "POST", {
      file_path: filePath,
      current_pose: currentPose,
      with_materials: withMaterials,
    });
  }

  async wfGetFloorContact(): Promise<WorkflowFloorContactResult> {
    return this.request<WorkflowFloorContactResult>("/workflow/floor_contact/get", "POST", {});
  }

  async wfSetFloorContact(value: Record<string, unknown>): Promise<WorkflowSimpleResult> {
    return this.request<WorkflowSimpleResult>("/workflow/floor_contact/set", "POST", { value });
  }

  async wfAutoAdjustFootHeight(): Promise<WorkflowSimpleResult> {
    return this.request<WorkflowSimpleResult>("/workflow/foot_auto", "POST", {});
  }

  async wfRenderViewport(filePath: string): Promise<WorkflowRenderResult> {
    return this.request<WorkflowRenderResult>("/workflow/render", "POST", {
      file_path: filePath,
    });
  }

  async wfCaptureViews4(
    folder: string,
    prefix: string,
    target?: WorkflowItemSelector
  ): Promise<WorkflowViews4Result> {
    const body: Record<string, unknown> = { folder, prefix };
    if (target !== undefined) body.target = target;
    return this.request<WorkflowViews4Result>("/workflow/views4", "POST", body);
  }

  // --- Physics (Soft Cloth) routes ---

  async wfPhysicsInfo(sel: WorkflowItemSelector): Promise<PhysicsInfoResult> {
    return this.request<PhysicsInfoResult>("/workflow/physics/info", "POST", { ...sel });
  }

  async wfPhysicsActivate(
    sel: WorkflowItemSelector,
    enable: boolean
  ): Promise<PhysicsActivateResult> {
    return this.request<PhysicsActivateResult>("/workflow/physics/activate", "POST", {
      ...sel,
      enable,
    });
  }

  async wfPhysicsLoadWeightMap(
    sel: WorkflowItemSelector,
    target: PhysicsMaterialTarget,
    filePath: string
  ): Promise<PhysicsWeightMapResult> {
    return this.request<PhysicsWeightMapResult>("/workflow/physics/weight_map", "POST", {
      ...sel,
      ...physicsTargetBody(target),
      file_path: filePath,
    });
  }

  async wfPhysicsGetParams(
    sel: WorkflowItemSelector,
    target: PhysicsMaterialTarget,
    names?: string[]
  ): Promise<PhysicsParamsResult> {
    const body: Record<string, unknown> = { ...sel, ...physicsTargetBody(target) };
    if (names !== undefined) body.names = names;
    return this.request<PhysicsParamsResult>("/workflow/physics/params/get", "POST", body);
  }

  async wfPhysicsSetParams(
    sel: WorkflowItemSelector,
    target: PhysicsMaterialTarget,
    values: Record<string, number | boolean>
  ): Promise<PhysicsParamsResult> {
    return this.request<PhysicsParamsResult>("/workflow/physics/params/set", "POST", {
      ...sel,
      ...physicsTargetBody(target),
      values,
    });
  }

  async wfPhysicsGetCollision(
    sel: WorkflowItemSelector,
    target: PhysicsMaterialTarget,
    collisionNames?: string[]
  ): Promise<PhysicsCollisionGetResult> {
    const body: Record<string, unknown> = { ...sel, ...physicsTargetBody(target) };
    if (collisionNames !== undefined) body.collision_names = collisionNames;
    return this.request<PhysicsCollisionGetResult>("/workflow/physics/collision/get", "POST", body);
  }

  async wfPhysicsSetCollision(
    sel: WorkflowItemSelector,
    target: PhysicsMaterialTarget,
    shapes: PhysicsCollisionUpdate[]
  ): Promise<PhysicsCollisionSetResult> {
    return this.request<PhysicsCollisionSetResult>("/workflow/physics/collision/set", "POST", {
      ...sel,
      ...physicsTargetBody(target),
      shapes,
    });
  }
}

/** Only send mesh_name / material_name when they were given. */
function physicsTargetBody(target: PhysicsMaterialTarget): Record<string, string> {
  const body: Record<string, string> = {};
  if (target.mesh_name !== undefined) body.mesh_name = target.mesh_name;
  if (target.material_name !== undefined) body.material_name = target.material_name;
  return body;
}
