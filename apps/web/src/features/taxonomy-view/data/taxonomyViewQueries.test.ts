// abstract: Unit tests for taxonomy query adapters and contract normalization.
// out_of_scope: React Flow rendering and page-level interaction behavior.

import { describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();

vi.mock("../../../shared/api/contractsClient", () => ({
  getContractsClient: () => ({
    GET: mockGet,
    POST: vi.fn(),
  }),
}));

import { taxonomyNodeViewQueryOptions } from "./taxonomyViewQueries";

describe("taxonomyNodeViewQueryOptions", () => {
  it("normalizes leaf edge tuples from the generated client payload", async () => {
    mockGet.mockResolvedValueOnce({
      data: {
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
      },
      response: { ok: true, status: 200 },
    });

    const queryOptions = taxonomyNodeViewQueryOptions(59);
    const queryFn = queryOptions.queryFn;

    if (!queryFn) {
      throw new Error(
        "Expected taxonomy node query options to expose a queryFn.",
      );
    }

    const result = await queryFn({
      client: undefined,
      meta: undefined,
      queryKey: queryOptions.queryKey,
      signal: new AbortController().signal,
    } as never);

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
    mockGet.mockResolvedValueOnce({
      data: {
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
      },
      response: { ok: true, status: 200 },
    });

    const queryOptions = taxonomyNodeViewQueryOptions(59);
    const queryFn = queryOptions.queryFn;

    if (!queryFn) {
      throw new Error(
        "Expected taxonomy node query options to expose a queryFn.",
      );
    }

    await expect(
      queryFn({
        client: undefined,
        meta: undefined,
        queryKey: queryOptions.queryKey,
        signal: new AbortController().signal,
      } as never),
    ).rejects.toThrow(
      "Taxonomy leaf edge payload must contain 3 numeric values.",
    );
  });
});
