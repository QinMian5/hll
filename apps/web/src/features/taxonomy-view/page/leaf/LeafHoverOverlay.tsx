// abstract: DOM hover disclosure overlay for hydrated leaf cards in the deck.gl scene.
// out_of_scope: deck.gl picking and viewport state management.

import { useLayoutEffect, useRef, useState } from "react";

import type { LeafHoverState } from "./leafSceneTypes";

interface LeafHoverOverlayProps {
  readonly hoverState: LeafHoverState | null;
}

const HOVER_GAP_PX = 8;
const HOVER_EDGE_PADDING_PX = 12;

interface OverlayPosition {
  readonly left: number;
  readonly top: number;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export function LeafHoverOverlay({ hoverState }: LeafHoverOverlayProps) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState<OverlayPosition | null>(null);

  useLayoutEffect(() => {
    if (!hoverState?.card.content || !overlayRef.current?.parentElement) {
      setPosition(null);
      return;
    }

    const parentRect = overlayRef.current.parentElement.getBoundingClientRect();
    const overlayRect = overlayRef.current.getBoundingClientRect();

    if (
      parentRect.width <= 0 ||
      parentRect.height <= 0 ||
      overlayRect.width <= 0 ||
      overlayRect.height <= 0
    ) {
      setPosition({
        left: hoverState.anchorX,
        top: hoverState.anchorBottomY + HOVER_GAP_PX,
      });
      return;
    }

    const halfWidth = overlayRect.width / 2;
    const minLeft = HOVER_EDGE_PADDING_PX + halfWidth;
    const maxLeft = parentRect.width - HOVER_EDGE_PADDING_PX - halfWidth;
    const clampedLeft = clamp(hoverState.anchorX, minLeft, maxLeft);
    const belowTop = hoverState.anchorBottomY + HOVER_GAP_PX;
    const aboveTop = hoverState.anchorTopY - overlayRect.height - HOVER_GAP_PX;
    const fitsBelow =
      belowTop + overlayRect.height <=
      parentRect.height - HOVER_EDGE_PADDING_PX;
    const fitsAbove = aboveTop >= HOVER_EDGE_PADDING_PX;

    setPosition({
      left: clampedLeft,
      top: fitsBelow
        ? belowTop
        : fitsAbove
          ? aboveTop
          : clamp(
              belowTop,
              HOVER_EDGE_PADDING_PX,
              parentRect.height - overlayRect.height - HOVER_EDGE_PADDING_PX,
            ),
    });
  }, [hoverState]);

  if (!hoverState?.card.content) {
    return null;
  }

  return (
    <div
      className="pointer-events-none absolute z-[22] w-max max-w-[min(17.5rem,42vw)] rounded-[18px] border border-[#d5e1f2]/85 bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(243,247,255,0.96)_100%)] px-4 py-3 text-left text-[12px] leading-[1.4] text-[#314967] shadow-[0_20px_50px_rgba(165,183,212,0.28)]"
      data-testid="taxonomy-leaf-hover-overlay"
      ref={overlayRef}
      style={{
        left: position?.left ?? hoverState.anchorX,
        top: position?.top ?? hoverState.anchorBottomY + HOVER_GAP_PX,
        transform: "translateX(-50%)",
      }}
    >
      {hoverState.card.content}
    </div>
  );
}
