// abstract: Contract tests for authenticated card suggested-edit BFF route.
// out_of_scope: Browser dialog rendering and FastAPI persistence behavior.
// @vitest-environment node

import { Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";
import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import type { CardSuggestedEditsInternalApi } from "./cardSuggestedEdits.js";
import { createCardSuggestedEditsRouter } from "./cardSuggestedEdits.js";

const TEST_ENV = {
  KNOWLEDGE_WEB_COOKIE_SECURE: "false",
  KNOWLEDGE_WEB_INTERNAL_API_BASE_URL: "http://api:8000",
  KNOWLEDGE_WEB_LOGTO_APP_ID: "test-app",
  KNOWLEDGE_WEB_LOGTO_APP_SECRET: "test-secret",
  KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://logto:3001",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_API_BASE_URL: "http://logto:3001/api",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_ID: "management-client",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_SECRET: "management-secret",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_RESOURCE: "https://default.logto.app/api",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES:
    "read:users create:verification_records",
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_TOKEN_URL: "http://logto:3001/oidc/token",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL: "http://mcp:8001",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_ID: "usage-client",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_SECRET: "usage-secret",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_RESOURCE: "https://knowledge-mcp.internal",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_SCOPES: "usage:read",
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_TOKEN_URL: "http://logto:3001/oidc/token",
  KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET:
    "test-pat-fingerprint-secret-with-enough-length",
  KNOWLEDGE_WEB_PUBLIC_BASE_URL: "http://localhost:5173",
  KNOWLEDGE_WEB_REDIS_URL: "redis://redis:6379/0",
  KNOWLEDGE_WEB_SESSION_SECRET: "test-session-secret-with-enough-length",
};

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
      .send({
        base_version: 1,
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
        suggested_content: "Better content",
        suggested_title: "Better title",
      },
      "logto-user-123",
    );
  });

  it("rejects anonymous suggestions before calling the internal API", async () => {
    const createSuggestedEdit = vi.fn();
    const app = await createTestApp({
      client: { createSuggestedEdit },
      session: { status: "anonymous" },
    });

    const response = await request(app)
      .post("/web-api/cards/1/suggested-edits")
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

    await request(app).post("/web-api/cards/1/suggested-edits").send({
      base_version: 1,
      suggested_by_user_id: "browser-controlled-user",
      suggested_content: "Better content",
      suggested_title: "Better title",
    });

    expect(createSuggestedEdit).toHaveBeenCalledWith(
      1,
      {
        base_version: 1,
        suggested_content: "Better content",
        suggested_title: "Better title",
      },
      "logto-user-123",
    );
  });
});
