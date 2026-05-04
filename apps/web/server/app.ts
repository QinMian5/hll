// abstract: Express application assembly for the web BFF runtime.
// out_of_scope: Auth policy, quota policy, and backend route forwarding implementations.

import cookieParser from "cookie-parser";
import express, {
  type Express,
  type RequestHandler,
  type Router,
} from "express";

import { injectBrowserRuntimeConfig } from "./browserRuntimeConfig.js";
import type { WebServerConfig } from "./config.js";

export interface ProductionRuntime {
  readonly clientRoot?: string;
  readonly indexHtml: string;
  readonly kind: "production";
}

export interface DevelopmentRuntime {
  readonly kind: "development";
  readonly renderIndexHtml: (url: string) => Promise<string>;
  readonly viteMiddlewares: RequestHandler;
}

export type WebAppRuntime = DevelopmentRuntime | ProductionRuntime;

export interface CreateAppOptions {
  readonly config: WebServerConfig;
  readonly runtime: WebAppRuntime;
  readonly sessionMiddleware?: RequestHandler;
  readonly webApiRouter?: Router;
}

export async function createApp(options: CreateAppOptions): Promise<Express> {
  const app = express();
  const { runtime } = options;

  app.disable("x-powered-by");
  app.set("trust proxy", options.config.trustProxy);
  app.use(express.json({ limit: "1mb" }));
  app.use(express.urlencoded({ extended: false, limit: "16kb" }));
  app.use(cookieParser());

  if (options.sessionMiddleware !== undefined) {
    app.use(options.sessionMiddleware);
  }

  if (options.webApiRouter !== undefined) {
    app.use("/web-api", options.webApiRouter);
  }

  app.use("/web-api", (_request, response) => {
    response.status(404).json({
      error: {
        code: "web_api_route_not_found",
        message: "Web API route not found.",
      },
    });
  });

  if (runtime.kind === "production") {
    if (runtime.clientRoot !== undefined) {
      app.use(express.static(runtime.clientRoot, { index: false }));
    }

    app.use((request, response, next) => {
      if (request.method !== "GET" && request.method !== "HEAD") {
        next();
        return;
      }

      const html = injectBrowserRuntimeConfig(
        runtime.indexHtml,
        options.config,
      );
      response.type("html").send(html);
    });

    return app;
  }

  app.use(runtime.viteMiddlewares);
  app.use(async (request, response, next) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
      next();
      return;
    }

    try {
      const html = injectBrowserRuntimeConfig(
        await runtime.renderIndexHtml(request.originalUrl),
        options.config,
      );
      response.type("html").send(html);
    } catch (error) {
      next(error);
    }
  });

  return app;
}
