// abstract: View-state and visible-tile helpers for semantic-map rendering.
// out_of_scope: React component composition and semantic-level selection policy.

import type { OrthographicViewState } from "@deck.gl/core";

import type { SemanticMapManifestViewModel } from "../data/mappers";

export interface SemanticMapViewState {
  readonly target: readonly [number, number];
  readonly zoom: number;
}

export interface VisibleTileState {
  readonly tileBounds: readonly [number, number, number, number];
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

interface ClampRange {
  readonly max: number;
  readonly min: number;
}

interface GetVisibleTileArgs {
  readonly manifest: SemanticMapManifestViewModel;
  readonly viewState: SemanticMapViewState;
}

function clamp(value: number, range: ClampRange): number {
  return Math.min(range.max, Math.max(range.min, value));
}

export function createDefaultViewState(
  manifest: SemanticMapManifestViewModel,
): SemanticMapViewState {
  return {
    target: [manifest.defaultView.target[0], manifest.defaultView.target[1]],
    zoom: manifest.defaultView.zoom,
  };
}

export function clampViewState(
  viewState: SemanticMapViewState,
  manifest: SemanticMapManifestViewModel,
): SemanticMapViewState {
  const [minX, minY, maxX, maxY] = manifest.worldBounds;

  return {
    target: [
      clamp(viewState.target[0], { max: maxX, min: minX }),
      clamp(viewState.target[1], { max: maxY, min: minY }),
    ],
    zoom: clamp(viewState.zoom, { max: manifest.maxZoom, min: 0 }),
  };
}

export function toDeckViewState(
  viewState: SemanticMapViewState,
  manifest: SemanticMapManifestViewModel,
): OrthographicViewState {
  return {
    maxZoom: manifest.maxZoom,
    minZoom: 0,
    target: [viewState.target[0], viewState.target[1], 0],
    zoom: viewState.zoom,
  };
}

export function fromDeckViewState(
  deckViewState: OrthographicViewState,
  manifest: SemanticMapManifestViewModel,
): SemanticMapViewState {
  const fallbackViewState = createDefaultViewState(manifest);
  const target = deckViewState.target ?? fallbackViewState.target;
  const zoom = Array.isArray(deckViewState.zoom)
    ? deckViewState.zoom[0]
    : (deckViewState.zoom ?? fallbackViewState.zoom);

  return clampViewState(
    {
      target: [target[0], target[1]],
      zoom,
    },
    manifest,
  );
}

export function getVisibleTileState({
  manifest,
  viewState,
}: GetVisibleTileArgs): VisibleTileState {
  const [minX, minY, maxX, maxY] = manifest.worldBounds;
  const clampedViewState = clampViewState(viewState, manifest);
  const z = Math.floor(clampedViewState.zoom);
  const tilesPerAxis = 2 ** z;
  const tileWidth = (maxX - minX) / tilesPerAxis;
  const tileHeight = (maxY - minY) / tilesPerAxis;

  const x = clamp(Math.floor((clampedViewState.target[0] - minX) / tileWidth), {
    max: tilesPerAxis - 1,
    min: 0,
  });
  const y = clamp(
    Math.floor((clampedViewState.target[1] - minY) / tileHeight),
    { max: tilesPerAxis - 1, min: 0 },
  );

  return {
    tileBounds: [
      minX + x * tileWidth,
      minY + y * tileHeight,
      minX + (x + 1) * tileWidth,
      minY + (y + 1) * tileHeight,
    ],
    x,
    y,
    z,
  };
}
