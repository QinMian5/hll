// abstract: Scene-data shaping helpers for mapping leaf layout output into deck.gl-ready primitives.
// out_of_scope: Viewport control and deck.gl layer construction.

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import type {
  BuildLeafSceneModelInput,
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

export function selectLeafTitleNodeIdsByPriority(options: {
  readonly maxNodeCount: number;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly priorityNodeIds: readonly (number | null)[];
  readonly visibleNodeIds: readonly number[];
}): number[] {
  if (options.maxNodeCount <= 0) {
    return [];
  }

  const priorityNodeIds = new Set(
    options.priorityNodeIds.filter(
      (nodeId): nodeId is number => nodeId !== null,
    ),
  );
  return [...new Set(options.visibleNodeIds)]
    .sort((leftNodeId, rightNodeId) => {
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
    })
    .slice(0, options.maxNodeCount);
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
