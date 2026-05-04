// abstract: Browser-facing BFF routes for authenticated card proposals.
// out_of_scope: Frontend dialog rendering and FastAPI persistence behavior.

import { type Request, type Response, Router } from "express";
import type { WebSessionResponse } from "../auth/sessionState.js";
import type {
  CardProposalCreateRequest,
  CardProposalReviewRequest,
  InternalApiClient,
} from "../internal-api/client.js";
import {
  handleWebRouteError,
  WebRouteInputError,
} from "../internal-api/errors.js";

export type CardProposalsInternalApi = Pick<
  InternalApiClient,
  | "acceptCardProposal"
  | "createCardProposal"
  | "listMyCardProposals"
  | "listReviewQueue"
  | "rejectCardProposal"
  | "withdrawCardProposal"
>;

export type WebSessionResolver = (
  request: Request,
  response: Response,
) => Promise<WebSessionResponse>;

export interface CreateCardProposalsRouterOptions {
  readonly getSession: WebSessionResolver;
  readonly internalApi: CardProposalsInternalApi;
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

function readOptionalPositiveInteger(value: unknown, fieldName: string) {
  if (value === undefined || value === null) {
    return undefined;
  }
  return readPositiveInteger(value, fieldName);
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

function readOptionalNonEmptyString(value: unknown, fieldName: string) {
  if (value === undefined || value === null) {
    return undefined;
  }
  return readNonEmptyString(value, fieldName);
}

function readProposalType(
  value: unknown,
): CardProposalCreateRequest["proposal_type"] {
  if (value === "create" || value === "edit" || value === "delete") {
    return value;
  }
  throw new WebRouteInputError(
    "invalid_request",
    "proposal_type must be create, edit, or delete.",
  );
}

function readCreateProposalPayload(body: unknown): CardProposalCreateRequest {
  const source =
    typeof body === "object" && body !== null
      ? (body as Record<string, unknown>)
      : {};
  const proposalType = readProposalType(source.proposal_type);
  return {
    base_version: readOptionalPositiveInteger(
      source.base_version,
      "base_version",
    ),
    proposed_content: readOptionalNonEmptyString(
      source.proposed_content,
      "proposed_content",
    ),
    proposed_title: readOptionalNonEmptyString(
      source.proposed_title,
      "proposed_title",
    ),
    proposal_type: proposalType,
    reason: readNonEmptyString(source.reason, "reason"),
    suggested_content: readOptionalNonEmptyString(
      source.suggested_content,
      "suggested_content",
    ),
    suggested_title: readOptionalNonEmptyString(
      source.suggested_title,
      "suggested_title",
    ),
    target_node_id: readOptionalPositiveInteger(
      source.target_node_id,
      "target_node_id",
    ),
  };
}

function readReviewPayload(body: unknown): CardProposalReviewRequest {
  const source =
    typeof body === "object" && body !== null
      ? (body as Record<string, unknown>)
      : {};
  return {
    review_note: readOptionalNonEmptyString(source.review_note, "review_note"),
  };
}

async function requireAuthenticatedSession(
  options: CreateCardProposalsRouterOptions,
  request: Request,
  response: Response,
) {
  const session = await options.getSession(request, response);
  if (session.status !== "authenticated") {
    response.status(401).json({
      error: {
        code: "authentication_required",
        message: "Sign in to propose card changes.",
      },
    });
    return undefined;
  }

  return session;
}

export function createCardProposalsRouter(
  options: CreateCardProposalsRouterOptions,
): Router {
  const router = Router();

  router.post("/", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      const result = await options.internalApi.createCardProposal(
        readCreateProposalPayload(request.body),
        session.user.id,
      );
      response.status(201).json(result);
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  router.get("/my", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      response.json(
        await options.internalApi.listMyCardProposals(session.user.id),
      );
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  router.get("/review-queue", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      response.json(await options.internalApi.listReviewQueue(session.user.id));
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  router.post("/:proposalId/accept", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      const result = await options.internalApi.acceptCardProposal(
        readPositiveInteger(request.params.proposalId, "proposalId"),
        readReviewPayload(request.body),
        session.user.id,
      );
      response.json(result);
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  router.post("/:proposalId/reject", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      const result = await options.internalApi.rejectCardProposal(
        readPositiveInteger(request.params.proposalId, "proposalId"),
        readReviewPayload(request.body),
        session.user.id,
      );
      response.json(result);
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  router.post("/:proposalId/withdraw", async (request, response, next) => {
    try {
      const session = await requireAuthenticatedSession(
        options,
        request,
        response,
      );
      if (session === undefined) {
        return;
      }

      const result = await options.internalApi.withdrawCardProposal(
        readPositiveInteger(request.params.proposalId, "proposalId"),
        session.user.id,
      );
      response.json(result);
    } catch (error) {
      handleWebRouteError(error, response, next);
    }
  });

  return router;
}
