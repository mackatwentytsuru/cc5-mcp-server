/**
 * Shared mock factory for CC5Bridge.
 * Returns a vi.fn()-backed partial mock that satisfies the CC5Bridge interface.
 */

import { vi } from "vitest";
import type { CC5Bridge } from "../../src/cc5-bridge.js";
import type {
  CC5Avatar,
  AvatarInfo,
  MorphCatalog,
  OperationResult,
  CreateAvatarResult,
  CaptureResult,
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
} from "../../src/types.js";

export type MockBridge = {
  [K in keyof CC5Bridge]: ReturnType<typeof vi.fn>;
};

export function createMockBridge(): MockBridge {
  return {
    healthCheck: vi.fn<[], Promise<boolean>>(),
    getAvatars: vi.fn<[], Promise<CC5Avatar[]>>(),
    getAvatarInfo: vi.fn<[], Promise<AvatarInfo | null>>(),
    getMorphCatalog: vi.fn<[], Promise<MorphCatalog>>(),
    getMorphValue: vi.fn<[string], Promise<{ success: boolean; morph_id?: string; value?: number; error?: string }>>(),
    setMorph: vi.fn<[string, number], Promise<OperationResult>>(),
    setMultipleMorphs: vi.fn<[Array<{ morph_id: string; value: number }>], Promise<OperationResult>>(),
    createDefaultAvatar: vi.fn<[], Promise<CreateAvatarResult>>(),
    loadAsset: vi.fn<[string], Promise<OperationResult>>(),
    exportFbx: vi.fn<[string, number?], Promise<OperationResult>>(),
    captureViewport: vi.fn<[string?], Promise<CaptureResult>>(),
    setSubdivisionLevel: vi.fn<[number], Promise<OperationResult>>(),
    undo: vi.fn<[], Promise<OperationResult>>(),
    redo: vi.fn<[], Promise<OperationResult>>(),
    getCameraInfo: vi.fn<[], Promise<CameraInfo>>(),
    setCameraFocalLength: vi.fn<[number], Promise<FocalLengthResult>>(),
    getLights: vi.fn<[], Promise<LightInfo[]>>(),
    setLightColor: vi.fn<[string, number, number, number], Promise<LightColorResult>>(),
    getLightInfo: vi.fn<[string], Promise<LightDetailInfo>>(),
    setLightMultiplier: vi.fn<[string, number], Promise<LightMultiplierResult>>(),
    getExpressionInfo: vi.fn<[], Promise<ExpressionInfo>>(),
    resetAllMorphs: vi.fn<[string?], Promise<ResetMorphsResult>>(),
    searchMorphs: vi.fn<[string, string?], Promise<Array<{ id: string; display_name: string; category: string }>>>(),
    getMaterialInfo: vi.fn<[string?], Promise<MaterialInfo>>(),
    getDiffuseColor: vi.fn<[string, string], Promise<DiffuseColor>>(),
    setDiffuseColor: vi.fn<[string, string, number, number, number], Promise<SetDiffuseColorResult>>(),
    getMaterialProperties: vi.fn<[string, string], Promise<MaterialProperties>>(),
    setMaterialOpacity: vi.fn<[string, string, number], Promise<SetMaterialPropertyResult>>(),
    setMaterialGlossiness: vi.fn<[string, string, number], Promise<SetMaterialPropertyResult>>(),
    setMaterialSpecular: vi.fn<[string, string, number], Promise<SetMaterialPropertyResult>>(),
  };
}

export const SUCCESS: OperationResult = { success: true };
export const FAILURE: OperationResult = { success: false, error: "operation failed" };
export const CREATE_SUCCESS: CreateAvatarResult = { success: true, name: "Default Character" };
export const CAPTURE_SUCCESS: CaptureResult = { success: true, path: "C:/temp/capture.png", base64: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" };
