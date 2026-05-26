export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages?: number;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Version {
  id: string;
  object_id: string;
  version_num: number;
  filename: string;
  content_hash: string;
  file_size_bytes: number;
  parse_status: string;
  lifecycle_state: string;
  description: string | null;
  created_at: string;
  hcp_uri?: string | null;
}

export interface HardwareObject {
  id: string;
  org_id: string;
  project_id: string;
  name: string;
  object_type: string;
  created_at: string;
  latest_version?: Version | null;
}

export interface UploadResult {
  object: HardwareObject;
  version: Version;
  deduplicated: boolean;
}

export interface SearchResult {
  data: Array<Record<string, unknown>>;
  pagination: Pagination;
  facets?: Record<string, unknown>;
}

export interface GraphResult {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
}

export interface BomResult {
  lines?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}

export interface ClientOptions {
  apiKey?: string;
  accessToken?: string;
  apiUrl?: string;
  timeout?: number;
  maxRetries?: number;
}
