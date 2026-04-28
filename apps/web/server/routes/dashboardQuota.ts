// abstract: Browser-facing BFF route for dashboard MCP account quota.
// out_of_scope: Figma dashboard rendering and MCP quota persistence.

import {
  type NextFunction,
  type Request,
  type Response,
  Router,
} from "express";

import type { WebSessionResponse } from "../auth/sessionState.js";
import { DashboardDependencyError } from "../dashboard/errors.js";
import type { McpQuotaSummaryResponse } from "../dashboard/mcpQuotaSummary.js";

export interface DashboardMcpQuotaSummaryClient {
  readonly getQuotaSummary: (
    userSub: string,
  ) => Promise<McpQuotaSummaryResponse>;
}

export interface CreateDashboardQuotaRouterOptions {
  readonly getSession: (
    request: Request,
    response: Response,
  ) => Promise<WebSessionResponse>;
  readonly mcpQuotaClient: DashboardMcpQuotaSummaryClient;
  readonly quotaMiddleware?: import("express").RequestHandler;
}

class DashboardQuotaRouteError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "DashboardQuotaRouteError";
    this.status = status;
    this.code = code;
  }
}

async function requireAuthenticatedUser(
  options: CreateDashboardQuotaRouterOptions,
  request: Request,
  response: Response,
): Promise<string> {
  const session = await options.getSession(request, response);

  if (session.status === "anonymous") {
    throw new DashboardQuotaRouteError(
      401,
      "dashboard_auth_required",
      "Authentication is required.",
    );
  }

  return session.user.id;
}

function handleDashboardQuotaError(
  error: unknown,
  response: Response,
  next: NextFunction,
): void {
  if (error instanceof DashboardQuotaRouteError) {
    response.status(error.status).json({
      error: {
        code: error.code,
        message: error.message,
      },
    });
    return;
  }

  if (error instanceof DashboardDependencyError) {
    response.json({
      quota: null,
      quotaAvailable: false,
    });
    return;
  }

  next(error);
}

export function createDashboardQuotaRouter(
  options: CreateDashboardQuotaRouterOptions,
): Router {
  const router = Router();

  if (options.quotaMiddleware !== undefined) {
    router.use(options.quotaMiddleware);
  }

  router.get("/quota", async (request, response, next) => {
    try {
      const userSub = await requireAuthenticatedUser(
        options,
        request,
        response,
      );
      const result = await options.mcpQuotaClient.getQuotaSummary(userSub);

      response.json({
        quota: result.quota,
        quotaAvailable: true,
      });
    } catch (error) {
      handleDashboardQuotaError(error, response, next);
    }
  });

  return router;
}
