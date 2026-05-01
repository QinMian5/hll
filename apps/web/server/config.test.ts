// abstract: Contract tests for web BFF runtime configuration parsing.
// out_of_scope: Route behavior and external dependency request execution.
// @vitest-environment node

import { describe, expect, it } from "vitest";

import { loadWebServerConfig } from "./config.js";
import { createWebServerTestEnv } from "./testSupport/webServerEnv.js";

const TEST_ENV = createWebServerTestEnv();

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

  it("loads taxonomy view quota overrides from first-class env variables", () => {
    const config = loadWebServerConfig(TEST_ENV);

    expect(config.quotaRouteOverrides).toEqual({
      "taxonomy-view": {
        anonymous: {
          burst: { limit: 60, windowSeconds: 60 },
          total: { limit: 600, windowSeconds: 86400 },
        },
        authenticated: {
          burst: { limit: 240, windowSeconds: 60 },
          total: { limit: 5000, windowSeconds: 86400 },
        },
        ip: {
          burst: { limit: 600, windowSeconds: 60 },
          total: { limit: 15000, windowSeconds: 86400 },
        },
      },
    });
  });

  it("requires explicit web quota env values instead of code defaults", () => {
    const { KNOWLEDGE_WEB_ANON_BURST_LIMIT, ...env } = TEST_ENV;

    expect(() => loadWebServerConfig(env)).toThrow();
    expect(KNOWLEDGE_WEB_ANON_BURST_LIMIT).toBeDefined();
  });
});
