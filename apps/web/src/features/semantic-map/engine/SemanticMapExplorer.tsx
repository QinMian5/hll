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

interface ConnectedPointViewModel {
  readonly point: SemanticMapPointViewModel;
  readonly strength: number;
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

  const selectedNodeId = selectedPoint?.nodeId ?? null;
  const highlightedNodeIds = new Set<number>();
  const connectedPoints: ConnectedPointViewModel[] = [];
  if (selectedNodeId !== null && tileQuery.data) {
    const connectedStrengthByNodeId = new Map<number, number>();
    for (const edge of tileQuery.data.edges) {
      if (edge.sourceNodeId === selectedNodeId) {
        const previousStrength =
          connectedStrengthByNodeId.get(edge.targetNodeId) ?? 0;
        connectedStrengthByNodeId.set(
          edge.targetNodeId,
          Math.max(previousStrength, edge.strength),
        );
      } else if (edge.targetNodeId === selectedNodeId) {
        const previousStrength =
          connectedStrengthByNodeId.get(edge.sourceNodeId) ?? 0;
        connectedStrengthByNodeId.set(
          edge.sourceNodeId,
          Math.max(previousStrength, edge.strength),
        );
      }
    }

    for (const nodeId of connectedStrengthByNodeId.keys()) {
      highlightedNodeIds.add(nodeId);
    }

    for (const point of tileQuery.data.points) {
      const strength = connectedStrengthByNodeId.get(point.nodeId);
      if (strength !== undefined) {
        connectedPoints.push({ point, strength });
      }
    }

    connectedPoints.sort(
      (left, right) =>
        right.strength - left.strength ||
        left.point.title.localeCompare(right.point.title),
    );
  }

  const handleConnectedPointSelect = (nodeId: number) => {
    if (!tileQuery.data) {
      return;
    }
    const point =
      tileQuery.data.points.find((candidate) => candidate.nodeId === nodeId) ??
      null;
    handlePointSelect(point);
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
            highlightedNodeIds={highlightedNodeIds}
            manifest={manifest}
            onPointSelect={handlePointSelect}
            onViewStateChange={handleViewStateChange}
            selectedNodeId={selectedNodeId}
            tile={tileQuery.data ?? null}
            viewState={toDeckViewState(currentViewState, manifest)}
          />
          <section className="semantic-map-inspector" aria-live="polite">
            <h2>Point inspection</h2>
            {tileQuery.isPending ? (
              <p>Loading tile points.</p>
            ) : selectedPoint ? (
              <>
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
                  <div>
                    <dt>Connected cards</dt>
                    <dd>{connectedPoints.length}</dd>
                  </div>
                </dl>
                {connectedPoints.length > 0 ? (
                  <ul className="semantic-map-inspector-list">
                    {connectedPoints.map((connected) => (
                      <li
                        key={connected.point.nodeId}
                        className="semantic-map-inspector-list-item"
                      >
                        <button
                          className="semantic-map-inspector-link"
                          onClick={() =>
                            handleConnectedPointSelect(connected.point.nodeId)
                          }
                          type="button"
                        >
                          {connected.point.title}
                        </button>
                        <span className="semantic-map-inspector-strength">
                          {connected.strength.toFixed(2)}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No connected cards in the current tile.</p>
                )}
              </>
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
