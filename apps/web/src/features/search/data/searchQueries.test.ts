// abstract: Unit tests for browser search query adapters.
// out_of_scope: Search page rendering and backend ranking behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import { searchQueryOptions } from "./searchQueries";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

async function runSearchQuery(query: string) {
  const queryOptions = searchQueryOptions(query);
  const queryFn = queryOptions.queryFn;

  if (!queryFn) {
    throw new Error("Expected search query options to expose a queryFn.");
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

describe("searchQueryOptions", () => {
  it("calls the same-origin BFF search endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        connected_titles: ["Physics"],
        matched_cards: [{ content: "Energy content", title: "Energy" }],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runSearchQuery("energy");

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/search?query=energy",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      connected_titles: ["Physics"],
      matched_cards: [{ content: "Energy content", title: "Energy" }],
    });
  });
});
