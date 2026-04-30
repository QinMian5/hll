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

export interface LeafSceneTitleLabelNode {
  readonly content?: string;
  readonly graphNodeId: number;
  readonly id: string;
  readonly position: LayoutPoint;
  readonly scope: "inner" | "outer";
  readonly title: string;
}

export interface LeafDisclosureNode {
  readonly content: string;
  readonly currentVersion: number;
  readonly graphNodeId: number;
  readonly id: string;
  readonly position: LayoutPoint;
  readonly scope: "inner" | "outer";
  readonly title: string;
}

export interface LeafDisclosureState {
  readonly mode: "hover" | "selected";
  readonly node: LeafDisclosureNode;
}

export interface BuildLeafSceneModelInput {
  readonly edges: readonly LeafEdgeLayoutInput[];
  readonly layoutNodes: readonly TaxonomyLayoutNode[];
}

export interface LeafSceneModel {
  readonly edgeIdsByNodeId: ReadonlyMap<number, ReadonlySet<string>>;
  readonly bounds: LeafWorldBounds;
  readonly edges: readonly LeafSceneEdge[];
  readonly focusNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly highlightEdgesByNodeId: ReadonlyMap<
    number,
    readonly LeafSceneEdge[]
  >;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly pointNodes: readonly LeafScenePointNode[];
  readonly titleLabelNodes: readonly LeafSceneTitleLabelNode[];
}

export interface LeafSceneModelBase {
  readonly edgeIdsByNodeId: ReadonlyMap<number, ReadonlySet<string>>;
  readonly bounds: LeafWorldBounds;
  readonly edges: readonly LeafSceneEdge[];
  readonly focusNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly highlightEdgesByNodeId: ReadonlyMap<
    number,
    readonly LeafSceneEdge[]
  >;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly pointNodes: readonly LeafScenePointNode[];
}
