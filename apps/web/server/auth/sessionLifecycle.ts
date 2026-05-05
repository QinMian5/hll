// abstract: Helpers for authenticated web session metadata and local session lifecycle.
// out_of_scope: Logto SDK token exchange and browser auth coordination.

import type { Request, Response } from "express";

export const WEB_AUTH_IDLE_SESSION_MS = 30 * 24 * 60 * 60 * 1000;
export const WEB_AUTH_ABSOLUTE_SESSION_MS = 90 * 24 * 60 * 60 * 1000;
export const WEB_AUTH_SESSION_COOKIE_NAME = "knowledge.sid";

export interface AuthenticatedSessionMeta {
  readonly authenticatedAt: number;
  readonly lastSeenAt: number;
}

interface SessionLike {
  [key: string]: unknown;
  destroy: (callback: (error?: Error | null) => void) => void;
  regenerate: (callback: (error?: Error | null) => void) => void;
  webAuth?: unknown;
}

function sessionFor(request: Request): SessionLike {
  const session = request.session as unknown as SessionLike | undefined;
  if (session === undefined) {
    throw new Error("Express session middleware is required.");
  }

  return session;
}

function readWebAuth(value: unknown): AuthenticatedSessionMeta | undefined {
  if (typeof value !== "object" || value === null) {
    return undefined;
  }

  const candidate = value as Partial<AuthenticatedSessionMeta>;
  if (
    typeof candidate.authenticatedAt !== "number" ||
    typeof candidate.lastSeenAt !== "number"
  ) {
    return undefined;
  }

  return {
    authenticatedAt: candidate.authenticatedAt,
    lastSeenAt: candidate.lastSeenAt,
  };
}

export function markAuthenticatedSession(
  request: Request,
  now = Date.now(),
): void {
  sessionFor(request).webAuth = {
    authenticatedAt: now,
    lastSeenAt: now,
  } satisfies AuthenticatedSessionMeta;
}

export function readExpiredSessionReason(
  request: Request,
  now = Date.now(),
): "idle" | "absolute" | undefined {
  const webAuth = readWebAuth(sessionFor(request).webAuth);
  if (webAuth === undefined) {
    return undefined;
  }

  if (now - webAuth.authenticatedAt > WEB_AUTH_ABSOLUTE_SESSION_MS) {
    return "absolute";
  }

  if (now - webAuth.lastSeenAt > WEB_AUTH_IDLE_SESSION_MS) {
    return "idle";
  }

  return undefined;
}

export function touchAuthenticatedSession(
  request: Request,
  now = Date.now(),
): void {
  const session = sessionFor(request);
  const webAuth = readWebAuth(session.webAuth);
  if (webAuth === undefined) {
    return;
  }

  session.webAuth = {
    authenticatedAt: webAuth.authenticatedAt,
    lastSeenAt: now,
  } satisfies AuthenticatedSessionMeta;
}

export async function regenerateSessionPreserving(
  request: Request,
  keys: readonly string[],
): Promise<void> {
  const session = sessionFor(request);
  const preserved = new Map<string, unknown>();
  for (const key of keys) {
    const value = session[key];
    if (value !== undefined) {
      preserved.set(key, value);
    }
  }

  await new Promise<void>((resolve, reject) => {
    session.regenerate((error) => {
      if (error == null) {
        resolve();
        return;
      }
      reject(error);
    });
  });

  const nextSession = sessionFor(request);
  for (const [key, value] of preserved) {
    nextSession[key] = value;
  }
}

export async function destroyLocalSession(
  request: Request,
  response: Response,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    sessionFor(request).destroy((error) => {
      if (error == null) {
        resolve();
        return;
      }
      reject(error);
    });
  });
  response.clearCookie(WEB_AUTH_SESSION_COOKIE_NAME);
}
