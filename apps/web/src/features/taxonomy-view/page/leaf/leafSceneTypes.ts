// abstract: Shared scene and viewport types for the deck.gl-backed taxonomy leaf renderer.
// out_of_scope: React component composition and deck.gl layer instantiation.

import type {
  LayoutPoint,
  LayoutViewport,
  LeafEdgeLayoutInput,
  TaxonomyLayoutNode,
} from "../layout/taxonomyLayoutTypes";

export interface LeafWorldBounds {
  readonly bottom: number;
  readonly left: number;
  readonly right: number;
  readonly top: number;
}

export interface LeafOrthographicViewport {
  readonly target: readonly [number, number, number];
  readonly zoom: number;
}

export interface BuildLeafViewportStateInput {
  readonly canvas: LayoutViewport;
  readonly overscan: number;
  readonly viewport: LeafOrthographicViewport;
}

export interface LeafViewportState {
  readonly bounds: LeafWorldBounds;
  readonly overscanBounds: LeafWorldBounds;
  readonly shouldHydrateCards: boolean;
  readonly viewport: LeafOrthographicViewport;
}

export interface LeafSceneEdge {
  readonly id: string;
  readonly source: LayoutPoint;
  readonly strength: number;
  readonly target: LayoutPoint;
}

export interface LeafScenePointNode {
  readonly graphNodeId: number;
  readonly id: string;
  readonly position: LayoutPoint;
  readonly radius: number;
  readonly scope: "inner" | "outer";
}

export interface LeafSceneCardNode {
  readonly content?: string;
  readonly graphNodeId: number;
  readonly id: string;
  readonly label: string;
  readonly position: LayoutPoint;
  readonly scope: "inner" | "outer";
  readonly size: {
    readonly height: number;
    readonly width: number;
  };
}

export interface BuildLeafSceneModelInput {
  readonly edges: readonly LeafEdgeLayoutInput[];
  readonly layoutNodes: readonly TaxonomyLayoutNode[];
}

export interface LeafSceneModel {
  readonly edgeIdsByNodeId: ReadonlyMap<number, ReadonlySet<string>>;
  readonly bounds: LeafWorldBounds;
  readonly cardNodes: readonly LeafSceneCardNode[];
  readonly edges: readonly LeafSceneEdge[];
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly pointNodes: readonly LeafScenePointNode[];
}

export interface LeafHoverState {
  readonly anchorX: number;
  readonly anchorBottomY: number;
  readonly anchorTopY: number;
  readonly card: LeafSceneCardNode;
}
