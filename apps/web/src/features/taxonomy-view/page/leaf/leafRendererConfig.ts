// abstract: Shared constants and defaults for the deck.gl-backed taxonomy leaf renderer.
// out_of_scope: Query orchestration and scene-layer instantiation.

export const LEAF_POINT_TITLE_ACTIVATION_ZOOM = 0.85;
export const LEAF_HYDRATION_OVERSCAN = 320;
export const LEAF_LAYOUT_TILE_SIZE = 2048;
export const LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS = 48;

export const LEAF_POINT_COLOR_RGB = [120, 163, 243] as const;
export const LEAF_POINT_OUTER_OPACITY = 0.68;
export const LEAF_POINT_INNER_OPACITY = 0.96;
export const LEAF_POINT_DIMMED_OPACITY = 0.28;
export const LEAF_POINT_HOVER_OPACITY = 1;
export const LEAF_EDGE_BASE_OPACITY = 0.52;
export const LEAF_EDGE_DIMMED_OPACITY = 0.22;
export const LEAF_EDGE_ACTIVE_OPACITY = 0.88;
