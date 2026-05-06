// abstract: Contract tests for the Express web BFF application shell.
// out_of_scope: Auth route behavior, quota enforcement, and backend API forwarding.
// @vitest-environment node

import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Router } from "express";
import request from "supertest";
import { afterEach, describe, expect, it } from "vitest";

import { createApp } from "./app.js";
import { loadWebServerConfig } from "./config.js";
import { createWebServerTestEnv } from "./testSupport/webServerEnv.js";

const TEST_ENV = createWebServerTestEnv();
const TEMP_DIRS: string[] = [];

async function createClientRootWithAsset(): Promise<string> {
  const clientRoot = await mkdtemp(join(tmpdir(), "knowledge-web-assets-"));
  TEMP_DIRS.push(clientRoot);
  await mkdir(join(clientRoot, "assets"));
  await writeFile(
    join(clientRoot, "assets", "SearchResultCard-DK5X5RqA.js"),
    "export const SearchResultCard = 'ok';",
  );
  return clientRoot;
}

afterEach(async () => {
  await Promise.all(
    TEMP_DIRS.splice(0).map(async (path) => {
      await rm(path, { force: true, recursive: true });
    }),
  );
});

describe("createApp", () => {
  it("returns JSON 404 for unmatched web API routes instead of the SPA fallback", async () => {
    const app = await createApp({
      config: loadWebServerConfig(TEST_ENV),
      runtime: {
        indexHtml: '<html><body><div id="root"></div></body></html>',
        kind: "production",
      },
    });

    const response = await request(app).get("/web-api/missing");

    expect(response.status).toBe(404);
    expect(response.type).toBe("application/json");
    expect(response.body).toEqual({
      error: {
        code: "web_api_route_not_found",
        message: "Web API route not found.",
      },
    });
  });

  it("rejects cross-origin web API mutations before feature handlers run", async () => {
    const config = loadWebServerConfig(TEST_ENV);
    const webApiRouter = Router();
    let handlerWasCalled = false;

    webApiRouter.post("/auth/sign-in", (_request, response) => {
      handlerWasCalled = true;
      response.status(204).send();
    });
    const app = await createApp({
      config,
      runtime: {
        indexHtml: '<html><body><div id="root"></div></body></html>',
        kind: "production",
      },
      webApiRouter,
    });

    const response = await request(app)
      .post("/web-api/auth/sign-in")
      .set("Origin", "https://evil.example")
      .type("form")
      .send({ return_to: "/dashboard" });

    expect(response.status).toBe(403);
    expect(response.body).toEqual({
      error: {
        code: "csrf_origin_rejected",
        message: "Request origin is not allowed.",
      },
    });
    expect(handlerWasCalled).toBe(false);
  });

  it("serves the client HTML fallback for non-API routes", async () => {
    const app = await createApp({
      config: loadWebServerConfig(TEST_ENV),
      runtime: {
        indexHtml:
          '<html><body><div id="root">Knowledge App</div></body></html>',
        kind: "production",
      },
    });

    const response = await request(app).get("/graph");

    expect(response.status).toBe(200);
    expect(response.type).toBe("text/html");
    expect(response.headers["cache-control"]).toBe("no-cache");
    expect(response.text).toContain("Knowledge App");
    expect(response.text).toContain(
      'window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp","searchMaxConnected":20,"searchMaxMatched":6}',
    );
  });

  it("serves existing hashed assets with immutable cache headers", async () => {
    const app = await createApp({
      config: loadWebServerConfig(TEST_ENV),
      runtime: {
        clientRoot: await createClientRootWithAsset(),
        indexHtml: '<html><body><div id="root"></div></body></html>',
        kind: "production",
      },
    });

    const response = await request(app).get(
      "/assets/SearchResultCard-DK5X5RqA.js",
    );

    expect(response.status).toBe(200);
    expect(response.type).toBe("text/javascript");
    expect(response.headers["cache-control"]).toBe(
      "public, max-age=31536000, immutable",
    );
    expect(response.text).toBe("export const SearchResultCard = 'ok';");
  });

  it("returns a non-cacheable 404 for missing hashed assets instead of the SPA fallback", async () => {
    const app = await createApp({
      config: loadWebServerConfig(TEST_ENV),
      runtime: {
        clientRoot: await createClientRootWithAsset(),
        indexHtml:
          '<html><body><div id="root">Knowledge App</div></body></html>',
        kind: "production",
      },
    });

    const response = await request(app).get(
      "/assets/SearchResultCard-BheaZfE9.js",
    );

    expect(response.status).toBe(404);
    expect(response.type).toBe("application/json");
    expect(response.headers["cache-control"]).toBe("no-store");
    expect(response.body).toEqual({
      error: {
        code: "static_asset_not_found",
        message: "Static asset not found.",
      },
    });
  });

  it("injects browser runtime config into development HTML fallbacks", async () => {
    const app = await createApp({
      config: loadWebServerConfig(TEST_ENV),
      runtime: {
        kind: "development",
        renderIndexHtml: async () =>
          '<html><body><div id="root">Knowledge Dev</div></body></html>',
        viteMiddlewares: (_request, _response, next) => {
          next();
        },
      },
    });

    const response = await request(app).get("/docs");

    expect(response.status).toBe(200);
    expect(response.text).toContain("Knowledge Dev");
    expect(response.text).toContain(
      'window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp","searchMaxConnected":20,"searchMaxMatched":6}',
    );
  });
});

describe("loadWebServerConfig", () => {
  it("does not require the old browser API proxy variables", () => {
    const config = loadWebServerConfig({
      ...TEST_ENV,
      API_PROXY_TARGET: "",
      VITE_API_BASE_URL: "",
    });

    expect(config.internalApiBaseUrl).toBe("http://api:8000");
  });

  it("keeps public and internal Logto endpoints separate", () => {
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://localhost:3011",
      KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: "http://logto:3001",
    });

    expect(config.logtoEndpoint).toBe("http://localhost:3011");
    expect(config.logtoInternalEndpoint).toBe("http://logto:3001");
  });
});
