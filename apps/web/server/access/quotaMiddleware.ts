// abstract: Express middleware for BFF anonymous/authenticated quota enforcement.
// out_of_scope: Feature route forwarding and Redis client lifecycle ownership.

import type { Request, RequestHandler, Response } from "express";

import type { WebSessionResponse } from "../auth/sessionState.js";
import type { WebServerConfig } from "../config.js";
import {
  type AnonymousIdentityOptions,
  ensureAnonymousIdentity,
} from "./anonymousIdentity.js";
import { resolveQuotaPrincipal } from "./principal.js";
import { buildQuotaConsumptions } from "./quotaPolicy.js";
import type { QuotaStore } from "./quotaStore.js";

export interface CreateQuotaMiddlewareOptions {
  readonly anonymousIdentity?: AnonymousIdentityOptions;
  readonly config: WebServerConfig;
  readonly cost?: number;
  readonly getSession?: (
    request: Request,
    response: Response,
  ) => Promise<WebSessionResponse>;
  readonly routeGroup: string;
  readonly store: QuotaStore;
}

function resolveIpAddress(request: Request): string {
  return request.ip || request.socket.remoteAddress || "unknown";
}

export function createQuotaMiddleware(
  options: CreateQuotaMiddlewareOptions,
): RequestHandler {
  return async (request, response, next) => {
    try {
      const session = await (options.getSession?.(request, response) ??
        Promise.resolve({ status: "anonymous" as const }));
      const anonymousId =
        session.status === "anonymous"
          ? ensureAnonymousIdentity(
              request,
              response,
              options.config,
              options.anonymousIdentity,
            )
          : undefined;
      const principal = resolveQuotaPrincipal({
        anonymousId,
        ipAddress: resolveIpAddress(request),
        session,
      });
      const consumptions = buildQuotaConsumptions(options.config, {
        cost: options.cost ?? 1,
        principal,
        routeGroup: options.routeGroup,
      });

      for (const consumption of consumptions) {
        const result = await options.store.consume(consumption);

        if (!result.allowed) {
          response.setHeader("Retry-After", String(result.retryAfterSeconds));
          response.status(429).json({
            error: {
              code: "quota_exceeded",
              message: "Rate limit exceeded.",
            },
          });
          return;
        }
      }

      next();
    } catch (error) {
      next(error);
    }
  };
}
