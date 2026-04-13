// abstract: Scene-data shaping helpers for mapping leaf layout output into deck.gl-ready primitives.
// out_of_scope: Viewport control and deck.gl layer construction.

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import type {
  BuildLeafSceneModelInput,
  LeafSceneCardNode,
  LeafSceneEdge,
  LeafSceneModel,
  LeafScenePointNode,
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
        node.data.renderMode === "point" &&
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

function toCardNodes(
  nodes: readonly TaxonomyLayoutNode[],
): LeafSceneCardNode[] {
  return nodes
    .filter(
      (node) =>
        node.data.scope !== "branch" &&
        node.data.renderMode === "card" &&
        typeof node.data.graphNodeId === "number",
    )
    .map((node) => ({
      content: node.data.content,
      graphNodeId: node.data.graphNodeId as number,
      id: node.id,
      label: node.data.label,
      position: nodeCenter(node),
      scope: node.data.scope as "inner" | "outer",
      size: {
        height: node.style.height,
        width: node.style.width,
      },
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

export function buildLeafSceneModel(
  input: BuildLeafSceneModelInput,
): LeafSceneModel {
  const positionsByNodeId = toEdgeMap(input.layoutNodes);
  const adjacency = toAdjacencyMaps(input);
  const pointNodes = toPointNodes(input.layoutNodes);
  const cardNodes = toCardNodes(input.layoutNodes);
  const edges: LeafSceneEdge[] = input.edges.map(
    ([sourceId, targetId, strength]) => {
      const source = positionsByNodeId.get(`card-${sourceId}`);
      const target = positionsByNodeId.get(`card-${targetId}`);

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

  return {
    bounds: deriveSceneBounds(input.layoutNodes),
    cardNodes,
    edgeIdsByNodeId: adjacency.edgeIdsByNodeId,
    edges,
    neighborNodeIdsByNodeId: adjacency.neighborNodeIdsByNodeId,
    pointNodes,
  };
}
