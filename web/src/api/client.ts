import type {
  ApiError,
  AuditEntry,
  BomResponse,
  GraphResponse,
  HardwareObject,
  Project,
  SearchResponse,
  TokenResponse,
  TreeNode,
  UploadResult,
  User,
  Version,
} from "./types";

export class ApiClientError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
}

type TokenGetter = () => string | null;

export class ApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getToken: TokenGetter
  ) {}

  private headers(json = true): HeadersInit {
    const h: Record<string, string> = {};
    if (json) h["Content-Type"] = "application/json";
    const token = this.getToken();
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }

  private async parseError(res: Response): Promise<ApiClientError> {
    let message = res.statusText;
    let code: string | undefined;
    try {
      const body = (await res.json()) as ApiError;
      message = body.error?.message ?? message;
      code = body.error?.code;
    } catch {
      /* ignore */
    }
    return new ApiClientError(message, res.status, code);
  }

  private async request<T>(
    path: string,
    init?: RequestInit
  ): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { ...this.headers(!(init?.body instanceof FormData)), ...init?.headers },
    });
    if (!res.ok) throw await this.parseError(res);
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  login(email: string, password: string): Promise<TokenResponse> {
    return this.request("/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  me(): Promise<{ user: User }> {
    return this.request("/v1/auth/me");
  }

  listProjects(): Promise<{ data: Project[] }> {
    return this.request("/v1/projects");
  }

  createProject(name: string, description?: string): Promise<Project> {
    return this.request("/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
  }

  getProject(projectId: string): Promise<Project> {
    return this.request(`/v1/projects/${projectId}`);
  }

  getProjectTree(projectId: string): Promise<{ data: TreeNode[] }> {
    return this.request(`/v1/projects/${projectId}/tree`);
  }

  getObject(objectId: string): Promise<HardwareObject> {
    return this.request(`/v1/objects/${objectId}`);
  }

  listVersions(objectId: string): Promise<{ data: Version[] }> {
    return this.request(`/v1/objects/${objectId}/versions`);
  }

  getVersion(objectId: string, versionNum: number): Promise<Version> {
    return this.request(`/v1/objects/${objectId}/versions/${versionNum}`);
  }

  async uploadObject(
    file: File,
    projectId: string,
    name: string,
    description?: string,
    objectId?: string
  ): Promise<UploadResult> {
    const form = new FormData();
    form.append("file", file);
    form.append("project_id", projectId);
    form.append("name", name);
    if (description) form.append("description", description);
    if (objectId) form.append("object_id", objectId);

    const res = await fetch(`${this.baseUrl}/v1/objects/upload`, {
      method: "POST",
      headers: this.headers(false),
      body: form,
    });
    if (!res.ok) throw await this.parseError(res);
    return (await res.json()) as UploadResult;
  }

  promote(
    objectId: string,
    versionNum: number,
    targetState: string,
    comment?: string
  ): Promise<Version> {
    return this.request(`/v1/objects/${objectId}/versions/${versionNum}/promote`, {
      method: "POST",
      body: JSON.stringify({ target_state: targetState, comment }),
    });
  }

  getParsed(objectId: string, versionNum: number): Promise<Record<string, unknown>> {
    return this.request(`/v1/objects/${objectId}/versions/${versionNum}/parsed`);
  }

  getBom(objectId: string, versionNum?: number): Promise<BomResponse> {
    const path =
      versionNum !== undefined
        ? `/v1/bom/${objectId}/versions/${versionNum}`
        : `/v1/bom/${objectId}`;
    return this.request(path);
  }

  getGraph(objectId: string, depth = 2): Promise<GraphResponse> {
    return this.request(`/v1/graph/${objectId}/dependencies?depth=${depth}`);
  }

  search(params: URLSearchParams): Promise<SearchResponse> {
    return this.request(`/v1/search?${params.toString()}`);
  }

  getAuditLog(objectId: string): Promise<{ data: AuditEntry[] }> {
    return this.request(`/v1/objects/${objectId}/audit`);
  }
}

export const apiBaseUrl = import.meta.env.VITE_API_URL ?? "";
