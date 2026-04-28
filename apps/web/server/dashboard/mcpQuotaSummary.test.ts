// abstract: Contract tests for the MCP internal quota summary adapter.
// out_of_scope: MCP quota persistence and browser-facing route response shape.
// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  createMcpQuotaSummaryClient,
  type McpQuotaSummaryError,
} from "./mcpQuotaSummary.js";

function createClient(fetchMcp: typeof fetch) {
  return createMcpQuotaSummaryClient({
    accessToken: async () => "quota-token",
    baseUrl: "https://mcp.example",
    fetch: fetchMcp,
  });
}

describe("MCP quota summary client", () => {
  it("requests Daily and Weekly account quota by user subject", async () => {
    const quota = {
      daily: {
        limit: 1000,
        remaining: 963,
        resetAt: "2026-04-29T10:00:00.000Z",
        startedAt: "2026-04-28T10:00:00.000Z",
        used: 37,
        windowSeconds: 86_400,
      },
      weekly: {
        limit: 5000,
        remaining: 4816,
        resetAt: "2026-05-05T10:00:00.000Z",
        startedAt: "2026-04-28T10:00:00.000Z",
        used: 184,
        windowSeconds: 604_800,
      },
    };
    const fetchMcp = vi.fn(async () => {
      return Response.json({ quota });
    });
    const client = createClient(fetchMcp);

    await expect(client.getQuotaSummary("user-1")).resolves.toEqual({
      quota,
    });

    expect(fetchMcp).toHaveBeenCalledWith(
      "https://mcp.example/internal/dashboard/quota-summary",
      {
        body: JSON.stringify({ userSub: "user-1" }),
        headers: {
          authorization: "Bearer quota-token",
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

    await expect(client.getQuotaSummary("user-1")).rejects.toMatchObject({
      code: "dashboard_quota_summary_unavailable",
      name: "McpQuotaSummaryError",
      status: 502,
    } satisfies Partial<McpQuotaSummaryError>);
  });
});
