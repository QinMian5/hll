// abstract: Contract tests for dashboard token lifecycle BFF routes.
// out_of_scope: Browser UI rendering and Logto Management API internals.
// @vitest-environment node

import { type RequestHandler, Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import type { WebSessionResponse } from "../auth/sessionState.js";
import { loadWebServerConfig } from "../config.js";
import { DashboardDependencyError } from "../dashboard/errors.js";
import { createPatFingerprint } from "../dashboard/patFingerprint.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import {
  createDashboardTokensRouter,
  type DashboardLogtoPersonalAccessTokensClient,
  type DashboardMcpUsageSummaryClient,
} from "./dashboardTokens.js";

const TEST_ENV = createWebServerTestEnv();

const TOKEN = {
  createdAt: "2026-04-28T10:00:00.000Z",
  expiresAt: "2026-05-28T10:00:00.000Z",
  name: "Laptop",
  value: "kg_pat_plaintext_value",
};

const USER_SESSION: WebSessionResponse = {
  status: "authenticated",
  user: { id: "user-1" },
};

function createLogtoClient(
  overrides: Partial<DashboardLogtoPersonalAccessTokensClient> = {},
): DashboardLogtoPersonalAccessTokensClient {
  return {
    createPersonalAccessToken: vi.fn(async () => TOKEN),
    deletePersonalAccessToken: vi.fn(async () => undefined),
    listPersonalAccessTokens: vi.fn(async () => [TOKEN]),
    renamePersonalAccessToken: vi.fn(async () => ({
      ...TOKEN,
      name: "Workstation",
    })),
    ...overrides,
  };
}

function createUsageClient(
  overrides: Partial<DashboardMcpUsageSummaryClient> = {},
): DashboardMcpUsageSummaryClient {
  return {
    getUsageSummaries: vi.fn(async () => new Map()),
    ...overrides,
  };
}

async function createTestApp(options: {
  readonly getSession?: () => Promise<WebSessionResponse>;
  readonly logtoClient?: DashboardLogtoPersonalAccessTokensClient;
  readonly mcpUsageClient?: DashboardMcpUsageSummaryClient;
  readonly quotaMiddleware?: RequestHandler;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/dashboard",
    createDashboardTokensRouter({
      getSession: async () =>
        options.getSession === undefined
          ? USER_SESSION
          : await options.getSession(),
      logtoClient: options.logtoClient ?? createLogtoClient(),
      mcpUsageClient: options.mcpUsageClient ?? createUsageClient(),
      patFingerprintSecret: config.patFingerprintSecret,
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

describe("dashboard token routes", () => {
  it("lists authenticated user tokens with raw values and successful search usage", async () => {
    const patFingerprint = createPatFingerprint(
      TOKEN.value,
      TEST_ENV.KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET,
    );
    const logtoClient = createLogtoClient();
    const mcpUsageClient = createUsageClient({
      getUsageSummaries: vi.fn(async () => {
        return new Map([
          [
            patFingerprint,
            {
              lastUsedAt: "2026-04-28T11:00:00.000Z",
              patFingerprint,
              successfulSearchCount: 12,
            },
          ],
        ]);
      }),
    });
    const app = await createTestApp({ logtoClient, mcpUsageClient });

    const response = await request(app).get("/web-api/dashboard/tokens");

    expect(response.status).toBe(200);
    expect(logtoClient.listPersonalAccessTokens).toHaveBeenCalledWith("user-1");
    expect(mcpUsageClient.getUsageSummaries).toHaveBeenCalledWith([
      patFingerprint,
    ]);
    expect(response.body).toEqual({
      tokens: [
        {
          createdAt: TOKEN.createdAt,
          expiresAt: TOKEN.expiresAt,
          lastUsedAt: "2026-04-28T11:00:00.000Z",
          maskedToken: "kg_pat_***********alue",
          name: TOKEN.name,
          successfulSearchCount: 12,
          tokenValue: TOKEN.value,
        },
      ],
      usageAvailable: true,
    });
    expect(response.text).not.toContain(patFingerprint);
  });

  it("rejects anonymous token access before calling Logto", async () => {
    const logtoClient = createLogtoClient();
    const app = await createTestApp({
      getSession: async () => ({ status: "anonymous" }),
      logtoClient,
    });

    const response = await request(app).get("/web-api/dashboard/tokens");

    expect(response.status).toBe(401);
    expect(logtoClient.listPersonalAccessTokens).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "authentication_required",
        message: "Authentication is required.",
      },
    });
  });

  it("creates a token for the authenticated Logto user", async () => {
    const logtoClient = createLogtoClient();
    const app = await createTestApp({ logtoClient });

    const response = await request(app)
      .post("/web-api/dashboard/tokens")
      .set("Origin", "http://localhost:5173")
      .send({ name: "Laptop" });

    expect(response.status).toBe(201);
    expect(logtoClient.createPersonalAccessToken).toHaveBeenCalledWith(
      "user-1",
      "Laptop",
    );
    expect(response.body).toMatchObject({
      token: {
        maskedToken: "kg_pat_***********alue",
        name: "Laptop",
        successfulSearchCount: 0,
        tokenValue: TOKEN.value,
      },
      usageAvailable: true,
    });
  });

  it("renames a token for the authenticated Logto user", async () => {
    const logtoClient = createLogtoClient();
    const app = await createTestApp({ logtoClient });

    const response = await request(app)
      .patch("/web-api/dashboard/tokens")
      .set("Origin", "http://localhost:5173")
      .send({ currentName: "Laptop", name: "Workstation" });

    expect(response.status).toBe(200);
    expect(logtoClient.renamePersonalAccessToken).toHaveBeenCalledWith(
      "user-1",
      "Laptop",
      "Workstation",
    );
    expect(response.body).toMatchObject({
      token: {
        maskedToken: "kg_pat_***********alue",
        name: "Workstation",
        tokenValue: TOKEN.value,
      },
    });
  });

  it("deletes a token for the authenticated Logto user", async () => {
    const logtoClient = createLogtoClient();
    const app = await createTestApp({ logtoClient });

    const response = await request(app)
      .post("/web-api/dashboard/tokens/delete")
      .set("Origin", "http://localhost:5173")
      .send({ name: "Laptop" });

    expect(response.status).toBe(204);
    expect(logtoClient.deletePersonalAccessToken).toHaveBeenCalledWith(
      "user-1",
      "Laptop",
    );
  });

  it("rejects blank token names before calling Logto", async () => {
    const logtoClient = createLogtoClient();
    const app = await createTestApp({ logtoClient });

    const response = await request(app)
      .post("/web-api/dashboard/tokens")
      .set("Origin", "http://localhost:5173")
      .send({ name: "   " });

    expect(response.status).toBe(400);
    expect(logtoClient.createPersonalAccessToken).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "dashboard_invalid_token_name",
        message: "Token name is required.",
      },
    });
  });

  it("keeps list available when usage summary is unavailable", async () => {
    const app = await createTestApp({
      mcpUsageClient: createUsageClient({
        getUsageSummaries: vi.fn(async () => {
          throw new DashboardDependencyError("usage unavailable");
        }),
      }),
    });

    const response = await request(app).get("/web-api/dashboard/tokens");

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      tokens: [
        {
          createdAt: TOKEN.createdAt,
          expiresAt: TOKEN.expiresAt,
          lastUsedAt: null,
          maskedToken: "kg_pat_***********alue",
          name: TOKEN.name,
          successfulSearchCount: null,
          tokenValue: TOKEN.value,
        },
      ],
      usageAvailable: false,
    });
  });
});
