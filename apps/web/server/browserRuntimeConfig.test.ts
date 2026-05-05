// abstract: Tests for browser-facing runtime configuration serialization.
// out_of_scope: Browser feature rendering and server route assembly.
// @vitest-environment node

import { describe, expect, it } from "vitest";

import {
  createBrowserRuntimeConfig,
  injectBrowserRuntimeConfig,
  serializeBrowserRuntimeConfig,
} from "./browserRuntimeConfig.js";
import { loadWebServerConfig } from "./config.js";
import { createWebServerTestEnv } from "./testSupport/webServerEnv.js";

const TEST_CONFIG = loadWebServerConfig(
  createWebServerTestEnv({
    KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL: "http://localhost:8002/mcp",
  }),
);

describe("browser runtime config", () => {
  it("serializes browser-safe runtime configuration", () => {
    expect(createBrowserRuntimeConfig(TEST_CONFIG)).toEqual({
      mcpPublicBaseUrl: "http://localhost:8002/mcp",
      searchMaxConnected: 20,
      searchMaxMatched: 6,
    });
  });

  it("escapes HTML-breaking characters in serialized config", () => {
    const script = serializeBrowserRuntimeConfig({
      mcpPublicBaseUrl: "https://knowledge.example/mcp?<script>",
      searchMaxConnected: 20,
      searchMaxMatched: 6,
    });

    expect(script).not.toContain("mcp?<script>");
    expect(script).toContain("\\u003cscript>");
  });

  it("injects the runtime config before the head closes", () => {
    const html = "<html><head><title>Knowledge</title></head><body></body>";

    expect(injectBrowserRuntimeConfig(html, TEST_CONFIG)).toBe(
      '<html><head><title>Knowledge</title><script>window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp","searchMaxConnected":20,"searchMaxMatched":6};</script></head><body></body>',
    );
  });

  it("appends the runtime config when the document has no head close", () => {
    const html = '<html><body><div id="root"></div></body></html>';

    expect(injectBrowserRuntimeConfig(html, TEST_CONFIG)).toBe(
      '<html><body><div id="root"></div></body></html><script>window.__KNOWLEDGE_RUNTIME_CONFIG__={"mcpPublicBaseUrl":"http://localhost:8002/mcp","searchMaxConnected":20,"searchMaxMatched":6};</script>',
    );
  });
});
