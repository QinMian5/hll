// abstract: Express route definitions for browser-facing BFF authentication.
// out_of_scope: Logto SDK storage internals and application quota policy.

import {
  type NextFunction,
  type Request,
  type Response,
  Router,
} from "express";

import type { WebServerConfig } from "../config.js";
import {
  createLogtoClientFactory,
  LogtoAccountApiRequestError,
  WebAuthRequiredError,
  type WebLogtoClientFactory,
} from "./logto.js";

export interface CreateAuthRouterOptions {
  readonly config: WebServerConfig;
  readonly createClient?: WebLogtoClientFactory;
}

interface AuthSessionState {
  authReturnTo?: string;
}

const defaultPostAuthRedirect = "/";
const maxReturnToLength = 2048;

function joinPublicUrl(config: WebServerConfig, pathname: string): string {
  return new URL(pathname, config.publicBaseUrl).toString();
}

function isBlockedReturnToPath(pathname: string): boolean {
  return pathname === "/web-api" || pathname.startsWith("/web-api/");
}

function authSessionState(request: Request): AuthSessionState | undefined {
  if (request.session === undefined) {
    return undefined;
  }

  return request.session as unknown as AuthSessionState;
}

function normalizeReturnTo(
  config: WebServerConfig,
  value: unknown,
): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const returnTo = value.trim();
  if (
    returnTo === "" ||
    returnTo.length > maxReturnToLength ||
    !returnTo.startsWith("/") ||
    returnTo.startsWith("//")
  ) {
    return undefined;
  }

  let parsed: URL;
  try {
    parsed = new URL(returnTo, config.publicBaseUrl);
  } catch {
    return undefined;
  }

  if (
    parsed.origin !== new URL(config.publicBaseUrl).origin ||
    isBlockedReturnToPath(parsed.pathname)
  ) {
    return undefined;
  }

  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

function storeAuthReturnTo(
  request: Request,
  config: WebServerConfig,
  value: unknown,
): void {
  const session = authSessionState(request);
  if (session === undefined) {
    return;
  }

  delete session.authReturnTo;

  const returnTo = normalizeReturnTo(config, value);
  if (returnTo !== undefined) {
    session.authReturnTo = returnTo;
  }
}

function takeAuthReturnTo(request: Request): string {
  const session = authSessionState(request);
  const returnTo = session?.authReturnTo;

  if (session !== undefined) {
    delete session.authReturnTo;
  }

  return returnTo ?? defaultPostAuthRedirect;
}

function readProfileName(value: unknown): string | null {
  if (value === null) {
    return null;
  }

  if (typeof value !== "string") {
    throw new Error("invalid_account_name");
  }

  const name = value.trim();
  if (name.length > 128) {
    throw new Error("invalid_account_name");
  }

  return name === "" ? null : name;
}

function handleProfileRouteError(
  error: unknown,
  response: Response,
  next: NextFunction,
): void {
  if (error instanceof Error && error.message === "invalid_account_name") {
    response.status(400).json({
      error: {
        code: "invalid_account_name",
        message: "Name must be 128 characters or fewer.",
      },
    });
    return;
  }

  if (error instanceof WebAuthRequiredError) {
    response.status(401).json({
      error: {
        code: "authentication_required",
        message: "Authentication required.",
      },
    });
    return;
  }

  if (error instanceof LogtoAccountApiRequestError) {
    response.status(502).json({
      error: {
        code: "logto_account_profile_unavailable",
        message: "Account profile is unavailable.",
      },
    });
    return;
  }

  next(error);
}

export function createAuthRouter(options: CreateAuthRouterOptions): Router {
  const router = Router();
  const createClient =
    options.createClient ?? createLogtoClientFactory(options.config);

  router.get("/session", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      response.json(await client.getSession());
    } catch (error) {
      next(error);
    }
  });

  router.get("/profile", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      response.json(await client.getProfile());
    } catch (error) {
      handleProfileRouteError(error, response, next);
    }
  });

  router.patch("/profile", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      response.json(
        await client.updateProfile({
          name: readProfileName(request.body?.name),
        }),
      );
    } catch (error) {
      handleProfileRouteError(error, response, next);
    }
  });

  router.post("/sign-in", async (request, response, next) => {
    try {
      storeAuthReturnTo(request, options.config, request.body?.return_to);
      const client = createClient(request, response);
      const redirectUrl = await client.signIn({
        redirectUri: joinPublicUrl(options.config, "/web-api/auth/callback"),
      });

      response.redirect(303, redirectUrl);
    } catch (error) {
      next(error);
    }
  });

  router.get("/callback", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      await client.handleSignInCallback(
        joinPublicUrl(options.config, request.originalUrl),
      );

      response.redirect(303, takeAuthReturnTo(request));
    } catch (error) {
      next(error);
    }
  });

  router.post("/sign-out", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      const redirectUrl = await client.signOut(options.config.publicBaseUrl);

      response.redirect(303, redirectUrl);
    } catch (error) {
      next(error);
    }
  });

  return router;
}
