// abstract: Behavior tests for shared browser runtime configuration rules.
// out_of_scope: React rendering behavior and Vite dev-server proxy wiring.

import { describe, expect, it } from "vitest";

import { resolveBrowserRuntimeConfig } from "./index";

describe("resolveBrowserRuntimeConfig", () => {
  it("loads the public MCP endpoint for browser code", () => {
    expect(
      resolveBrowserRuntimeConfig({
        mcpPublicBaseUrl: "http://localhost:8002/mcp",
        searchMaxConnected: 20,
        searchMaxMatched: 6,
      }),
    ).toEqual({
      mcpPublicBaseUrl: "http://localhost:8002/mcp",
      searchMaxConnected: 20,
      searchMaxMatched: 6,
    });
  });

  it("does not expose private or internal origins to browser code", () => {
    expect(
      resolveBrowserRuntimeConfig({
        KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL: "http://mcp:8080",
        PRIVATE_API_BASE_URL: "https://api.example.com/",
        mcpPublicBaseUrl: "http://localhost:8002/mcp",
        searchMaxConnected: 20,
        searchMaxMatched: 6,
      }),
    ).toEqual({
      mcpPublicBaseUrl: "http://localhost:8002/mcp",
      searchMaxConnected: 20,
      searchMaxMatched: 6,
    });
  });

  it("requires a public MCP endpoint", () => {
    expect(() => resolveBrowserRuntimeConfig({})).toThrow(
      "Missing browser runtime config: mcpPublicBaseUrl.",
    );
  });

  it("requires the public MCP endpoint to be a URL", () => {
    expect(() =>
      resolveBrowserRuntimeConfig({
        mcpPublicBaseUrl: "not a url",
      }),
    ).toThrow("Invalid browser runtime config: mcpPublicBaseUrl.");
  });

  it("requires positive integer search result limits", () => {
    expect(() =>
      resolveBrowserRuntimeConfig({
        mcpPublicBaseUrl: "http://localhost:8002/mcp",
        searchMaxConnected: 20,
      }),
    ).toThrow("Missing browser runtime config: searchMaxMatched.");

    expect(() =>
      resolveBrowserRuntimeConfig({
        mcpPublicBaseUrl: "http://localhost:8002/mcp",
        searchMaxConnected: 20,
        searchMaxMatched: 0,
      }),
    ).toThrow("Invalid browser runtime config: searchMaxMatched.");
  });
});
