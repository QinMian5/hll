// abstract: Redis-backed Express session middleware for the web BFF.
// out_of_scope: Anonymous identity cookies and application quota storage.

import { RedisStore } from "connect-redis";
import type { RequestHandler } from "express";
import session, { type CookieOptions } from "express-session";
import { createClient } from "redis";

import type { WebServerConfig } from "../config.js";

const SESSION_COOKIE_NAME = "knowledge.sid";
const SESSION_REDIS_PREFIX = "knowledge:web:session:";

export function buildSessionCookieOptions(
  config: WebServerConfig,
): CookieOptions {
  return {
    ...(config.cookieDomain === undefined
      ? {}
      : { domain: config.cookieDomain }),
    httpOnly: true,
    sameSite: "lax",
    secure: config.cookieSecure,
  };
}

export async function createRedisSessionMiddleware(
  config: WebServerConfig,
): Promise<RequestHandler> {
  const redisClient = createClient({ url: config.redisUrl });
  await redisClient.connect();

  return session({
    cookie: buildSessionCookieOptions(config),
    name: SESSION_COOKIE_NAME,
    resave: false,
    saveUninitialized: false,
    secret: config.sessionSecret,
    store: new RedisStore({
      client: redisClient,
      prefix: SESSION_REDIS_PREFIX,
    }),
  });
}
