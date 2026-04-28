// abstract: Contract tests for OAuth client-credentials service token requests.
// out_of_scope: Token caching and Logto authorization policy.
// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  type DashboardDependencyError,
  requestServiceAccessToken,
} from "./serviceAccessToken.js";

const TOKEN_CONFIG = {
  clientId: "service-client",
  clientSecret: "service-secret",
  resource: "https://knowledge-mcp.internal",
  scopes: "usage:read",
  tokenUrl: "https://logto.example/oidc/token",
};

describe("service access token requests", () => {
  it("requests a client-credentials token with resource and scope", async () => {
    const fetchToken = vi.fn(async () => {
      return new Response(JSON.stringify({ access_token: "service-token" }), {
        headers: { "content-type": "application/json" },
        status: 200,
      });
    });

    const token = await requestServiceAccessToken(TOKEN_CONFIG, fetchToken);

    expect(token).toBe("service-token");
    expect(fetchToken).toHaveBeenCalledTimes(1);
    const [url, init] = fetchToken.mock.calls[0] ?? [];
    expect(url).toBe("https://logto.example/oidc/token");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toEqual({
      "content-type": "application/x-www-form-urlencoded",
    });
    const body = new URLSearchParams(String(init?.body));
    expect(body.get("grant_type")).toBe("client_credentials");
    expect(body.get("client_id")).toBe("service-client");
    expect(body.get("client_secret")).toBe("service-secret");
    expect(body.get("resource")).toBe("https://knowledge-mcp.internal");
    expect(body.get("scope")).toBe("usage:read");
  });

  it("maps token endpoint failures to a safe dependency error", async () => {
    const fetchToken = vi.fn(async () => {
      return new Response("forbidden", { status: 403 });
    });

    await expect(
      requestServiceAccessToken(TOKEN_CONFIG, fetchToken),
    ).rejects.toMatchObject({
      code: "dashboard_dependency_unavailable",
      name: "DashboardDependencyError",
      status: 502,
    } satisfies Partial<DashboardDependencyError>);
  });
});
