// abstract: MCP internal usage-summary adapter for dashboard token rows.
// out_of_scope: MCP event aggregation and Logto token lifecycle operations.

import { z } from "zod";

import { DashboardDependencyError } from "./errors.js";

export class McpUsageSummaryError extends DashboardDependencyError {
  constructor(message = "MCP usage summary request failed.") {
    super(message, {
      code: "dashboard_usage_summary_unavailable",
    });
    this.name = "McpUsageSummaryError";
  }
}

const McpUsageSummaryRowSchema = z
  .object({
    lastUsedAt: z.string().nullable(),
    patFingerprint: z.string().min(1),
    successfulSearchCount: z.number().int().nonnegative(),
  })
  .strict();

const McpUsageSummaryResponseSchema = z
  .object({
    summaries: z.array(McpUsageSummaryRowSchema),
  })
  .strict();

export type McpUsageSummaryRow = z.infer<typeof McpUsageSummaryRowSchema>;

export interface McpUsageSummaryClient {
  readonly getUsageSummaries: (
    patFingerprints: readonly string[],
  ) => Promise<Map<string, McpUsageSummaryRow>>;
}

export interface McpUsageSummaryClientOptions {
  readonly accessToken: () => Promise<string>;
  readonly baseUrl: string;
  readonly fetch?: typeof fetch;
}

function joinMcpUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;

  return new URL(normalizedPath, normalizedBaseUrl).toString();
}

export function createMcpUsageSummaryClient(
  options: McpUsageSummaryClientOptions,
): McpUsageSummaryClient {
  return {
    getUsageSummaries: async (patFingerprints) => {
      const token = await options.accessToken();
      const fetchMcp = options.fetch ?? fetch;
      const response = await fetchMcp(
        joinMcpUrl(options.baseUrl, "/internal/dashboard/usage-summary"),
        {
          body: JSON.stringify({ patFingerprints: [...patFingerprints] }),
          headers: {
            authorization: `Bearer ${token}`,
            "content-type": "application/json",
          },
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new McpUsageSummaryError();
      }

      const parsed = McpUsageSummaryResponseSchema.safeParse(
        await response.json(),
      );

      if (!parsed.success) {
        throw new McpUsageSummaryError(
          "MCP usage summary response did not include valid summaries.",
        );
      }

      return new Map(
        parsed.data.summaries.map((summary) => [
          summary.patFingerprint,
          summary,
        ]),
      );
    },
  };
}
