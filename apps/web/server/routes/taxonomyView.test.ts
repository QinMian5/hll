// abstract: Contract tests for web BFF taxonomy-view routes.
// out_of_scope: Taxonomy layout behavior and backend taxonomy service logic.
// @vitest-environment node

import { type RequestHandler, Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import type { TaxonomyViewInternalApi } from "./taxonomyView.js";
import { createTaxonomyViewRouter } from "./taxonomyView.js";

const TEST_ENV = {
  KNOWLEDGE_WEB_COOKIE_SECURE: "false",
  KNOWLEDGE_WEB_INTERNAL_API_BASE_URL: "http://api:8000",
  KNOWLEDGE_WEB_LOGTO_APP_ID: "test-app",
  KNOWLEDGE_WEB_LOGTO_APP_SECRET: "test-secret",
  KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://logto:3001",
  KNOWLEDGE_WEB_PUBLIC_BASE_URL: "http://localhost:5173",
  KNOWLEDGE_WEB_REDIS_URL: "redis://redis:6379/0",
  KNOWLEDGE_WEB_SESSION_SECRET: "test-session-secret-with-enough-length",
};

function createClient(overrides: Partial<TaxonomyViewInternalApi> = {}) {
  return {
    getTaxonomyLeafNodeDetails: vi.fn(async () => ({
      nodes: [{ content: "Card content", node_id: 10, title: "Card" }],
    })),
    getTaxonomyNode: vi.fn(async () => ({
      edges: [],
      node_id: 42,
      node_kind: "branch",
      nodes: [],
      title: "Physics",
    })),
    getTaxonomyRoot: vi.fn(async () => ({
      root_node_id: 1,
      title: "Science",
    })),
    ...overrides,
  };
}

async function createTestApp(options: {
  readonly client: TaxonomyViewInternalApi;
  readonly quotaMiddleware?: RequestHandler;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/taxonomy/view",
    createTaxonomyViewRouter({
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

describe("taxonomy view route", () => {
  it("calls the internal taxonomy root API", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get("/web-api/taxonomy/view/root");

    expect(response.status).toBe(200);
    expect(client.getTaxonomyRoot).toHaveBeenCalledWith();
    expect(response.body).toEqual({
      root_node_id: 1,
      title: "Science",
    });
  });

  it("calls the internal taxonomy node API with a numeric node id", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get("/web-api/taxonomy/view/nodes/42");

    expect(response.status).toBe(200);
    expect(client.getTaxonomyNode).toHaveBeenCalledWith(42);
    expect(response.body).toMatchObject({
      node_id: 42,
      title: "Physics",
    });
  });

  it("rejects invalid node ids before calling the internal API", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get(
      "/web-api/taxonomy/view/nodes/nope",
    );

    expect(response.status).toBe(400);
    expect(client.getTaxonomyNode).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "invalid_request",
        message: "Node id must be a positive integer.",
      },
    });
  });

  it("calls the internal taxonomy leaf detail API", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app)
      .post("/web-api/taxonomy/view/leaves/7/details")
      .send({ node_ids: [10, 11] });

    expect(response.status).toBe(200);
    expect(client.getTaxonomyLeafNodeDetails).toHaveBeenCalledWith(7, [10, 11]);
    expect(response.body).toEqual({
      nodes: [{ content: "Card content", node_id: 10, title: "Card" }],
    });
  });
});
