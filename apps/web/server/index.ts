// abstract: Process entrypoint for the Express web BFF service.
// out_of_scope: Feature route implementation and deployment orchestration.

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { Router } from "express";
import { createServer as createViteServer } from "vite";

import { createApp, type WebAppRuntime } from "./app.js";
import { createAuthRouter } from "./auth/routes.js";
import { loadWebServerConfig } from "./config.js";
import { createRedisSessionMiddleware } from "./session/redisSessionStore.js";
import { loadProductionRuntime } from "./staticAssets.js";

async function createRuntime(): Promise<WebAppRuntime> {
  if (process.env.NODE_ENV === "production") {
    return await loadProductionRuntime();
  }

  const vite = await createViteServer({
    appType: "custom",
    server: { middlewareMode: true },
  });

  return {
    kind: "development",
    renderIndexHtml: async (url) => {
      const template = await readFile(
        resolve(process.cwd(), "index.html"),
        "utf-8",
      );
      return await vite.transformIndexHtml(url, template);
    },
    viteMiddlewares: vite.middlewares,
  };
}

async function main(): Promise<void> {
  const config = loadWebServerConfig();
  const runtime = await createRuntime();
  const webApiRouter = Router();
  webApiRouter.use("/auth", createAuthRouter({ config }));

  const app = await createApp({
    config,
    runtime,
    sessionMiddleware: await createRedisSessionMiddleware(config),
    webApiRouter,
  });

  const server = app.listen(config.port, config.host, () => {
    console.info(`web BFF listening on ${config.host}:${config.port}`);
  });

  const close = () => {
    server.close((error) => {
      if (error) {
        console.error(error);
        process.exit(1);
      }

      process.exit(0);
    });
  };

  process.on("SIGINT", close);
  process.on("SIGTERM", close);
}

await main();
