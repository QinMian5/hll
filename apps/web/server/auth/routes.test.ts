// abstract: Contract tests for web BFF authentication routes.
// out_of_scope: Logto network behavior and Redis session persistence.
// @vitest-environment node

import { LogtoClientError, LogtoError } from "@logto/node";
import { Router } from "express";
import session from "express-session";
import { exportJWK, generateKeyPair, SignJWT } from "jose";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import {
  buildSessionCookieOptions,
  buildSessionOptions,
} from "../session/redisSessionStore.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import {
  createLogtoJwtVerifier,
  createLogtoRequester,
  LogtoAccountApiRequestError,
  WebAuthRequiredError,
  type WebLogtoClient,
} from "./logto.js";
import { createAuthRouter } from "./routes.js";
import { WebSessionExpiredError } from "./tokenResolver.js";

const TEST_ENV = createWebServerTestEnv();

function createFakeClient(
  overrides: Partial<WebLogtoClient> = {},
): WebLogtoClient {
  return {
    getProfile: vi.fn(async () => ({
      email: "ada@example.com",
      id: "user-1",
      name: "Ada",
    })),
    getSession: vi.fn(async () => ({ status: "anonymous" })),
    handleSignInCallback: vi.fn(async () => undefined),
    signIn: vi.fn(async () => "https://logto.example/sign-in"),
    signOut: vi.fn(async () => "https://logto.example/sign-out"),
    updateProfile: vi.fn(async ({ name }) => ({
      email: "ada@example.com",
      id: "user-1",
      name: name ?? undefined,
    })),
    ...overrides,
  };
}

function firstCookieValue(response: request.Response): string | undefined {
  const rawCookie = response.headers["set-cookie"];
  const cookies = Array.isArray(rawCookie) ? rawCookie : [rawCookie];
  return cookies
    .find((cookie): cookie is string => typeof cookie === "string")
    ?.split(";")[0];
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
    sessionMiddleware: session({
      ...buildSessionOptions(config),
    }),
    webApiRouter,
  });
}

describe("auth routes", () => {
  it("returns anonymous session state without token fields", async () => {
    const app = await createTestApp(createFakeClient());

    const response = await request(app).get("/web-api/auth/session");

    expect(response.status).toBe(200);
    expect(response.headers["cache-control"]).toContain("no-store");
    expect(response.body).toEqual({ status: "anonymous" });
    expect(response.text).not.toContain("accessToken");
    expect(response.text).not.toContain("idToken");
  });

  it("does not return conditional cache responses for session state", async () => {
    const app = await createTestApp(createFakeClient());

    const firstResponse = await request(app).get("/web-api/auth/session");
    const secondResponse = await request(app)
      .get("/web-api/auth/session")
      .set("If-None-Match", firstResponse.headers.etag ?? "");

    expect(firstResponse.status).toBe(200);
    expect(secondResponse.status).toBe(200);
    expect(secondResponse.body).toEqual({ status: "anonymous" });
    expect(secondResponse.headers["cache-control"]).toContain("no-store");
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

    const response = await request(app)
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/graph/science/mathematics?focus=1" });

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("https://logto.example/sign-in");
    expect(client.signIn).toHaveBeenCalledWith({
      redirectUri: "http://localhost:5173/web-api/auth/callback",
    });
  });

  it("returns to the validated pre-login route after callback", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);
    const agent = request.agent(app);

    const signInResponse = await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/graph/science/mathematics?focus=1" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(signInResponse.status).toBe(303);
    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe(
      "/graph/science/mathematics?focus=1",
    );
  });

  it("handles callback requests before the web API fallback route", async () => {
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

  it("does not accept duplicate auth-prefixed callback aliases", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);

    const response = await request(app).get(
      "/web-api/auth/auth/callback?code=abc&state=xyz",
    );

    expect(response.status).toBe(404);
    expect(response.body).toEqual({
      error: {
        code: "web_api_route_not_found",
        message: "Web API route not found.",
      },
    });
    expect(client.handleSignInCallback).not.toHaveBeenCalled();
  });

  it("regenerates the local session id after interactive callback", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);
    const agent = request.agent(app);

    const signInResponse = await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/dashboard" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(signInResponse.status).toBe(303);
    expect(callbackResponse.status).toBe(303);
    expect(firstCookieValue(callbackResponse)).toMatch(/^knowledge\.sid=/);
    expect(firstCookieValue(callbackResponse)).not.toBe(
      firstCookieValue(signInResponse),
    );
  });

  it("clears local state and returns to the protected route when the callback session is stale", async () => {
    const client = createFakeClient({
      handleSignInCallback: vi.fn(async () => {
        throw new LogtoClientError("sign_in_session.not_found");
      }),
    });
    const app = await createTestApp(client);
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/dashboard" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe("/dashboard");
    expect(callbackResponse.headers["set-cookie"]).toEqual(
      expect.arrayContaining([expect.stringMatching(/^knowledge\.sid=;/)]),
    );
    expect(callbackResponse.text).not.toContain("Sign-in session not found");
  });

  it("clears local state and returns safely when the callback state is mismatched", async () => {
    const client = createFakeClient({
      handleSignInCallback: vi.fn(async () => {
        throw new LogtoError("callback_uri_verification.state_mismatched");
      }),
    });
    const app = await createTestApp(client);
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/overview" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe("/overview");
    expect(callbackResponse.text).not.toContain("State mismatched");
  });

  it("falls back to root for external pre-login return URLs", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "https://evil.example/steal" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe("/");
  });

  it("falls back to root for BFF API return paths", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/web-api/auth/callback?code=abc" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe("/");
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

    const response = await request(app)
      .post("/web-api/auth/sign-out")
      .set("Origin", "http://localhost:5173");

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("https://logto.example/sign-out");
    expect(client.signOut).toHaveBeenCalledWith("http://localhost:5173");
  });

  it("destroys the local session during sign-out", async () => {
    const client = createFakeClient();
    const app = await createTestApp(client);
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/dashboard" });
    const response = await agent
      .post("/web-api/auth/sign-out")
      .set("Origin", "http://localhost:5173");

    expect(response.status).toBe(303);
    expect(response.headers["set-cookie"]).toEqual(
      expect.arrayContaining([expect.stringMatching(/^knowledge\.sid=;/)]),
    );
  });

  it("starts silent sign-in with prompt none and the silent callback route", async () => {
    const signIn = vi.fn(async () => "https://logto.example/silent");
    const app = await createTestApp(createFakeClient({ signIn }));

    const response = await request(app)
      .post("/web-api/auth/silent-sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/overview" });

    expect(response.status).toBe(303);
    expect(response.headers.location).toBe("https://logto.example/silent");
    expect(signIn).toHaveBeenCalledWith({
      prompt: "none",
      redirectUri: "http://localhost:5173/web-api/auth/silent-callback",
    });
  });

  it("returns a same-origin silent success message after silent callback", async () => {
    const app = await createTestApp(createFakeClient());

    const response = await request(app).get(
      "/web-api/auth/silent-callback?code=abc&state=xyz",
    );

    expect(response.status).toBe(200);
    expect(response.type).toBe("text/html");
    expect(response.text).toContain("knowledge.auth.silent");
    expect(response.text).toContain('"status":"success"');
    expect(response.text).not.toContain("code=abc");
    expect(response.text).not.toContain("accessToken");
  });

  it("returns a same-origin silent failure message without exposing provider details", async () => {
    const app = await createTestApp(
      createFakeClient({
        handleSignInCallback: vi.fn(async () => {
          throw new Error("provider said login_required with token detail");
        }),
      }),
    );

    const response = await request(app).get(
      "/web-api/auth/silent-callback?error=login_required&state=xyz",
    );

    expect(response.status).toBe(200);
    expect(response.type).toBe("text/html");
    expect(response.text).toContain("knowledge.auth.silent");
    expect(response.text).toContain('"status":"failed"');
    expect(response.text).not.toContain("provider said");
    expect(response.text).not.toContain("token detail");
  });

  it("keeps silent auth state from overwriting interactive return paths", async () => {
    const app = await createTestApp(createFakeClient());
    const agent = request.agent(app);

    await agent
      .post("/web-api/auth/sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/dashboard" });
    await agent
      .post("/web-api/auth/silent-sign-in")
      .set("Origin", "http://localhost:5173")
      .type("form")
      .send({ return_to: "/overview" });
    const callbackResponse = await agent.get(
      "/web-api/auth/callback?code=abc&state=xyz",
    );

    expect(callbackResponse.status).toBe(303);
    expect(callbackResponse.headers.location).toBe("/dashboard");
  });

  it("returns account profile metadata without token fields", async () => {
    const getProfile = vi.fn(async () => ({
      email: "ada@example.com",
      id: "user-1",
      name: "Ada",
    }));
    const app = await createTestApp(createFakeClient({ getProfile }));

    const response = await request(app).get("/web-api/auth/profile");

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      email: "ada@example.com",
      id: "user-1",
      name: "Ada",
    });
    expect(getProfile).toHaveBeenCalledOnce();
    expect(response.text).not.toContain("accessToken");
    expect(response.text).not.toContain("idToken");
  });

  it("trims account profile names before updating", async () => {
    const updateProfile = vi.fn(async ({ name }) => ({
      email: "ada@example.com",
      id: "user-1",
      name: name ?? undefined,
    }));
    const app = await createTestApp(createFakeClient({ updateProfile }));

    const response = await request(app)
      .patch("/web-api/auth/profile")
      .set("Origin", "http://localhost:5173")
      .send({ name: "  Grace Hopper  " });

    expect(response.status).toBe(200);
    expect(updateProfile).toHaveBeenCalledWith({ name: "Grace Hopper" });
    expect(response.body).toEqual({
      email: "ada@example.com",
      id: "user-1",
      name: "Grace Hopper",
    });
    expect(response.text).not.toContain("accessToken");
    expect(response.text).not.toContain("idToken");
  });

  it("normalizes blank account profile names to null", async () => {
    const updateProfile = vi.fn(async ({ name }) => ({
      email: "ada@example.com",
      id: "user-1",
      name: name ?? undefined,
    }));
    const app = await createTestApp(createFakeClient({ updateProfile }));

    const response = await request(app)
      .patch("/web-api/auth/profile")
      .set("Origin", "http://localhost:5173")
      .send({ name: "   " });

    expect(response.status).toBe(200);
    expect(updateProfile).toHaveBeenCalledWith({ name: null });
    expect(response.body).toEqual({
      email: "ada@example.com",
      id: "user-1",
    });
  });

  it("accepts null account profile names for explicit clearing", async () => {
    const updateProfile = vi.fn(async ({ name }) => ({
      email: "ada@example.com",
      id: "user-1",
      name: name ?? undefined,
    }));
    const app = await createTestApp(createFakeClient({ updateProfile }));

    const response = await request(app)
      .patch("/web-api/auth/profile")
      .set("Origin", "http://localhost:5173")
      .send({ name: null });

    expect(response.status).toBe(200);
    expect(updateProfile).toHaveBeenCalledWith({ name: null });
    expect(response.body).toEqual({
      email: "ada@example.com",
      id: "user-1",
    });
  });

  it("rejects account profile names longer than 128 characters", async () => {
    const updateProfile = vi.fn();
    const app = await createTestApp(createFakeClient({ updateProfile }));

    const response = await request(app)
      .patch("/web-api/auth/profile")
      .set("Origin", "http://localhost:5173")
      .send({ name: "x".repeat(129) });

    expect(response.status).toBe(400);
    expect(response.body).toEqual({
      error: {
        code: "invalid_account_name",
        message: "Name must be 128 characters or fewer.",
      },
    });
    expect(updateProfile).not.toHaveBeenCalled();
  });

  it("rejects account profile access without an authenticated session", async () => {
    const app = await createTestApp(
      createFakeClient({
        getProfile: vi.fn(async () => {
          throw new WebAuthRequiredError();
        }),
      }),
    );

    const response = await request(app).get("/web-api/auth/profile");

    expect(response.status).toBe(401);
    expect(response.body).toEqual({
      error: {
        code: "authentication_required",
        message: "Authentication required.",
      },
    });
  });

  it("maps Logto Account API failures to safe profile errors", async () => {
    const app = await createTestApp(
      createFakeClient({
        updateProfile: vi.fn(async () => {
          throw new LogtoAccountApiRequestError();
        }),
      }),
    );

    const response = await request(app)
      .patch("/web-api/auth/profile")
      .set("Origin", "http://localhost:5173")
      .send({ name: "Ada" });

    expect(response.status).toBe(502);
    expect(response.body).toEqual({
      error: {
        code: "logto_account_profile_unavailable",
        message: "Account profile is unavailable.",
      },
    });
    expect(response.text).not.toContain("token");
    expect(response.text).not.toContain("upstream");
  });

  it("maps expired account profile sessions to safe auth errors", async () => {
    const app = await createTestApp(
      createFakeClient({
        getProfile: vi.fn(async () => {
          throw new WebSessionExpiredError();
        }),
      }),
    );

    const response = await request(app).get("/web-api/auth/profile");

    expect(response.status).toBe(401);
    expect(response.body).toEqual({
      error: {
        code: "session_expired",
        message: "Session expired.",
      },
    });
    expect(response.text).not.toContain("token");
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
      maxAge: 30 * 24 * 60 * 60 * 1000,
      sameSite: "lax",
      secure: true,
    });
    expect(buildSessionOptions(config)).toMatchObject({
      name: "knowledge.sid",
      rolling: true,
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
