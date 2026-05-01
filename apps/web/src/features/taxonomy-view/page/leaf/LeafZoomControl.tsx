// abstract: Responsive Figma-aligned zoom control for the taxonomy leaf graph.
// out_of_scope: deck.gl viewport ownership and zoom percentage math.

import { MinusIcon, PlusIcon } from "lucide-react";
import * as React from "react";

import {
  LEAF_ZOOM_CONTROL_MAX_PERCENT,
  LEAF_ZOOM_CONTROL_MIN_PERCENT,
  LEAF_ZOOM_CONTROL_SNAP_PERCENTS,
} from "./leafRendererConfig";
import {
  clampLeafZoomPercent,
  getNextLeafZoomSnap,
  getPreviousLeafZoomSnap,
  leafZoomPercentToTrackPosition,
  leafZoomPercentToTrackValue,
  leafZoomTrackPositionToPercent,
  leafZoomTrackValueToPercent,
  snapLeafZoomPercent,
} from "./leafZoomControl";

interface LeafZoomControlProps {
  readonly zoomPercent: number;
  readonly onZoomPercentChange: (percent: number) => void;
  readonly onZoomPercentCommit: (percent: number) => void;
}

const SLIDER_MIN = -2;
const SLIDER_MAX = 2;
const SLIDER_STEP = 0.01;

function makePositionStyle(
  variableName: "--leaf-zoom-active" | "--leaf-zoom-pos",
  position: number,
) {
  return {
    [variableName]: `${position * 100}%`,
  } as React.CSSProperties;
}

function publishStep(
  percent: number,
  onZoomPercentChange: (percent: number) => void,
  onZoomPercentCommit: (percent: number) => void,
) {
  onZoomPercentChange(percent);
  onZoomPercentCommit(percent);
}

function pointerEventToTrackPosition(event: React.PointerEvent<HTMLElement>) {
  const rect = event.currentTarget.getBoundingClientRect();

  if (rect.height > rect.width) {
    return 1 - (event.clientY - rect.top) / rect.height;
  }

  return (event.clientX - rect.left) / rect.width;
}

export function LeafZoomControl({
  onZoomPercentChange,
  onZoomPercentCommit,
  zoomPercent,
}: LeafZoomControlProps) {
  const dragPointerIdRef = React.useRef<number | null>(null);
  const pendingPointerPercentRef = React.useRef<number | null>(null);
  const clampedZoomPercent = clampLeafZoomPercent(zoomPercent);
  const sliderValue = leafZoomPercentToTrackValue(clampedZoomPercent);
  const activePosition = leafZoomPercentToTrackPosition(clampedZoomPercent);
  const activeStyle = makePositionStyle("--leaf-zoom-active", activePosition);
  const snapTicks = React.useMemo(
    () =>
      LEAF_ZOOM_CONTROL_SNAP_PERCENTS.map((snapPercent) => ({
        isThreshold: snapPercent === 100,
        position: leafZoomPercentToTrackPosition(snapPercent),
        snapPercent,
      })),
    [],
  );

  const publishPointerPosition = (event: React.PointerEvent<HTMLElement>) => {
    const percent = leafZoomTrackPositionToPercent(
      pointerEventToTrackPosition(event),
    );

    pendingPointerPercentRef.current = percent;
    onZoomPercentChange(percent);
  };

  const handleTrackPointerDown = (
    event: React.PointerEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();
    dragPointerIdRef.current = event.pointerId;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    publishPointerPosition(event);
  };

  const handleTrackPointerMove = (
    event: React.PointerEvent<HTMLDivElement>,
  ) => {
    if (dragPointerIdRef.current !== event.pointerId) {
      return;
    }

    publishPointerPosition(event);
  };

  const handleTrackPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragPointerIdRef.current !== event.pointerId) {
      return;
    }

    publishPointerPosition(event);
    onZoomPercentCommit(
      snapLeafZoomPercent(
        pendingPointerPercentRef.current ?? clampedZoomPercent,
      ),
    );
    pendingPointerPercentRef.current = null;
    dragPointerIdRef.current = null;
  };

  const handleTrackPointerCancel = () => {
    pendingPointerPercentRef.current = null;
    dragPointerIdRef.current = null;
  };

  const commitSliderValue = (value: string) => {
    onZoomPercentCommit(
      snapLeafZoomPercent(leafZoomTrackValueToPercent(Number(value))),
    );
  };

  return (
    <div
      className="absolute bottom-4 left-4 right-4 z-20 flex h-14 max-w-[408px] items-center justify-between rounded-[10px] border border-[#d9e2ee] bg-white/[0.94] px-4 shadow-[0_16px_32px_rgba(15,23,42,0.14)] md:bottom-6 md:left-auto md:right-6 md:h-[400px] md:w-[52px] md:max-w-none md:flex-col md:px-0 md:py-3"
      data-desktop-frame="52x400-right-24-bottom-24"
      data-mobile-frame="408x56-left-16-right-16-bottom-16"
      data-testid="leaf-zoom-control"
    >
      <button
        aria-label="Zoom out"
        className="order-1 flex size-8 items-center justify-center rounded-[8px] text-[#506279] transition hover:bg-[#eef4ff] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#78a3f3] md:order-5"
        onClick={() =>
          publishStep(
            getPreviousLeafZoomSnap(clampedZoomPercent),
            onZoomPercentChange,
            onZoomPercentCommit,
          )
        }
        type="button"
      >
        <MinusIcon aria-hidden="true" className="size-4" strokeWidth={2.4} />
      </button>

      <div
        aria-hidden="true"
        className="order-2 h-8 w-px bg-[#d9e2ee] md:h-px md:w-full"
      />

      <div
        className="relative order-3 h-4 w-[240px] cursor-pointer md:h-[276px] md:w-6"
        data-testid="leaf-zoom-track-hit-area"
        onPointerCancel={handleTrackPointerCancel}
        onPointerDown={handleTrackPointerDown}
        onPointerMove={handleTrackPointerMove}
        onPointerUp={handleTrackPointerUp}
      >
        <div className="absolute left-0 top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-[#d9e2ee] md:left-1/2 md:top-0 md:h-full md:w-1 md:-translate-x-1/2 md:translate-y-0" />
        <div
          className="absolute left-0 top-1/2 h-1 w-[var(--leaf-zoom-active)] -translate-y-1/2 rounded-full bg-[#78a3f3] md:bottom-0 md:left-1/2 md:top-auto md:h-[var(--leaf-zoom-active)] md:w-1 md:-translate-x-1/2 md:translate-y-0"
          data-testid="leaf-zoom-active-range"
          style={activeStyle}
        />
        {snapTicks.map(({ isThreshold, position, snapPercent }) => {
          return (
            <div
              aria-hidden="true"
              className={
                isThreshold
                  ? "absolute left-[var(--leaf-zoom-pos)] top-1/2 h-4 w-[2px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#315fba] md:bottom-[var(--leaf-zoom-pos)] md:left-1/2 md:top-auto md:h-[2px] md:w-4 md:translate-y-1/2"
                  : "absolute left-[var(--leaf-zoom-pos)] top-1/2 h-2 w-px -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#9fb0c6] md:bottom-[var(--leaf-zoom-pos)] md:left-1/2 md:top-auto md:h-px md:w-2 md:translate-y-1/2"
              }
              data-testid={
                isThreshold ? "leaf-zoom-threshold-tick" : "leaf-zoom-snap-tick"
              }
              data-track-position={position}
              data-zoom-percent={snapPercent}
              key={snapPercent}
              style={makePositionStyle("--leaf-zoom-pos", position)}
            />
          );
        })}
        <div
          aria-hidden="true"
          className="absolute left-[var(--leaf-zoom-active)] top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-[#78a3f3] shadow-[0_2px_8px_rgba(15,23,42,0.18)] md:bottom-[var(--leaf-zoom-active)] md:left-1/2 md:top-auto md:translate-y-1/2"
          data-testid="leaf-zoom-thumb"
          style={activeStyle}
        />
        <input
          aria-label="Leaf zoom"
          aria-valuemax={LEAF_ZOOM_CONTROL_MAX_PERCENT}
          aria-valuemin={LEAF_ZOOM_CONTROL_MIN_PERCENT}
          aria-valuenow={Math.round(clampedZoomPercent)}
          aria-valuetext={`${Math.round(clampedZoomPercent)}%`}
          className="pointer-events-none absolute left-0 top-1/2 z-10 h-14 w-full -translate-y-1/2 opacity-0 md:left-[-126px] md:top-1/2 md:h-[52px] md:w-[276px] md:-translate-y-1/2 md:-rotate-90"
          max={SLIDER_MAX}
          min={SLIDER_MIN}
          onBlur={(event) => commitSliderValue(event.currentTarget.value)}
          onChange={(event) =>
            onZoomPercentChange(
              leafZoomTrackValueToPercent(Number(event.currentTarget.value)),
            )
          }
          step={SLIDER_STEP}
          type="range"
          value={sliderValue}
        />
      </div>

      <div
        aria-hidden="true"
        className="order-4 h-8 w-px bg-[#d9e2ee] md:h-px md:w-full"
      />

      <button
        aria-label="Zoom in"
        className="order-5 flex size-8 items-center justify-center rounded-[8px] text-[#506279] transition hover:bg-[#eef4ff] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#78a3f3] md:order-1"
        onClick={() =>
          publishStep(
            getNextLeafZoomSnap(clampedZoomPercent),
            onZoomPercentChange,
            onZoomPercentCommit,
          )
        }
        type="button"
      >
        <PlusIcon aria-hidden="true" className="size-4" strokeWidth={2.4} />
      </button>
    </div>
  );
}
