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
  id: string;
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
  [key: string]: unknown;
}
