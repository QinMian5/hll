// abstract: Error types and response mapping for web BFF route handlers.
// out_of_scope: Internal API transport execution and quota policy decisions.

import type { NextFunction, Response } from "express";

export class InternalApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "InternalApiError";
    this.status = status;
  }
}

export class WebRouteInputError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "WebRouteInputError";
    this.code = code;
  }
}

export function handleWebRouteError(
  error: unknown,
  response: Response,
  next: NextFunction,
): void {
  if (error instanceof WebRouteInputError) {
    response.status(400).json({
      error: {
        code: error.code,
        message: error.message,
      },
    });
    return;
  }

  if (error instanceof InternalApiError) {
    response.status(error.status).json({
      error: {
        code: "internal_api_request_failed",
        message: "Internal API request failed.",
      },
    });
    return;
  }

  next(error);
}
