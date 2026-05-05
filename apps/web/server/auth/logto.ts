// abstract: Logto Node client adapter for BFF-owned server sessions.
// out_of_scope: Express route definitions and quota principal resolution.

import LogtoClient, {
  type ClientAdapter,
  type IdTokenClaims,
  type JwtVerifier,
  type LogtoConfig,
  type PersistKey,
  Prompt,
  type StandardLogtoClient,
  type Storage,
  type StorageKey,
} from "@logto/node";
import type { Response as ExpressResponse, Request } from "express";
import {
  createLocalJWKSet,
  type JSONWebKeySet,
  type JWTVerifyGetKey,
  jwtVerify,
} from "jose";

import type { WebServerConfig } from "../config.js";
import type {
  AuthenticatedWebUser,
  UpdateWebAccountProfileRequest,
  WebAccountProfile,
  WebSessionResponse,
} from "./sessionState.js";
import {
  requestWithUserAccessTokenRetry,
  type UserAccessTokenClient,
} from "./tokenResolver.js";

type LogtoStorageKey = StorageKey | PersistKey;
type LogtoAccountProfilePayload = {
  readonly email?: unknown;
  readonly id?: unknown;
  readonly name?: unknown;
  readonly primaryEmail?: unknown;
};

export interface SignInRequest {
  readonly prompt?: "none";
  readonly redirectUri: string;
}

export interface WebLogtoClient {
  readonly getProfile: () => Promise<WebAccountProfile>;
  readonly getSession: () => Promise<WebSessionResponse>;
  readonly handleSignInCallback: (callbackUri: string) => Promise<void>;
  readonly signIn: (request: SignInRequest) => Promise<string>;
  readonly signOut: (postLogoutRedirectUri: string) => Promise<string>;
  readonly updateProfile: (
    request: UpdateWebAccountProfileRequest,
  ) => Promise<WebAccountProfile>;
}

export class WebAuthRequiredError extends Error {
  constructor() {
    super("Authentication required.");
    this.name = "WebAuthRequiredError";
  }
}

export class LogtoAccountApiRequestError extends Error {
  constructor() {
    super("Logto account profile is unavailable.");
    this.name = "LogtoAccountApiRequestError";
  }
}

class LogtoAccountApiUnauthorizedError extends Error {
  constructor() {
    super("Logto account profile token was rejected.");
    this.name = "LogtoAccountApiUnauthorizedError";
  }
}

export type WebLogtoClientFactory = (
  request: Request,
  response: ExpressResponse,
) => WebLogtoClient;

interface SessionLike {
  [key: string]: unknown;
}

const LOGTO_ID_TOKEN_CLOCK_TOLERANCE_SECONDS = 300;

function requireSession(request: Request): SessionLike {
  const maybeSession = request.session as unknown as SessionLike | undefined;

  if (maybeSession === undefined) {
    throw new Error("Logto requires Express session middleware.");
  }

  return maybeSession;
}

function createSessionStorage(request: Request): Storage<LogtoStorageKey> {
  const session = requireSession(request);

  return {
    getItem: async (key) => {
      const value = session[key];
      return value === undefined ? null : String(value);
    },
    removeItem: async (key) => {
      session[key] = undefined;
    },
    setItem: async (key, value) => {
      session[key] = value;
    },
  };
}

function createLogtoConfig(config: WebServerConfig): LogtoConfig {
  return {
    appId: config.logtoAppId,
    appSecret: config.logtoAppSecret,
    endpoint: config.logtoEndpoint,
  };
}

function createClientAuthorization(config: WebServerConfig): string {
  return `Basic ${Buffer.from(
    `${config.logtoAppId}:${config.logtoAppSecret}`,
    "utf8",
  ).toString("base64")}`;
}

function rewriteLogtoServerUrl(config: WebServerConfig, value: string): string {
  if (config.logtoInternalEndpoint === undefined) {
    return value;
  }

  const publicEndpoint = new URL(config.logtoEndpoint);
  const internalEndpoint = new URL(config.logtoInternalEndpoint);
  const url = new URL(value);

  if (url.origin !== publicEndpoint.origin) {
    return value;
  }

  url.protocol = internalEndpoint.protocol;
  url.host = internalEndpoint.host;
  return url.toString();
}

function rewriteFetchInput(
  config: WebServerConfig,
  input: Parameters<typeof fetch>[0],
): Parameters<typeof fetch>[0] {
  if (typeof input === "string") {
    return rewriteLogtoServerUrl(config, input);
  }

  if (input instanceof URL) {
    return new URL(rewriteLogtoServerUrl(config, input.toString()));
  }

  const rewrittenUrl = rewriteLogtoServerUrl(config, input.url);
  return rewrittenUrl === input.url ? input : new Request(rewrittenUrl, input);
}

function withLogtoForwardedHeaders(
  config: WebServerConfig,
  init: Parameters<typeof fetch>[1],
): Parameters<typeof fetch>[1] {
  const headers = new Headers(init?.headers);

  if (config.logtoInternalEndpoint !== undefined) {
    const publicEndpoint = new URL(config.logtoEndpoint);
    headers.set("x-forwarded-host", publicEndpoint.host);
    headers.set("x-forwarded-proto", publicEndpoint.protocol.slice(0, -1));
  }

  return { ...init, headers };
}

function withClientAuthorization(
  config: WebServerConfig,
  init: Parameters<typeof fetch>[1],
): Parameters<typeof fetch>[1] {
  const nextInit = withLogtoForwardedHeaders(config, init);
  const headers = new Headers(nextInit?.headers);
  if (!headers.has("authorization")) {
    headers.set("authorization", createClientAuthorization(config));
  }

  return { ...nextInit, headers };
}

export function createLogtoRequester(
  config: WebServerConfig,
  fetchFunction: typeof fetch = fetch,
): ClientAdapter["requester"] {
  const requester: ClientAdapter["requester"] = async <T>(
    ...args: Parameters<typeof fetch>
  ): Promise<T> => {
    const [input, init] = args;
    const response = await fetchFunction(
      rewriteFetchInput(config, input),
      withClientAuthorization(config, init),
    );

    if (!response.ok) {
      throw new Error(`Logto request failed with status ${response.status}.`);
    }

    return (await response.json()) as T;
  };

  return requester;
}

async function fetchLogtoJwks(
  config: WebServerConfig,
  jwksUri: string,
  fetchFunction: typeof fetch,
): Promise<JSONWebKeySet> {
  const response = await fetchFunction(
    rewriteLogtoServerUrl(config, jwksUri),
    withLogtoForwardedHeaders(config, undefined),
  );

  if (!response.ok) {
    throw new Error(
      `Logto JWKS request failed with status ${response.status}.`,
    );
  }

  return (await response.json()) as JSONWebKeySet;
}

export function createLogtoJwtVerifier(
  config: WebServerConfig,
  fetchFunction: typeof fetch = fetch,
): (client: StandardLogtoClient) => JwtVerifier {
  return (client) => {
    let verifyGetKey: JWTVerifyGetKey | undefined;

    return {
      verifyIdToken: async (idToken) => {
        const { appId } = client.logtoConfig;
        const { issuer, jwksUri } = await client.getOidcConfig();
        verifyGetKey ??= createLocalJWKSet(
          await fetchLogtoJwks(config, jwksUri, fetchFunction),
        );
        const result = await jwtVerify(idToken, verifyGetKey, {
          audience: appId,
          clockTolerance: LOGTO_ID_TOKEN_CLOCK_TOLERANCE_SECONDS,
          issuer,
        });

        if (
          Math.abs((result.payload.iat ?? 0) - Date.now() / 1000) >
          LOGTO_ID_TOKEN_CLOCK_TOLERANCE_SECONDS
        ) {
          throw new Error(
            "Logto ID token issued-at time is outside tolerance.",
          );
        }
      },
    };
  };
}

function takeRedirectUrl(redirectUrl: string | undefined): string {
  if (redirectUrl === undefined || redirectUrl === "") {
    throw new Error("Logto did not produce a redirect URL.");
  }

  return redirectUrl;
}

function readUserFromClaims(claims: IdTokenClaims): AuthenticatedWebUser {
  return {
    email: claims.email ?? undefined,
    id: claims.sub,
    name: claims.name ?? undefined,
  };
}

function joinLogtoUrl(config: WebServerConfig, pathname: string): string {
  const baseUrl = config.logtoEndpoint.endsWith("/")
    ? config.logtoEndpoint
    : `${config.logtoEndpoint}/`;
  const relativePath = pathname.startsWith("/") ? pathname.slice(1) : pathname;

  return new URL(relativePath, baseUrl).toString();
}

function readString(value: unknown): string | undefined {
  return typeof value === "string" && value !== "" ? value : undefined;
}

function readAccountPayload(value: unknown): LogtoAccountProfilePayload {
  if (typeof value !== "object" || value === null) {
    throw new LogtoAccountApiRequestError();
  }

  return value as LogtoAccountProfilePayload;
}

function mergeAccountProfile(
  claims: IdTokenClaims,
  payload: LogtoAccountProfilePayload,
): WebAccountProfile {
  return {
    email:
      readString(payload.email) ??
      readString(payload.primaryEmail) ??
      claims.email ??
      undefined,
    id: readString(payload.id) ?? claims.sub,
    name: readString(payload.name),
  };
}

type LogtoAccessTokenClient = Pick<
  StandardLogtoClient,
  "clearAccessToken" | "getAccessToken"
>;

type LogtoAccountProfileRequestInit = Omit<RequestInit, "headers"> & {
  readonly headers?: Record<string, string>;
};

async function requestAccountProfile(
  config: WebServerConfig,
  accessToken: string,
  init: LogtoAccountProfileRequestInit = {},
): Promise<LogtoAccountProfilePayload> {
  let accountResponse: globalThis.Response;

  try {
    accountResponse = await fetch(
      rewriteLogtoServerUrl(config, joinLogtoUrl(config, "/api/my-account")),
      withLogtoForwardedHeaders(config, {
        ...init,
        headers: {
          ...init.headers,
          authorization: `Bearer ${accessToken}`,
        },
      }),
    );
  } catch {
    throw new LogtoAccountApiRequestError();
  }

  if (accountResponse.status === 401) {
    throw new LogtoAccountApiUnauthorizedError();
  }

  if (!accountResponse.ok) {
    throw new LogtoAccountApiRequestError();
  }

  try {
    return readAccountPayload(await accountResponse.json());
  } catch (error) {
    if (error instanceof LogtoAccountApiRequestError) {
      throw error;
    }

    throw new LogtoAccountApiRequestError();
  }
}

async function requestAccountProfileWithTokenRefresh(
  config: WebServerConfig,
  client: LogtoAccessTokenClient,
  init: LogtoAccountProfileRequestInit = {},
): Promise<LogtoAccountProfilePayload> {
  return await requestWithUserAccessTokenRetry(
    client as UserAccessTokenClient,
    async (accessToken) =>
      await requestAccountProfile(config, accessToken, init),
    {
      isAccessTokenRejected: (error) =>
        error instanceof LogtoAccountApiUnauthorizedError,
    },
  );
}

export function createLogtoClientFactory(
  config: WebServerConfig,
): WebLogtoClientFactory {
  return (request, _response) => {
    let redirectUrl: string | undefined;
    const client = new LogtoClient(
      createLogtoConfig(config),
      {
        navigate: (url) => {
          redirectUrl = url;
        },
        requester: createLogtoRequester(config),
        storage: createSessionStorage(request),
      },
      createLogtoJwtVerifier(config),
    );

    return {
      getSession: async () => {
        if (!(await client.isAuthenticated())) {
          return { status: "anonymous" };
        }

        const claims = await client.getIdTokenClaims();

        return {
          status: "authenticated",
          user: readUserFromClaims(claims),
        };
      },
      getProfile: async () => {
        if (!(await client.isAuthenticated())) {
          throw new WebAuthRequiredError();
        }

        const [claims, accountProfile] = await Promise.all([
          client.getIdTokenClaims(),
          requestAccountProfileWithTokenRefresh(config, client),
        ]);

        return mergeAccountProfile(claims, accountProfile);
      },
      handleSignInCallback: async (callbackUri) => {
        await client.handleSignInCallback(callbackUri);
      },
      signIn: async ({ prompt, redirectUri }) => {
        redirectUrl = undefined;
        await client.signIn({
          prompt: prompt === "none" ? Prompt.None : undefined,
          redirectUri,
        });
        return takeRedirectUrl(redirectUrl);
      },
      signOut: async (postLogoutRedirectUri) => {
        redirectUrl = undefined;
        await client.signOut(postLogoutRedirectUri);
        return takeRedirectUrl(redirectUrl);
      },
      updateProfile: async ({ name }) => {
        if (!(await client.isAuthenticated())) {
          throw new WebAuthRequiredError();
        }

        const [claims, accountProfile] = await Promise.all([
          client.getIdTokenClaims(),
          requestAccountProfileWithTokenRefresh(config, client, {
            body: JSON.stringify({ name }),
            headers: {
              "content-type": "application/json",
            },
            method: "PATCH",
          }),
        ]);

        return mergeAccountProfile(claims, accountProfile);
      },
    };
  };
}
