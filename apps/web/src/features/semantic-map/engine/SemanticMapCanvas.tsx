// abstract: Deck.gl canvas wrapper for semantic-map region and label rendering.
// out_of_scope: HTTP transport, query caching, and debug overlay composition.

import {
  OrthographicView,
  type OrthographicViewState,
  type ViewStateChangeParameters,
} from "@deck.gl/core";
import { DeckGL } from "@deck.gl/react";

import type {
  SemanticMapManifestViewModel,
  SemanticMapTileViewModel,
} from "../data/mappers";
import { createLabelTileLayer } from "./createLabelTileLayer";
import { createRegionTileLayer } from "./createRegionTileLayer";

const ORTHOGRAPHIC_VIEW = new OrthographicView({
  flipY: false,
  id: "semantic-map-view",
});

interface SemanticMapCanvasProps {
  readonly manifest: SemanticMapManifestViewModel;
  readonly onViewStateChange: (
    viewState: ViewStateChangeParameters<OrthographicViewState>["viewState"],
  ) => void;
  readonly tile: SemanticMapTileViewModel | null;
  readonly viewState: OrthographicViewState;
}

export function SemanticMapCanvas({
  manifest,
  onViewStateChange,
  tile,
  viewState,
}: SemanticMapCanvasProps) {
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
        height="100%"
        layers={[createRegionTileLayer(tile), createLabelTileLayer(tile)]}
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
