// abstract: Shared dashboard BFF error types with safe browser-facing codes.
// out_of_scope: Express route serialization and external request execution.

export class DashboardDependencyError extends Error {
  readonly code: string;
  readonly status: number;
  readonly upstreamStatus?: number;

  constructor(
    message: string,
    options: {
      readonly code?: string;
      readonly status?: number;
      readonly upstreamStatus?: number;
    } = {},
  ) {
    super(message);
    this.name = "DashboardDependencyError";
    this.code = options.code ?? "dashboard_dependency_unavailable";
    this.status = options.status ?? 502;
    this.upstreamStatus = options.upstreamStatus;
  }
}

export class DashboardTokenError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "DashboardTokenError";
    this.code = code;
    this.status = status;
  }
}
