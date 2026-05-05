// abstract: Tests for Logto Account API routing from the web BFF.
// out_of_scope: Express auth route status mapping and browser settings rendering.
// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

import { loadWebServerConfig } from "../config.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";

const logtoMock = vi.hoisted(() => {
  const client = {
    clearAccessToken: vi.fn(async () => {}),
    getAccessToken: vi.fn(async () => "user-access-token"),
    getIdTokenClaims: vi.fn(async () => ({
      email: "claims@example.com",
      sub: "claims-user",
    })),
    isAuthenticated: vi.fn(async () => true),
  };

  function LogtoClient() {
    return client;
  }

  return {
    client,
    LogtoClient: vi.fn(LogtoClient),
  };
});

vi.mock("@logto/node", () => ({
  default: logtoMock.LogtoClient,
}));

const TEST_ENV = createWebServerTestEnv();

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe("Logto Account API routing", () => {
  it("uses the internal endpoint and public forwarded headers for profile reads and updates", async () => {
    const { createLogtoClientFactory } = await import("./logto.js");
    const requested: Array<{
      body: string | undefined;
      headers: Headers;
      method: string;
      url: string;
    }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        requested.push({
          body: typeof init?.body === "string" ? init.body : undefined,
          headers: new Headers(init?.headers),
          method: init?.method ?? "GET",
          url: String(input),
        });

        return new Response(
          JSON.stringify({
            id: "account-user",
            name: "Ada Account",
            primaryEmail: "account@example.com",
          }),
          {
            headers: { "content-type": "application/json" },
            status: 200,
          },
        );
      }),
    );
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://localhost:3011",
      KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: "http://logto:3001",
    });
    const client = createLogtoClientFactory(config)({ session: {} }, {});

    await client.getProfile();
    await client.updateProfile({ name: "Ada Account" });

    expect(requested).toEqual([
      expect.objectContaining({
        body: undefined,
        method: "GET",
        url: "http://logto:3001/api/my-account",
      }),
      expect.objectContaining({
        body: JSON.stringify({ name: "Ada Account" }),
        method: "PATCH",
        url: "http://logto:3001/api/my-account",
      }),
    ]);
    for (const request of requested) {
      expect(request.headers.get("authorization")).toBe(
        "Bearer user-access-token",
      );
      expect(request.headers.get("x-forwarded-host")).toBe("localhost:3011");
      expect(request.headers.get("x-forwarded-proto")).toBe("http");
    }
  });

  it("refreshes the cached token once when the Account API rejects it", async () => {
    const { createLogtoClientFactory } = await import("./logto.js");
    const requestedAuthorizations: Array<string | null> = [];
    logtoMock.client.getAccessToken
      .mockResolvedValueOnce("stale-access-token")
      .mockResolvedValueOnce("fresh-access-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
        requestedAuthorizations.push(
          new Headers(init?.headers).get("authorization"),
        );

        if (requestedAuthorizations.length === 1) {
          return new Response(
            JSON.stringify({
              code: "auth.unauthorized",
              message: "Unauthorized.",
            }),
            {
              headers: { "content-type": "application/json" },
              status: 401,
            },
          );
        }

        return new Response(
          JSON.stringify({
            id: "account-user",
            name: "Ada Account",
          }),
          {
            headers: { "content-type": "application/json" },
            status: 200,
          },
        );
      }),
    );
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://localhost:3011",
      KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: "http://logto:3001",
    });
    const client = createLogtoClientFactory(config)({ session: {} }, {});

    const profile = await client.getProfile();

    expect(profile.name).toBe("Ada Account");
    expect(logtoMock.client.clearAccessToken).toHaveBeenCalledTimes(1);
    expect(requestedAuthorizations).toEqual([
      "Bearer stale-access-token",
      "Bearer fresh-access-token",
    ]);
  });
});
