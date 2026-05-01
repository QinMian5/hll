// abstract: Logto Management API adapter for user personal access tokens.
// out_of_scope: Browser route authorization and MCP usage aggregation.

import { z } from "zod";

import { DashboardDependencyError, DashboardTokenError } from "./errors.js";

export class LogtoPersonalAccessTokenError extends DashboardTokenError {
  constructor(status: number, code: string, message: string) {
    super(status, code, message);
    this.name = "LogtoPersonalAccessTokenError";
  }
}

const LogtoTimestampSchema = z.union([
  z.string().min(1),
  z.number().transform((value) => new Date(value).toISOString()),
]);

const LogtoPersonalAccessTokenSchema = z
  .object({
    createdAt: LogtoTimestampSchema,
    expiresAt: LogtoTimestampSchema.nullable(),
    name: z.string().min(1),
    value: z.string().min(1),
  })
  .strip();

const LogtoPersonalAccessTokenListSchema = z.array(
  LogtoPersonalAccessTokenSchema,
);

export type LogtoPersonalAccessToken = z.infer<
  typeof LogtoPersonalAccessTokenSchema
>;

export interface LogtoPersonalAccessTokensClient {
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

export interface LogtoPersonalAccessTokensClientOptions {
  readonly accessToken: () => Promise<string>;
  readonly apiBaseUrl: string;
  readonly fetch?: typeof fetch;
}

interface LogtoErrorPayload {
  readonly code?: unknown;
}

function joinLogtoApiUrl(apiBaseUrl: string, path: string): string {
  const baseUrl = apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;

  return new URL(path, baseUrl).toString();
}

function userPatPath(userId: string): string {
  return `users/${encodeURIComponent(userId)}/personal-access-tokens`;
}

function userPatNamePath(userId: string, name: string): string {
  return `${userPatPath(userId)}/${encodeURIComponent(name)}`;
}

async function readJson(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  return await response.json();
}

async function readLogtoErrorPayload(
  response: Response,
): Promise<LogtoErrorPayload | undefined> {
  try {
    return (await response.json()) as LogtoErrorPayload;
  } catch {
    return undefined;
  }
}

async function mapLogtoError(response: Response): Promise<never> {
  const payload = await readLogtoErrorPayload(response);
  const code = typeof payload?.code === "string" ? payload.code : null;

  if (
    response.status === 422 &&
    code === "user.personal_access_token_name_exists"
  ) {
    throw new LogtoPersonalAccessTokenError(
      409,
      "dashboard_token_name_conflict",
      "Token name already exists.",
    );
  }

  if (response.status === 400) {
    throw new LogtoPersonalAccessTokenError(
      400,
      "dashboard_invalid_token_name",
      "Token name is invalid.",
    );
  }

  if (response.status === 404) {
    throw new LogtoPersonalAccessTokenError(
      404,
      "dashboard_token_not_found",
      "Token was not found.",
    );
  }

  if (response.status === 409) {
    throw new LogtoPersonalAccessTokenError(
      409,
      "dashboard_token_name_conflict",
      "Token name already exists.",
    );
  }

  throw new DashboardDependencyError("Logto Management API request failed.", {
    code: "dashboard_token_dependency_unavailable",
    upstreamStatus: response.status,
  });
}

function parseTokenResponse(payload: unknown): LogtoPersonalAccessToken {
  const parsed = LogtoPersonalAccessTokenSchema.safeParse(payload);

  if (!parsed.success) {
    throw new DashboardDependencyError(
      "Logto Management API response did not include a valid token.",
      { code: "dashboard_token_dependency_unavailable" },
    );
  }

  return parsed.data;
}

function parseTokenListResponse(payload: unknown): LogtoPersonalAccessToken[] {
  const parsed = LogtoPersonalAccessTokenListSchema.safeParse(payload);

  if (!parsed.success) {
    throw new DashboardDependencyError(
      "Logto Management API response did not include a valid token list.",
      { code: "dashboard_token_dependency_unavailable" },
    );
  }

  return parsed.data;
}

async function authorizedFetch(
  options: LogtoPersonalAccessTokensClientOptions,
  path: string,
  init: RequestInit,
): Promise<Response> {
  const token = await options.accessToken();
  const fetchLogto = options.fetch ?? fetch;
  const headers = {
    authorization: `Bearer ${token}`,
    ...init.headers,
  };

  return await fetchLogto(joinLogtoApiUrl(options.apiBaseUrl, path), {
    ...init,
    headers,
  });
}

export function createLogtoPersonalAccessTokensClient(
  options: LogtoPersonalAccessTokensClientOptions,
): LogtoPersonalAccessTokensClient {
  return {
    createPersonalAccessToken: async (userId, name) => {
      const response = await authorizedFetch(options, userPatPath(userId), {
        body: JSON.stringify({ name }),
        headers: {
          "content-type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        await mapLogtoError(response);
      }

      return parseTokenResponse(await readJson(response));
    },
    deletePersonalAccessToken: async (userId, name) => {
      const response = await authorizedFetch(
        options,
        userPatNamePath(userId, name),
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        await mapLogtoError(response);
      }
    },
    listPersonalAccessTokens: async (userId) => {
      const response = await authorizedFetch(options, userPatPath(userId), {
        method: "GET",
      });

      if (!response.ok) {
        await mapLogtoError(response);
      }

      return parseTokenListResponse(await readJson(response));
    },
    renamePersonalAccessToken: async (userId, currentName, name) => {
      const response = await authorizedFetch(options, userPatPath(userId), {
        body: JSON.stringify({ currentName, name }),
        headers: {
          "content-type": "application/json",
        },
        method: "PATCH",
      });

      if (!response.ok) {
        await mapLogtoError(response);
      }

      return parseTokenResponse(await readJson(response));
    },
  };
}
