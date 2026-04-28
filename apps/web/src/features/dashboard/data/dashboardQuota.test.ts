// abstract: Unit tests for dashboard quota query adapters.
// out_of_scope: Dashboard quota rendering and MCP server behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import { dashboardQuotaQueryOptions } from "./dashboardQuota";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

async function runDashboardQuotaQuery() {
  const queryOptions = dashboardQuotaQueryOptions();
  const queryFn = queryOptions.queryFn;

  if (!queryFn) {
    throw new Error(
      "Expected dashboard quota query options to expose queryFn.",
    );
  }

  return await queryFn({
    client: undefined,
    meta: undefined,
    queryKey: queryOptions.queryKey,
    signal: new AbortController().signal,
  } as never);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboardQuotaQueryOptions", () => {
  it("loads Daily and Weekly quota from the dashboard BFF", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        quota: {
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
        },
        quotaAvailable: true,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runDashboardQuotaQuery();

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/quota",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      quota: {
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
      },
      quotaAvailable: true,
    });
  });
});
