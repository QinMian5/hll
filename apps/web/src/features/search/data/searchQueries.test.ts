// abstract: Unit tests for browser search query adapters.
// out_of_scope: Search page rendering and backend ranking behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import { createSuggestedEdit, searchQueryOptions } from "./searchQueries";

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
        matched_cards: [
          {
            content: "Energy content",
            current_version: 1,
            node_id: 10,
            title: "Energy",
          },
        ],
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
      matched_cards: [
        {
          content: "Energy content",
          current_version: 1,
          node_id: 10,
          title: "Energy",
        },
      ],
    });
  });
});

describe("createSuggestedEdit", () => {
  it("posts the browser-safe suggestion payload without user identity", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        base_version: 2,
        created_at: "2026-04-28T18:00:00Z",
        id: 99,
        node_id: 10,
        status: "pending",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await createSuggestedEdit({
      baseVersion: 2,
      nodeId: 10,
      suggestedContent: "Better content",
      suggestedTitle: "Better title",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/cards/10/suggested-edits",
      expect.objectContaining({
        body: JSON.stringify({
          base_version: 2,
          suggested_content: "Better content",
          suggested_title: "Better title",
        }),
        credentials: "include",
        method: "POST",
      }),
    );
    expect(result.status).toBe("pending");
  });
});
