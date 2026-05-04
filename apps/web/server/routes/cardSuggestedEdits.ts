// abstract: Browser-facing BFF route for authenticated card suggested edits.
// out_of_scope: Review-workbench actions and frontend dialog rendering.

import { type Request, type Response, Router } from "express";
import type { WebSessionResponse } from "../auth/sessionState.js";
import type {
  InternalApiClient,
  SuggestedEditCreateRequest,
} from "../internal-api/client.js";
import {
  handleWebRouteError,
  WebRouteInputError,
} from "../internal-api/errors.js";

export type CardSuggestedEditsInternalApi = Pick<
  InternalApiClient,
  "createSuggestedEdit"
>;

export type WebSessionResolver = (
  request: Request,
  response: Response,
) => Promise<WebSessionResponse>;

export interface CreateCardSuggestedEditsRouterOptions {
  readonly getSession: WebSessionResolver;
  readonly internalApi: CardSuggestedEditsInternalApi;
}

function readPositiveInteger(value: unknown, fieldName: string): number {
  const parsed =
    typeof value === "number"
      ? value
      : typeof value === "string"
        ? Number(value)
        : Number.NaN;
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new WebRouteInputError(
      "invalid_request",
      `${fieldName} must be a positive integer.`,
    );
  }

  return parsed;
}

function readNonEmptyString(value: unknown, fieldName: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new WebRouteInputError(
      "invalid_request",
      `${fieldName} must be a non-empty string.`,
    );
  }

  return value.trim();
}

export function createCardSuggestedEditsRouter(
  options: CreateCardSuggestedEditsRouterOptions,
): Router {
  const router = Router();

  router.post("/:nodeId/suggested-edits", async (request, response, next) => {
    try {
      const session = await options.getSession(request, response);
      if (session.status !== "authenticated") {
        response.status(401).json({
          error: {
            code: "authentication_required",
            message: "Sign in to suggest edits.",
          },
        });
        return;
      }

      const nodeId = readPositiveInteger(request.params.nodeId, "nodeId");
      const payload: SuggestedEditCreateRequest = {
        base_version: readPositiveInteger(
          request.body?.base_version,
          "base_version",
        ),
        reason: readNonEmptyString(request.body?.reason, "reason"),
        suggested_content: readNonEmptyString(
          request.body?.suggested_content,
          "suggested_content",
        ),
        suggested_title: readNonEmptyString(
          request.body?.suggested_title,
          "suggested_title",
        ),
      };
      const result = await options.internalApi.createSuggestedEdit(
        nodeId,
        payload,
        session.user.id,
      );

      response.status(201).json(result);
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  return router;
}
