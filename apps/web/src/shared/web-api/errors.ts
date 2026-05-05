// abstract: Error types and auth-error events for browser calls to the web BFF API.
// out_of_scope: Feature-specific query orchestration and auth UI rendering.

export const WEB_AUTH_ERROR_EVENT = "knowledge.web-auth-error";
export const WEB_AUTH_ERROR_CODES = [
  "authentication_required",
  "session_expired",
] as const;

export type WebAuthErrorCode = (typeof WEB_AUTH_ERROR_CODES)[number];

export interface WebAuthErrorEventDetail {
  readonly code: WebAuthErrorCode;
  readonly message: string;
  readonly status: number;
}

export class WebApiRequestError extends Error {
  readonly code: string;
  readonly retryAfterSeconds: number | undefined;
  readonly status: number;

  constructor(options: {
    readonly code: string;
    readonly message: string;
    readonly retryAfterSeconds?: number;
    readonly status: number;
  }) {
    super(options.message);
    this.name = "WebApiRequestError";
    this.code = options.code;
    this.retryAfterSeconds = options.retryAfterSeconds;
    this.status = options.status;
  }
}

export function isWebAuthError(
  error: unknown,
): error is WebApiRequestError & { readonly code: WebAuthErrorCode } {
  return (
    error instanceof WebApiRequestError &&
    error.status === 401 &&
    WEB_AUTH_ERROR_CODES.includes(error.code as WebAuthErrorCode)
  );
}

export function dispatchWebAuthError(error: WebApiRequestError): void {
  if (!isWebAuthError(error) || typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(
    new CustomEvent<WebAuthErrorEventDetail>(WEB_AUTH_ERROR_EVENT, {
      detail: {
        code: error.code,
        message: error.message,
        status: error.status,
      },
    }),
  );
}

export function subscribeToWebAuthErrors(
  listener: (detail: WebAuthErrorEventDetail) => void,
): () => void {
  function handleEvent(event: Event) {
    listener((event as CustomEvent<WebAuthErrorEventDetail>).detail);
  }

  window.addEventListener(WEB_AUTH_ERROR_EVENT, handleEvent);
  return () => {
    window.removeEventListener(WEB_AUTH_ERROR_EVENT, handleEvent);
  };
}
