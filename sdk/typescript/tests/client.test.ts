import { readFile } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Client } from "../src/index.js";
import {
  AuthenticationError,
  NotFoundError,
  ParseTimeoutError,
  PermissionError,
  RateLimitError,
  ServerError,
  ValidationError,
} from "../src/errors.js";

vi.mock("node:fs/promises", () => ({
  readFile: vi.fn(),
}));

const BASE = "https://api.test.hcp.io";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates projects", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ id: "p1", name: "Rev C", org_id: "o", created_at: "", description: null })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const project = await client.projects.create("Rev C");
    expect(project.name).toBe("Rev C");
  });

  it("lists projects", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ data: [{ id: "1", name: "A" }] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const list = await client.projects.list();
    expect(list).toHaveLength(1);
  });

  it("gets objects", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ id: "o1", name: "board", object_type: "PCB" })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const obj = await client.objects.get("o1");
    expect(obj.object_type).toBe("PCB");
  });

  it("searches", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        data: [{ id: "1", name: "STM32" }],
        pagination: { page: 1, per_page: 20, total: 1 },
        facets: { types: ["PCB"] },
      })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const results = await client.search.query({ q: "STM32", type: "PCB" });
    expect(results.data[0].name).toBe("STM32");
  });

  it("graph dependencies", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ nodes: [], edges: [] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const deps = await client.graph.dependencies("o1", 2);
    expect(deps.nodes).toEqual([]);
  });

  it("bom flat", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ lines: [] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const bom = await client.bom.flat("o1");
    expect(bom.lines).toEqual([]);
  });

  it("raises auth error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ error: { code: "unauthorized", message: "bad" } }, 401)
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await expect(client.projects.list()).rejects.toBeInstanceOf(AuthenticationError);
  });

  it("raises not found", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ error: { code: "not_found", message: "missing" } }, 404)
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await expect(client.objects.get("x")).rejects.toBeInstanceOf(NotFoundError);
  });

  it("bom diff", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ added: [], removed: [] })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const diff = await client.bom.diff("o1", 1, 2);
    expect(diff.added).toEqual([]);
  });

  it("graph link", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "rel-1" }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const rel = await client.graph.link("a", "VALIDATES", "b");
    expect(rel.id).toBe("rel-1");
  });

  it("lists object versions", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ data: [{ version_num: 1, id: "v1" }] })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const versions = await client.objects.listVersions("o1");
    expect(versions[0]?.version_num).toBe(1);
  });

  it("gets project tree", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ data: [] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const tree = await client.projects.tree("p1");
    expect(tree.data).toEqual([]);
  });

  it("bom get with version", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ lines: [{ ref: "R1" }] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const bom = await client.bom.get("o1", 2);
    expect(bom.lines).toHaveLength(1);
  });

  it("uploads file", async () => {
    vi.mocked(readFile).mockResolvedValue(Buffer.from("pcb"));

    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        object: { id: "o3", name: "b", org_id: "x", project_id: "p", object_type: "PCB", created_at: "" },
        version: { id: "v", object_id: "o3", version_num: 1, filename: "b.kicad_pcb", content_hash: "", file_size_bytes: 1, parse_status: "pending", lifecycle_state: "draft", description: null, created_at: "" },
        deduplicated: false,
      })
    );

    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const result = await client.objects.upload({
      filePath: "/tmp/b.kicad_pcb",
      projectId: "p",
      name: "b",
    });
    expect(result.object.id).toBe("o3");
  });

  it("waits for parse", async () => {
    vi.mocked(readFile).mockResolvedValue(Buffer.from("x"));
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          object: { id: "o4", name: "x", org_id: "", project_id: "p", object_type: "BOM", created_at: "" },
          version: { id: "v", object_id: "o4", version_num: 1, filename: "x.csv", content_hash: "", file_size_bytes: 1, parse_status: "pending", lifecycle_state: "draft", description: null, created_at: "" },
          deduplicated: false,
        })
      )
      .mockResolvedValueOnce(jsonResponse({ version_num: 1, parse_status: "complete", id: "v", object_id: "o4", filename: "x.csv", content_hash: "", file_size_bytes: 1, lifecycle_state: "draft", description: null, created_at: "" }));

    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const result = await client.objects.upload({
      filePath: "/tmp/x.csv",
      projectId: "p",
      name: "x",
      waitForParse: true,
      parseTimeoutMs: 5000,
    });
    expect(result.version.parse_status).toBe("complete");
  });

  it("promotes version", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ version_num: 1, lifecycle_state: "in_review", id: "v", object_id: "o", filename: "f", content_hash: "", file_size_bytes: 0, parse_status: "complete", description: null, created_at: "" })
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    const v = await client.objects.promote("o", 1, "in_review");
    expect(v.lifecycle_state).toBe("in_review");
  });

  it("download url", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ url: "https://signed" }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    expect(await client.objects.downloadUrl("o", 1)).toBe("https://signed");
  });

  it("graph lineage and dependents", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ nodes: [] }))
      .mockResolvedValueOnce(jsonResponse({ nodes: [], edges: [] }));
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await client.graph.lineage("o1");
    await client.graph.dependents("o1", 1);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("raises permission and validation errors", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "forbidden", message: "nope" } }, 403)
      )
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "validation_error", message: "bad" } }, 422)
      );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await expect(client.projects.list()).rejects.toBeInstanceOf(PermissionError);
    await expect(client.projects.list()).rejects.toBeInstanceOf(ValidationError);
  });

  it("raises server error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ error: { code: "server_error", message: "down" } }, 500)
    );
    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await expect(client.projects.list()).rejects.toBeInstanceOf(ServerError);
  });

  it("parse timeout on upload", async () => {
    vi.mocked(readFile).mockResolvedValue(Buffer.from("x"));
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          object: { id: "o5", name: "x", org_id: "", project_id: "p", object_type: "BOM", created_at: "" },
          version: { id: "v", object_id: "o5", version_num: 1, filename: "x.csv", content_hash: "", file_size_bytes: 1, parse_status: "pending", lifecycle_state: "draft", description: null, created_at: "" },
          deduplicated: false,
        })
      )
      .mockResolvedValue(jsonResponse({ parse_status: "pending", version_num: 1 }));

    const client = new Client({ apiKey: "k", apiUrl: BASE });
    await expect(
      client.objects.upload({
        filePath: "/tmp/x.csv",
        projectId: "p",
        name: "x",
        waitForParse: true,
        parseTimeoutMs: 50,
      })
    ).rejects.toBeInstanceOf(ParseTimeoutError);
  });
});
