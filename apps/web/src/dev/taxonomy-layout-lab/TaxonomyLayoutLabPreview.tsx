// abstract: Production leaf-scene preview for the standalone taxonomy layout lab.
// out_of_scope: Layout solver requests and parameter form controls.

import { useMemo, useState } from "react";

import type { TaxonomyCardScopeLayoutSliceResponse } from "../../features/taxonomy-view/data/taxonomyViewQueries";
import { LeafDeckScene } from "../../features/taxonomy-view/page/leaf/LeafDeckScene";
import { buildRenderableLeafLayout } from "../../features/taxonomy-view/page/leaf/leafLayoutAdapter";
import type {
  LeafOrthographicViewport,
  LeafSceneModel,
} from "../../features/taxonomy-view/page/leaf/leafSceneTypes";
import { buildLeafSceneModelBase } from "../../features/taxonomy-view/page/leaf/useLeafSceneModel";

interface TaxonomyLayoutLabPreviewProps {
  readonly layout: TaxonomyCardScopeLayoutSliceResponse | null;
}

export function TaxonomyLayoutLabPreview({
  layout,
}: TaxonomyLayoutLabPreviewProps) {
  const initialViewport = useMemo(() => buildInitialViewport(layout), [layout]);
  const [hoveredPointNodeId, setHoveredPointNodeId] = useState<number | null>(
    null,
  );
  const [selectedPointNodeId, setSelectedPointNodeId] = useState<number | null>(
    null,
  );
  const scene = useMemo(() => buildScene(layout), [layout]);

  if (!layout || !scene) {
    return (
      <div
        className="flex h-full items-center justify-center text-sm text-[#64748B]"
        data-testid="layout-lab-empty-preview"
      >
        No layout loaded
      </div>
    );
  }

  const activeFocusNodeId = selectedPointNodeId ?? hoveredPointNodeId;

  return (
    <div className="relative h-full min-h-0 overflow-hidden">
      <LeafDeckScene
        activeFocusNodeId={activeFocusNodeId}
        disclosure={null}
        hiddenLabelNodeId={null}
        hoveredPointNodeId={hoveredPointNodeId}
        initialViewport={initialViewport}
        isPointInteractionEnabled={true}
        onCanvasClick={() => {
          setSelectedPointNodeId(null);
        }}
        onPointClick={(nodeId) => {
          setSelectedPointNodeId((currentNodeId) =>
            currentNodeId === nodeId ? null : nodeId,
          );
        }}
        onPointHover={setHoveredPointNodeId}
        onViewportChange={() => undefined}
        scene={scene}
      />
    </div>
  );
}

function buildScene(
  layout: TaxonomyCardScopeLayoutSliceResponse | null,
): LeafSceneModel | null {
  if (!layout || layout.nodes.length === 0) {
    return null;
  }

  const renderableLayout = buildRenderableLeafLayout(layout);
  const sceneBase = buildLeafSceneModelBase({
    edges: renderableLayout.edges,
    layoutNodes: renderableLayout.nodes,
  });

  return {
    ...sceneBase,
    titleLabelNodes: [],
  };
}

function buildInitialViewport(
  layout: TaxonomyCardScopeLayoutSliceResponse | null,
): LeafOrthographicViewport {
  if (!layout) {
    return { target: [0, 0, 0], zoom: 0 };
  }

  const bounds = layout.requested_bounds;
  const centerX = (bounds.min_x + bounds.max_x) / 2;
  const centerY = (bounds.min_y + bounds.max_y) / 2;
  const spanX = bounds.max_x - bounds.min_x;
  const spanY = bounds.max_y - bounds.min_y;
  const largestSpan = Math.max(spanX, spanY, 1);
  const zoom = Math.max(-4, Math.min(2, Math.log2(700 / largestSpan)));

  return {
    target: [centerX, centerY, 0],
    zoom,
  };
}
