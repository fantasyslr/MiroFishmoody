// frontend/src/lib/contracts.ts
// API Contract Lock — frozen 2026-03-18
//
// DO NOT change these types without updating the corresponding Flask endpoint.
// Source of truth: backend/app/api/
//
// Rule: Page components MUST import API types from contracts.ts, NOT from api.ts directly.
// This creates a stable named surface that TypeScript can validate during Phase 14 rewrite.
//
// lib/api.ts is FROZEN — do not modify it. Add new types here if needed.

import type {
  AuthUser,
  RacePayload,
  RaceResult,
  EvaluatePayload,
  TaskStatusResponse,
  EvaluateResult,
  UploadImageResponse,
  VersionInfo,
  VersionCompareResult,
} from './api'

// Re-export from api.ts — single source of truth
export type {
  AuthUser,
  RacePayload,
  RaceResult,
  EvaluatePayload,
  TaskStatusResponse,
  EvaluateResult,
  UploadImageResponse,
  VersionInfo,
  VersionCompareResult,
}

// Types not yet in api.ts — endpoint-literal shapes

/** Response shape from POST /api/campaign/evaluate */
export type EvaluateSubmitResponse = {
  task_id: string
  set_id: string
  campaign_count: number
  message: string
}

/** Single image entry from GET /api/campaign/images/<set_id> */
export type ImageFileEntry = {
  filename: string
  url: string
}

/** Response shape from GET /api/campaign/images/<set_id> */
export type ListImagesResponse = {
  images: ImageFileEntry[]
}

/** Response shape from POST /api/auth/logout */
export type LogoutResponse = {
  status: string
}
