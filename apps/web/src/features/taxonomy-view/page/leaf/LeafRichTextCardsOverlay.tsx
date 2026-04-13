// abstract: DOM overlay host for hydrated taxonomy leaf cards that need shared rich-text rendering.
// out_of_scope: deck.gl point and edge rendering, viewport state ownership, and leaf detail fetching.

import { useLayoutEffect, useRef } from "react";

import { KnowledgeRichText } from "../../../../shared/ui";
import type {
  LayoutViewport,
  LeafCardMeasuredSize,
} from "../layout/taxonomyLayoutTypes";
import type {
  LeafHoverState,
  LeafOrthographicViewport,
  LeafSceneCardNode,
} from "./leafSceneTypes";

interface LeafRichTextCardsOverlayProps {
  readonly canvas: LayoutViewport;
  readonly cardNodes: readonly LeafSceneCardNode[];
  readonly hoveredNodeId: number | null;
  readonly neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>;
  readonly onCardMeasurementsChange?: (
    measurements: ReadonlyArray<
      { readonly graphNodeId: number } & LeafCardMeasuredSize
    >,
  ) => void;
  readonly onHoverChange: (hoverState: LeafHoverState | null) => void;
  readonly viewport: LeafOrthographicViewport;
}

interface ProjectedPoint {
  readonly x: number;
  readonly y: number;
}

function scaleFromZoom(zoom: number) {
  return 2 ** zoom;
}

function fallbackHoverState(
  card: LeafSceneCardNode,
  projected: ProjectedPoint,
): LeafHoverState {
  return {
    anchorBottomY: projected.y + card.size.height / 2,
    anchorTopY: projected.y - card.size.height / 2,
    anchorX: projected.x,
    card,
  };
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

function cardToneClasses(
  card: LeafSceneCardNode,
  hoveredNodeId: number | null,
  neighborNodeIdsByNodeId: ReadonlyMap<number, ReadonlySet<number>>,
) {
  if (hoveredNodeId === null) {
    return card.scope === "inner"
      ? "border-[rgba(214,227,247,0.86)] bg-[rgba(255,255,255,0.94)] text-[rgba(18,23,41,0.96)] shadow-[0_18px_42px_rgba(107,133,189,0.14)]"
      : "border-[rgba(210,222,242,0.92)] bg-[rgba(241,246,252,0.96)] text-[rgba(34,47,70,0.94)] shadow-[0_18px_42px_rgba(107,133,189,0.12)]";
  }

  if (card.graphNodeId === hoveredNodeId) {
    return "border-[rgba(182,204,242,0.98)] bg-[rgba(255,255,255,0.98)] text-[rgba(15,23,42,1)] shadow-[0_20px_48px_rgba(86,122,194,0.22)]";
  }

  const neighbors =
    neighborNodeIdsByNodeId.get(hoveredNodeId) ?? new Set<number>();
  if (neighbors.has(card.graphNodeId)) {
    return "border-[rgba(204,219,243,0.96)] bg-[rgba(247,250,255,0.96)] text-[rgba(30,41,59,0.94)] shadow-[0_18px_42px_rgba(107,133,189,0.14)]";
  }

  return "border-[rgba(214,223,238,0.72)] bg-[rgba(238,243,250,0.74)] text-[rgba(91,107,132,0.76)] opacity-70 shadow-[0_12px_28px_rgba(107,133,189,0.08)]";
}

function buildHoverStateFromElement(options: {
  readonly card: LeafSceneCardNode;
  readonly element: HTMLElement;
  readonly overlayElement: HTMLDivElement | null;
  readonly projected: ProjectedPoint;
}): LeafHoverState {
  const fallbackState = fallbackHoverState(options.card, options.projected);

  if (!options.overlayElement) {
    return fallbackState;
  }

  const overlayRect = options.overlayElement.getBoundingClientRect();
  const elementRect = options.element.getBoundingClientRect();

  if (
    overlayRect.width <= 0 ||
    overlayRect.height <= 0 ||
    elementRect.width <= 0 ||
    elementRect.height <= 0
  ) {
    return fallbackState;
  }

  const anchorTopY = elementRect.top - overlayRect.top;

  return {
    anchorBottomY: anchorTopY + elementRect.height,
    anchorTopY,
    anchorX: elementRect.left - overlayRect.left + elementRect.width / 2,
    card: options.card,
  };
}

export function LeafRichTextCardsOverlay({
  canvas,
  cardNodes,
  hoveredNodeId,
  neighborNodeIdsByNodeId,
  onCardMeasurementsChange,
  onHoverChange,
  viewport,
}: LeafRichTextCardsOverlayProps) {
  const cardRefs = useRef(new Map<number, HTMLButtonElement | null>());
  const overlayRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!onCardMeasurementsChange) {
      return;
    }

    const measurements = cardNodes.flatMap((card) => {
      const element = cardRefs.current.get(card.graphNodeId);

      if (!element) {
        return [];
      }

      const rect = element.getBoundingClientRect();

      if (rect.width <= 0 || rect.height <= 0) {
        return [];
      }

      return [
        {
          graphNodeId: card.graphNodeId,
          height: rect.height,
          width: rect.width,
        },
      ];
    });

    if (measurements.length > 0) {
      onCardMeasurementsChange(measurements);
    }
  }, [cardNodes, onCardMeasurementsChange]);

  return (
    <div
      className="pointer-events-none absolute inset-0 z-[16]"
      data-testid="taxonomy-leaf-rich-text-cards-overlay"
      ref={overlayRef}
    >
      {cardNodes.map((card) => {
        const projected = projectLeafWorldPoint(
          canvas,
          viewport,
          card.position,
        );

        return (
          <button
            aria-label={card.label}
            className={`pointer-events-auto absolute flex h-auto appearance-none items-center justify-center rounded-[18px] border px-4 py-3 text-center transition-[opacity,box-shadow,border-color,background-color] duration-150 ${cardToneClasses(card, hoveredNodeId, neighborNodeIdsByNodeId)}`}
            data-testid={`taxonomy-leaf-rich-text-card-${card.graphNodeId}`}
            key={card.id}
            ref={(element) => {
              cardRefs.current.set(card.graphNodeId, element);
            }}
            onFocus={(event) => {
              onHoverChange(
                buildHoverStateFromElement({
                  card,
                  element: event.currentTarget,
                  overlayElement: overlayRef.current,
                  projected,
                }),
              );
            }}
            onBlur={() => {
              onHoverChange(null);
            }}
            onMouseEnter={(event) => {
              onHoverChange(
                buildHoverStateFromElement({
                  card,
                  element: event.currentTarget,
                  overlayElement: overlayRef.current,
                  projected,
                }),
              );
            }}
            onMouseLeave={() => {
              onHoverChange(null);
            }}
            style={{
              left: `${projected.x}px`,
              minHeight: `${card.size.height}px`,
              top: `${projected.y}px`,
              transform: "translate(-50%, -50%)",
              width: `${card.size.width}px`,
            }}
            type="button"
          >
            <KnowledgeRichText text={card.label} variant="title" />
          </button>
        );
      })}
    </div>
  );
}
