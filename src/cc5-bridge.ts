/**
 * HTTP client for communicating with the CC5 Python bridge plugin.
 */

import type {
  CC5Avatar,
  CC5Response,
  MorphCatalog,
  AvatarInfo,
  OperationResult,
  MorphSetRequest,
} from "./types.js";

const DEFAULT_BASE_URL = "http://127.0.0.1:5100";
const REQUEST_TIMEOUT_MS = 30_000;

export class CC5Bridge {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ?? process.env.CC5_BRIDGE_URL ?? DEFAULT_BASE_URL;
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

      return data.result as T;
    } finally {
      clearTimeout(timeout);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.request<{ status: string }>("/health");
      return true;
    } catch {
      return false;
    }
  }

  async getAvatars(): Promise<CC5Avatar[]> {
    return this.request<CC5Avatar[]>("/avatars");
  }

  async getAvatarInfo(): Promise<AvatarInfo | null> {
    return this.request<AvatarInfo | null>("/avatar/info");
  }

  async getMorphCatalog(): Promise<MorphCatalog> {
    return this.request<MorphCatalog>("/morphs/catalog");
  }

  async getMorphValue(morphId: string): Promise<number | null> {
    return this.request<number | null>("/morph/get", "POST", {
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

  async loadAsset(filePath: string): Promise<OperationResult> {
    return this.request<OperationResult>("/asset/load", "POST", {
      file_path: filePath,
    });
  }

  async exportFbx(
    outputPath: string,
    options: number = 0
  ): Promise<OperationResult> {
    return this.request<OperationResult>("/export/fbx", "POST", {
      output_path: outputPath,
      options,
    });
  }

  async setSubdivisionLevel(level: number): Promise<OperationResult> {
    return this.request<OperationResult>("/subdivision", "POST", { level });
  }
}
