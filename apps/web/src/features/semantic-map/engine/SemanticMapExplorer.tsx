// abstract: Manifest-ready semantic-map explorer that owns view state and tile reads.
// out_of_scope: Manifest bootstrap, empty-state routing, and OpenAPI client construction.

import { startTransition, useDeferredValue, useEffect, useState } from "react";

import type {
  SemanticMapManifestViewModel,
  SemanticMapPointViewModel,
} from "../data/mappers";
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
  const [selectedPoint, setSelectedPoint] =
    useState<SemanticMapPointViewModel | null>(null);
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

  useEffect(() => {
    if (!selectedPoint || !tileQuery.data) {
      return;
    }

    if (!tileQuery.data.points.some((point) => point.id === selectedPoint.id)) {
      setSelectedPoint(null);
    }
  }, [selectedPoint, tileQuery.data]);

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

  const handlePointSelect = (point: SemanticMapPointViewModel | null) => {
    startTransition(() => {
      setSelectedPoint(point);
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
        <>
          <SemanticMapCanvas
            manifest={manifest}
            onPointSelect={handlePointSelect}
            onViewStateChange={handleViewStateChange}
            tile={tileQuery.data ?? null}
            viewState={toDeckViewState(currentViewState, manifest)}
          />
          <section className="semantic-map-inspector" aria-live="polite">
            <h2>Point inspection</h2>
            {tileQuery.isPending ? (
              <p>Loading tile points.</p>
            ) : selectedPoint ? (
              <dl className="semantic-map-inspector-grid">
                <div>
                  <dt>Title</dt>
                  <dd>{selectedPoint.title}</dd>
                </div>
                <div>
                  <dt>Node ID</dt>
                  <dd>{selectedPoint.nodeId}</dd>
                </div>
                <div>
                  <dt>Leaf region</dt>
                  <dd>{selectedPoint.leafRegionId}</dd>
                </div>
              </dl>
            ) : (tileQuery.data?.points.length ?? 0) > 0 ? (
              <p>Click a point to inspect card details.</p>
            ) : (
              <p>No points are available in the current tile.</p>
            )}
          </section>
        </>
      )}
    </>
  );
}
