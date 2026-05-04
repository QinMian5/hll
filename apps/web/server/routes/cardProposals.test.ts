// abstract: Contract tests for authenticated card proposal BFF routes.
// out_of_scope: Browser dialog rendering and FastAPI persistence behavior.
// @vitest-environment node

import { Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import type { CardProposalsInternalApi } from "./cardProposals.js";
import { createCardProposalsRouter } from "./cardProposals.js";

const TEST_ENV = createWebServerTestEnv();

async function createTestApp(options: {
  readonly client: CardProposalsInternalApi;
  readonly session: WebSessionResponse;
}) {
  const webApiRouter = Router();
  webApiRouter.use(
    "/card-proposals",
    createCardProposalsRouter({
      getSession: async () => options.session,
      internalApi: options.client,
    }),
  );

  return await createApp({
    config: loadWebServerConfig(TEST_ENV),
    runtime: {
      indexHtml: '<html><body><div id="root"></div></body></html>',
      kind: "production",
    },
    webApiRouter,
  });
}

describe("card proposal routes", () => {
  it("forwards authenticated create/edit/delete submissions with BFF-derived identity", async () => {
    const createCardProposal = vi.fn(async () => ({
      created_at: "2026-04-28T18:00:00Z",
      id: 199,
      payload: {
        base_version: 3,
        suggested_content: "Better content",
        suggested_title: "Better title",
        target_node_id: 10,
      },
      proposal_type: "edit" as const,
      reason: "This improves the card explanation.",
      reviewed_at: null,
      reviewed_by_user_id: null,
      review_note: null,
      status: "pending_review" as const,
      submitted_by_user_id: "logto-user-123",
      updated_at: "2026-04-28T18:00:00Z",
    }));
    const app = await createTestApp({
      client: {
        acceptCardProposal: vi.fn(),
        createCardProposal,
        listMyCardProposals: vi.fn(),
        listReviewQueue: vi.fn(),
        rejectCardProposal: vi.fn(),
        withdrawCardProposal: vi.fn(),
      },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    const response = await request(app).post("/web-api/card-proposals").send({
      base_version: 3,
      proposal_type: "edit",
      reason: "This improves the card explanation.",
      suggested_by_user_id: "browser-controlled",
      suggested_content: "Better content",
      suggested_title: "Better title",
      target_node_id: 10,
    });

    expect(response.status).toBe(201);
    expect(response.body.status).toBe("pending_review");
    expect(createCardProposal).toHaveBeenCalledWith(
      {
        base_version: 3,
        proposal_type: "edit",
        reason: "This improves the card explanation.",
        suggested_content: "Better content",
        suggested_title: "Better title",
        target_node_id: 10,
      },
      "logto-user-123",
    );
  });

  it("rejects authenticated proposal submissions without a reason", async () => {
    const createCardProposal = vi.fn();
    const app = await createTestApp({
      client: {
        acceptCardProposal: vi.fn(),
        createCardProposal,
        listMyCardProposals: vi.fn(),
        listReviewQueue: vi.fn(),
        rejectCardProposal: vi.fn(),
        withdrawCardProposal: vi.fn(),
      },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    const response = await request(app).post("/web-api/card-proposals").send({
      base_version: 3,
      proposal_type: "edit",
      suggested_content: "Better content",
      suggested_title: "Better title",
      target_node_id: 10,
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toMatchObject({
      code: "invalid_request",
      message: "reason must be a non-empty string.",
    });
    expect(createCardProposal).not.toHaveBeenCalled();
  });

  it("rejects anonymous proposal submission before calling the internal API", async () => {
    const createCardProposal = vi.fn();
    const app = await createTestApp({
      client: {
        acceptCardProposal: vi.fn(),
        createCardProposal,
        listMyCardProposals: vi.fn(),
        listReviewQueue: vi.fn(),
        rejectCardProposal: vi.fn(),
        withdrawCardProposal: vi.fn(),
      },
      session: { status: "anonymous" },
    });

    const response = await request(app).post("/web-api/card-proposals").send({
      proposed_content: "New card content",
      proposed_title: "New card",
      proposal_type: "create",
    });

    expect(response.status).toBe(401);
    expect(response.body).toEqual({
      error: {
        code: "authentication_required",
        message: "Sign in to propose card changes.",
      },
    });
    expect(createCardProposal).not.toHaveBeenCalled();
  });

  it("forwards reviewer accept actions with the authenticated reviewer identity", async () => {
    const acceptCardProposal = vi.fn(async () => ({
      created_at: "2026-04-28T18:00:00Z",
      id: 199,
      payload: { target_node_id: 10 },
      proposal_type: "delete" as const,
      reason: "Duplicate card.",
      reviewed_at: "2026-04-28T19:00:00Z",
      reviewed_by_user_id: "reviewer-user",
      review_note: "Archive duplicate.",
      status: "accepted_applied" as const,
      submitted_by_user_id: "contributor",
      updated_at: "2026-04-28T18:00:00Z",
    }));
    const app = await createTestApp({
      client: {
        acceptCardProposal,
        createCardProposal: vi.fn(),
        listMyCardProposals: vi.fn(),
        listReviewQueue: vi.fn(),
        rejectCardProposal: vi.fn(),
        withdrawCardProposal: vi.fn(),
      },
      session: {
        status: "authenticated",
        user: { id: "reviewer-user" },
      },
    });

    const response = await request(app)
      .post("/web-api/card-proposals/199/accept")
      .send({ review_note: "Archive duplicate." });

    expect(response.status).toBe(200);
    expect(response.body.status).toBe("accepted_applied");
    expect(acceptCardProposal).toHaveBeenCalledWith(
      199,
      { review_note: "Archive duplicate." },
      "reviewer-user",
    );
  });
});
