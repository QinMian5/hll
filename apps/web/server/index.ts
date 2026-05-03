// abstract: Process entrypoint for the Express web BFF service.
// out_of_scope: Feature route implementation and deployment orchestration.

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { Router } from "express";
import { createServer as createViteServer } from "vite";
import { createQuotaMiddleware } from "./access/quotaMiddleware.js";
import { createRedisQuotaStore } from "./access/quotaStore.js";
import { createApp, type WebAppRuntime } from "./app.js";
import { createLogtoClientFactory } from "./auth/logto.js";
import { createAuthRouter } from "./auth/routes.js";
import { loadWebServerConfig } from "./config.js";
import { createLogtoPersonalAccessTokensClient } from "./dashboard/logtoPersonalAccessTokens.js";
import { createMcpQuotaSummaryClient } from "./dashboard/mcpQuotaSummary.js";
import { createMcpUsageSummaryClient } from "./dashboard/mcpUsageSummary.js";
import { requestServiceAccessToken } from "./dashboard/serviceAccessToken.js";
import { createInternalApiClient } from "./internal-api/client.js";
import { createCardProposalsRouter } from "./routes/cardProposals.js";
import { createCardSuggestedEditsRouter } from "./routes/cardSuggestedEdits.js";
import { createDashboardQuotaRouter } from "./routes/dashboardQuota.js";
import { createDashboardTokensRouter } from "./routes/dashboardTokens.js";
import { createSearchRouter } from "./routes/search.js";
import { createTaxonomyViewRouter } from "./routes/taxonomyView.js";
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
  const internalApi = createInternalApiClient(config);
  const logtoClientFactory = createLogtoClientFactory(config);
  const logtoPersonalAccessTokens = createLogtoPersonalAccessTokensClient({
    accessToken: async () =>
      await requestServiceAccessToken({
        clientId: config.logtoManagementClientId,
        clientSecret: config.logtoManagementClientSecret,
        resource: config.logtoManagementResource,
        scopes: config.logtoManagementScopes,
        tokenUrl: config.logtoManagementTokenUrl,
      }),
    apiBaseUrl: config.logtoManagementApiBaseUrl,
  });
  const mcpUsageSummary = createMcpUsageSummaryClient({
    accessToken: async () =>
      await requestServiceAccessToken({
        clientId: config.mcpUsageSummaryClientId,
        clientSecret: config.mcpUsageSummaryClientSecret,
        resource: config.mcpUsageSummaryResource,
        scopes: config.mcpUsageSummaryScopes,
        tokenUrl: config.mcpUsageSummaryTokenUrl,
      }),
    baseUrl: config.mcpUsageSummaryBaseUrl,
  });
  const mcpQuotaSummary = createMcpQuotaSummaryClient({
    accessToken: async () =>
      await requestServiceAccessToken({
        clientId: config.mcpUsageSummaryClientId,
        clientSecret: config.mcpUsageSummaryClientSecret,
        resource: config.mcpUsageSummaryResource,
        scopes: config.mcpUsageSummaryScopes,
        tokenUrl: config.mcpUsageSummaryTokenUrl,
      }),
    baseUrl: config.mcpUsageSummaryBaseUrl,
  });
  const quotaStore = await createRedisQuotaStore(config);
  const createRouteQuotaMiddleware = (routeGroup: string) =>
    createQuotaMiddleware({
      config,
      getSession: async (request, response) =>
        await logtoClientFactory(request, response).getSession(),
      routeGroup,
      store: quotaStore,
    });
  const webApiRouter = Router();
  webApiRouter.use("/auth", createAuthRouter({ config }));
  webApiRouter.use(
    "/dashboard",
    createDashboardTokensRouter({
      getSession: async (request, response) =>
        await logtoClientFactory(request, response).getSession(),
      logtoClient: logtoPersonalAccessTokens,
      mcpUsageClient: mcpUsageSummary,
      patFingerprintSecret: config.patFingerprintSecret,
      quotaMiddleware: createRouteQuotaMiddleware("dashboard-tokens"),
    }),
  );
  webApiRouter.use(
    "/dashboard",
    createDashboardQuotaRouter({
      getSession: async (request, response) =>
        await logtoClientFactory(request, response).getSession(),
      mcpQuotaClient: mcpQuotaSummary,
      quotaMiddleware: createRouteQuotaMiddleware("dashboard-quota"),
    }),
  );
  webApiRouter.use(
    "/card-proposals",
    createCardProposalsRouter({
      getSession: async (request, response) =>
        await logtoClientFactory(request, response).getSession(),
      internalApi,
    }),
  );
  webApiRouter.use(
    "/cards",
    createCardSuggestedEditsRouter({
      getSession: async (request, response) =>
        await logtoClientFactory(request, response).getSession(),
      internalApi,
    }),
  );
  webApiRouter.use(
    "/search",
    createSearchRouter({
      internalApi,
      quotaMiddleware: createRouteQuotaMiddleware("search"),
    }),
  );
  webApiRouter.use(
    "/taxonomy/view",
    createTaxonomyViewRouter({
      internalApi,
      quotaMiddleware: createRouteQuotaMiddleware("taxonomy-view"),
    }),
  );

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
