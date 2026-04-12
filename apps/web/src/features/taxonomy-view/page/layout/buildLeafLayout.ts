// abstract: Force-based leaf layout helper for title-first taxonomy graph nodes.
// out_of_scope: Hover-disclosure UI wiring and page-level React Flow orchestration.

import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from "d3-force";

import type {
  LayoutPoint,
  LeafLayoutInput,
  LeafLayoutResult,
} from "./taxonomyLayoutTypes";

interface LeafSimulationNode {
  readonly graphNodeId: number;
  readonly height: number;
  readonly id: string;
  readonly scope: "inner" | "outer";
  readonly width: number;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
}

export const LEAF_CARD_MIN_WIDTH = 104;
export const LEAF_CARD_MAX_WIDTH = 176;
export const LEAF_CARD_MIN_HEIGHT = 52;
export const LEAF_COLLISION_RADIUS = 25;
const LEAF_CARD_HORIZONTAL_PADDING = 16;
const LEAF_CARD_VERTICAL_PADDING = 14;
const LEAF_CARD_LINE_HEIGHT = 18;
const LEAF_CARD_MAX_LINES = 3;
const LEAF_CARD_BORDER_RADIUS = 18;
const LEAF_CARD_APPROX_CHAR_WIDTH = 7;
const LEAF_POINT_INNER_DIAMETER = 10;
const LEAF_POINT_OUTER_DIAMETER = 8;
const LEAF_LAYOUT_SPACING_SCALE = 2;

function positionOnSpiral(options: {
  readonly center: LayoutPoint;
  readonly index: number;
}): LayoutPoint {
  const angle = options.index * 2.399963229728653;
  const radius = 80 + Math.sqrt(options.index + 1) * 72;

  return {
    x: options.center.x + Math.cos(angle) * radius,
    y: options.center.y + Math.sin(angle) * radius,
  };
}

function pointNodeDiameter(scope: "inner" | "outer") {
  return scope === "inner"
    ? LEAF_POINT_INNER_DIAMETER
    : LEAF_POINT_OUTER_DIAMETER;
}

export function scalePointAroundCenter(
  point: LayoutPoint,
  center: LayoutPoint,
  scale: number,
): LayoutPoint {
  return {
    x: center.x + (point.x - center.x) * scale,
    y: center.y + (point.y - center.y) * scale,
  };
}

function estimateWrappedLineCount(title: string, maxTextWidth: number) {
  const maxCharsPerLine = Math.max(
    6,
    Math.floor(maxTextWidth / LEAF_CARD_APPROX_CHAR_WIDTH),
  );
  const normalizedTitle = title.trim().replace(/\s+/g, " ");

  if (normalizedTitle.length === 0) {
    return 1;
  }

  let lineCount = 1;
  let lineLength = 0;

  for (const token of normalizedTitle.split(" ")) {
    const tokenLength = token.length;

    if (tokenLength > maxCharsPerLine) {
      if (lineLength > 0) {
        lineCount += 1;
        lineLength = 0;
      }

      lineCount += Math.ceil(tokenLength / maxCharsPerLine) - 1;
      lineLength = tokenLength % maxCharsPerLine;
      continue;
    }

    const nextLength =
      lineLength === 0 ? tokenLength : lineLength + 1 + tokenLength;

    if (nextLength > maxCharsPerLine) {
      lineCount += 1;
      lineLength = tokenLength;
      continue;
    }

    lineLength = nextLength;
  }

  return Math.max(1, Math.min(lineCount, LEAF_CARD_MAX_LINES));
}

function estimateCardDimensions(title: string) {
  const normalizedTitle = title.trim().replace(/\s+/g, " ");
  const maxTextWidth = LEAF_CARD_MAX_WIDTH - LEAF_CARD_HORIZONTAL_PADDING * 2;
  const longestTokenLength = normalizedTitle
    .split(" ")
    .reduce((longest, token) => Math.max(longest, token.length), 0);
  const estimatedTextWidth = Math.min(
    maxTextWidth,
    Math.max(
      LEAF_CARD_MIN_WIDTH - LEAF_CARD_HORIZONTAL_PADDING * 2,
      longestTokenLength * LEAF_CARD_APPROX_CHAR_WIDTH,
      normalizedTitle.length * LEAF_CARD_APPROX_CHAR_WIDTH * 0.42,
    ),
  );
  const width = Math.max(
    LEAF_CARD_MIN_WIDTH,
    Math.min(
      LEAF_CARD_MAX_WIDTH,
      estimatedTextWidth + LEAF_CARD_HORIZONTAL_PADDING * 2,
    ),
  );
  const lineCount = estimateWrappedLineCount(
    normalizedTitle,
    width - LEAF_CARD_HORIZONTAL_PADDING * 2,
  );

  return {
    height: Math.max(
      LEAF_CARD_MIN_HEIGHT,
      LEAF_CARD_VERTICAL_PADDING * 2 + lineCount * LEAF_CARD_LINE_HEIGHT,
    ),
    width,
  };
}

export function buildLeafLayout(input: LeafLayoutInput): LeafLayoutResult {
  const hydratedNodeDetailsById = input.hydratedNodeDetailsById ?? {};
  const visibleCardNodeIds = new Set(input.visibleCardNodeIds ?? []);
  const sortedNodes = [...input.nodes].sort(
    (left, right) => left.id - right.id,
  );
  const simulationNodes: LeafSimulationNode[] = sortedNodes.map(
    (node, index) => {
      const position = positionOnSpiral({
        center: input.center,
        index,
      });

      return {
        graphNodeId: node.id,
        id: `card-${node.id}`,
        scope: node.scope,
        height: pointNodeDiameter(node.scope),
        width: pointNodeDiameter(node.scope),
        x: position.x,
        y: position.y,
      };
    },
  );

  const nodeIds = new Set(simulationNodes.map((node) => node.id));
  const linkEdges = input.edges.map((edge) => {
    const [sourceNodeId, targetNodeId, strength] = edge;
    const source = `card-${sourceNodeId}`;
    const target = `card-${targetNodeId}`;

    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      throw new Error(
        `Leaf edge ${sourceNodeId}:${targetNodeId} references an unknown node.`,
      );
    }

    return {
      source,
      strength,
      target,
    };
  });

  forceSimulation(simulationNodes)
    .force(
      "link",
      forceLink<
        LeafSimulationNode,
        {
          readonly source: string;
          readonly strength: number;
          readonly target: string;
        }
      >(linkEdges)
        .id((node) => node.id)
        .distance((edge) => 130 - edge.strength * 24)
        .strength((edge) => 0.25 + edge.strength * 0.2),
    )
    .force("charge", forceManyBody<LeafSimulationNode>().strength(-240))
    .force(
      "collide",
      forceCollide<LeafSimulationNode>()
        .radius(() => LEAF_COLLISION_RADIUS)
        .strength(1),
    )
    .force("center", forceCenter(input.center.x, input.center.y).strength(0.12))
    .stop()
    .tick(220);

  return {
    edges: input.edges.map((edge) => ({
      id: `${edge[0]}:${edge[1]}`,
      source: `card-${edge[0]}`,
      target: `card-${edge[1]}`,
    })),
    nodes: simulationNodes.map((node) => {
      const hydratedDetails = hydratedNodeDetailsById[node.graphNodeId];
      const shouldRenderCard =
        visibleCardNodeIds.has(node.graphNodeId) &&
        hydratedDetails !== undefined;
      const scaledCenter = scalePointAroundCenter(
        { x: node.x, y: node.y },
        input.center,
        LEAF_LAYOUT_SPACING_SCALE,
      );
      const renderedDimensions = shouldRenderCard
        ? estimateCardDimensions(hydratedDetails.title)
        : {
            height: node.height,
            width: node.width,
          };

      return {
        data: {
          content: shouldRenderCard ? hydratedDetails.content : undefined,
          depth: 0,
          graphNodeId: node.graphNodeId,
          label: shouldRenderCard ? hydratedDetails.title : "",
          renderMode: shouldRenderCard ? "card" : "point",
          scope: node.scope,
          targetNodeId: null,
          tooltip: shouldRenderCard ? hydratedDetails.title : "",
        },
        id: node.id,
        position: {
          x: scaledCenter.x - renderedDimensions.width / 2,
          y: scaledCenter.y - renderedDimensions.height / 2,
        },
        style: {
          borderRadius: shouldRenderCard
            ? `${LEAF_CARD_BORDER_RADIUS}px`
            : `${Math.max(renderedDimensions.width, renderedDimensions.height)}px`,
          height: renderedDimensions.height,
          width: renderedDimensions.width,
        },
        type: "bubble",
      };
    }),
  };
}
