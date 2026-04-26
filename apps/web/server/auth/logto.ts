// abstract: Logto Node client adapter for BFF-owned server sessions.
// out_of_scope: Express route definitions and quota principal resolution.

import LogtoClient, {
  type IdTokenClaims,
  type LogtoConfig,
  type PersistKey,
  type Storage,
  type StorageKey,
} from "@logto/node";
import type { Request, Response } from "express";

import type { WebServerConfig } from "../config.js";
import type {
  AuthenticatedWebUser,
  WebSessionResponse,
} from "./sessionState.js";

type LogtoStorageKey = StorageKey | PersistKey;

export interface SignInRequest {
  readonly redirectUri: string;
}

export interface WebLogtoClient {
  readonly getSession: () => Promise<WebSessionResponse>;
  readonly handleSignInCallback: (callbackUri: string) => Promise<void>;
  readonly signIn: (request: SignInRequest) => Promise<string>;
  readonly signOut: (postLogoutRedirectUri: string) => Promise<string>;
}

export type WebLogtoClientFactory = (
  request: Request,
  response: Response,
) => WebLogtoClient;

interface SessionLike {
  [key: string]: unknown;
}

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

export function createLogtoClientFactory(
  config: WebServerConfig,
): WebLogtoClientFactory {
  return (request, _response) => {
    let redirectUrl: string | undefined;
    const client = new LogtoClient(createLogtoConfig(config), {
      navigate: (url) => {
        redirectUrl = url;
      },
      storage: createSessionStorage(request),
    });

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
      handleSignInCallback: async (callbackUri) => {
        await client.handleSignInCallback(callbackUri);
      },
      signIn: async ({ redirectUri }) => {
        redirectUrl = undefined;
        await client.signIn({ redirectUri });
        return takeRedirectUrl(redirectUrl);
      },
      signOut: async (postLogoutRedirectUri) => {
        redirectUrl = undefined;
        await client.signOut(postLogoutRedirectUri);
        return takeRedirectUrl(redirectUrl);
      },
    };
  };
}
