// abstract: Contract tests for the Express web BFF application shell.
// out_of_scope: Auth route behavior, quota enforcement, and backend API forwarding.
// @vitest-environment node

import request from "supertest";
import { describe, expect, it } from "vitest";

import { createApp } from "./app.js";
import { loadWebServerConfig } from "./config.js";
import { createWebServerTestEnv } from "./testSupport/webServerEnv.js";

const TEST_ENV = createWebServerTestEnv();

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
    expect(response.text).toContain("Knowledge App");
    expect(response.text).toContain(
      'window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp"}',
    );
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
      'window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp"}',
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
