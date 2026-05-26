import { ParseTimeoutError, raiseForStatus } from "./errors.js";
import type { ClientOptions } from "./types.js";

export class HttpClient {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;
  private readonly timeout: number;
  private readonly maxRetries: number;

  constructor(options: ClientOptions) {
    const token = options.accessToken ?? options.apiKey;
    if (!token) {
      throw new Error("apiKey or accessToken required");
    }
    this.baseUrl = (options.apiUrl ?? "https://api.hcp.io").replace(/\/$/, "");
    this.timeout = options.timeout ?? 30_000;
    this.maxRetries = options.maxRetries ?? 3;
    this.headers = {
      Authorization: `Bearer ${token}`,
    };
  }

  async request(
    method: string,
    path: string,
    init?: RequestInit & { params?: Record<string, string | number | undefined> }
  ): Promise<Response> {
    const url = new URL(path.startsWith("http") ? path : `${this.baseUrl}${path}`);
    if (init?.params) {
      for (const [k, v] of Object.entries(init.params)) {
        if (v !== undefined) url.searchParams.set(k, String(v));
      }
    }

    const { params: _p, ...rest } = init ?? {};
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeout);
      try {
        const response = await fetch(url, {
          method,
          headers: this.headers,
          signal: controller.signal,
          ...rest,
        });
        clearTimeout(timer);
        if (response.status === 429 && attempt < this.maxRetries) {
          await sleep(2 ** attempt * 1000);
          continue;
        }
        await raiseForStatus(response);
        return response;
      } catch (err) {
        clearTimeout(timer);
        if (err instanceof Error && err.name.endsWith("Error") && err.name !== "Error") {
          const hcpNames = [
            "HCPError",
            "AuthenticationError",
            "PermissionError",
            "NotFoundError",
            "ValidationError",
            "RateLimitError",
            "ServerError",
            "ParseTimeoutError",
          ];
          if (hcpNames.includes(err.name)) throw err;
        }
        lastError = err instanceof Error ? err : new Error(String(err));
        if (attempt < this.maxRetries) {
          await sleep(2 ** attempt * 1000);
        }
      }
    }
    throw lastError ?? new Error("Request failed");
  }

  async getJson<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
    const res = await this.request("GET", path, { params });
    return (await res.json()) as T;
  }

  async postJson<T>(path: string, body: unknown): Promise<T> {
    const res = await this.request("POST", path, {
      headers: { "Content-Type": "application/json", ...this.headers },
      body: JSON.stringify(body),
    });
    return (await res.json()) as T;
  }

  async pollParse(
    objectId: string,
    versionNum: number,
    timeoutMs: number,
    intervalMs = 2000
  ): Promise<Record<string, unknown>> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const version = await this.getJson<Record<string, unknown>>(
        `/v1/objects/${objectId}/versions/${versionNum}`
      );
      const status = version.parse_status as string | undefined;
      if (status === "complete" || status === "failed") return version;
      await sleep(intervalMs);
    }
    throw new ParseTimeoutError(`Parse did not complete within ${timeoutMs}ms`, undefined, "parse_timeout");
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
