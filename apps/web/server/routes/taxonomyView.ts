// abstract: Explicit browser-facing BFF routes for taxonomy-view data.
// out_of_scope: Browser graph rendering and backend taxonomy service behavior.

import { type RequestHandler, Router } from "express";

import type { InternalApiClient } from "../internal-api/client.js";
import {
  handleWebRouteError,
  WebRouteInputError,
} from "../internal-api/errors.js";

export type TaxonomyViewInternalApi = Pick<
  InternalApiClient,
  | "getTaxonomyLeafNodeDetails"
  | "getTaxonomyLeafNodeTitles"
  | "getTaxonomyNode"
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

  router.post(
    "/leaves/:nodeId/details",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const nodeId = parseNodeId(request.params.nodeId);
        const nodeIds = parseNodeIdsBody(request.body);
        response.json(
          await options.internalApi.getTaxonomyLeafNodeDetails(nodeId, nodeIds),
        );
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  router.post(
    "/leaves/:nodeId/titles",
    options.quotaMiddleware,
    async (request, response, next) => {
      try {
        const nodeId = parseNodeId(request.params.nodeId);
        const nodeIds = parseNodeIdsBody(request.body);
        response.json(
          await options.internalApi.getTaxonomyLeafNodeTitles(nodeId, nodeIds),
        );
      } catch (error) {
        handleWebRouteError(error, response, next);
      }
    },
  );

  return router;
}
