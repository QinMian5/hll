// abstract: Contract tests for the MCP internal usage summary adapter.
// out_of_scope: MCP event aggregation and browser-facing route response shape.
// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  createMcpUsageSummaryClient,
  type McpUsageSummaryError,
} from "./mcpUsageSummary.js";

const PAT_FINGERPRINT =
  "pat_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

function createClient(fetchMcp: typeof fetch) {
  return createMcpUsageSummaryClient({
    accessToken: async () => "usage-token",
    baseUrl: "https://mcp.example",
    fetch: fetchMcp,
  });
}

describe("MCP usage summary client", () => {
  it("requests successful search usage summaries by PAT fingerprint", async () => {
    const fetchMcp = vi.fn(async () => {
      return Response.json({
        summaries: [
          {
            lastUsedAt: "2026-04-28T10:00:00.000Z",
            patFingerprint: PAT_FINGERPRINT,
            successfulSearchCount: 12,
          },
        ],
      });
    });
    const client = createClient(fetchMcp);

    await expect(client.getUsageSummaries([PAT_FINGERPRINT])).resolves.toEqual(
      new Map([
        [
          PAT_FINGERPRINT,
          {
            lastUsedAt: "2026-04-28T10:00:00.000Z",
            patFingerprint: PAT_FINGERPRINT,
            successfulSearchCount: 12,
          },
        ],
      ]),
    );

    expect(fetchMcp).toHaveBeenCalledWith(
      "https://mcp.example/internal/dashboard/usage-summary",
      {
        body: JSON.stringify({ patFingerprints: [PAT_FINGERPRINT] }),
        headers: {
          authorization: "Bearer usage-token",
          "content-type": "application/json",
        },
        method: "POST",
      },
    );
  });

  it("maps MCP failures to a typed adapter error", async () => {
    const fetchMcp = vi.fn(async () => {
      return Response.json({ error: "forbidden" }, { status: 403 });
    });
    const client = createClient(fetchMcp);

    await expect(
      client.getUsageSummaries([PAT_FINGERPRINT]),
    ).rejects.toMatchObject({
      code: "dashboard_usage_summary_unavailable",
      name: "McpUsageSummaryError",
      status: 502,
    } satisfies Partial<McpUsageSummaryError>);
  });
});
