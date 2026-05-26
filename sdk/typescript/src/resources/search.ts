import type { HttpClient } from "../http.js";
import type { SearchResult } from "../types.js";

export interface SearchQueryOptions {
  q?: string;
  type?: string;
  state?: string;
  projectId?: string;
  page?: number;
  perPage?: number;
}

export class SearchResource {
  constructor(private readonly http: HttpClient) {}

  async query(options: SearchQueryOptions = {}): Promise<SearchResult> {
    return this.http.getJson("/v1/search", {
      q: options.q,
      type: options.type,
      state: options.state,
      project_id: options.projectId,
      page: options.page ?? 1,
      per_page: options.perPage ?? 20,
    });
  }
}
