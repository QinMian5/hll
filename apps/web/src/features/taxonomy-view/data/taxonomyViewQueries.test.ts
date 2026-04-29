// abstract: Unit tests for taxonomy query adapters and contract normalization.
// out_of_scope: React Flow rendering and page-level interaction behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  type TaxonomyNodeView,
  taxonomyLeafNodeDetailsQueryOptions,
  taxonomyLeafNodeTitlesQueryOptions,
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
    | typeof taxonomyLeafNodeDetailsQueryOptions
    | typeof taxonomyLeafNodeTitlesQueryOptions
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

  it("calls the same-origin BFF leaf detail endpoint", async () => {
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
      taxonomyLeafNodeDetailsQueryOptions(59, [11, 10]),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/leaves/59/details",
      expect.objectContaining({
        body: JSON.stringify({ node_ids: [10, 11] }),
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

  it("calls the same-origin BFF leaf title endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        nodes: [{ id: 10, title: "Card" }],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery(
      taxonomyLeafNodeTitlesQueryOptions(59, [11, 10]),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/taxonomy/view/leaves/59/titles",
      expect.objectContaining({
        body: JSON.stringify({ node_ids: [10, 11] }),
        credentials: "include",
        method: "POST",
      }),
    );
    expect(result).toEqual({
      nodes: [{ id: 10, title: "Card" }],
    });
  });

  it("normalizes leaf edge tuples from the generated client payload", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        breadcrumb: [],
        current_node: {
          depth: 2,
          id: 59,
          is_leaf: true,
          name: "Leaf 59",
          parent_id: 11,
        },
        edges: [
          [10, 11, 0.8],
          [11, 12, 0.6],
        ],
        node_kind: "leaf",
        nodes: [
          { id: 10, scope: "inner" },
          { id: 11, scope: "outer" },
          { id: 12, scope: "outer" },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await runQuery<TaxonomyNodeView>(
      taxonomyNodeViewQueryOptions(59),
    );

    expect(result.node_kind).toBe("leaf");
    if (result.node_kind !== "leaf") {
      throw new Error("Expected a leaf taxonomy node view.");
    }

    expect(result.edges).toEqual([
      [10, 11, 0.8],
      [11, 12, 0.6],
    ]);
  });

  it("rejects malformed leaf edge payloads", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        breadcrumb: [],
        current_node: {
          depth: 2,
          id: 59,
          is_leaf: true,
          name: "Leaf 59",
          parent_id: 11,
        },
        edges: [[10, 11]],
        node_kind: "leaf",
        nodes: [{ id: 10, scope: "inner" }],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(runQuery(taxonomyNodeViewQueryOptions(59))).rejects.toThrow(
      "Taxonomy leaf edge payload must contain 3 numeric values.",
    );
  });
});
