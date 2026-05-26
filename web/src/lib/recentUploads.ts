import type { UploadResult } from "../api/types";

const KEY = "hcp_recent_uploads";
const MAX = 20;

export interface RecentUpload {
  objectId: string;
  objectName: string;
  projectId: string;
  versionNum: number;
  filename: string;
  objectType: string;
  uploadedAt: string;
}

export function loadRecentUploads(): RecentUpload[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentUpload[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function pushRecentUpload(result: UploadResult): RecentUpload[] {
  const entry: RecentUpload = {
    objectId: result.object.id,
    objectName: result.object.name,
    projectId: result.object.project_id,
    versionNum: result.version.version_num,
    filename: result.version.filename,
    objectType: result.object.object_type,
    uploadedAt: new Date().toISOString(),
  };
  const next = [entry, ...loadRecentUploads().filter((u) => u.objectId !== entry.objectId)].slice(
    0,
    MAX
  );
  sessionStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
