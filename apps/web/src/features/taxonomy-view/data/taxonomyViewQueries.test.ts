// abstract: Unit tests for taxonomy query adapters and contract normalization.
// out_of_scope: React Flow rendering and page-level interaction behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  type TaxonomyCardScopeLayoutSliceResponse,
  taxonomyCardScopeLayoutSliceQueryOptions,
  taxonomyCardScopeNodeDetailsQueryOptions,
  taxonomyCardScopeNodeTitlesQueryOptions,
  taxonomyNodeViewByPathQueryOptions,
  taxonomyNodeViewQueryOptions,
  taxonomyRootViewQueryOptions,
} from "./taxonomyViewQueries";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

async function runQuery<TResult>(
  queryOptions: ReturnType<
    | typeof taxonomyCardScopeNodeDetailsQueryOptions
    | typeof taxonomyCardScopeLayoutSliceQueryOptions
    | typeof taxonomyCardScopeNodeTitlesQueryOptions
    | typeof taxonomyNodeViewByPathQueryOptions
    | typeof taxonomyNodeViewQueryOptions
    | typeof taxonomyRootViewQueryOptions
  >,
): Promise<TResult> {
  const queryFn = queryOptions.queryFn;

  if (!queryFn) {
    throw new Error("Expected taxonomy query options to expose a queryFn.");
  }

  return (await queryFn({
    client: undefined,
    meta: undefined,
    queryKey: queryOptions.queryKey,
    signal: new AbortController().signal,
  } as never)) as TResult;
}

const cardScopeLayoutIdentity = {
  generatedAt: "2026-04-29T00:00:00Z",
  layoutVersion: "taxonomy-card-scope-layout-v1",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("taxonomyNodeViewQueryOptions", () => {
  it("calls the same-origin BFF taxonomy root endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        root_node_id: 1,
        title: "Science",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(taxonomyRootViewQueryOptions());

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/root",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      root_node_id: 1,
      title: "Science",
    });
  });

  it("calls the same-origin BFF taxonomy node endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        edges: [],
        node_id: 42,
        node_kind: "branch",
        nodes: [],
        title: "Physics",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(taxonomyNodeViewQueryOptions(42));

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/nodes/42",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toMatchObject({
      node_id: 42,
      title: "Physics",
    });
  });

  it("calls the same-origin BFF taxonomy path endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        current_scope: {
          depth: 1,
          name: "Mathematics",
          parent_taxonomy_node_id: 1,
          route_path: "science/mathematics",
          route_slug: "mathematics",
          scope_kind: "taxonomy_node",
          taxonomy_node_id: 42,
        },
        node_kind: "branch",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(
      taxonomyNodeViewByPathQueryOptions("science/mathematics"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/path/science/mathematics",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toMatchObject({
      current_scope: {
        route_path: "science/mathematics",
      },
      node_kind: "branch",
    });
  });

  it("calls the same-origin BFF card-scope detail endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        nodes: [
          {
            content: "Card content",
            current_version: 4,
            id: 10,
            title: "Card",
          },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(
      taxonomyCardScopeNodeDetailsQueryOptions("science/mathematics", [11, 10]),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/card-scopes/details",
      expect.objectContaining({
        body: JSON.stringify({
          node_ids: [10, 11],
          route_path: "science/mathematics",
        }),
        credentials: "include",
        method: "POST",
      }),
    );
    expect(result).toEqual({
      nodes: [
        { content: "Card content", current_version: 4, id: 10, title: "Card" },
      ],
    });
  });

  it("calls the same-origin BFF card-scope layout endpoint with viewport bounds", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        edges: [[10, 11, 0.8]],
        layout_version: "taxonomy-card-scope-layout-v1",
        nodes: [
          { id: 10, scope: "inner", x: 1.5, y: 2.5 },
          { id: 11, scope: "outer", x: 3.5, y: 4.5 },
        ],
        route_path: "science/mathematics",
        scope_kind: "taxonomy_node",
        taxonomy_node_id: 59,
        requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery<TaxonomyCardScopeLayoutSliceResponse>(
      taxonomyCardScopeLayoutSliceQueryOptions(
        "science/mathematics",
        {
          max_x: 100,
          max_y: 200,
          min_x: -100,
          min_y: -200,
        },
        cardScopeLayoutIdentity,
      ),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/card-scopes/layout?max_x=100&max_y=200&min_x=-100&min_y=-200&route_path=science%2Fmathematics",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      edges: [[10, 11, 0.8]],
      layout_version: "taxonomy-card-scope-layout-v1",
      nodes: [
        { id: 10, scope: "inner", x: 1.5, y: 2.5 },
        { id: 11, scope: "outer", x: 3.5, y: 4.5 },
      ],
      route_path: "science/mathematics",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 59,
      requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
    });
  });

  it("keeps previous card-scope layout data while fetching a new viewport tile", () => {
    const options = taxonomyCardScopeLayoutSliceQueryOptions(
      "science/mathematics",
      {
        max_x: 100,
        max_y: 200,
        min_x: -100,
        min_y: -200,
      },
      cardScopeLayoutIdentity,
    );
    const previous: TaxonomyCardScopeLayoutSliceResponse = {
      edges: [[10, 11, 0.8]],
      layout_version: "taxonomy-card-scope-layout-v1",
      nodes: [{ id: 10, scope: "inner", x: 1.5, y: 2.5 }],
      route_path: "math/algebra",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 59,
      requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
    };
    const placeholderData = options.placeholderData;

    expect(options.queryKey).toEqual([
      "taxonomy-view",
      "card-scope-layout",
      "science/mathematics",
      "taxonomy-card-scope-layout-v1",
      "2026-04-29T00:00:00Z",
      -100,
      -200,
      100,
      200,
    ]);
    expect(options.staleTime).toBe(5 * 60 * 1000);
    expect(options.gcTime).toBe(30 * 60 * 1000);
    expect(typeof placeholderData).toBe("function");
    if (typeof placeholderData !== "function") {
      throw new Error(
        "Expected card-scope layout placeholder data to be a function.",
      );
    }
    expect(placeholderData(previous as never, undefined as never)).toBe(
      previous,
    );
  });

  it("keeps layout slices distinct when backend layout identity changes", () => {
    const first = taxonomyCardScopeLayoutSliceQueryOptions(
      "science/mathematics",
      {
        max_x: 100,
        max_y: 200,
        min_x: -100,
        min_y: -200,
      },
      cardScopeLayoutIdentity,
    );
    const second = taxonomyCardScopeLayoutSliceQueryOptions(
      "science/mathematics",
      {
        max_x: 100,
        max_y: 200,
        min_x: -100,
        min_y: -200,
      },
      {
        generatedAt: "2026-04-29T00:05:00Z",
        layoutVersion: "taxonomy-card-scope-layout-v1",
      },
    );

    expect(first.queryKey).not.toEqual(second.queryKey);
  });

  it("calls the same-origin BFF card-scope title endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        nodes: [{ id: 10, title: "Card" }],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(
      taxonomyCardScopeNodeTitlesQueryOptions("science/mathematics", [11, 10]),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/card-scopes/titles",
      expect.objectContaining({
        body: JSON.stringify({
          node_ids: [10, 11],
          route_path: "science/mathematics",
        }),
        credentials: "include",
        method: "POST",
      }),
    );
    expect(result).toEqual({
      nodes: [{ id: 10, title: "Card" }],
    });
  });

  it("normalizes card-scope layout edge tuples from the generated client payload", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        edges: [
          [10, 11, 0.8],
          [11, 12, 0.6],
        ],
        layout_version: "taxonomy-card-scope-layout-v1",
        nodes: [
          { id: 10, scope: "inner", x: 1.5, y: 2.5 },
          { id: 11, scope: "outer", x: 3.5, y: 4.5 },
          { id: 12, scope: "outer", x: 5.5, y: 6.5 },
        ],
        route_path: "science/mathematics",
        scope_kind: "taxonomy_node",
        taxonomy_node_id: 59,
        requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery<TaxonomyCardScopeLayoutSliceResponse>(
      taxonomyCardScopeLayoutSliceQueryOptions(
        "science/mathematics",
        {
          max_x: 100,
          max_y: 200,
          min_x: -100,
          min_y: -200,
        },
        cardScopeLayoutIdentity,
      ),
    );

    expect(result.edges).toEqual([
      [10, 11, 0.8],
      [11, 12, 0.6],
    ]);
  });

  it("rejects malformed card-scope layout edge payloads", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        edges: [[10, 11]],
        layout_version: "taxonomy-card-scope-layout-v1",
        nodes: [{ id: 10, scope: "inner", x: 1.5, y: 2.5 }],
        route_path: "science/mathematics",
        scope_kind: "taxonomy_node",
        taxonomy_node_id: 59,
        requested_bounds: { max_x: 100, max_y: 200, min_x: -100, min_y: -200 },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      runQuery(
        taxonomyCardScopeLayoutSliceQueryOptions(
          "science/mathematics",
          {
            max_x: 100,
            max_y: 200,
            min_x: -100,
            min_y: -200,
          },
          cardScopeLayoutIdentity,
        ),
      ),
    ).rejects.toThrow(
      "Taxonomy card-scope edge payload must contain 3 numeric values.",
    );
  });
});
