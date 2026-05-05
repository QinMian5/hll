// abstract: Contract tests for dashboard quota BFF routes.
// out_of_scope: Browser UI rendering and MCP quota persistence.
// @vitest-environment node

import { type RequestHandler, Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import { DashboardDependencyError } from "../dashboard/errors.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import {
  createDashboardQuotaRouter,
  type DashboardMcpQuotaSummaryClient,
} from "./dashboardQuota.js";

const TEST_ENV = createWebServerTestEnv();

const USER_SESSION: WebSessionResponse = {
  status: "authenticated",
  user: { id: "user-1" },
};

const QUOTA_RESPONSE = {
  quota: {
    daily: {
      limit: 1000,
      remaining: 963,
      resetAt: "2026-04-29T10:00:00.000Z",
      startedAt: "2026-04-28T10:00:00.000Z",
      used: 37,
      windowSeconds: 86_400,
    },
    weekly: {
      limit: 5000,
      remaining: 4816,
      resetAt: "2026-05-05T10:00:00.000Z",
      startedAt: "2026-04-28T10:00:00.000Z",
      used: 184,
      windowSeconds: 604_800,
    },
  },
};

function createQuotaClient(
  overrides: Partial<DashboardMcpQuotaSummaryClient> = {},
): DashboardMcpQuotaSummaryClient {
  return {
    getQuotaSummary: vi.fn(async () => QUOTA_RESPONSE),
    ...overrides,
  };
}

async function createTestApp(options: {
  readonly getSession?: () => Promise<WebSessionResponse>;
  readonly mcpQuotaClient?: DashboardMcpQuotaSummaryClient;
  readonly quotaMiddleware?: RequestHandler;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/dashboard",
    createDashboardQuotaRouter({
      getSession: async () =>
        options.getSession === undefined
          ? USER_SESSION
          : await options.getSession(),
      mcpQuotaClient: options.mcpQuotaClient ?? createQuotaClient(),
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

describe("dashboard quota routes", () => {
  it("returns authenticated user account quota", async () => {
    const mcpQuotaClient = createQuotaClient();
    const app = await createTestApp({ mcpQuotaClient });

    const response = await request(app).get("/web-api/dashboard/quota");

    expect(response.status).toBe(200);
    expect(mcpQuotaClient.getQuotaSummary).toHaveBeenCalledWith("user-1");
    expect(response.body).toEqual({
      quota: QUOTA_RESPONSE.quota,
      quotaAvailable: true,
    });
  });

  it("rejects anonymous quota access before calling MCP", async () => {
    const mcpQuotaClient = createQuotaClient();
    const app = await createTestApp({
      getSession: async () => ({ status: "anonymous" }),
      mcpQuotaClient,
    });

    const response = await request(app).get("/web-api/dashboard/quota");

    expect(response.status).toBe(401);
    expect(mcpQuotaClient.getQuotaSummary).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "authentication_required",
        message: "Authentication is required.",
      },
    });
  });

  it("keeps the dashboard available when quota summary is unavailable", async () => {
    const app = await createTestApp({
      mcpQuotaClient: createQuotaClient({
        getQuotaSummary: vi.fn(async () => {
          throw new DashboardDependencyError("quota unavailable");
        }),
      }),
    });

    const response = await request(app).get("/web-api/dashboard/quota");

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      quota: null,
      quotaAvailable: false,
    });
  });
});
