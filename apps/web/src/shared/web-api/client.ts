// abstract: Same-origin JSON client for browser calls to the web BFF API.
// out_of_scope: Server-side internal API transport and feature query state.

import { dispatchWebAuthError, WebApiRequestError } from "./errors";

interface WebApiErrorPayload {
  readonly error?: {
    readonly code?: unknown;
    readonly message?: unknown;
  };
}

export interface WebApiJsonRequestOptions {
  readonly body?: unknown;
  readonly method?: "GET" | "PATCH" | "POST";
}

function assertWebApiPath(path: string): void {
  if (!path.startsWith("/web-api/")) {
    throw new Error("Web API requests must use same-origin /web-api paths.");
  }
}

async function readError(response: Response): Promise<WebApiRequestError> {
  let payload: WebApiErrorPayload | undefined;

  try {
    payload = (await response.json()) as WebApiErrorPayload;
  } catch (_error) {
    payload = undefined;
  }

  const code =
    typeof payload?.error?.code === "string"
      ? payload.error.code
      : "web_api_request_failed";
  const message =
    typeof payload?.error?.message === "string"
      ? payload.error.message
      : `Web API request failed with status ${response.status}.`;

  return new WebApiRequestError({
    code,
    message,
    retryAfterSeconds: parseRetryAfterSeconds(response),
    status: response.status,
  });
}

function parseRetryAfterSeconds(response: Response): number | undefined {
  const rawValue = response.headers.get("Retry-After");
  if (rawValue === null) {
    return undefined;
  }

  const parsed = Number(rawValue);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return undefined;
  }
  return parsed;
}

export async function fetchWebApiJson<TResponse>(
  path: string,
  options: WebApiJsonRequestOptions = {},
): Promise<TResponse> {
  assertWebApiPath(path);

  const method = options.method ?? "GET";
  const response = await fetch(path, {
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: "include",
    headers:
      options.body === undefined
        ? undefined
        : { "Content-Type": "application/json" },
    method,
  });

  if (!response.ok) {
    const error = await readError(response);
    dispatchWebAuthError(error);
    throw error;
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}
