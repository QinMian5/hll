// abstract: Unit tests for dashboard token query and mutation adapters.
// out_of_scope: Token directory rendering and Logto/MCP server behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createDashboardToken,
  dashboardTokensQueryOptions,
  deleteDashboardToken,
  renameDashboardToken,
} from "./dashboardTokens";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

async function runDashboardTokensQuery() {
  const queryOptions = dashboardTokensQueryOptions();
  const queryFn = queryOptions.queryFn;

  if (!queryFn) {
    throw new Error(
      "Expected dashboard token query options to expose queryFn.",
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

describe("dashboardTokensQueryOptions", () => {
  it("loads token rows from the dashboard BFF and normalizes usage counts", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        tokens: [
          {
            createdAt: "2026-04-28T10:00:00.000Z",
            expiresAt: null,
            lastUsedAt: "2026-04-28T11:00:00.000Z",
            maskedToken: "kn_pat_...alpha",
            name: "Research MCP",
            successfulSearchCount: 12400,
            tokenValue: "kn_pat_clear_alpha",
          },
        ],
        usageAvailable: true,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runDashboardTokensQuery();

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/tokens",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      tokens: [
        {
          createdAt: "2026-04-28T10:00:00.000Z",
          expiresAt: null,
          lastUsedAt: "2026-04-28T11:00:00.000Z",
          maskedToken: "kn_pat_...alpha",
          name: "Research MCP",
          tokenValue: "kn_pat_clear_alpha",
          usageCount: 12400,
        },
      ],
      usageAvailable: true,
    });
  });
});

describe("dashboard token mutations", () => {
  it("creates tokens through the BFF lifecycle endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        {
          token: {
            createdAt: "2026-04-28T10:00:00.000Z",
            expiresAt: null,
            lastUsedAt: null,
            maskedToken: "kn_pat_...beta",
            name: "Research Lab",
            successfulSearchCount: 0,
            tokenValue: "kn_pat_clear_beta",
          },
          usageAvailable: true,
        },
        201,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createDashboardToken({ name: "Research Lab" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/tokens",
      expect.objectContaining({
        body: JSON.stringify({ name: "Research Lab" }),
        method: "POST",
      }),
    );
    expect(result.token.usageCount).toBe(0);
    expect(result.token.tokenValue).toBe("kn_pat_clear_beta");
  });

  it("renames tokens with PATCH and the Logto-compatible current name", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        token: {
          createdAt: "2026-04-28T10:00:00.000Z",
          expiresAt: null,
          lastUsedAt: null,
          maskedToken: "kn_pat_...alpha",
          name: "Research API",
          successfulSearchCount: 18,
          tokenValue: "kn_pat_clear_alpha",
        },
        usageAvailable: true,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await renameDashboardToken({
      currentName: "Research MCP",
      name: "Research API",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/tokens",
      expect.objectContaining({
        body: JSON.stringify({
          currentName: "Research MCP",
          name: "Research API",
        }),
        method: "PATCH",
      }),
    );
  });

  it("deletes tokens through the BFF lifecycle endpoint", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await deleteDashboardToken({ name: "Research MCP" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/tokens/delete",
      expect.objectContaining({
        body: JSON.stringify({ name: "Research MCP" }),
        method: "POST",
      }),
    );
  });
});
