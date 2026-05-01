// abstract: Pure helpers for leaf zoom-control percentage, track, and snap behavior.
// out_of_scope: React control rendering and deck.gl viewport publication.

import {
  LEAF_POINT_TITLE_ACTIVATION_ZOOM,
  LEAF_ZOOM_CONTROL_MAX_PERCENT,
  LEAF_ZOOM_CONTROL_MIN_PERCENT,
  LEAF_ZOOM_CONTROL_SNAP_PERCENTS,
} from "./leafRendererConfig";

const MIN_TRACK_VALUE = Math.log2(LEAF_ZOOM_CONTROL_MIN_PERCENT / 100);
const MAX_TRACK_VALUE = Math.log2(LEAF_ZOOM_CONTROL_MAX_PERCENT / 100);
const TRACK_VALUE_RANGE = MAX_TRACK_VALUE - MIN_TRACK_VALUE;
const SNAP_TRACK_RADIUS = 0.05;

export function clampLeafZoomPercent(percent: number) {
  return Math.min(
    LEAF_ZOOM_CONTROL_MAX_PERCENT,
    Math.max(LEAF_ZOOM_CONTROL_MIN_PERCENT, percent),
  );
}

export function clampLeafZoomTrackPosition(position: number) {
  return Math.min(1, Math.max(0, position));
}

export function leafZoomPercentToTrackValue(percent: number) {
  return Math.log2(clampLeafZoomPercent(percent) / 100);
}

export function leafZoomTrackValueToPercent(trackValue: number) {
  return clampLeafZoomPercent(100 * 2 ** trackValue);
}

export function leafZoomPercentToTrackPosition(percent: number) {
  return (
    (leafZoomPercentToTrackValue(percent) - MIN_TRACK_VALUE) / TRACK_VALUE_RANGE
  );
}

export function leafZoomTrackPositionToPercent(position: number) {
  const trackValue =
    MIN_TRACK_VALUE + clampLeafZoomTrackPosition(position) * TRACK_VALUE_RANGE;

  return leafZoomTrackValueToPercent(trackValue);
}

export function deckZoomToLeafZoomPercent(deckZoom: number) {
  return clampLeafZoomPercent(
    100 * 2 ** (deckZoom - LEAF_POINT_TITLE_ACTIVATION_ZOOM),
  );
}

export function leafZoomPercentToDeckZoom(percent: number) {
  return (
    LEAF_POINT_TITLE_ACTIVATION_ZOOM + leafZoomPercentToTrackValue(percent)
  );
}

export function snapLeafZoomPercent(percent: number) {
  const clampedPercent = clampLeafZoomPercent(percent);
  const trackPosition = leafZoomPercentToTrackPosition(clampedPercent);
  const nearestSnapPercent = LEAF_ZOOM_CONTROL_SNAP_PERCENTS.reduce(
    (nearest, snapPercent) =>
      Math.abs(leafZoomPercentToTrackPosition(snapPercent) - trackPosition) <
      Math.abs(leafZoomPercentToTrackPosition(nearest) - trackPosition)
        ? snapPercent
        : nearest,
  );
  const nearestSnapDistance = Math.abs(
    leafZoomPercentToTrackPosition(nearestSnapPercent) - trackPosition,
  );

  return nearestSnapDistance <= SNAP_TRACK_RADIUS
    ? nearestSnapPercent
    : clampedPercent;
}

export function getNextLeafZoomSnap(percent: number) {
  const clampedPercent = clampLeafZoomPercent(percent);

  return (
    LEAF_ZOOM_CONTROL_SNAP_PERCENTS.find(
      (snapPercent) => snapPercent > clampedPercent,
    ) ?? LEAF_ZOOM_CONTROL_MAX_PERCENT
  );
}

export function getPreviousLeafZoomSnap(percent: number) {
  const clampedPercent = clampLeafZoomPercent(percent);

  for (
    let index = LEAF_ZOOM_CONTROL_SNAP_PERCENTS.length - 1;
    index >= 0;
    index -= 1
  ) {
    const snapPercent = LEAF_ZOOM_CONTROL_SNAP_PERCENTS[index];

    if (snapPercent < clampedPercent) {
      return snapPercent;
    }
  }

  return LEAF_ZOOM_CONTROL_MIN_PERCENT;
}
