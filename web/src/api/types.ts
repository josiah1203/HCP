export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  token_type: string;
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

export interface Pagination {
  page: number;
  per_page: number;
  total: number;
  total_pages?: number;
}

export interface SearchHit {
  id: string;
  name: string;
  object_type?: string;
  lifecycle_state?: string;
  project_id?: string;
  snippet?: string;
  [key: string]: unknown;
}

export interface SearchResponse {
  data: SearchHit[];
  pagination: Pagination;
  facets?: {
    types?: Array<{ value: string; count: number }>;
    states?: Array<{ value: string; count: number }>;
    projects?: Array<{ value: string; count: number; label?: string }>;
  };
}

export interface TreeNode {
  id: string;
  name: string;
  object_type: string;
  lifecycle_state?: string;
  version_num?: number;
  parse_status?: string;
  children?: TreeNode[];
}

export interface GraphNode {
  id: string;
  label?: string;
  type?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type?: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface BomLine {
  ref?: string;
  mpn?: string;
  manufacturer?: string;
  quantity?: number;
  value?: string;
  [key: string]: unknown;
}

export interface BomResponse {
  lines?: BomLine[];
  components?: Array<Record<string, unknown>>;
}

export interface AuditEntry {
  id: string;
  event_type: string;
  from_state?: string | null;
  to_state?: string | null;
  actor_email: string;
  comment?: string | null;
  created_at: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}
