/**
 * Type definitions for CC5 MCP Server.
 */

/** /health payload. `main_thread_blocked` is true when a modal dialog (or any main-thread
 *  block) is stopping CC5 from draining the RLPy command queue. */
export interface CC5Health {
  status: string;
  service: string;
  version?: string;
  main_thread_blocked: boolean;
  ms_since_main_thread_tick: number | null;
  queue_depth: number;
  hint?: string;
}

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

export interface DeleteAvatarResult extends OperationResult {
  removed?: string[];
}

export interface CaptureResult extends OperationResult {
  path?: string;
  base64?: string;
  /** Set when the image is not a clean render (e.g. a window screenshot fallback). */
  warning?: string;
  fallback?: "window_screenshot";
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

export interface AvatarPart {
  type: string;
  name: string;
  id?: number | string;
  /** Only Brow and Beard parts can be removed. */
  removable?: boolean;
  visible?: boolean | null;
}

export interface AvatarPartsResult extends OperationResult {
  avatar?: string;
  parts?: AvatarPart[];
}

export interface RemoveAvatarPartResult extends OperationResult {
  removed?: Array<{ type: string; name: string }>;
  remaining_face_hair?: string[];
}

export interface CameraState {
  name: string;
  position?: [number, number, number];
  focal_length?: number;
  /** Vertical angle of view in degrees. */
  angle_of_view?: number;
  /** False on the Preview Camera: scripts cannot set its position. */
  transform_writable?: boolean;
  current?: boolean;
}

export interface CameraListResult extends OperationResult {
  current?: string;
  cameras?: CameraState[];
}

export interface CameraDollyResult extends OperationResult {
  method?: string;
  notches?: number;
  moved_cm?: number;
  before?: [number, number, number];
  after?: [number, number, number];
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

/** Result of get_facial_profile — the current avatar's expression profile. */
export interface FacialProfileInfo extends OperationResult {
  avatar?: string;
  /** RLPy EFacialProfile enum int (0=None,1=CC5MetaHuman,2=CC4Extended,3=CC4Standard,4=Traditional). */
  profile_type_id?: number;
  /** Authoritative profile type label from GetProfileType(). */
  profile_type?: string;
  /** Expression-set UID string from GetExpressionSetUid(), e.g. "CC5 MetaHuman". */
  expression_set_uid?: string;
  category_slider_counts?: Record<string, number>;
  total_sliders?: number;
  category_count?: number;
  /** Heuristic ExPlus/HD/MetaHuman/Traditional class from UID + slider count. */
  heuristic_class?: string;
  arkit_capable?: boolean;
}

/** Small before/after profile summary embedded in ConvertFacialProfileResult. */
export interface FacialProfileSummary {
  profile_type?: string;
  expression_set_uid?: string;
  total_sliders?: number;
}

/** Result of convert_facial_profile (LoadProfile-based swap; dry_run by default). */
export interface ConvertFacialProfileResult extends OperationResult {
  dry_run?: boolean;
  applied?: boolean;
  current_profile?: FacialProfileSummary;
  before?: FacialProfileSummary;
  after?: FacialProfileSummary;
  target_profile_path?: string;
  target_path_valid?: boolean;
  path_error?: string | null;
  backup_current_to?: string;
  backup_saved_to?: string | null;
  notes?: string[];
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
  /** "Embed Textures" — bundle textures into the FBX. */
  embed_textures?: boolean;
  /** FBX Options: true = "Mesh and Motion" (default), false = "Mesh" only. */
  export_motion?: boolean;
  /** Include Motion frame rate (e.g. 30). Maps to RLPy.RFps.Fps{n}. */
  fps?: number;
  /** Include Motion frame range [start, end]. Omit for "All". */
  motion_range?: [number, number];
  /** "Convert Image Format" (TIF -> PNG). */
  convert_image_format?: boolean;
  /** "Max Texture Size" in pixels (0 = original). */
  texture_size?: number;
}

export interface ExportFbxResult extends OperationResult {
  path?: string;
  flags?: number;
  flags2?: number;
  flags3?: number;
  flags_applied?: boolean;
  notes?: string[];
  target_tool?: string;
  /** HD Character Subdivision Level actually applied (SetExportLevel). */
  export_level?: number;
  /** Whether motion was included ("Mesh and Motion"). */
  export_motion?: boolean;
  /** Motion frame rate actually applied. */
  fps?: number;
  /** Motion frame range actually applied. */
  motion_range?: [number, number];
  /** Max texture size actually applied. */
  texture_size?: number;
  /** Whether textures were embedded. */
  embed_textures?: boolean;
  /** Whether image format conversion was applied. */
  convert_image_format?: boolean;
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

// --- ActorMIXER PRO: Create Mixer Assets ---

/** Head-part checkboxes on the Create Mixer Assets dialog (default: all true). */
export interface MixerHeadParts {
  eyes?: boolean;
  forehead?: boolean;
  chin?: boolean;
  mouth?: boolean;
  ears?: boolean;
  nose?: boolean;
  head_shape?: boolean;
}

/** Body-part checkboxes (default: all false). */
export interface MixerBodyParts {
  body?: boolean;
  torso?: boolean;
}

/**
 * 'Save Presets' groupbox + children. `enabled` toggles the groupbox itself.
 * Default: enabled with character/head/head_parts/body on, body_parts off.
 */
export interface MixerSavePresets {
  enabled?: boolean;
  character?: boolean;
  head?: boolean;
  head_parts?: boolean;
  body?: boolean;
  body_parts?: boolean;
}

/** 'Save Avatar Presets' groupbox (default: disabled). */
export interface MixerSaveAvatarPresets {
  enabled?: boolean;
}

export interface CreateActorMixerOptions {
  morph_name?: string;
  slider_path?: string;
  use_parts_folder?: boolean;
  head_parts?: MixerHeadParts;
  body_parts?: MixerBodyParts;
  save_presets?: MixerSavePresets;
  save_avatar_presets?: MixerSaveAvatarPresets;
  /** Safety gate. false (default) => set fields then CANCEL (dry-run). true => click Create once. */
  confirm_create?: boolean;
}

export interface CreateActorMixerResult extends OperationResult {
  morph_name?: string;
  created?: boolean;
  dry_run?: boolean;
  new_presets?: string[];
  presets_dir?: string;
  scheduled?: boolean;
  notes?: string[];
  poll_endpoint?: string;
  /** True when the open avatar holds trial content; ActorMIXER refuses to run. */
  trial_content?: boolean;
}

// --- Text-only workflow routes (/workflow/*) ---

/** Kind of a scene item, as reported by /workflow/items. */
export type WorkflowItemKind =
  | "avatar"
  | "cloth"
  | "accessory"
  | "hair"
  | "prop"
  | "light"
  | "camera";

/** Minimal item reference: name, id and kind. */
export interface WorkflowItemRef {
  name: string;
  id: string;
  kind: WorkflowItemKind;
}

/** Scene item as returned by list_scene_items. */
export interface WorkflowItem extends WorkflowItemRef {
  visible: boolean | null;
  parent: string | null;
  cloth_type?: string;
  hair_type?: string;
}

/** Item selector accepted by most workflow routes. At least one field must be set. */
export interface WorkflowItemSelector {
  item_name?: string;
  item_id?: string;
}

/** Shared base for workflow replies; `matches` is present when a name was ambiguous. */
export interface WorkflowItemResult extends OperationResult {
  name?: string;
  matches?: WorkflowItemRef[];
}

export interface WorkflowListItemsResult extends OperationResult {
  items?: WorkflowItem[];
}

export interface WorkflowSetVisibleResult extends WorkflowItemResult {
  id?: string;
  visible?: boolean;
}

export interface WorkflowRemoveItemResult extends OperationResult {
  removed?: WorkflowItemRef;
}

export interface WorkflowImportFbxResult extends OperationResult {
  item?: WorkflowItemRef;
}

export interface WorkflowAttachResult extends WorkflowItemResult {
  bone?: string;
  /** Candidate bone names when the requested bone was unknown. */
  bones?: string[];
}

/** Templates accepted by /workflow/transfer_weights. */
export type WorkflowWeightTemplate =
  | "default"
  | "dress"
  | "gloves"
  | "shoes"
  | "cloak"
  | "other";

export interface WorkflowTransferWeightsResult extends WorkflowItemResult {
  template?: WorkflowWeightTemplate;
  kind_after?: WorkflowItemKind;
}

/** Templates accepted by /workflow/convert_hair. */
export type WorkflowHairTemplate =
  | "top"
  | "base_all"
  | "rear"
  | "bangs"
  | "accessory"
  | "brows"
  | "upper_lash"
  | "lower_lash";

export interface WorkflowConvertHairResult extends WorkflowItemResult {
  template?: WorkflowHairTemplate;
}

export type WorkflowClothToAccessoryResult = WorkflowItemResult;

export interface WorkflowConformResult extends WorkflowItemResult {
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
}

export interface WorkflowTransformResult extends WorkflowItemResult {
  move?: number[];
  rotate?: number[];
  scale?: number[];
  /** Units of move/rotate/scale (cm, degrees, percent when read from the Transform data block). */
  units?: Record<string, string>;
  /** Set when only raw values could be read; they must not be passed back to set_transform. */
  units_warning?: string;
}

/** Transform values to apply; omitted fields are left unchanged. */
export interface WorkflowTransformUpdate {
  move?: number[];
  rotate?: number[];
  scale?: number[];
}

export interface WorkflowSaveResult extends OperationResult {
  path?: string;
  /** true when no path was given and the open project file was overwritten. */
  in_place?: boolean;
  /** true when a save-as replaced a file that already existed. */
  overwrote_existing?: boolean;
}

export interface WorkflowExportObjResult extends OperationResult {
  path?: string;
  bytes?: number;
}

/** Result of /workflow/mesh/offset (moving a mesh's vertices in world space). */
export interface WorkflowMeshOffsetResult extends WorkflowItemResult {
  mesh?: string;
  vertices?: number;
  /** Turn about Z between GetVertices(True) and the true world; null when none fits. */
  frame_turn_deg?: number | null;
  frame_errors_cm?: Record<string, number>;
  offset?: number[];
  /** Largest read-back difference from the target on the sampled vertices. */
  after_error_cm?: number;
  /** Vertices that a deltas_file moved. */
  deltas_moved?: number;
  dry_run?: boolean;
}

export interface WorkflowFloorContactResult extends OperationResult {
  value?: unknown;
}

/** Reply with only success/error (floor-contact set, auto foot height). */
export type WorkflowSimpleResult = OperationResult;

export interface WorkflowRenderResult extends OperationResult {
  path?: string;
}

export interface WorkflowViews4Result extends OperationResult {
  /** [front, side, top, perspective] */
  files?: string[];
}

// --- Physics (Soft Cloth) workflow routes (/workflow/physics/*) ---

/**
 * Soft PhysX property names accepted by /workflow/physics/params/*.
 * RLPy does not document them; this is CC5's own soft-cloth key table.
 * SoftVsRigidCollision and SelfCollision are on/off switches (1 / 0).
 */
export const SOFT_PHYSX_PROPERTIES = [
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
] as const;

export type SoftPhysxProperty = (typeof SOFT_PHYSX_PROPERTIES)[number];

/** Optional soft-cloth mesh/material target (auto-picked when the item has only one). */
export interface PhysicsMaterialTarget {
  mesh_name?: string;
  material_name?: string;
}

export interface PhysicsMeshEntry {
  mesh: string;
  materials: string[];
}

/** Shared reply fields for routes that act on one soft-cloth material. */
export interface PhysicsMaterialResult extends WorkflowItemResult {
  mesh?: string;
  material?: string;
  notes?: string[];
  /** Soft-cloth meshes, sent when the mesh/material was missing or unknown. */
  meshes?: PhysicsMeshEntry[];
}

export interface PhysicsInfoResult extends WorkflowItemResult {
  kind?: WorkflowItemKind;
  /** Activate Physics state; null when it could not be read. */
  activate?: boolean | null;
  meshes?: PhysicsMeshEntry[];
  properties?: string[];
  weight_map_import?: boolean;
  notes?: string[];
}

export interface PhysicsActivateResult extends WorkflowItemResult {
  activate?: boolean;
  verified?: boolean;
  notes?: string[];
}

export interface PhysicsWeightMapResult extends PhysicsMaterialResult {
  path?: string;
  status?: string;
  weight_map_present?: boolean | null;
  /** True when the weight map must be loaded by hand in the CC5 GUI. */
  gui_only?: boolean;
}

export interface PhysicsParamsResult extends PhysicsMaterialResult {
  params?: Record<string, unknown>;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  unreadable?: Record<string, string>;
  failures?: Record<string, string>;
  mismatched?: Record<string, { wanted: number; got: unknown }>;
  allowed?: string[];
}

export interface PhysicsCollisionShape {
  name: string;
  enabled: boolean | null;
  value: number | null;
}

/** One collision-shape change to apply; at least one of enabled/value is set. */
export interface PhysicsCollisionUpdate {
  name: string;
  enabled?: boolean;
  value?: number;
}

export interface PhysicsCollisionGetResult extends PhysicsMaterialResult {
  shapes?: PhysicsCollisionShape[];
  probed?: number;
  unknown?: string[];
}

export interface PhysicsCollisionSetResult extends PhysicsMaterialResult {
  shapes?: Array<{
    name: string;
    before: PhysicsCollisionShape | null;
    after: PhysicsCollisionShape | null;
    errors?: string[];
  }>;
}

// ── UI automation (/ui/ routes: presets, SkinGen, windows, framed capture) ─────

/** Reply of a route that starts a job; poll /ui/job with job_id. */
export interface UiJobStart extends OperationResult {
  job_id?: string;
  state?: string;
}

export interface UiWindowInfo {
  index?: number;
  title: string;
  class?: string;
  text: string;
  buttons: string[];
  checkboxes?: Array<{ text: string; checked: boolean }>;
  modal?: boolean;
  progress?: boolean;
  geometry?: number[] | null;
  /** The word that makes this window off limits (licence, purchase, login, ...). */
  needs_human?: string | null;
  /** Name of the known question rule that would answer this window. */
  answerable_as?: string | null;
  blocked_reason?: string;
  png_base64?: string;
  png_size?: number[];
  error?: string;
}

export interface UiWindowsResult extends OperationResult {
  count?: number;
  windows?: UiWindowInfo[];
  main_window?: { title?: string; png_base64?: string; png_size?: number[]; error?: string };
}

export type UiJobState = "queued" | "running" | "done" | "failed";

export interface UiJobStatus<T = OperationResult> extends OperationResult {
  job_id?: string;
  kind?: string;
  state?: UiJobState;
  elapsed_s?: number;
  result?: T;
  windows?: UiWindowInfo[];
}

/** What waiting for a job gave: the job's result, or the last status when time ran out. */
export interface UiJobOutcome<T = OperationResult> {
  finished: boolean;
  result?: T;
  status?: UiJobStatus<T>;
}

export interface UiPresetEntry {
  name: string;
  path: string;
  folder: string;
  ext: string;
  installed: boolean;
}

export interface UiPresetListResult extends OperationResult {
  folders?: string[];
  total?: number;
  presets?: UiPresetEntry[];
  missing?: string[];
  truncated?: boolean;
  subfolders?: string[];
  errors?: string[];
  note?: string;
}

export interface UiApplyFileResult {
  path: string;
  ok: boolean;
  status_error?: boolean | null;
  added?: string[];
  removed?: string[];
  watched?: string[];
  settled?: boolean;
  blocked_by?: UiWindowInfo | null;
  error?: string;
}

export interface UiAnsweredWindow {
  rule: string;
  pressed: string;
  window: string;
  text?: string;
}

export interface UiApplyPresetResult extends OperationResult {
  avatar?: string;
  files?: UiApplyFileResult[];
  answered?: UiAnsweredWindow[];
  /** Windows the answerer looked at and left alone, with the reason. */
  blocked_windows?: Array<{ title: string; why: string }>;
  skipped?: string[];
  skingen?: { editor_active: boolean | null; layers: Array<string | null> };
  note?: string;
}

export interface SkinGenLayer {
  index: number;
  name: string | null;
  number?: string;
  visible: boolean | null;
  selected: boolean;
  other_labels?: string[];
}

export interface SkinGenState extends OperationResult {
  editor_found?: boolean;
  editor_active?: boolean | null;
  table_found?: boolean;
  layers?: SkinGenLayer[];
  selected?: number | null;
  opacity?: number | null;
  opacity_range?: number[];
  tab?: string;
  combos?: Record<string, string>;
  hint?: string;
}

export interface SkinGenEditorResult extends OperationResult {
  changed?: boolean;
  editor_active?: boolean;
  waited_s?: number | null;
  answered?: UiAnsweredWindow[];
  blocked_windows?: Array<{ title: string; why: string }>;
  blocked_by?: UiWindowInfo | null;
  windows?: UiWindowInfo[];
}

export interface SkinGenLayerResult extends OperationResult {
  layer?: number | SkinGenLayer;
  layers?: SkinGenLayer[];
  selected?: number | null;
  opacity?: number | null;
  opacity_before?: number;
  opacity_after?: number | null;
  scope?: string;
  layers_before?: number;
  layers_after?: number;
  menu?: string[];
  blocked_by?: UiWindowInfo | null;
}

export interface UiWidgetState {
  object_name: string;
  class: string;
  visible: boolean;
  enabled: boolean;
  text?: string;
  current_text?: string;
  value?: number;
  checked?: boolean;
  tooltip?: string;
  path: string;
}

export interface UiWidgetsResult extends OperationResult {
  count?: number;
  shown?: number;
  widgets?: UiWidgetState[];
}

// Bodies of the /ui/ routes (snake_case, as the bridge reads them).

export interface UiApplyPresetArgs {
  file_path?: string;
  file_paths?: string[];
  avatar_name?: string;
  answers?: { layer_choice?: "replace" | "add"; restore_neutral_lash?: boolean };
  watch_prefix?: string;
  timeout_s?: number;
}

export interface UiListPresetsArgs {
  category?: string;
  folder?: string;
  query?: string;
  names?: string[];
  ext?: string;
  recursive?: boolean;
  list_folders?: boolean;
  limit?: number;
}

export interface SkinGenEditorArgs {
  active: boolean;
  exit_answer?: "yes" | "no";
  timeout_s?: number;
}

export type SkinGenLayerAction = "select" | "show" | "hide" | "opacity" | "delete";
export type SkinGenDeleteScope = "selected_layer" | "current_material" | "all_material";

export interface SkinGenLayerArgs {
  action: SkinGenLayerAction;
  index?: number;
  name?: string;
  opacity?: number;
  scope?: SkinGenDeleteScope;
  confirm?: boolean;
}

export interface UiWindowsArgs {
  screenshot?: boolean;
  max_width?: number;
  target?: "dialogs" | "main";
  include_other?: boolean;
}

export interface UiWidgetsArgs {
  object_name?: string;
  name_contains?: string;
  class_name?: string;
  text_contains?: string;
  ancestor?: string;
  visible_only?: boolean;
  limit?: number;
}

export interface UiCaptureCropArgs {
  view?: string;
  size?: number;
  crop?: number[];
  crop_fraction?: number[];
  output_path?: string;
  full_path?: string;
  avatar_name?: string;
  overwrite?: boolean;
  settle_ms?: number;
}

export interface UiCaptureCropResult extends OperationResult {
  view?: string;
  full_path?: string;
  render_size?: number[];
  crop_path?: string;
  crop_box?: number[];
  crop_size?: number[];
  png_base64?: string;
  /** Present when no crop box was given: the picture is a scaled-down preview of the whole render. */
  preview_size?: number[];
  /** full-render pixels per preview pixel (multiply preview coordinates by this to get render pixels). */
  preview_scale?: number;
  warning?: string;
  note?: string;
  path?: string;
}
