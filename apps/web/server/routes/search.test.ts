// abstract: Contract tests for the web BFF search route.
// out_of_scope: Backend search ranking and browser query adapters.
// @vitest-environment node

import { type RequestHandler, Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import { InternalApiError } from "../internal-api/errors.js";
import type { SearchInternalApi } from "./search.js";
import { createSearchRouter } from "./search.js";

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
    "read:users create:users update:users delete:users",
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
  readonly client: SearchInternalApi;
  readonly quotaMiddleware?: RequestHandler;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/search",
    createSearchRouter({
      internalApi: options.client,
      quotaMiddleware:
        options.quotaMiddleware ??
        ((_request, _response, next) => {
          next();
        }),
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

describe("search route", () => {
  it("calls the internal search API through the explicit web route", async () => {
    const search = vi.fn(async () => ({
      connected_titles: ["Physics"],
      matched_cards: [{ content: "Energy content", title: "Energy" }],
    }));
    const app = await createTestApp({
      client: { search },
    });

    const response = await request(app).get("/web-api/search?query=energy");

    expect(response.status).toBe(200);
    expect(search).toHaveBeenCalledWith("energy");
    expect(response.body).toEqual({
      connected_titles: ["Physics"],
      matched_cards: [{ content: "Energy content", title: "Energy" }],
    });
  });

  it("rejects missing query before calling the internal API", async () => {
    const search = vi.fn();
    const app = await createTestApp({
      client: { search },
    });

    const response = await request(app).get("/web-api/search");

    expect(response.status).toBe(400);
    expect(search).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "invalid_request",
        message: "Search query is required.",
      },
    });
  });

  it("maps internal API failures to safe browser errors", async () => {
    const app = await createTestApp({
      client: {
        search: vi.fn(async () => {
          throw new InternalApiError(503, "backend unavailable");
        }),
      },
    });

    const response = await request(app).get("/web-api/search?query=energy");

    expect(response.status).toBe(503);
    expect(response.body).toEqual({
      error: {
        code: "internal_api_request_failed",
        message: "Internal API request failed.",
      },
    });
    expect(response.text).not.toContain("backend unavailable");
  });
});
