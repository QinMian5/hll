// abstract: Error types for browser calls to the web BFF API.
// out_of_scope: Feature-specific query orchestration and auth UI rendering.

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
