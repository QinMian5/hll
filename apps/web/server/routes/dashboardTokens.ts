// abstract: Browser-facing BFF routes for dashboard personal access token lifecycle.
// out_of_scope: Figma dashboard rendering and external dependency implementation details.

import {
  type NextFunction,
  type Request,
  type Response,
  Router,
} from "express";
import { z } from "zod";

import type { WebSessionResponse } from "../auth/sessionState.js";
import {
  DashboardDependencyError,
  DashboardTokenError,
} from "../dashboard/errors.js";
import type { LogtoPersonalAccessToken } from "../dashboard/logtoPersonalAccessTokens.js";
import type { McpUsageSummaryRow } from "../dashboard/mcpUsageSummary.js";
import {
  createPatFingerprint,
  maskTokenValue,
} from "../dashboard/patFingerprint.js";

export interface DashboardLogtoPersonalAccessTokensClient {
  readonly createPersonalAccessToken: (
    userId: string,
    name: string,
  ) => Promise<LogtoPersonalAccessToken>;
  readonly deletePersonalAccessToken: (
    userId: string,
    name: string,
  ) => Promise<void>;
  readonly listPersonalAccessTokens: (
    userId: string,
  ) => Promise<LogtoPersonalAccessToken[]>;
  readonly renamePersonalAccessToken: (
    userId: string,
    currentName: string,
    name: string,
  ) => Promise<LogtoPersonalAccessToken>;
}

export interface DashboardMcpUsageSummaryClient {
  readonly getUsageSummaries: (
    patFingerprints: readonly string[],
  ) => Promise<Map<string, McpUsageSummaryRow>>;
}

export interface CreateDashboardTokensRouterOptions {
  readonly getSession: (
    request: Request,
    response: Response,
  ) => Promise<WebSessionResponse>;
  readonly logtoClient: DashboardLogtoPersonalAccessTokensClient;
  readonly mcpUsageClient: DashboardMcpUsageSummaryClient;
  readonly patFingerprintSecret: string;
  readonly quotaMiddleware?: import("express").RequestHandler;
}

interface TokenRow {
  readonly createdAt: string;
  readonly expiresAt: string | null;
  readonly lastUsedAt: string | null;
  readonly maskedToken: string;
  readonly name: string;
  readonly successfulSearchCount: number | null;
  readonly tokenValue: string;
}

interface TokenRowsResult {
  readonly tokens: TokenRow[];
  readonly usageAvailable: boolean;
}

const TokenNameSchema = z.string().trim().min(1);
const CreateTokenBodySchema = z
  .object({
    name: TokenNameSchema,
  })
  .strict();
const RenameTokenBodySchema = z
  .object({
    currentName: TokenNameSchema,
    name: TokenNameSchema,
  })
  .strict();

async function requireAuthenticatedUser(
  options: CreateDashboardTokensRouterOptions,
  request: Request,
  response: Response,
): Promise<string> {
  const session = await options.getSession(request, response);

  if (session.status === "anonymous") {
    throw new DashboardTokenError(
      401,
      "authentication_required",
      "Authentication is required.",
    );
  }

  return session.user.id;
}

function parseTokenNameBody(body: unknown): string {
  const parsed = CreateTokenBodySchema.safeParse(body);

  if (!parsed.success) {
    throw new DashboardTokenError(
      400,
      "dashboard_invalid_token_name",
      "Token name is required.",
    );
  }

  return parsed.data.name;
}

function parseRenameBody(body: unknown): {
  readonly currentName: string;
  readonly name: string;
} {
  const parsed = RenameTokenBodySchema.safeParse(body);

  if (!parsed.success) {
    throw new DashboardTokenError(
      400,
      "dashboard_invalid_token_name",
      "Token name is required.",
    );
  }

  return parsed.data;
}

function tokenUsage(
  usage: Map<string, McpUsageSummaryRow>,
  fingerprint: string,
  usageAvailable: boolean,
): Pick<TokenRow, "lastUsedAt" | "successfulSearchCount"> {
  if (!usageAvailable) {
    return {
      lastUsedAt: null,
      successfulSearchCount: null,
    };
  }

  const summary = usage.get(fingerprint);

  return {
    lastUsedAt: summary?.lastUsedAt ?? null,
    successfulSearchCount: summary?.successfulSearchCount ?? 0,
  };
}

async function buildTokenRows(
  options: CreateDashboardTokensRouterOptions,
  tokens: readonly LogtoPersonalAccessToken[],
): Promise<TokenRowsResult> {
  const fingerprints = tokens.map((token) =>
    createPatFingerprint(token.value, options.patFingerprintSecret),
  );
  let usage = new Map<string, McpUsageSummaryRow>();
  let usageAvailable = true;

  if (fingerprints.length > 0) {
    try {
      usage = await options.mcpUsageClient.getUsageSummaries(fingerprints);
    } catch {
      usageAvailable = false;
    }
  }

  return {
    tokens: tokens.map((token, index) => ({
      createdAt: token.createdAt,
      expiresAt: token.expiresAt ?? null,
      maskedToken: maskTokenValue(token.value),
      name: token.name,
      tokenValue: token.value,
      ...tokenUsage(usage, fingerprints[index] ?? "", usageAvailable),
    })),
    usageAvailable,
  };
}

function handleDashboardTokenError(
  error: unknown,
  response: Response,
  next: NextFunction,
): void {
  if (error instanceof DashboardTokenError) {
    response.status(error.status).json({
      error: {
        code: error.code,
        message: error.message,
      },
    });
    return;
  }

  if (error instanceof DashboardDependencyError) {
    response.status(error.status).json({
      error: {
        code: error.code,
        message: "Dashboard dependency unavailable.",
      },
    });
    return;
  }

  next(error);
}

export function createDashboardTokensRouter(
  options: CreateDashboardTokensRouterOptions,
): Router {
  const router = Router();

  if (options.quotaMiddleware !== undefined) {
    router.use(options.quotaMiddleware);
  }

  router.get("/tokens", async (request, response, next) => {
    try {
      const userId = await requireAuthenticatedUser(options, request, response);
      const tokens = await options.logtoClient.listPersonalAccessTokens(userId);
      const result = await buildTokenRows(options, tokens);

      response.json(result);
    } catch (error) {
      handleDashboardTokenError(error, response, next);
    }
  });

  router.post("/tokens", async (request, response, next) => {
    try {
      const userId = await requireAuthenticatedUser(options, request, response);
      const name = parseTokenNameBody(request.body);
      const token = await options.logtoClient.createPersonalAccessToken(
        userId,
        name,
      );
      const result = await buildTokenRows(options, [token]);

      response.status(201).json({
        token: result.tokens[0],
        usageAvailable: result.usageAvailable,
      });
    } catch (error) {
      handleDashboardTokenError(error, response, next);
    }
  });

  router.patch("/tokens", async (request, response, next) => {
    try {
      const userId = await requireAuthenticatedUser(options, request, response);
      const { currentName, name } = parseRenameBody(request.body);
      const token = await options.logtoClient.renamePersonalAccessToken(
        userId,
        currentName,
        name,
      );
      const result = await buildTokenRows(options, [token]);

      response.json({
        token: result.tokens[0],
        usageAvailable: result.usageAvailable,
      });
    } catch (error) {
      handleDashboardTokenError(error, response, next);
    }
  });

  router.post("/tokens/delete", async (request, response, next) => {
    try {
      const userId = await requireAuthenticatedUser(options, request, response);
      const name = parseTokenNameBody(request.body);

      await options.logtoClient.deletePersonalAccessToken(userId, name);
      response.status(204).send();
    } catch (error) {
      handleDashboardTokenError(error, response, next);
    }
  });

  return router;
}
