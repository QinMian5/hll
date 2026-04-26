// abstract: Explicit browser-facing BFF route for search requests.
// out_of_scope: Browser query hooks and backend search ranking behavior.

import { type RequestHandler, Router } from "express";

import type { InternalApiClient } from "../internal-api/client.js";
import {
  handleWebRouteError,
  WebRouteInputError,
} from "../internal-api/errors.js";

export type SearchInternalApi = Pick<InternalApiClient, "search">;

export interface CreateSearchRouterOptions {
  readonly internalApi: SearchInternalApi;
  readonly quotaMiddleware: RequestHandler;
}

function readSearchQuery(value: unknown): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new WebRouteInputError(
      "invalid_request",
      "Search query is required.",
    );
  }

  return value.trim();
}

export function createSearchRouter(options: CreateSearchRouterOptions): Router {
  const router = Router();

  router.get("/", options.quotaMiddleware, async (request, response, next) => {
    try {
      const query = readSearchQuery(request.query.query);
      response.json(await options.internalApi.search(query));
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  return router;
}
