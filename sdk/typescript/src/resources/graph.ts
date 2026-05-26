import type { HttpClient } from "../http.js";
import type { GraphResult } from "../types.js";

export class GraphResource {
  constructor(private readonly http: HttpClient) {}

  async dependencies(objectId: string, depth = 3): Promise<GraphResult> {
    return this.http.getJson(`/v1/graph/${objectId}/dependencies`, { depth });
  }

  async dependents(objectId: string, depth = 3): Promise<GraphResult> {
    return this.http.getJson(`/v1/graph/${objectId}/dependents`, { depth });
  }

  async lineage(objectId: string): Promise<Record<string, unknown>> {
    return this.http.getJson(`/v1/graph/${objectId}/lineage`);
  }

  async link(
    fromObjectId: string,
    relationshipType: string,
    toObjectId: string
  ): Promise<Record<string, unknown>> {
    return this.http.postJson("/v1/graph/link", {
      from_object_id: fromObjectId,
      relationship_type: relationshipType,
      to_object_id: toObjectId,
    });
  }
}
