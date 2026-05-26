import { readFile } from "node:fs/promises";

import type { HttpClient } from "../http.js";
import type { HardwareObject, UploadResult, Version } from "../types.js";

export interface UploadOptions {
  filePath: string;
  projectId: string;
  name: string;
  description?: string;
  objectId?: string;
  waitForParse?: boolean;
  parseTimeoutMs?: number;
}

export class ObjectsResource {
  constructor(private readonly http: HttpClient) {}

  async get(objectId: string): Promise<HardwareObject> {
    return this.http.getJson<HardwareObject>(`/v1/objects/${objectId}`);
  }

  async listVersions(objectId: string): Promise<Version[]> {
    const payload = await this.http.getJson<{ data: Version[] }>(
      `/v1/objects/${objectId}/versions`
    );
    return payload.data;
  }

  async getVersion(objectId: string, versionNum: number): Promise<Version> {
    return this.http.getJson<Version>(`/v1/objects/${objectId}/versions/${versionNum}`);
  }

  async getParsed(objectId: string, versionNum: number): Promise<Record<string, unknown>> {
    return this.http.getJson(`/v1/objects/${objectId}/versions/${versionNum}/parsed`);
  }

  async downloadUrl(objectId: string, versionNum: number): Promise<string> {
    const payload = await this.http.getJson<{ url: string }>(
      `/v1/objects/${objectId}/versions/${versionNum}/download`
    );
    return payload.url;
  }

  async promote(
    objectId: string,
    versionNum: number,
    targetState: string,
    comment?: string
  ): Promise<Version> {
    return this.http.postJson(`/v1/objects/${objectId}/versions/${versionNum}/promote`, {
      target_state: targetState,
      comment,
    });
  }

  async upload(options: UploadOptions): Promise<UploadResult> {
    const buffer = await readFile(options.filePath);
    const filename = options.filePath.split(/[/\\]/).pop() ?? "file";
    const form = new FormData();
    form.append("file", new Blob([buffer]), filename);
    form.append("project_id", options.projectId);
    form.append("name", options.name);
    if (options.description) form.append("description", options.description);
    if (options.objectId) form.append("object_id", options.objectId);

    const res = await this.http.request("POST", "/v1/objects/upload", { body: form });
    let result = (await res.json()) as UploadResult;

    if (options.waitForParse) {
      const oid = result.object.id;
      const vnum = result.version.version_num;
      result = {
        ...result,
        version: (await this.http.pollParse(
          oid,
          vnum,
          options.parseTimeoutMs ?? 120_000
        )) as Version,
      };
    }

    return result;
  }
}
