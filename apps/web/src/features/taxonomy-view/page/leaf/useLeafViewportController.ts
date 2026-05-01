// abstract: Pure viewport helpers for deck.gl-backed taxonomy leaf hydration and bounds selection.
// out_of_scope: React state wiring and deck.gl scene rendering.

import type { TaxonomyLayoutNode } from "../layout/taxonomyLayoutTypes";
import {
  LEAF_INITIAL_POINT_TITLE_ZOOM,
  LEAF_POINT_TITLE_ACTIVATION_ZOOM,
} from "./leafRendererConfig";
import type {
  BuildLeafViewportStateInput,
  LeafOrthographicViewport,
  LeafViewportState,
  LeafWorldBounds,
} from "./leafSceneTypes";

function scaleFromZoom(zoom: number) {
  return 2 ** zoom;
}

export function isLeafPointTitleModeActive(zoom: number) {
  return zoom >= LEAF_POINT_TITLE_ACTIVATION_ZOOM;
}

export function buildInitialLeafViewport(input: {
  readonly canvas: { readonly height: number; readonly width: number };
  readonly padding: number;
  readonly worldBounds: LeafWorldBounds;
}): LeafOrthographicViewport {
  const centerX = (input.worldBounds.left + input.worldBounds.right) / 2;
  const centerY = (input.worldBounds.top + input.worldBounds.bottom) / 2;

  return {
    target: [centerX, centerY, 0],
    zoom: LEAF_INITIAL_POINT_TITLE_ZOOM,
  };
}

export function expandLeafWorldBounds(
  bounds: LeafWorldBounds,
  overscan: number,
): LeafWorldBounds {
  return {
    bottom: bounds.bottom + overscan,
    left: bounds.left - overscan,
    right: bounds.right + overscan,
    top: bounds.top - overscan,
  };
}

export function snapLeafWorldBoundsToTile(
  bounds: LeafWorldBounds,
  tileSize: number,
): LeafWorldBounds {
  if (tileSize <= 0) {
    throw new Error("Leaf layout tile size must be positive.");
  }

  return {
    bottom: Math.ceil(bounds.bottom / tileSize) * tileSize,
    left: Math.floor(bounds.left / tileSize) * tileSize,
    right: Math.ceil(bounds.right / tileSize) * tileSize,
    top: Math.floor(bounds.top / tileSize) * tileSize,
  };
}

export function leafWorldBoundsFromViewport(
  input: BuildLeafViewportStateInput,
): LeafWorldBounds {
  if (input.canvas.width <= 0 || input.canvas.height <= 0) {
    throw new Error("Leaf viewport canvas dimensions must be positive.");
  }

  const scale = scaleFromZoom(input.viewport.zoom);
  const halfWorldWidth = input.canvas.width / scale / 2;
  const halfWorldHeight = input.canvas.height / scale / 2;
  const [targetX, targetY] = input.viewport.target;

  return {
    bottom: targetY + halfWorldHeight,
    left: targetX - halfWorldWidth,
    right: targetX + halfWorldWidth,
    top: targetY - halfWorldHeight,
  };
}

export function buildLeafViewportState(
  input: BuildLeafViewportStateInput,
): LeafViewportState {
  const bounds = leafWorldBoundsFromViewport(input);

  return {
    bounds,
    overscanBounds: expandLeafWorldBounds(bounds, input.overscan),
    viewport: input.viewport,
  };
}

export function selectLeafHydrationNodeIds(
  nodes: readonly TaxonomyLayoutNode[],
  bounds: LeafWorldBounds,
): number[] {
  return nodes
    .filter((node) => {
      const left = node.position.x;
      const top = node.position.y;
      const right = node.position.x + node.style.width;
      const bottom = node.position.y + node.style.height;

      return !(
        right < bounds.left ||
        left > bounds.right ||
        bottom < bounds.top ||
        top > bounds.bottom
      );
    })
    .map((node) => node.data.graphNodeId)
    .filter((nodeId): nodeId is number => Number.isFinite(nodeId));
}
