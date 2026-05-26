import type { ApiErrorBody } from "./types.js";

export class HCPError extends Error {
  readonly statusCode?: number;
  readonly code?: string;

  constructor(message: string, statusCode?: number, code?: string) {
    super(message);
    this.name = "HCPError";
    this.statusCode = statusCode;
    this.code = code;
  }
}

export class AuthenticationError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "AuthenticationError";
  }
}

export class PermissionError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "PermissionError";
  }
}

export class NotFoundError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "NotFoundError";
  }
}

export class ValidationError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "ValidationError";
  }
}

export class RateLimitError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "RateLimitError";
  }
}

export class ServerError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "ServerError";
  }
}

export class ParseTimeoutError extends HCPError {
  constructor(message: string, statusCode?: number, code?: string) {
    super(message, statusCode, code);
    this.name = "ParseTimeoutError";
  }
}

export async function raiseForStatus(response: Response): Promise<void> {
  if (response.ok) return;

  let message = response.statusText;
  let code: string | undefined;
  try {
    const data = (await response.json()) as ApiErrorBody;
    if (data.error?.message) message = data.error.message;
    code = data.error?.code;
  } catch {
    /* ignore */
  }

  const status = response.status;
  const mapping: Record<number, typeof HCPError> = {
    401: AuthenticationError,
    403: PermissionError,
    404: NotFoundError,
    422: ValidationError,
    429: RateLimitError,
  };
  if (status >= 500) {
    throw new ServerError(message, status, code);
  }
  const Exc = mapping[status] ?? HCPError;
  throw new Exc(message, status, code);
}
