// abstract: Contract tests for BFF quota middleware behavior.
// out_of_scope: Redis command implementation and feature route forwarding.
// @vitest-environment node

import { Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import { createQuotaMiddleware } from "./quotaMiddleware.js";
import type {
  QuotaConsumption,
  QuotaConsumptionResult,
  QuotaStore,
} from "./quotaStore.js";

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

class RecordingQuotaStore implements QuotaStore {
  readonly consumptions: QuotaConsumption[] = [];

  constructor(
    private readonly result: QuotaConsumptionResult = {
      allowed: true,
      remaining: 99,
      retryAfterSeconds: 0,
    },
  ) {}

  readonly consume = vi.fn(async (consumption: QuotaConsumption) => {
    this.consumptions.push(consumption);
    return this.result;
  });
}

async function createLimitedApp(options: {
  readonly getSession: () => Promise<WebSessionResponse>;
  readonly routeGroup?: string;
  readonly store: QuotaStore;
}) {
  const config = loadWebServerConfig({
    ...TEST_ENV,
    KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON:
      '{"search":{"anonymous":{"burst":{"limit":2}}}}',
  });
  const webApiRouter = Router();

  webApiRouter.get(
    "/limited",
    createQuotaMiddleware({
      anonymousIdentity: {
        generateId: () => "anon-1",
      },
      config,
      getSession: options.getSession,
      routeGroup: options.routeGroup ?? "taxonomy",
      store: options.store,
    }),
    (_request, response) => {
      response.json({ ok: true });
    },
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

describe("createQuotaMiddleware", () => {
  it("sets anonymous identity and consumes principal and IP quota with cost one", async () => {
    const store = new RecordingQuotaStore();
    const app = await createLimitedApp({
      getSession: async () => ({ status: "anonymous" }),
      store,
    });

    const response = await request(app).get("/web-api/limited");

    expect(response.status).toBe(200);
    expect(response.headers["set-cookie"][0]).toContain(
      "knowledge.anonymous_id=anon-1;",
    );
    expect(store.consumptions).toHaveLength(4);
    expect(
      store.consumptions.every((consumption) => consumption.cost === 1),
    ).toBe(true);
    expect(store.consumptions.map((consumption) => consumption.scope)).toEqual([
      "principal",
      "principal",
      "ip",
      "ip",
    ]);
    expect(store.consumptions[0]?.key).toContain("anonymous:");
  });

  it("uses authenticated user principal while still consuming IP quota", async () => {
    const store = new RecordingQuotaStore();
    const app = await createLimitedApp({
      getSession: async () => ({
        status: "authenticated",
        user: { id: "user-1" },
      }),
      store,
    });

    const response = await request(app).get("/web-api/limited");

    expect(response.status).toBe(200);
    expect(response.headers["set-cookie"]).toBeUndefined();
    expect(store.consumptions).toHaveLength(4);
    expect(store.consumptions[0]?.key).toContain("user:");
    expect(
      store.consumptions.some((consumption) => consumption.scope === "ip"),
    ).toBe(true);
  });

  it("returns 429 with Retry-After when a quota check is exceeded", async () => {
    const store = new RecordingQuotaStore({
      allowed: false,
      remaining: 0,
      retryAfterSeconds: 17,
    });
    const app = await createLimitedApp({
      getSession: async () => ({ status: "anonymous" }),
      store,
    });

    const response = await request(app).get("/web-api/limited");

    expect(response.status).toBe(429);
    expect(response.headers["retry-after"]).toBe("17");
    expect(response.body).toEqual({
      error: {
        code: "quota_exceeded",
        message: "Rate limit exceeded.",
      },
    });
  });

  it("applies route-level quota overrides", async () => {
    const store = new RecordingQuotaStore();
    const app = await createLimitedApp({
      getSession: async () => ({ status: "anonymous" }),
      routeGroup: "search",
      store,
    });

    const response = await request(app).get("/web-api/limited");

    expect(response.status).toBe(200);
    expect(store.consumptions[0]).toMatchObject({
      limit: 2,
      routeGroup: "search",
      windowName: "burst",
    });
  });
});
