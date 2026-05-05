// abstract: Express route definitions for browser-facing BFF authentication.
// out_of_scope: Logto SDK storage internals and application quota policy.

import { LogtoClientError, LogtoError } from "@logto/node";
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
import {
  destroyLocalSession,
  markAuthenticatedSession,
  regenerateSessionPreserving,
} from "./sessionLifecycle.js";
import { WebSessionExpiredError } from "./tokenResolver.js";

export interface CreateAuthRouterOptions {
  readonly config: WebServerConfig;
  readonly createClient?: WebLogtoClientFactory;
}

interface AuthSessionState {
  authReturnTo?: string;
}

const defaultPostAuthRedirect = "/";
const maxReturnToLength = 2048;
const recoverableCallbackClientErrorCodes = new Set([
  "sign_in_session.invalid",
  "sign_in_session.not_found",
]);

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

function hasInteractiveAuthReturnTo(request: Request): boolean {
  return authSessionState(request)?.authReturnTo !== undefined;
}

function sessionKeys(request: Request): string[] {
  const session = authSessionState(request);
  return session === undefined ? [] : Object.keys(session);
}

function renderSilentCallbackDocument(
  config: WebServerConfig,
  status: "failed" | "success",
): string {
  const targetOrigin = JSON.stringify(new URL(config.publicBaseUrl).origin);
  const message = JSON.stringify({
    status,
    type: "knowledge.auth.silent",
  });

  return `<!doctype html><html><body><script>window.parent.postMessage(${message},${targetOrigin});</script></body></html>`;
}

function applyAuthNoStoreHeaders(
  request: Request,
  response: Response,
  next: NextFunction,
): void {
  delete request.headers["if-modified-since"];
  delete request.headers["if-none-match"];
  response.set({
    "Cache-Control": "no-store, max-age=0",
    Expires: "0",
    Pragma: "no-cache",
  });
  next();
}

function isRecoverableSignInCallbackError(error: unknown): boolean {
  if (
    error instanceof LogtoClientError &&
    recoverableCallbackClientErrorCodes.has(error.code)
  ) {
    return true;
  }

  return (
    error instanceof LogtoError &&
    error.code.startsWith("callback_uri_verification.")
  );
}

async function redirectAfterRecoverableSignInCallbackError(
  request: Request,
  response: Response,
): Promise<void> {
  const returnTo = takeAuthReturnTo(request);
  await destroyLocalSession(request, response);
  response.redirect(303, returnTo);
}

async function handleInteractiveCallback(
  request: Request,
  response: Response,
  next: NextFunction,
  config: WebServerConfig,
  createClient: WebLogtoClientFactory,
): Promise<void> {
  try {
    const client = createClient(request, response);
    await client.handleSignInCallback(
      joinPublicUrl(config, request.originalUrl),
    );
    const returnTo = takeAuthReturnTo(request);
    markAuthenticatedSession(request);
    await regenerateSessionPreserving(request, sessionKeys(request));

    response.redirect(303, returnTo);
  } catch (error) {
    if (isRecoverableSignInCallbackError(error)) {
      try {
        await redirectAfterRecoverableSignInCallbackError(request, response);
      } catch (sessionError) {
        next(sessionError);
      }
      return;
    }

    next(error);
  }
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

  if (error instanceof WebSessionExpiredError) {
    response.status(401).json({
      error: {
        code: "session_expired",
        message: "Session expired.",
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

  router.use(applyAuthNoStoreHeaders);

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

  router.get("/callback", (request, response, next) => {
    void handleInteractiveCallback(
      request,
      response,
      next,
      options.config,
      createClient,
    );
  });

  router.post("/silent-sign-in", async (request, response, next) => {
    try {
      if (hasInteractiveAuthReturnTo(request)) {
        response
          .status(200)
          .type("html")
          .send(renderSilentCallbackDocument(options.config, "failed"));
        return;
      }

      const client = createClient(request, response);
      const redirectUrl = await client.signIn({
        prompt: "none",
        redirectUri: joinPublicUrl(
          options.config,
          "/web-api/auth/silent-callback",
        ),
      });

      response.redirect(303, redirectUrl);
    } catch (error) {
      next(error);
    }
  });

  router.get("/silent-callback", async (request, response) => {
    if (hasInteractiveAuthReturnTo(request)) {
      response
        .status(200)
        .type("html")
        .send(renderSilentCallbackDocument(options.config, "failed"));
      return;
    }

    try {
      const client = createClient(request, response);
      await client.handleSignInCallback(
        joinPublicUrl(options.config, request.originalUrl),
      );
      markAuthenticatedSession(request);
      await regenerateSessionPreserving(request, sessionKeys(request));

      response
        .status(200)
        .type("html")
        .send(renderSilentCallbackDocument(options.config, "success"));
    } catch {
      response
        .status(200)
        .type("html")
        .send(renderSilentCallbackDocument(options.config, "failed"));
    }
  });

  router.post("/sign-out", async (request, response, next) => {
    try {
      const client = createClient(request, response);
      const redirectUrl = await client.signOut(options.config.publicBaseUrl);
      await destroyLocalSession(request, response);

      response.redirect(303, redirectUrl);
    } catch (error) {
      next(error);
    }
  });

  return router;
}
