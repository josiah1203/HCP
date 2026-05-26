import * as core from "@actions/core";
import * as glob from "@actions/glob";
import { readFile } from "node:fs/promises";
import path from "node:path";

interface UploadResult {
  object: { id: string; name: string };
  version: { id: string; version_num: number; parse_status: string };
}

async function uploadFile(
  apiUrl: string,
  apiKey: string,
  projectId: string,
  filePath: string,
  waitForParse: boolean,
  parseTimeoutMs: number
): Promise<UploadResult> {
  const buffer = await readFile(filePath);
  const filename = path.basename(filePath);
  const name = filename.replace(/\.[^.]+$/, "") || filename;

  const form = new FormData();
  form.append("file", new Blob([buffer]), filename);
  form.append("project_id", projectId);
  form.append("name", name);

  const res = await fetch(`${apiUrl.replace(/\/$/, "")}/v1/objects/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body: form,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Upload failed (${res.status}): ${text}`);
  }

  let result = (await res.json()) as UploadResult;

  if (waitForParse) {
    const oid = result.object.id;
    const vnum = result.version.version_num;
    const deadline = Date.now() + parseTimeoutMs;
    while (Date.now() < deadline) {
      const vRes = await fetch(
        `${apiUrl.replace(/\/$/, "")}/v1/objects/${oid}/versions/${vnum}`,
        { headers: { Authorization: `Bearer ${apiKey}` } }
      );
      if (!vRes.ok) break;
      const version = (await vRes.json()) as { parse_status: string };
      if (version.parse_status === "complete" || version.parse_status === "failed") {
        result = { ...result, version: { ...result.version, parse_status: version.parse_status } };
        break;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  }

  return result;
}

async function run(): Promise<void> {
  const apiKey = core.getInput("api_key", { required: true });
  const projectId = core.getInput("project_id", { required: true });
  const filesPattern = core.getInput("files") || "build/**/*";
  const waitForParse = (core.getInput("wait_for_parse") || "true") === "true";
  const apiUrl = core.getInput("api_url") || "https://api.hcp.io";

  const globber = await glob.create(filesPattern);
  const files = await globber.glob();

  if (files.length === 0) {
    core.setFailed(`No files matched pattern: ${filesPattern}`);
    return;
  }

  const objectIds: string[] = [];
  const versionIds: string[] = [];

  for (const file of files) {
    core.info(`Uploading ${file}`);
    const result = await uploadFile(apiUrl, apiKey, projectId, file, waitForParse, 120_000);
    objectIds.push(result.object.id);
    versionIds.push(result.version.id);
    core.info(`Uploaded ${result.object.name} → ${result.object.id} v${result.version.version_num}`);
  }

  core.setOutput("object_ids", objectIds.join(","));
  core.setOutput("version_ids", versionIds.join(","));
}

run().catch((err: Error) => {
  core.setFailed(err.message);
});
