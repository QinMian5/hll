// abstract: Transport-to-view-model mapping for semantic-map generated contracts.
// out_of_scope: HTTP transport execution and React query cache orchestration.

import type { components } from "@knowledge/contracts/generated/types";
import type { Readable } from "openapi-typescript-helpers";

type ManifestTransport = Readable<
  components["schemas"]["SemanticMapManifestResponse"]
>;
type TileTransport = Readable<components["schemas"]["SemanticMapTileResponse"]>;
type Bounds4 = Readable<components["schemas"]["Bounds4"]>;
type Point2 = Readable<components["schemas"]["Point2"]>;
type RegionGeometry = Readable<components["schemas"]["RegionGeometryPayload"]>;

export interface SemanticMapLevelViewModel {
  readonly childContentRole: string;
  readonly displayName: string;
  readonly level: number;
  readonly maxZoom: number;
  readonly minZoom: number;
  readonly regionRole: string;
  readonly stableId: string;
}

export interface SemanticMapManifestViewModel {
  readonly builtAt: string;
  readonly coordinateSystem: {
    readonly axisDirection: "x-right-y-up";
    readonly boundsFormat: "min_x_min_y_max_x_max_y";
    readonly kind: "cartesian2d";
  };
  readonly defaultSemanticLevel: number;
  readonly defaultView: {
    readonly target: Point2;
    readonly zoom: number;
  };
  readonly levels: readonly SemanticMapLevelViewModel[];
  readonly maxZoom: number;
  readonly schemaVersion: string;
  readonly tileSize: number;
  readonly version: string;
  readonly worldBounds: Bounds4;
}

export interface SemanticMapTileViewModel {
  readonly labels: readonly {
    readonly fontSize: number;
    readonly id: string;
    readonly labelRank: number;
    readonly position: readonly number[];
    readonly regionId: string;
    readonly text: string;
  }[];
  readonly regions: readonly {
    readonly bbox: readonly number[];
    readonly centroid: readonly number[];
    readonly childrenAvailable: boolean;
    readonly displayRank: number;
    readonly geometry: RegionGeometry;
    readonly id: string;
    readonly parentId: string | null;
    readonly regionName: string;
  }[];
  readonly schemaVersion: string;
  readonly semanticLevel: number;
  readonly stats: {
    readonly labelCount: number;
    readonly regionCount: number;
  };
  readonly tile: {
    readonly boundsFormat: "min_x_min_y_max_x_max_y";
    readonly tileBounds: Bounds4;
    readonly x: number;
    readonly y: number;
    readonly z: number;
  };
  readonly version: string;
}

export function mapManifestToViewModel(
  manifest: ManifestTransport,
): SemanticMapManifestViewModel {
  return {
    builtAt: manifest.built_at,
    coordinateSystem: {
      axisDirection: manifest.coordinate_system.axis_direction,
      boundsFormat: manifest.coordinate_system.bounds_format,
      kind: manifest.coordinate_system.kind,
    },
    defaultSemanticLevel: manifest.default_semantic_level,
    defaultView: {
      target: manifest.default_view.target,
      zoom: manifest.default_view.zoom,
    },
    levels: manifest.semantic_levels.map((level) => ({
      childContentRole: level.child_content_role,
      displayName: level.display_name,
      level: level.level,
      maxZoom: level.max_zoom,
      minZoom: level.min_zoom,
      regionRole: level.region_role,
      stableId: level.stable_id,
    })),
    maxZoom: manifest.max_zoom,
    schemaVersion: manifest.schema_version,
    tileSize: manifest.tile_size,
    version: manifest.version,
    worldBounds: manifest.world_bounds,
  };
}

export function mapRegionTileToViewModel(
  tile: TileTransport,
): SemanticMapTileViewModel {
  return {
    labels: tile.labels.map((label) => ({
      fontSize: label.font_size,
      id: label.id,
      labelRank: label.label_rank,
      position: label.position,
      regionId: label.region_id,
      text: label.text,
    })),
    regions: tile.regions.map((region) => ({
      bbox: region.bbox,
      centroid: region.centroid,
      childrenAvailable: region.children_available,
      displayRank: region.display_rank,
      geometry: region.geometry,
      id: region.id,
      parentId: region.parent_id,
      regionName: region.region_name,
    })),
    schemaVersion: tile.schema_version,
    semanticLevel: tile.semantic_level,
    stats: {
      labelCount: tile.stats.label_count,
      regionCount: tile.stats.region_count,
    },
    tile: {
      boundsFormat: tile.tile.bounds_format,
      tileBounds: tile.tile.tile_bounds,
      x: tile.tile.x,
      y: tile.tile.y,
      z: tile.tile.z,
    },
    version: tile.version,
  };
}
