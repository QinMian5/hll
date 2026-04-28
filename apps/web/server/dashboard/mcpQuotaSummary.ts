// abstract: MCP internal quota-summary adapter for dashboard account quota.
// out_of_scope: MCP quota persistence and browser-facing route serialization.

import { z } from "zod";

import { DashboardDependencyError } from "./errors.js";

export class McpQuotaSummaryError extends DashboardDependencyError {
  constructor(message = "MCP quota summary request failed.") {
    super(message, {
      code: "dashboard_quota_summary_unavailable",
    });
    this.name = "McpQuotaSummaryError";
  }
}

const McpQuotaWindowSchema = z
  .object({
    limit: z.number().int().nonnegative(),
    remaining: z.number().int().nonnegative(),
    resetAt: z.string().nullable(),
    startedAt: z.string().nullable(),
    used: z.number().int().nonnegative(),
    windowSeconds: z.number().int().positive(),
  })
  .strict();

const McpQuotaSummaryResponseSchema = z
  .object({
    quota: z
      .object({
        daily: McpQuotaWindowSchema,
        weekly: McpQuotaWindowSchema,
      })
      .strict(),
  })
  .strict();

export type McpQuotaWindow = z.infer<typeof McpQuotaWindowSchema>;
export type McpQuotaSummaryResponse = z.infer<
  typeof McpQuotaSummaryResponseSchema
>;

export interface McpQuotaSummaryClient {
  readonly getQuotaSummary: (
    userSub: string,
  ) => Promise<McpQuotaSummaryResponse>;
}

export interface McpQuotaSummaryClientOptions {
  readonly accessToken: () => Promise<string>;
  readonly baseUrl: string;
  readonly fetch?: typeof fetch;
}

function joinMcpUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;

  return new URL(normalizedPath, normalizedBaseUrl).toString();
}

export function createMcpQuotaSummaryClient(
  options: McpQuotaSummaryClientOptions,
): McpQuotaSummaryClient {
  return {
    getQuotaSummary: async (userSub) => {
      const token = await options.accessToken();
      const fetchMcp = options.fetch ?? fetch;
      const response = await fetchMcp(
        joinMcpUrl(options.baseUrl, "/internal/dashboard/quota-summary"),
        {
          body: JSON.stringify({ userSub }),
          headers: {
            authorization: `Bearer ${token}`,
            "content-type": "application/json",
          },
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new McpQuotaSummaryError();
      }

      const parsed = McpQuotaSummaryResponseSchema.safeParse(
        await response.json(),
      );

      if (!parsed.success) {
        throw new McpQuotaSummaryError(
          "MCP quota summary response did not include valid quota windows.",
        );
      }

      return parsed.data;
    },
  };
}
