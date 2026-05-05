// abstract: Same-origin guard for state-changing browser web API requests.
// out_of_scope: Feature authorization, CORS policy, and session authentication.

import type { NextFunction, Request, RequestHandler, Response } from "express";

import type { WebServerConfig } from "../config.js";

const safeMethods = new Set(["GET", "HEAD", "OPTIONS"]);

function readOrigin(value: string | undefined): string | undefined {
  if (value === undefined || value.trim() === "") {
    return undefined;
  }

  try {
    return new URL(value).origin;
  } catch {
    return undefined;
  }
}

function requestOrigin(request: Request): string | undefined {
  const origin = readOrigin(request.get("origin"));
  if (origin !== undefined) {
    return origin;
  }

  return readOrigin(request.get("referer"));
}

function rejectOrigin(response: Response): void {
  response.status(403).json({
    error: {
      code: "csrf_origin_rejected",
      message: "Request origin is not allowed.",
    },
  });
}

export function createWebApiOriginGuard(
  config: WebServerConfig,
): RequestHandler {
  const expectedOrigin = new URL(config.publicBaseUrl).origin;

  return (request: Request, response: Response, next: NextFunction) => {
    if (safeMethods.has(request.method.toUpperCase())) {
      next();
      return;
    }

    if (requestOrigin(request) === expectedOrigin) {
      next();
      return;
    }

    rejectOrigin(response);
  };
}
