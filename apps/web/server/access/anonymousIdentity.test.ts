// abstract: Unit tests for anonymous browser identity cookie handling.
// out_of_scope: Quota policy evaluation and Redis persistence.
// @vitest-environment node

import express from "express";
import request from "supertest";
import { describe, expect, it } from "vitest";

import { loadWebServerConfig } from "../config.js";
import { ensureAnonymousIdentity } from "./anonymousIdentity.js";

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

describe("ensureAnonymousIdentity", () => {
  it("sets an httpOnly anonymous identity cookie when the request has none", async () => {
    const app = express();
    const config = loadWebServerConfig(TEST_ENV);

    app.get("/test", (request, response) => {
      response.json({
        anonymousId: ensureAnonymousIdentity(request, response, config, {
          generateId: () => "anon-1",
        }),
      });
    });

    const response = await request(app).get("/test");

    expect(response.body).toEqual({ anonymousId: "anon-1" });
    expect(response.headers["set-cookie"]).toEqual([
      expect.stringContaining("knowledge.anonymous_id=anon-1;"),
    ]);
    expect(response.headers["set-cookie"][0]).toContain("HttpOnly");
    expect(response.headers["set-cookie"][0]).toContain("SameSite=Lax");
  });

  it("reuses an existing anonymous identity cookie without resetting it", async () => {
    const app = express();
    const config = loadWebServerConfig(TEST_ENV);

    app.get("/test", (request, response) => {
      response.json({
        anonymousId: ensureAnonymousIdentity(request, response, config, {
          generateId: () => "new-anon",
        }),
      });
    });

    const response = await request(app)
      .get("/test")
      .set("Cookie", "knowledge.anonymous_id=existing-anon");

    expect(response.body).toEqual({ anonymousId: "existing-anon" });
    expect(response.headers["set-cookie"]).toBeUndefined();
  });
});
