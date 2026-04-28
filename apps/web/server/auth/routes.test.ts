// abstract: Contract tests for web BFF authentication routes.
// out_of_scope: Logto network behavior and Redis session persistence.
// @vitest-environment node

import { Router } from "express";
import { exportJWK, generateKeyPair, SignJWT } from "jose";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import { buildSessionCookieOptions } from "../session/redisSessionStore.js";
import {
  createLogtoJwtVerifier,
  createLogtoRequester,
  type WebLogtoClient,
} from "./logto.js";
import { createAuthRouter } from "./routes.js";

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

function createFakeClient(
  overrides: Partial<WebLogtoClient> = {},
): WebLogtoClient {
  return {
    getSession: vi.fn(async () => ({ status: "anonymous" })),
    handleSignInCallback: vi.fn(async () => undefined),
    signIn: vi.fn(async () => "https://logto.example/sign-in"),
    signOut: vi.fn(async () => "https://logto.example/sign-out"),
    ...overrides,
  };
}

async function createTestApp(client: WebLogtoClient) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/auth",
    createAuthRouter({
      config,
      createClient: () => client,
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

describe("auth routes", () => {
  it("returns anonymous session state without token fields", async () => {
    const app = await createTestApp(createFakeClient());

    const response = await request(app).get("/web-api/auth/session");

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: "anonymous" });
    expect(response.text).not.toContain("accessToken");
    expect(response.text).not.toContain("idToken");
  });

  it("returns authenticated user metadata without token fields", async () => {
    const app = await createTestApp(
      createFakeClient({
        getSession: vi.fn(async () => ({
          status: "authenticated",
          user: {
            email: "ada@example.com",
            id: "user-1",
            name: "Ada",
          },
        })),
      }),
    );

    const response = await request(app).get("/web-api/auth/session");

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      status: "authenticated",
      user: {
        email: "ada@example.com",
        id: "user-1",
        name: "Ada",
      },
    });
    expect(response.text).not.toContain("accessToken");
    expect(response.text).not.toContain("idToken");
  });

  it("starts sign-in with the approved callback route", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);

    const response = await request(app).post("/web-api/auth/sign-in");

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("https://logto.example/sign-in");
    expect(client.signIn).toHaveBeenCalledWith({
      redirectUri: "http://localhost:5173/web-api/auth/callback",
    });
  });

  it("handles Logto callback using the full public callback URI", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);

    const response = await request(app).get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("/");
    expect(client.handleSignInCallback).toHaveBeenCalledWith(
      "http://localhost:5173/web-api/auth/callback?code=abc&state=xyz",
    );
  });

  it("starts sign-out through Logto", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);

    const response = await request(app).post("/web-api/auth/sign-out");

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("https://logto.example/sign-out");
    expect(client.signOut).toHaveBeenCalledWith("http://localhost:5173");
  });
});

describe("session cookie policy", () => {
  it("uses httpOnly lax cookies and honors secure config", () => {
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_COOKIE_DOMAIN: "knowledge.example",
      KNOWLEDGE_WEB_COOKIE_SECURE: "true",
    });

    expect(buildSessionCookieOptions(config)).toEqual({
      domain: "knowledge.example",
      httpOnly: true,
      sameSite: "lax",
      secure: true,
    });
  });
});

describe("Logto requester", () => {
  it("uses the internal endpoint for server-side Logto HTTP requests", async () => {
    const requestedUrls: string[] = [];
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://localhost:3011",
      KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: "http://logto:3001",
    });
    const requester = createLogtoRequester(config, async (input, init) => {
      requestedUrls.push(String(input));
      const headers = new Headers(init?.headers);
      expect(headers.get("authorization")).toBe(
        "Basic dGVzdC1hcHA6dGVzdC1zZWNyZXQ=",
      );
      expect(headers.get("x-forwarded-host")).toBe("localhost:3011");
      expect(headers.get("x-forwarded-proto")).toBe("http");

      return new Response(JSON.stringify({ issuer: "ok" }), {
        headers: { "content-type": "application/json" },
        status: 200,
      });
    });

    await requester(
      "http://localhost:3011/oidc/.well-known/openid-configuration",
    );

    expect(requestedUrls).toEqual([
      "http://logto:3001/oidc/.well-known/openid-configuration",
    ]);
  });

  it("uses the internal endpoint when fetching JWKS for ID token verification", async () => {
    const requestedUrls: string[] = [];
    const config = loadWebServerConfig({
      ...TEST_ENV,
      KNOWLEDGE_WEB_LOGTO_ENDPOINT: "http://localhost:3011",
      KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: "http://logto:3001",
    });
    const { privateKey, publicKey } = await generateKeyPair("RS256");
    const publicJwk = await exportJWK(publicKey);
    const keyId = "test-key";
    const idToken = await new SignJWT({ sub: "user-1" })
      .setProtectedHeader({ alg: "RS256", kid: keyId })
      .setIssuer("http://localhost:3011/oidc")
      .setAudience("test-app")
      .setIssuedAt()
      .setExpirationTime("5m")
      .sign(privateKey);
    const verifier = createLogtoJwtVerifier(config, async (input, init) => {
      requestedUrls.push(String(input));
      const headers = new Headers(init?.headers);
      expect(headers.get("x-forwarded-host")).toBe("localhost:3011");
      expect(headers.get("x-forwarded-proto")).toBe("http");

      return new Response(
        JSON.stringify({
          keys: [{ ...publicJwk, alg: "RS256", kid: keyId, use: "sig" }],
        }),
        {
          headers: { "content-type": "application/json" },
          status: 200,
        },
      );
    })({
      getOidcConfig: async () => ({
        authorizationEndpoint: "http://localhost:3011/oidc/auth",
        endSessionEndpoint: "http://localhost:3011/oidc/session/end",
        issuer: "http://localhost:3011/oidc",
        jwksUri: "http://localhost:3011/oidc/jwks",
        revocationEndpoint: "http://localhost:3011/oidc/token/revocation",
        tokenEndpoint: "http://localhost:3011/oidc/token",
        userinfoEndpoint: "http://localhost:3011/oidc/me",
      }),
      logtoConfig: { appId: "test-app" },
    });

    await verifier.verifyIdToken(idToken);

    expect(requestedUrls).toEqual(["http://logto:3001/oidc/jwks"]);
  });
});
