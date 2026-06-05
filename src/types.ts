/**
 * Type definitions for CC5 MCP Server.
 */

export interface CC5Avatar {
  name: string;
  id: string;
  type: string;
}

export interface MorphEntry {
  id: string;
  display_name: string;
}

export interface MorphCatalog {
  [category: string]: MorphEntry[];
}

export interface MorphSetRequest {
  morph_id: string;
  /** Morph blend weight. Valid range: -1..1 (negative values shrink the feature, positive enlarge it). */
  value: number;
}

export interface AvatarInfo {
  name: string;
  id: string;
  active_morphs: Record<string, number>;
}

export interface CC5Response<T = unknown> {
  result?: T;
  error?: string;
}

export interface OperationResult {
  success: boolean;
  error?: string;
}

export interface CreateAvatarResult extends OperationResult {
  name?: string;
}

export interface CaptureResult extends OperationResult {
  path?: string;
  base64?: string;
}

export interface CameraInfo {
  name: string;
  position: { x: number; y: number; z: number };
  focal_length: number;
  error?: string;
}

export interface FocalLengthResult extends OperationResult {
  focal_length?: number;
}

export interface LightInfo {
  name: string;
  id: number;
  type: string;
}

export interface LightColorResult extends OperationResult {
  light?: string;
}

export interface LightDetailInfo {
  name: string;
  type: string;
  color: { r: number; g: number; b: number } | null;
  multiplier: number | null;
  active?: boolean | null;
  cast_shadow?: boolean | null;
  darken_shadow_strength?: number | null;
  range?: number | null;
  error?: string;
}

export interface LightMultiplierResult extends OperationResult {
  light?: string;
  multiplier?: number;
}

export interface LightActiveResult extends OperationResult {
  light?: string;
  active?: boolean;
}

export interface LightShadowResult extends OperationResult {
  light?: string;
  cast_shadow?: boolean;
  darken_shadow_strength?: number;
}

export interface VisualSettings extends OperationResult {
  ambient?: { r: number; g: number; b: number } | null;
  ibl_enabled?: boolean | null;
}

export interface SetAmbientResult extends OperationResult {
  ambient?: { r: number; g: number; b: number };
}

export interface SetIblResult extends OperationResult {
  ibl_enabled?: boolean;
  loaded_image?: string | null;
}

export interface ExpressionInfo {
  [group: string]: string[];
}

export interface ExpressionItem {
  name: string;
  weight: number;
}

export interface ExpressionSetResult extends OperationResult {
  applied?: ExpressionItem[];
  skipped?: (string | null)[];
}

export interface ExpressionResetResult extends OperationResult {
  reset_count?: number;
}

export interface ResetMorphsResult extends OperationResult {
  reset_count?: number;
}

export interface MaterialInfo {
  success?: boolean;
  meshes: Record<string, string[]>;
}

export interface DiffuseColor {
  r: number;
  g: number;
  b: number;
  error?: string;
}

export interface SetDiffuseColorResult extends OperationResult {
  mesh?: string;
  material?: string;
}

export interface MaterialProperties {
  mesh: string;
  material: string;
  opacity?: number;
  glossiness?: number;
  specular?: number;
  error?: string;
}

export interface SetMaterialPropertyResult extends OperationResult {
  mesh?: string;
  material?: string;
  opacity?: number;
  glossiness?: number;
  specular?: number;
}

export interface ShaderParameters extends OperationResult {
  mesh?: string;
  material?: string;
  shader?: string | null;
  parameters?: Record<string, number[]>;
}

export interface SetShaderParameterResult extends OperationResult {
  mesh?: string;
  material?: string;
  parameter?: string;
  values?: number[];
}

// --- Content Management (Tier 1) ---

export interface ClothingItem {
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

export interface RemoveItemResult extends OperationResult {
  removed?: string;
}

// --- Convenience Color Shortcuts (Tier 3) ---

export interface ColorResult extends OperationResult {
  applied_to?: string[];
}

// --- Visibility & Scene (Tier 4) ---

export interface SetVisibleResult extends OperationResult {
  item?: string;
  visible?: boolean;
}

export interface SceneObject {
  name: string;
  id: number;
  type: string;
}

// --- Mesh-to-MetaHuman pipeline ---

export interface ExportFbxOptions {
  target_tool?: "UE5" | "Default" | "Maya" | "Unity" | "Unreal";
  sub_d_level?: 0 | 1 | 2;
  include_current_pose?: boolean;
  delete_hidden_faces?: boolean;
  use_smooth_mesh?: boolean;
  remove_eyelash?: boolean;
  remove_tearline_occlusion?: boolean;
}

export interface ExportFbxResult extends OperationResult {
  path?: string;
  flags?: number;
  flags2?: number;
  notes?: string[];
  target_tool?: string;
}

export interface BakeSkinResult extends OperationResult {
  resolution?: number;
  triggered_action?: string;
  manual_step_required?: boolean;
  instructions?: string;
  notes?: string[];
}

export interface ExportHeadMetaHumanResult extends OperationResult {
  triggered_action?: string;
  manual_step_required?: boolean;
  instructions?: string;
  output_dir?: string;
  character_name?: string;
  gender?: string;
  notes?: string[];
}
