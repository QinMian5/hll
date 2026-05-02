// abstract: Contract tests for web BFF taxonomy-view routes.
// out_of_scope: Taxonomy layout behavior and backend taxonomy service logic.
// @vitest-environment node

import { type RequestHandler, Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import { InternalApiError } from "../internal-api/errors.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import type { TaxonomyViewInternalApi } from "./taxonomyView.js";
import { createTaxonomyViewRouter } from "./taxonomyView.js";

const TEST_ENV = createWebServerTestEnv();

function createClient(overrides: Partial<TaxonomyViewInternalApi> = {}) {
  return {
    getTaxonomyLeafLayoutSlice: vi.fn(async () => ({
      edges: [[10, 11, 0.8]],
      layout_version: "taxonomy-leaf-layout-v3",
      leaf_id: 7,
      nodes: [
        { id: 10, scope: "inner", x: 1.5, y: 2.5 },
        { id: 11, scope: "outer", x: 3.5, y: 4.5 },
      ],
      requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
    })),
    getTaxonomyLeafNodeDetails: vi.fn(async () => ({
      nodes: [
        { content: "Card content", current_version: 4, id: 10, title: "Card" },
      ],
    })),
    getTaxonomyLeafNodeTitles: vi.fn(async () => ({
      nodes: [{ id: 10, title: "Card" }],
    })),
    getTaxonomyNode: vi.fn(async () => ({
      edges: [],
      node_id: 42,
      node_kind: "branch",
      nodes: [],
      title: "Physics",
    })),
    getTaxonomyNodeByPath: vi.fn(async () => ({
      current_node: {
        depth: 2,
        id: 42,
        is_leaf: false,
        name: "Algebra",
        parent_id: 7,
        route_path: "science/mathematics/algebra",
        route_slug: "algebra",
      },
      breadcrumb: [],
      children: [],
      node_kind: "branch",
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

  it("calls the internal taxonomy path API with a nested route path", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get(
      "/web-api/taxonomy/view/path/science/mathematics/algebra",
    );

    expect(response.status).toBe(200);
    expect(client.getTaxonomyNodeByPath).toHaveBeenCalledWith(
      "science/mathematics/algebra",
    );
    expect(response.body.current_node).toMatchObject({
      id: 42,
      route_path: "science/mathematics/algebra",
    });
  });

  it("preserves taxonomy layout readiness errors from the internal API", async () => {
    const readinessError = new InternalApiError(503, "layout not ready", {
      clientMessage: "Taxonomy leaf layout is being prepared.",
      code: "layout_not_ready",
      retryAfterSeconds: 10,
    });
    const client = createClient({
      getTaxonomyLeafLayoutSlice: vi.fn(async () => {
        throw readinessError;
      }),
      getTaxonomyNodeByPath: vi.fn(async () => {
        throw readinessError;
      }),
    });
    const app = await createTestApp({ client });

    const pathResponse = await request(app).get(
      "/web-api/taxonomy/view/path/science/mathematics",
    );
    const layoutResponse = await request(app).get(
      "/web-api/taxonomy/view/leaves/7/layout?min_x=-100&min_y=-200&max_x=100&max_y=200",
    );

    for (const response of [pathResponse, layoutResponse]) {
      expect(response.status).toBe(503);
      expect(response.headers["retry-after"]).toBe("10");
      expect(response.body).toEqual({
        error: {
          code: "layout_not_ready",
          message: "Taxonomy leaf layout is being prepared.",
        },
      });
    }
  });

  it("preserves unresolved taxonomy path errors from the internal API", async () => {
    const client = createClient({
      getTaxonomyNodeByPath: vi.fn(async () => {
        throw new InternalApiError(404, "not found");
      }),
    });
    const app = await createTestApp({ client });

    const response = await request(app).get(
      "/web-api/taxonomy/view/path/science/missing",
    );

    expect(response.status).toBe(404);
    expect(client.getTaxonomyRoot).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "taxonomy_route_path_not_found",
        message: "Taxonomy route path was not found.",
      },
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
      nodes: [
        { content: "Card content", current_version: 4, id: 10, title: "Card" },
      ],
    });
  });

  it("calls the internal taxonomy leaf layout API with viewport bounds", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get(
      "/web-api/taxonomy/view/leaves/7/layout?min_x=-100&min_y=-200&max_x=100&max_y=200",
    );

    expect(response.status).toBe(200);
    expect(client.getTaxonomyLeafLayoutSlice).toHaveBeenCalledWith(7, {
      max_x: 100,
      max_y: 200,
      min_x: -100,
      min_y: -200,
    });
    expect(response.body).toEqual({
      edges: [[10, 11, 0.8]],
      layout_version: "taxonomy-leaf-layout-v3",
      leaf_id: 7,
      nodes: [
        { id: 10, scope: "inner", x: 1.5, y: 2.5 },
        { id: 11, scope: "outer", x: 3.5, y: 4.5 },
      ],
      requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
    });
  });

  it("rejects invalid leaf layout bounds before calling the internal API", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app).get(
      "/web-api/taxonomy/view/leaves/7/layout?min_x=-100&min_y=-200&max_x=nope&max_y=200",
    );

    expect(response.status).toBe(400);
    expect(client.getTaxonomyLeafLayoutSlice).not.toHaveBeenCalled();
    expect(response.body).toEqual({
      error: {
        code: "invalid_request",
        message: "Layout bounds must be finite numbers.",
      },
    });
  });

  it("calls the internal taxonomy leaf title API", async () => {
    const client = createClient();
    const app = await createTestApp({ client });

    const response = await request(app)
      .post("/web-api/taxonomy/view/leaves/7/titles")
      .send({ node_ids: [10, 11] });

    expect(response.status).toBe(200);
    expect(client.getTaxonomyLeafNodeTitles).toHaveBeenCalledWith(7, [10, 11]);
    expect(response.body).toEqual({
      nodes: [{ id: 10, title: "Card" }],
    });
  });
});
