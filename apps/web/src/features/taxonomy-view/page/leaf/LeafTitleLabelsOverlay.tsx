// abstract: DOM overlay host for display-only taxonomy leaf title labels.
// out_of_scope: deck.gl point picking, disclosure content, and title hydration ownership.

import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
} from "react";

import { KnowledgeRichText } from "../../../../shared/ui";
import type { LayoutViewport } from "../layout/taxonomyLayoutTypes";
import type {
  LeafOrthographicViewport,
  LeafSceneTitleLabelNode,
} from "./leafSceneTypes";

interface LeafTitleLabelsOverlayProps {
  readonly canvas: LayoutViewport;
  readonly hiddenLabelNodeId: number | null;
  readonly titleLabelNodes: readonly LeafSceneTitleLabelNode[];
  readonly viewport: LeafOrthographicViewport;
}

export interface LeafTitleLabelsOverlayHandle {
  syncViewport: (viewport: LeafOrthographicViewport) => void;
}

interface ProjectedPoint {
  readonly x: number;
  readonly y: number;
}

function scaleFromZoom(zoom: number) {
  return 2 ** zoom;
}

export function projectLeafWorldPoint(
  canvas: LayoutViewport,
  viewport: LeafOrthographicViewport,
  point: { readonly x: number; readonly y: number },
): ProjectedPoint {
  const [targetX, targetY] = viewport.target;
  const scale = scaleFromZoom(viewport.zoom);

  return {
    x: (point.x - targetX) * scale + canvas.width / 2,
    y: (point.y - targetY) * scale + canvas.height / 2,
  };
}

function projectedTitleTransform(projected: ProjectedPoint) {
  return `translate3d(${projected.x}px, ${projected.y + 8}px, 0px) translate(-50%, 0%)`;
}

export const LeafTitleLabelsOverlay = forwardRef<
  LeafTitleLabelsOverlayHandle,
  LeafTitleLabelsOverlayProps
>(function LeafTitleLabelsOverlay(
  { canvas, hiddenLabelNodeId, titleLabelNodes, viewport },
  ref,
) {
  const labelRefs = useRef(new Map<number, HTMLSpanElement | null>());
  const canvasRef = useRef(canvas);
  const titleLabelNodesRef = useRef(titleLabelNodes);
  const viewportRef = useRef(viewport);

  const syncViewport = useCallback((nextViewport: LeafOrthographicViewport) => {
    viewportRef.current = nextViewport;

    for (const label of titleLabelNodesRef.current) {
      const element = labelRefs.current.get(label.graphNodeId);

      if (!element) {
        continue;
      }

      const projected = projectLeafWorldPoint(
        canvasRef.current,
        nextViewport,
        label.position,
      );

      element.style.transform = projectedTitleTransform(projected);
    }
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      syncViewport,
    }),
    [syncViewport],
  );

  useLayoutEffect(() => {
    canvasRef.current = canvas;
    syncViewport(viewportRef.current);
  }, [canvas, syncViewport]);

  useLayoutEffect(() => {
    titleLabelNodesRef.current = titleLabelNodes;
    syncViewport(viewportRef.current);
  }, [syncViewport, titleLabelNodes]);

  useLayoutEffect(() => {
    viewportRef.current = viewport;
    syncViewport(viewport);
  }, [syncViewport, viewport]);

  return (
    <div
      className="pointer-events-none absolute inset-0 z-[16]"
      data-testid="taxonomy-leaf-title-labels-overlay"
    >
      {titleLabelNodes.map((label) => {
        const projected = projectLeafWorldPoint(
          canvas,
          viewport,
          label.position,
        );

        return (
          <span
            className="pointer-events-none absolute block max-w-[11rem] text-center text-[11px] leading-[1.25] font-medium text-[rgba(38,52,77,0.82)] tracking-normal transition-opacity duration-150"
            data-testid={`taxonomy-leaf-title-label-${label.graphNodeId}`}
            key={label.id}
            ref={(element) => {
              labelRefs.current.set(label.graphNodeId, element);
            }}
            style={{
              left: "0px",
              opacity: hiddenLabelNodeId === label.graphNodeId ? 0 : 1,
              top: "0px",
              transform: projectedTitleTransform(projected),
            }}
          >
            <KnowledgeRichText text={label.title} variant="leaf-label" />
          </span>
        );
      })}
    </div>
  );
});
