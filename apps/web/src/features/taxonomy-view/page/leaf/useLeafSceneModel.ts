// abstract: Scene-data shaping helpers for mapping leaf layout output into deck.gl-ready primitives.
// out_of_scope: Viewport control and deck.gl layer construction.

import type {
  LayoutViewport,
  TaxonomyLayoutNode,
} from "../layout/taxonomyLayoutTypes";
import {
  LEAF_TITLE_LABEL_COLLISION_AVERAGE_CHAR_WIDTH_EM,
  LEAF_TITLE_LABEL_COLLISION_MIN_WIDTH_EM,
  LEAF_TITLE_LABEL_COLLISION_PADDING_PX,
  LEAF_TITLE_LABEL_FONT_SIZE_PX,
  LEAF_TITLE_LABEL_LINE_HEIGHT,
  LEAF_TITLE_LABEL_MAX_WIDTH_EM,
  LEAF_TITLE_LABEL_PIXEL_OFFSET_Y,
} from "./leafRendererConfig";
import type {
  BuildLeafSceneModelInput,
  LeafOrthographicViewport,
  LeafSceneEdge,
  LeafSceneModel,
  LeafSceneModelBase,
  LeafScenePointNode,
  LeafSceneTitleLabelNode,
  LeafWorldBounds,
} from "./leafSceneTypes";

function nodeCenter(node: TaxonomyLayoutNode) {
  return {
    x: node.position.x + node.style.width / 2,
    y: node.position.y + node.style.height / 2,
  };
}

function deriveSceneBounds(
  nodes: readonly TaxonomyLayoutNode[],
): LeafWorldBounds {
  const left = Math.min(...nodes.map((node) => node.position.x));
  const top = Math.min(...nodes.map((node) => node.position.y));
  const right = Math.max(
    ...nodes.map((node) => node.position.x + node.style.width),
  );
  const bottom = Math.max(
    ...nodes.map((node) => node.position.y + node.style.height),
  );

  return {
    bottom,
    left,
    right,
    top,
  };
}

function toPointNodes(
  nodes: readonly TaxonomyLayoutNode[],
): LeafScenePointNode[] {
  return nodes
    .filter(
      (node) =>
        node.data.scope !== "branch" &&
        typeof node.data.graphNodeId === "number",
    )
    .map((node) => ({
      graphNodeId: node.data.graphNodeId as number,
      id: node.id,
      position: nodeCenter(node),
      radius: Math.max(node.style.width, node.style.height) / 2,
      scope: node.data.scope as "inner" | "outer",
    }));
}

function toEdgeMap(nodes: readonly TaxonomyLayoutNode[]) {
  return new Map(nodes.map((node) => [node.id, nodeCenter(node)] as const));
}

function toAdjacencyMaps(input: BuildLeafSceneModelInput) {
  const edgeIdsByNodeId = new Map<number, Set<string>>();
  const neighborNodeIdsByNodeId = new Map<number, Set<number>>();

  for (const [sourceId, targetId] of input.edges) {
    const edgeId = `${sourceId}:${targetId}`;

    if (!edgeIdsByNodeId.has(sourceId)) {
      edgeIdsByNodeId.set(sourceId, new Set<string>());
    }
    if (!edgeIdsByNodeId.has(targetId)) {
      edgeIdsByNodeId.set(targetId, new Set<string>());
    }
    if (!neighborNodeIdsByNodeId.has(sourceId)) {
      neighborNodeIdsByNodeId.set(sourceId, new Set<number>());
    }
    if (!neighborNodeIdsByNodeId.has(targetId)) {
      neighborNodeIdsByNodeId.set(targetId, new Set<number>());
    }

    edgeIdsByNodeId.get(sourceId)?.add(edgeId);
    edgeIdsByNodeId.get(targetId)?.add(edgeId);
    neighborNodeIdsByNodeId.get(sourceId)?.add(targetId);
    neighborNodeIdsByNodeId.get(targetId)?.add(sourceId);
  }

  return {
    edgeIdsByNodeId: new Map(
      [...edgeIdsByNodeId.entries()].map(([nodeId, edgeIds]) => [
        nodeId,
        new Set(edgeIds) as ReadonlySet<string>,
      ]),
    ) as ReadonlyMap<number, ReadonlySet<string>>,
    neighborNodeIdsByNodeId: new Map(
      [...neighborNodeIdsByNodeId.entries()].map(
        ([nodeId, neighborNodeIds]) => [
          nodeId,
          new Set(neighborNodeIds) as ReadonlySet<number>,
        ],
      ),
    ) as ReadonlyMap<number, ReadonlySet<number>>,
  };
}

function toHighlightEdgesByNodeId(input: {
  readonly edgeIdsByNodeId: ReadonlyMap<number, ReadonlySet<string>>;
  readonly edges: readonly LeafSceneEdge[];
}) {
  const edgesById = new Map(
    input.edges.map((edge) => [edge.id, edge] as const),
  );

  return new Map(
    [...input.edgeIdsByNodeId.entries()].map(([nodeId, edgeIds]) => [
      nodeId,
      [...edgeIds]
        .map((edgeId) => edgesById.get(edgeId))
        .filter((edge): edge is LeafSceneEdge => edge !== undefined),
    ]),
  ) as ReadonlyMap<number, readonly LeafSceneEdge[]>;
}

function toFocusNodeIdsByNodeId(
  neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>,
) {
  return new Map(
    [...neighborNodeIdsByNodeId.entries()].map(([nodeId, neighborNodeIds]) => [
      nodeId,
      new Set([nodeId, ...neighborNodeIds]) as ReadonlySet<number>,
    ]),
  ) as ReadonlyMap<number, ReadonlySet<number>>;
}

export function buildLeafSceneModelBase(
  input: BuildLeafSceneModelInput,
): LeafSceneModelBase {
  const positionsByNodeId = toEdgeMap(input.layoutNodes);
  const adjacency = toAdjacencyMaps(input);
  const pointNodes = toPointNodes(input.layoutNodes);
  const edges: LeafSceneEdge[] = input.edges.map(
    ([sourceId, targetId, strength]) => {
      const source = positionsByNodeId.get(`leaf-${sourceId}`);
      const target = positionsByNodeId.get(`leaf-${targetId}`);

      if (!source || !target) {
        throw new Error(
          `Leaf scene edge ${sourceId}:${targetId} is missing a positioned endpoint.`,
        );
      }

      return {
        id: `${sourceId}:${targetId}`,
        source,
        strength,
        target,
      };
    },
  );
  const highlightEdgesByNodeId = toHighlightEdgesByNodeId({
    edgeIdsByNodeId: adjacency.edgeIdsByNodeId,
    edges,
  });
  const focusNodeIdsByNodeId = toFocusNodeIdsByNodeId(
    adjacency.neighborNodeIdsByNodeId,
  );

  return {
    bounds: deriveSceneBounds(input.layoutNodes),
    edgeIdsByNodeId: adjacency.edgeIdsByNodeId,
    edges,
    focusNodeIdsByNodeId,
    highlightEdgesByNodeId,
    neighborNodeIdsByNodeId: adjacency.neighborNodeIdsByNodeId,
    pointNodes,
  };
}

export function buildLeafTitleLabelNodes(options: {
  readonly pointNodes: readonly LeafScenePointNode[];
  readonly titlesByNodeId: Readonly<Record<number, string>>;
  readonly visibleNodeIds: readonly number[];
}): LeafSceneTitleLabelNode[] {
  const pointNodesById = new Map(
    options.pointNodes.map(
      (pointNode) => [pointNode.graphNodeId, pointNode] as const,
    ),
  );

  return options.visibleNodeIds.flatMap((nodeId) => {
    const pointNode = pointNodesById.get(nodeId);
    const title = options.titlesByNodeId[nodeId];

    if (!pointNode || title === undefined) {
      return [];
    }

    return [
      {
        graphNodeId: pointNode.graphNodeId,
        id: pointNode.id,
        position: pointNode.position,
        scope: pointNode.scope,
        title,
      },
    ];
  });
}

function scaleFromZoom(zoom: number) {
  return 2 ** zoom;
}

function sortLeafTitleNodeIdsByPriority(options: {
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly priorityNodeIds: readonly (number | null)[];
  readonly visibleNodeIds: readonly number[];
}) {
  const priorityNodeIds = new Set(
    options.priorityNodeIds.filter(
      (nodeId): nodeId is number => nodeId !== null,
    ),
  );

  return [...new Set(options.visibleNodeIds)].sort(
    (leftNodeId, rightNodeId) => {
      const leftPriority = priorityNodeIds.has(leftNodeId) ? 1 : 0;
      const rightPriority = priorityNodeIds.has(rightNodeId) ? 1 : 0;
      if (leftPriority !== rightPriority) {
        return rightPriority - leftPriority;
      }

      const leftDegree =
        options.neighborNodeIdsByNodeId.get(leftNodeId)?.size ?? 0;
      const rightDegree =
        options.neighborNodeIdsByNodeId.get(rightNodeId)?.size ?? 0;
      if (leftDegree !== rightDegree) {
        return rightDegree - leftDegree;
      }

      return leftNodeId - rightNodeId;
    },
  );
}

interface ScreenBounds {
  readonly bottom: number;
  readonly left: number;
  readonly right: number;
  readonly top: number;
}

function estimateLeafTitleScreenBounds(input: {
  readonly canvas: LayoutViewport;
  readonly pointNode: LeafScenePointNode;
  readonly title: string;
  readonly viewport: LeafOrthographicViewport;
}): ScreenBounds {
  const scale = scaleFromZoom(input.viewport.zoom);
  const [targetX, targetY] = input.viewport.target;
  const screenX =
    (input.pointNode.position.x - targetX) * scale + input.canvas.width / 2;
  const screenY =
    (input.pointNode.position.y - targetY) * scale + input.canvas.height / 2;
  const rawWidth =
    input.title.length *
    LEAF_TITLE_LABEL_FONT_SIZE_PX *
    LEAF_TITLE_LABEL_COLLISION_AVERAGE_CHAR_WIDTH_EM;
  const maxWidth =
    LEAF_TITLE_LABEL_FONT_SIZE_PX * LEAF_TITLE_LABEL_MAX_WIDTH_EM;
  const minWidth =
    LEAF_TITLE_LABEL_FONT_SIZE_PX * LEAF_TITLE_LABEL_COLLISION_MIN_WIDTH_EM;
  const width = Math.min(maxWidth, Math.max(minWidth, rawWidth));
  const lineCount = Math.max(1, Math.ceil(rawWidth / maxWidth));
  const height =
    lineCount * LEAF_TITLE_LABEL_FONT_SIZE_PX * LEAF_TITLE_LABEL_LINE_HEIGHT;
  const padding = LEAF_TITLE_LABEL_COLLISION_PADDING_PX;
  const top = screenY + LEAF_TITLE_LABEL_PIXEL_OFFSET_Y;

  return {
    bottom: top + height + padding,
    left: screenX - width / 2 - padding,
    right: screenX + width / 2 + padding,
    top: top - padding,
  };
}

function screenBoundsOverlap(left: ScreenBounds, right: ScreenBounds) {
  return !(
    left.right < right.left ||
    left.left > right.right ||
    left.bottom < right.top ||
    left.top > right.bottom
  );
}

function screenBoundsIntersectCanvas(
  bounds: ScreenBounds,
  canvas: LayoutViewport,
) {
  return !(
    bounds.right < 0 ||
    bounds.left > canvas.width ||
    bounds.bottom < 0 ||
    bounds.top > canvas.height
  );
}

export function selectLeafTitleNodeIdsByPriority(options: {
  readonly maxNodeCount: number;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly priorityNodeIds: readonly (number | null)[];
  readonly visibleNodeIds: readonly number[];
}): number[] {
  if (options.maxNodeCount <= 0) {
    return [];
  }

  return sortLeafTitleNodeIdsByPriority({
    neighborNodeIdsByNodeId: options.neighborNodeIdsByNodeId,
    priorityNodeIds: options.priorityNodeIds,
    visibleNodeIds: options.visibleNodeIds,
  }).slice(0, options.maxNodeCount);
}

export function selectLeafTitleNodeIdsByScreenCollision(options: {
  readonly canvas: LayoutViewport;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly pointNodes: readonly LeafScenePointNode[];
  readonly priorityNodeIds: readonly (number | null)[];
  readonly titlesByNodeId: Readonly<Record<number, string>>;
  readonly viewport: LeafOrthographicViewport;
  readonly visibleNodeIds: readonly number[];
}): number[] {
  if (options.canvas.width <= 0 || options.canvas.height <= 0) {
    return [];
  }

  const pointNodesById = new Map(
    options.pointNodes.map(
      (pointNode) => [pointNode.graphNodeId, pointNode] as const,
    ),
  );
  const acceptedBounds: ScreenBounds[] = [];
  const selectedNodeIds: number[] = [];

  for (const nodeId of sortLeafTitleNodeIdsByPriority({
    neighborNodeIdsByNodeId: options.neighborNodeIdsByNodeId,
    priorityNodeIds: options.priorityNodeIds,
    visibleNodeIds: options.visibleNodeIds,
  })) {
    const pointNode = pointNodesById.get(nodeId);
    const title = options.titlesByNodeId[nodeId];

    if (!pointNode || title === undefined) {
      continue;
    }

    const bounds = estimateLeafTitleScreenBounds({
      canvas: options.canvas,
      pointNode,
      title,
      viewport: options.viewport,
    });

    if (!screenBoundsIntersectCanvas(bounds, options.canvas)) {
      continue;
    }
    if (
      acceptedBounds.some((accepted) => screenBoundsOverlap(bounds, accepted))
    ) {
      continue;
    }

    acceptedBounds.push(bounds);
    selectedNodeIds.push(nodeId);
  }

  return selectedNodeIds;
}

export function buildLeafSceneModel(
  input: BuildLeafSceneModelInput & {
    readonly titleLabelNodes?: readonly LeafSceneTitleLabelNode[];
  },
): LeafSceneModel {
  const baseScene = buildLeafSceneModelBase(input);

  return {
    ...baseScene,
    titleLabelNodes: input.titleLabelNodes ?? [],
  };
}
