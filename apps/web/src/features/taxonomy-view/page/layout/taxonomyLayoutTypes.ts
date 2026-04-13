// abstract: Shared input and output types for taxonomy branch and leaf layout helpers.
// out_of_scope: React component rendering and force-simulation implementation details.

export interface LayoutPoint {
  readonly x: number;
  readonly y: number;
}

export interface LayoutViewport {
  readonly height: number;
  readonly width: number;
}

export interface LeafCardMeasuredSize {
  readonly height: number;
  readonly width: number;
}

export interface BranchChildLayoutInput {
  readonly depth: number;
  readonly descendant_card_count: number;
  readonly id: number;
  readonly name: string;
}

export interface LeafSkeletonNodeLayoutInput {
  readonly id: number;
  readonly scope: "inner" | "outer";
}

export interface LeafHydratedNodeLayoutInput
  extends LeafSkeletonNodeLayoutInput {
  readonly content: string;
  readonly title: string;
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
  readonly renderMode?: "bubble" | "card" | "point";
  readonly scope: "branch" | "inner" | "outer";
  readonly targetNodeId: number | null;
  readonly tooltip: string;
};

export interface TaxonomyLayoutNode {
  readonly data: TaxonomyLayoutNodeData;
  readonly id: string;
  readonly position: LayoutPoint;
  readonly style: {
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
  readonly hydratedNodeDetailsById?: Readonly<
    Partial<Record<number, LeafHydratedNodeLayoutInput>>
  >;
  readonly lockedNodeCentersById?: ReadonlyMap<number, LayoutPoint>;
  readonly measuredCardSizesById?: Readonly<
    Partial<Record<number, LeafCardMeasuredSize>>
  >;
  readonly nodes: readonly LeafNodeLayoutInput[];
  readonly visibleCardNodeIds?: readonly number[];
  readonly viewport: LayoutViewport;
}

export interface BranchLayoutResult {
  readonly nodes: TaxonomyLayoutNode[];
}

export interface LeafLayoutResult {
  readonly edges: TaxonomyLayoutEdge[];
  readonly nodes: TaxonomyLayoutNode[];
}
