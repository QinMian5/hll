// abstract: Scene-data shaping helpers for mapping leaf layout output into deck.gl-ready primitives.
// out_of_scope: Viewport control and deck.gl layer construction.

import type {
  LayoutViewport,
  TaxonomyLayoutNode,
} from "../layout/taxonomyLayoutTypes";
import {
  LEAF_TITLE_LABEL_FONT_FAMILY,
  LEAF_TITLE_LABEL_FONT_SIZE_PX,
  LEAF_TITLE_LABEL_FONT_WEIGHT,
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

export interface LeafTitleTextMetrics {
  readonly actualBoundingBoxAscent?: number;
  readonly actualBoundingBoxDescent?: number;
  readonly actualBoundingBoxLeft?: number;
  readonly actualBoundingBoxRight?: number;
  readonly width: number;
}

export interface LeafTitleTextMeasurer {
  readonly measureText: (text: string) => LeafTitleTextMetrics;
}

const FALLBACK_AVERAGE_CHAR_WIDTH_EM = 0.54;

function createFallbackLeafTitleTextMeasurer(): LeafTitleTextMeasurer {
  return {
    measureText: (text) => ({
      actualBoundingBoxAscent: LEAF_TITLE_LABEL_FONT_SIZE_PX * 0.8,
      actualBoundingBoxDescent: LEAF_TITLE_LABEL_FONT_SIZE_PX * 0.2,
      actualBoundingBoxLeft: 0,
      actualBoundingBoxRight:
        Array.from(text).length *
        LEAF_TITLE_LABEL_FONT_SIZE_PX *
        FALLBACK_AVERAGE_CHAR_WIDTH_EM,
      width:
        Array.from(text).length *
        LEAF_TITLE_LABEL_FONT_SIZE_PX *
        FALLBACK_AVERAGE_CHAR_WIDTH_EM,
    }),
  };
}

export function createLeafTitleCanvasTextMeasurer(): LeafTitleTextMeasurer {
  if (
    typeof document === "undefined" ||
    typeof CanvasRenderingContext2D === "undefined"
  ) {
    return createFallbackLeafTitleTextMeasurer();
  }

  const context = document.createElement("canvas").getContext("2d");

  if (!context) {
    return createFallbackLeafTitleTextMeasurer();
  }

  context.font = `${LEAF_TITLE_LABEL_FONT_WEIGHT} ${LEAF_TITLE_LABEL_FONT_SIZE_PX}px ${LEAF_TITLE_LABEL_FONT_FAMILY}`;

  return {
    measureText: (text) => context.measureText(text),
  };
}

function measuredTextWidth(metrics: LeafTitleTextMetrics) {
  const actualWidth =
    typeof metrics.actualBoundingBoxLeft === "number" &&
    typeof metrics.actualBoundingBoxRight === "number"
      ? metrics.actualBoundingBoxLeft + metrics.actualBoundingBoxRight
      : 0;

  return Math.max(metrics.width, actualWidth);
}

function measuredTextHeight(metrics: LeafTitleTextMetrics) {
  const actualHeight =
    (metrics.actualBoundingBoxAscent ?? 0) +
    (metrics.actualBoundingBoxDescent ?? 0);

  return actualHeight > 0 ? actualHeight : LEAF_TITLE_LABEL_FONT_SIZE_PX;
}

function splitTokenIntoMeasuredLines(input: {
  readonly maxWidth: number;
  readonly textMeasurer: LeafTitleTextMeasurer;
  readonly token: string;
}) {
  const lines: string[] = [];
  let currentLine = "";

  for (const character of Array.from(input.token)) {
    const nextLine = `${currentLine}${character}`;

    if (
      currentLine !== "" &&
      measuredTextWidth(input.textMeasurer.measureText(nextLine)) >
        input.maxWidth
    ) {
      lines.push(currentLine);
      currentLine = character;
      continue;
    }

    currentLine = nextLine;
  }

  return {
    lines,
    remainingLine: currentLine,
  };
}

function wrapTitleIntoMeasuredLines(input: {
  readonly maxWidth: number;
  readonly textMeasurer: LeafTitleTextMeasurer;
  readonly title: string;
}) {
  const tokens = input.title.trim().split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let currentLine = "";

  for (const token of tokens.length > 0 ? tokens : [""]) {
    const nextLine = currentLine ? `${currentLine} ${token}` : token;

    if (
      measuredTextWidth(input.textMeasurer.measureText(nextLine)) <=
      input.maxWidth
    ) {
      currentLine = nextLine;
      continue;
    }

    if (currentLine) {
      lines.push(currentLine);
    }

    if (
      measuredTextWidth(input.textMeasurer.measureText(token)) <= input.maxWidth
    ) {
      currentLine = token;
      continue;
    }

    const splitToken = splitTokenIntoMeasuredLines({
      maxWidth: input.maxWidth,
      textMeasurer: input.textMeasurer,
      token,
    });
    lines.push(...splitToken.lines);
    currentLine = splitToken.remainingLine;
  }

  if (currentLine || lines.length === 0) {
    lines.push(currentLine);
  }

  return lines;
}

function measureLeafTitleTextBounds(input: {
  readonly textMeasurer: LeafTitleTextMeasurer;
  readonly title: string;
}) {
  const maxWidth =
    LEAF_TITLE_LABEL_FONT_SIZE_PX * LEAF_TITLE_LABEL_MAX_WIDTH_EM;
  const lines = wrapTitleIntoMeasuredLines({
    maxWidth,
    textMeasurer: input.textMeasurer,
    title: input.title,
  });
  const lineMetrics = lines.map((line) => input.textMeasurer.measureText(line));
  const width = Math.min(
    maxWidth,
    Math.max(...lineMetrics.map((metrics) => measuredTextWidth(metrics))),
  );
  const glyphHeight = Math.max(
    ...lineMetrics.map((metrics) => measuredTextHeight(metrics)),
  );
  const lineAdvance =
    LEAF_TITLE_LABEL_FONT_SIZE_PX * LEAF_TITLE_LABEL_LINE_HEIGHT;
  const height = glyphHeight + (lines.length - 1) * lineAdvance;

  return {
    height,
    width,
  };
}

function estimateLeafTitleScreenBounds(input: {
  readonly canvas: LayoutViewport;
  readonly pointNode: LeafScenePointNode;
  readonly textMeasurer: LeafTitleTextMeasurer;
  readonly title: string;
  readonly viewport: LeafOrthographicViewport;
}): ScreenBounds {
  const scale = scaleFromZoom(input.viewport.zoom);
  const [targetX, targetY] = input.viewport.target;
  const screenX =
    (input.pointNode.position.x - targetX) * scale + input.canvas.width / 2;
  const screenY =
    (input.pointNode.position.y - targetY) * scale + input.canvas.height / 2;
  const textBounds = measureLeafTitleTextBounds({
    textMeasurer: input.textMeasurer,
    title: input.title,
  });
  const top = screenY + LEAF_TITLE_LABEL_PIXEL_OFFSET_Y;

  return {
    bottom: top + textBounds.height,
    left: screenX - textBounds.width / 2,
    right: screenX + textBounds.width / 2,
    top,
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
  readonly textMeasurer: LeafTitleTextMeasurer;
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
      textMeasurer: options.textMeasurer,
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
