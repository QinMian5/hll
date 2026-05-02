// abstract: Shared input and output types for taxonomy branch and leaf layout helpers.
// out_of_scope: React component rendering and force-simulation implementation details.

import type { CSSProperties } from "react";

export interface LayoutPoint {
  readonly x: number;
  readonly y: number;
}

export interface LayoutViewport {
  readonly height: number;
  readonly width: number;
}

export interface LayoutBounds {
  readonly maxX: number;
  readonly maxY: number;
  readonly minX: number;
  readonly minY: number;
}

export interface BranchInitialViewport {
  readonly x: number;
  readonly y: number;
  readonly zoom: number;
}

export interface BranchChildLayoutInput {
  readonly depth: number;
  readonly descendant_card_count: number;
  readonly id: number | string;
  readonly name: string;
  readonly route_path: string;
  readonly taxonomy_node_id?: number | null;
}

export interface LeafSkeletonNodeLayoutInput {
  readonly id: number;
  readonly scope: "inner" | "outer";
}

export type LeafNodeLayoutInput = LeafSkeletonNodeLayoutInput;

export type LeafEdgeLayoutInput = readonly [
  sourceNodeId: number,
  targetNodeId: number,
  strength: number,
];

export type TaxonomyLayoutNodeData = Record<string, unknown> & {
  readonly content?: string;
  readonly depth: number;
  readonly graphNodeId?: number;
  readonly label: string;
  readonly renderMode?: "bubble" | "point";
  readonly scope: "branch" | "inner" | "outer";
  readonly targetNodeId: number | null;
  readonly targetRoutePath?: string | null;
  readonly tooltip: string;
};

export interface TaxonomyLayoutNode {
  readonly data: TaxonomyLayoutNodeData;
  readonly id: string;
  readonly position: LayoutPoint;
  readonly style: CSSProperties & {
    readonly "--taxonomy-bubble-label-font-size"?: string;
    readonly "--taxonomy-bubble-label-line-height"?: string;
    readonly "--taxonomy-bubble-label-width"?: string;
    readonly borderRadius: string;
    readonly height: number;
    readonly width: number;
  };
  readonly type: "bubble";
}

export interface TaxonomyLayoutEdge {
  readonly id: string;
  readonly source: string;
  readonly target: string;
}

export interface BranchLayoutInput {
  readonly center: LayoutPoint;
  readonly children: readonly BranchChildLayoutInput[];
  readonly viewport: LayoutViewport;
}

export interface LeafLayoutInput {
  readonly center: LayoutPoint;
  readonly edges: readonly LeafEdgeLayoutInput[];
  readonly lockedNodeCentersById?: ReadonlyMap<number, LayoutPoint>;
  readonly nodes: readonly LeafNodeLayoutInput[];
  readonly viewport: LayoutViewport;
}

export interface BranchLayoutResult {
  readonly bounds: LayoutBounds;
  readonly initialViewport: BranchInitialViewport;
  readonly nodes: TaxonomyLayoutNode[];
}

export interface LeafLayoutResult {
  readonly edges: TaxonomyLayoutEdge[];
  readonly nodes: TaxonomyLayoutNode[];
}
