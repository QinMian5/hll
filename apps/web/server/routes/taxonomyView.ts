// abstract: Explicit browser-facing BFF routes for taxonomy-view data.
// out_of_scope: Browser graph rendering and backend taxonomy service behavior.

import {
  type NextFunction,
  type RequestHandler,
  type Response,
  Router,
} from "express";

import type { InternalApiClient } from "../internal-api/client.js";
import {
  handleWebRouteError,
  InternalApiError,
  WebRouteInputError,
} from "../internal-api/errors.js";

export type TaxonomyViewInternalApi = Pick<
  InternalApiClient,
  | "getTaxonomyCardScopeNodeDetails"
  | "getTaxonomyCardScopeLayoutSlice"
  | "getTaxonomyCardScopeNodeTitles"
  | "getTaxonomyNode"
  | "getTaxonomyNodeByPath"
  | "getTaxonomyRoot"
>;

export interface CreateTaxonomyViewRouterOptions {
  readonly internalApi: TaxonomyViewInternalApi;
  readonly quotaMiddleware: RequestHandler;
}

function parseNodeId(value: unknown): number {
  if (typeof value !== "string") {
    throw new WebRouteInputError(
      "invalid_request",
      "Node id must be a positive integer.",
    );
  }

  const nodeId = Number(value);

  if (!Number.isInteger(nodeId) || nodeId <= 0) {
    throw new WebRouteInputError(
      "invalid_request",
      "Node id must be a positive integer.",
    );
  }

  return nodeId;
}

function parseNodeIdsBody(body: unknown): number[] {
  const nodeIds =
    typeof body === "object" && body !== null && "node_ids" in body
      ? (body as { readonly node_ids: unknown }).node_ids
      : undefined;

  if (
    !Array.isArray(nodeIds) ||
    nodeIds.some((nodeId) => !Number.isInteger(nodeId) || nodeId <= 0)
  ) {
    throw new WebRouteInputError(
      "invalid_request",
      "Node ids must be positive integers.",
    );
  }

  return nodeIds;
}

function parseRoutePathBody(body: unknown): string {
  const routePath =
    typeof body === "object" && body !== null && "route_path" in body
      ? (body as { readonly route_path: unknown }).route_path
      : undefined;

  if (typeof routePath !== "string") {
    throw new WebRouteInputError(
      "invalid_request",
      "Route path must be a string.",
    );
  }

  return routePath;
}

function parseRoutePathQuery(value: unknown): string {
  if (typeof value !== "string") {
    throw new WebRouteInputError(
      "invalid_request",
      "Route path must be a string.",
    );
  }

  return value;
}

function parseRoutePath(value: unknown): string {
  const segments =
    typeof value === "string" ? [value] : Array.isArray(value) ? value : [];

  if (
    segments.length === 0 ||
    segments.some((segment) => typeof segment !== "string" || segment === "")
  ) {
    throw new WebRouteInputError(
      "invalid_request",
      "Route path must be non-empty.",
    );
  }

  return segments.join("/");
}

function handleTaxonomyPathRouteError(
  error: unknown,
  response: Response,
  next: NextFunction,
): void {
  if (error instanceof InternalApiError && error.status === 404) {
    response.status(404).json({
      error: {
        code: "taxonomy_route_path_not_found",
        message: "Taxonomy route path was not found.",
      },
    });
    return;
  }

  handleWebRouteError(error, response, next);
}

function parseFiniteQueryNumber(value: unknown): number {
  if (typeof value !== "string") {
    throw new WebRouteInputError(
      "invalid_request",
      "Layout bounds must be finite numbers.",
    );
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new WebRouteInputError(
      "invalid_request",
      "Layout bounds must be finite numbers.",
    );
  }

  return parsed;
}

export function createTaxonomyViewRouter(
  options: CreateTaxonomyViewRouterOptions,
): Router {
  const router = Router();

  router.get(
    "/root",
    options.quotaMiddleware,
    async (_request, response, next) => {
      try {
        response.json(await options.internalApi.getTaxonomyRoot());
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  router.get(
    "/nodes/:nodeId",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const nodeId = parseNodeId(request.params.nodeId);
        response.json(await options.internalApi.getTaxonomyNode(nodeId));
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  router.get(
    "/path/*routePath",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const routePath = parseRoutePath(request.params.routePath);
        response.json(
          await options.internalApi.getTaxonomyNodeByPath(routePath),
        );
      } catch (error) {
        handleTaxonomyPathRouteError(error, response, next);
      }
    },
  );

  router.post(
    "/card-scopes/details",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const routePath = parseRoutePathBody(request.body);
        const nodeIds = parseNodeIdsBody(request.body);
        response.json(
          await options.internalApi.getTaxonomyCardScopeNodeDetails(
            routePath,
            nodeIds,
          ),
        );
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  router.get(
    "/card-scopes/layout",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const routePath = parseRoutePathQuery(request.query.route_path);
        response.json(
          await options.internalApi.getTaxonomyCardScopeLayoutSlice(routePath, {
            max_x: parseFiniteQueryNumber(request.query.max_x),
            max_y: parseFiniteQueryNumber(request.query.max_y),
            min_x: parseFiniteQueryNumber(request.query.min_x),
            min_y: parseFiniteQueryNumber(request.query.min_y),
          }),
        );
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  router.post(
    "/card-scopes/titles",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const routePath = parseRoutePathBody(request.body);
        const nodeIds = parseNodeIdsBody(request.body);
        response.json(
          await options.internalApi.getTaxonomyCardScopeNodeTitles(
            routePath,
            nodeIds,
          ),
        );
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  return router;
}
