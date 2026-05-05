// abstract: Unit tests for the repository summary web API query adapter.
// out_of_scope: GitHub API behavior and app shell rendering.

import { afterEach, describe, expect, it, vi } from "vitest";

import { repositorySummaryQueryOptions } from "./repositorySummary";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

async function runRepositorySummaryQuery() {
  const queryOptions = repositorySummaryQueryOptions();
  const queryFn = queryOptions.queryFn;

  if (!queryFn) {
    throw new Error(
      "Expected repository summary query options to expose queryFn.",
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

describe("repositorySummaryQueryOptions", () => {
  it("loads repository summary from the BFF", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        repositoryUrl: "https://github.com/QinMian5/hll",
        stars: 12,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runRepositorySummaryQuery();

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/repository-summary",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      repositoryUrl: "https://github.com/QinMian5/hll",
      stars: 12,
    });
  });
});
