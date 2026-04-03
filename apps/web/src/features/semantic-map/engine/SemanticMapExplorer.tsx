// abstract: Manifest-ready semantic-map explorer that owns view state and tile reads.
// out_of_scope: Manifest bootstrap, empty-state routing, and OpenAPI client construction.

import { startTransition, useDeferredValue, useEffect, useState } from "react";

import type { SemanticMapManifestViewModel } from "../data/mappers";
import { useSemanticMapRegionTileQuery } from "../data/semanticMapQueries";
import { getSemanticZoomState } from "../model/semanticLod";
import {
  clampViewState,
  createDefaultViewState,
  fromDeckViewState,
  getVisibleTileState,
  type SemanticMapViewState,
  toDeckViewState,
} from "../model/viewState";
import { DebugHud } from "../ui/DebugHud";
import { SemanticMapCanvas } from "./SemanticMapCanvas";

interface SemanticMapExplorerProps {
  readonly manifest: SemanticMapManifestViewModel;
}

export function SemanticMapExplorer({ manifest }: SemanticMapExplorerProps) {
  const [viewState, setViewState] = useState<SemanticMapViewState | null>(null);
  const currentViewState = viewState ?? createDefaultViewState(manifest);
  const deferredViewState = useDeferredValue(currentViewState);
  const semanticZoomState = getSemanticZoomState({
    defaultSemanticLevel: manifest.defaultSemanticLevel,
    levels: manifest.levels,
    zoom: deferredViewState.zoom,
  });
  const visibleTile = getVisibleTileState({
    manifest,
    viewState: deferredViewState,
  });
  const tileQuery = useSemanticMapRegionTileQuery({
    semanticLevel: semanticZoomState.activeLevel.level,
    version: manifest.version,
    x: visibleTile.x,
    y: visibleTile.y,
    z: visibleTile.z,
  });

  useEffect(() => {
    setViewState(createDefaultViewState(manifest));
  }, [manifest]);

  const handleResetView = () => {
    startTransition(() => {
      setViewState(createDefaultViewState(manifest));
    });
  };

  const handleViewStateChange = (
    nextViewState: Parameters<typeof fromDeckViewState>[0],
  ) => {
    startTransition(() => {
      setViewState(
        clampViewState(fromDeckViewState(nextViewState, manifest), manifest),
      );
    });
  };

  return (
    <>
      <DebugHud
        activeSemanticLevel={semanticZoomState.activeLevel}
        isTileLoading={tileQuery.isPending}
        onResetView={handleResetView}
        regionCount={tileQuery.data?.stats.regionCount ?? 0}
        version={manifest.version}
        visibleTile={visibleTile}
      />
      {tileQuery.isError ? (
        <section className="error-state" role="alert">
          <h2>Tile request failed</h2>
          <p>{tileQuery.error.message}</p>
        </section>
      ) : (
        <SemanticMapCanvas
          manifest={manifest}
          onViewStateChange={handleViewStateChange}
          tile={tileQuery.data ?? null}
          viewState={toDeckViewState(currentViewState, manifest)}
        />
      )}
    </>
  );
}
