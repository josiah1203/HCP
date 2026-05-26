import type { HttpClient } from "../http.js";
import type { BomResult } from "../types.js";

export class BomResource {
  constructor(private readonly http: HttpClient) {}

  async get(objectId: string, versionNum?: number): Promise<BomResult> {
    if (versionNum !== undefined) {
      return this.http.getJson(`/v1/bom/${objectId}/versions/${versionNum}`);
    }
    return this.http.getJson(`/v1/bom/${objectId}`);
  }

  async flat(objectId: string): Promise<BomResult> {
    return this.http.getJson(`/v1/bom/${objectId}/flat`);
  }

  async diff(objectId: string, versionA: number, versionB: number): Promise<BomResult> {
    return this.http.getJson(`/v1/bom/${objectId}/diff/${versionA}/${versionB}`);
  }
}
