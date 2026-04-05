// abstract: Deck.gl canvas wrapper for semantic-map region, edge, label, and point rendering.
// out_of_scope: HTTP transport, query caching, and point-detail panel composition.

import {
  OrthographicView,
  type OrthographicViewState,
  type PickingInfo,
  type ViewStateChangeParameters,
} from "@deck.gl/core";
import { DeckGL } from "@deck.gl/react";

import type {
  SemanticMapManifestViewModel,
  SemanticMapPointViewModel,
  SemanticMapTileViewModel,
} from "../data/mappers";
import { createEdgeTileLayer } from "./createEdgeTileLayer";
import { createLabelTileLayer } from "./createLabelTileLayer";
import {
  createPointTileLayer,
  isSemanticMapPointDatum,
} from "./createPointTileLayer";
import { createRegionTileLayer } from "./createRegionTileLayer";

const ORTHOGRAPHIC_VIEW = new OrthographicView({
  flipY: false,
  id: "semantic-map-view",
});

interface SemanticMapCanvasProps {
  readonly manifest: SemanticMapManifestViewModel;
  readonly onPointSelect: (point: SemanticMapPointViewModel | null) => void;
  readonly onViewStateChange: (
    viewState: ViewStateChangeParameters<OrthographicViewState>["viewState"],
  ) => void;
  readonly tile: SemanticMapTileViewModel | null;
  readonly viewState: OrthographicViewState;
}

export function SemanticMapCanvas({
  manifest,
  onPointSelect,
  onViewStateChange,
  tile,
  viewState,
}: SemanticMapCanvasProps) {
  const handleClick = (info: PickingInfo<unknown>) => {
    if (isSemanticMapPointDatum(info.object)) {
      onPointSelect(info.object);
      return;
    }
    onPointSelect(null);
  };

  const handleTooltip = (info: PickingInfo<unknown>) => {
    if (!isSemanticMapPointDatum(info.object)) {
      return null;
    }

    return { text: info.object.title };
  };

  return (
    <section
      className="semantic-map-canvas-shell"
      aria-label="Semantic map canvas"
    >
      <DeckGL
        controller={{
          doubleClickZoom: false,
          inertia: true,
        }}
        getTooltip={handleTooltip}
        height="100%"
        layers={[
          createRegionTileLayer(tile),
          createEdgeTileLayer(tile),
          createPointTileLayer(tile),
          createLabelTileLayer(tile),
        ]}
        onClick={handleClick}
        onViewStateChange={({ viewState: nextViewState }) =>
          onViewStateChange(nextViewState)
        }
        viewState={viewState}
        views={ORTHOGRAPHIC_VIEW}
        width="100%"
      />
      <div className="canvas-caption">
        Viewing version {manifest.version} in a Cartesian semantic-space
        projection.
      </div>
    </section>
  );
}
