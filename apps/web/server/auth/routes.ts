// abstract: Express route definitions for browser-facing BFF authentication.
// out_of_scope: Logto SDK storage internals and application quota policy.

import { Router } from "express";

import type { WebServerConfig } from "../config.js";
import {
  createLogtoClientFactory,
  type WebLogtoClientFactory,
} from "./logto.js";

export interface CreateAuthRouterOptions {
  readonly config: WebServerConfig;
  readonly createClient?: WebLogtoClientFactory;
}

function joinPublicUrl(config: WebServerConfig, pathname: string): string {
  return new URL(pathname, config.publicBaseUrl).toString();
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

  router.post("/sign-in", async (request, response, next) => {
    try {
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

      response.redirect(303, "/");
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
