// abstract: Contract tests for authenticated card suggested-edit BFF route.
// out_of_scope: Browser dialog rendering and FastAPI persistence behavior.
// @vitest-environment node

import { Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import { InternalApiError } from "../internal-api/errors.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import type { CardSuggestedEditsInternalApi } from "./cardSuggestedEdits.js";
import { createCardSuggestedEditsRouter } from "./cardSuggestedEdits.js";

const TEST_ENV = createWebServerTestEnv({
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES:
    "read:users create:verification_records",
});

async function createTestApp(options: {
  readonly client: CardSuggestedEditsInternalApi;
  readonly session: WebSessionResponse;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/cards",
    createCardSuggestedEditsRouter({
      getSession: async () => options.session,
      internalApi: options.client,
    }),
  );

  return await createApp({
    config,
    runtime: {
      indexHtml: '<html><body><div id="root"></div></body></html>',
      kind: "production",
    },
    webApiRouter,
  });
}

describe("card suggested edit route", () => {
  it("forwards authenticated suggestions with BFF-derived user identity", async () => {
    const createSuggestedEdit = vi.fn(async () => ({
      base_version: 1,
      created_at: "2026-04-28T18:00:00Z",
      id: 99,
      node_id: 1,
      status: "pending" as const,
    }));
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    const response = await request(app)
      .post("/web-api/cards/1/suggested-edits")
      .set("Origin", "http://localhost:5173")
      .send({
        base_version: 1,
        reason: "The current card needs clearer wording.",
        suggested_content: "Better content",
        suggested_title: "Better title",
      });

    expect(response.status).toBe(201);
    expect(response.body).toEqual({
      base_version: 1,
      created_at: "2026-04-28T18:00:00Z",
      id: 99,
      node_id: 1,
      status: "pending",
    });
    expect(createSuggestedEdit).toHaveBeenCalledWith(
      1,
      {
        base_version: 1,
        reason: "The current card needs clearer wording.",
        suggested_content: "Better content",
        suggested_title: "Better title",
      },
      "logto-user-123",
    );
  });

  it("rejects authenticated suggestions without a reason", async () => {
    const createSuggestedEdit = vi.fn();
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    const response = await request(app)
      .post("/web-api/cards/1/suggested-edits")
      .set("Origin", "http://localhost:5173")
      .send({
        base_version: 1,
        suggested_content: "Better content",
        suggested_title: "Better title",
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toMatchObject({
      code: "invalid_request",
      message: "reason must be a non-empty string.",
    });
    expect(createSuggestedEdit).not.toHaveBeenCalled();
  });

  it("rejects anonymous suggestions before calling the internal API", async () => {
    const createSuggestedEdit = vi.fn();
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: { status: "anonymous" },
    });

    const response = await request(app)
      .post("/web-api/cards/1/suggested-edits")
      .set("Origin", "http://localhost:5173")
      .send({
        base_version: 1,
        suggested_content: "Better content",
        suggested_title: "Better title",
      });

    expect(response.status).toBe(401);
    expect(response.body).toEqual({
      error: {
        code: "authentication_required",
        message: "Sign in to suggest edits.",
      },
    });
    expect(createSuggestedEdit).not.toHaveBeenCalled();
  });

  it("ignores browser-supplied suggested_by_user_id", async () => {
    const createSuggestedEdit = vi.fn(async () => ({
      base_version: 1,
      created_at: "2026-04-28T18:00:00Z",
      id: 99,
      node_id: 1,
      status: "pending" as const,
    }));
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    await request(app)
      .post("/web-api/cards/1/suggested-edits")
      .set("Origin", "http://localhost:5173")
      .send({
        base_version: 1,
        reason: "The current card needs clearer wording.",
        suggested_by_user_id: "browser-controlled-user",
        suggested_content: "Better content",
        suggested_title: "Better title",
      });

    expect(createSuggestedEdit).toHaveBeenCalledWith(
      1,
      {
        base_version: 1,
        reason: "The current card needs clearer wording.",
        suggested_content: "Better content",
        suggested_title: "Better title",
      },
      "logto-user-123",
    );
  });

  it("preserves safe internal API suggestion errors for the browser", async () => {
    const createSuggestedEdit = vi.fn(async () => {
      throw new InternalApiError(422, "internal API rejected suggestion", {
        clientMessage: "Suggested edit must change the card title or content.",
        code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
      });
    });
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: {
        status: "authenticated",
        user: { id: "logto-user-123" },
      },
    });

    const response = await request(app)
      .post("/web-api/cards/1/suggested-edits")
      .set("Origin", "http://localhost:5173")
      .send({
        base_version: 1,
        reason: "The current card needs clearer wording.",
        suggested_content: "Same content",
        suggested_title: "Same title",
      });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({
      error: {
        code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
        message: "Suggested edit must change the card title or content.",
      },
    });
  });
});
