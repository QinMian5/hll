// abstract: Anonymous browser identity cookie handling for quota principals.
// out_of_scope: User authentication state, Redis quota storage, and route policy.

import { randomBytes } from "node:crypto";

import type { Request, Response } from "express";

import type { WebServerConfig } from "../config.js";

export const ANONYMOUS_IDENTITY_COOKIE_NAME = "knowledge.anonymous_id";

const ANONYMOUS_IDENTITY_MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000;

export interface AnonymousIdentityOptions {
  readonly generateId?: () => string;
}

function parseCookieHeader(
  cookieHeader: string | undefined,
): Map<string, string> {
  const cookies = new Map<string, string>();

  if (cookieHeader === undefined || cookieHeader.trim() === "") {
    return cookies;
  }

  for (const part of cookieHeader.split(";")) {
    const [rawName, ...rawValueParts] = part.trim().split("=");
    if (!rawName || rawValueParts.length === 0) {
      continue;
    }

    cookies.set(rawName, decodeURIComponent(rawValueParts.join("=")));
  }

  return cookies;
}

function generateAnonymousId(): string {
  return randomBytes(24).toString("base64url");
}

export function readAnonymousIdentity(request: Request): string | undefined {
  return parseCookieHeader(request.headers.cookie).get(
    ANONYMOUS_IDENTITY_COOKIE_NAME,
  );
}

export function ensureAnonymousIdentity(
  request: Request,
  response: Response,
  config: WebServerConfig,
  options: AnonymousIdentityOptions = {},
): string {
  const existingIdentity = readAnonymousIdentity(request);

  if (existingIdentity !== undefined && existingIdentity !== "") {
    return existingIdentity;
  }

  const anonymousId = options.generateId?.() ?? generateAnonymousId();

  response.cookie(ANONYMOUS_IDENTITY_COOKIE_NAME, anonymousId, {
    ...(config.cookieDomain === undefined
      ? {}
      : { domain: config.cookieDomain }),
    httpOnly: true,
    maxAge: ANONYMOUS_IDENTITY_MAX_AGE_MS,
    path: "/",
    sameSite: "lax",
    secure: config.cookieSecure,
  });

  return anonymousId;
}
