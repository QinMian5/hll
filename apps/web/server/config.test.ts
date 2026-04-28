// abstract: Contract tests for web BFF runtime configuration parsing.
// out_of_scope: Route behavior and external dependency request execution.
// @vitest-environment node

import { describe, expect, it } from "vitest";

import { loadWebServerConfig } from "./config.js";

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

describe("web server config", () => {
  it("loads dashboard token management dependency settings", () => {
    const config = loadWebServerConfig(TEST_ENV);

    expect(config.logtoManagementApiBaseUrl).toBe("http://logto:3001/api");
    expect(config.logtoManagementClientId).toBe("management-client");
    expect(config.logtoManagementClientSecret).toBe("management-secret");
    expect(config.logtoManagementResource).toBe(
      "https://default.logto.app/api",
    );
    expect(config.logtoManagementScopes).toBe(
      "read:users create:users update:users delete:users",
    );
    expect(config.logtoManagementTokenUrl).toBe("http://logto:3001/oidc/token");
    expect(config.mcpUsageSummaryBaseUrl).toBe("http://mcp:8001");
    expect(config.mcpUsageSummaryClientId).toBe("usage-client");
    expect(config.mcpUsageSummaryClientSecret).toBe("usage-secret");
    expect(config.mcpUsageSummaryResource).toBe(
      "https://knowledge-mcp.internal",
    );
    expect(config.mcpUsageSummaryScopes).toBe("usage:read");
    expect(config.mcpUsageSummaryTokenUrl).toBe("http://logto:3001/oidc/token");
    expect(config.patFingerprintSecret).toBe(
      "test-pat-fingerprint-secret-with-enough-length",
    );
  });

  it("requires a PAT fingerprint secret", () => {
    const { KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET, ...env } = TEST_ENV;

    expect(() => loadWebServerConfig(env)).toThrow();
    expect(KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET).toBeDefined();
  });
});
