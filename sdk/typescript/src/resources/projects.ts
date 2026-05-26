import type { HttpClient } from "../http.js";
import type { Project } from "../types.js";

export class ProjectsResource {
  constructor(private readonly http: HttpClient) {}

  async create(name: string, description?: string | null): Promise<Project> {
    return this.http.postJson<Project>("/v1/projects", { name, description });
  }

  async list(): Promise<Project[]> {
    const payload = await this.http.getJson<{ data: Project[] }>("/v1/projects");
    return payload.data;
  }

  async get(projectId: string): Promise<Project> {
    return this.http.getJson<Project>(`/v1/projects/${projectId}`);
  }

  async tree(projectId: string): Promise<Record<string, unknown>> {
    return this.http.getJson(`/v1/projects/${projectId}/tree`);
  }
}
