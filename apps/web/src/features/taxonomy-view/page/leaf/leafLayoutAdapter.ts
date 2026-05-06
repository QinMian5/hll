// abstract: Backend-to-render-node adapter for taxonomy leaf layouts.
// out_of_scope: deck.gl scene construction and taxonomy query orchestration.

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../data/taxonomyViewQueries";
import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";

const LEAF_POINT_DIAMETER = 6;

export interface RenderableLeafLayout {
  readonly edges: TaxonomyCardScopeLayoutSliceResponse["edges"];
  readonly nodes: TaxonomyLayoutNode[];
}

export function buildRenderableLeafLayout(
  layoutSlice: TaxonomyCardScopeLayoutSliceResponse | undefined,
): RenderableLeafLayout {
  if (!layoutSlice) {
    return { edges: [], nodes: [] };
  }

  return {
    edges: layoutSlice.edges,
    nodes: layoutSlice.nodes.map((node) => ({
      data: {
        depth: 0,
        graphNodeId: node.id,
        label: "",
        renderMode: "point" as const,
        scope: node.scope,
        targetNodeId: null,
        tooltip: "",
      },
      id: `leaf-${node.id}`,
      position: {
        x: node.x - LEAF_POINT_DIAMETER / 2,
        y: node.y - LEAF_POINT_DIAMETER / 2,
      },
      style: {
        borderRadius: `${LEAF_POINT_DIAMETER}px`,
        height: LEAF_POINT_DIAMETER,
        width: LEAF_POINT_DIAMETER,
      },
      type: "bubble" as const,
    })),
  };
}
