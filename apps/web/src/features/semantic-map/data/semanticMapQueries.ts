// abstract: TanStack Query adapters for semantic-map contract-driven reads.
// out_of_scope: Page composition and deck.gl rendering logic.

import { queryOptions, useQuery } from "@tanstack/react-query";

import { mapManifestToViewModel, mapRegionTileToViewModel } from "./mappers";
import { createSemanticMapClient } from "./semanticMapClient";

export interface SemanticMapRegionTileQueryArgs {
  readonly semanticLevel: number;
  readonly version: string;
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

class SemanticMapRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "SemanticMapRequestError";
    this.status = status;
  }
}

const semanticMapQueryKeys = {
  currentManifest: ["semantic-map", "manifest", "current"] as const,
  regionTile: ({
    semanticLevel,
    version,
    x,
    y,
    z,
  }: SemanticMapRegionTileQueryArgs) =>
    ["semantic-map", "region-tile", version, semanticLevel, z, x, y] as const,
};

async function fetchCurrentManifest() {
  const result = await createSemanticMapClient().GET(
    "/semantic-map/manifest/current",
  );

  if (result.response.status === 404) {
    return null;
  }

  if (!result.response.ok) {
    throw new SemanticMapRequestError(
      `Semantic-map manifest request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error(
      "Semantic-map manifest response did not include a payload.",
    );
  }

  return mapManifestToViewModel(result.data);
}

async function fetchRegionTile(args: SemanticMapRegionTileQueryArgs) {
  const result = await createSemanticMapClient().GET(
    "/semantic-map/versions/{version}/tiles/regions/{semantic_level}/{z}/{x}/{y}",
    {
      params: {
        path: {
          semantic_level: args.semanticLevel,
          version: args.version,
          x: args.x,
          y: args.y,
          z: args.z,
        },
      },
    },
  );

  if (!result.response.ok) {
    throw new SemanticMapRequestError(
      `Semantic-map tile request failed with status ${result.response.status}.`,
      result.response.status,
    );
  }

  if (!result.data) {
    throw new Error("Semantic-map tile response did not include a payload.");
  }

  return mapRegionTileToViewModel(result.data);
}

export function semanticMapManifestQueryOptions() {
  return queryOptions({
    queryFn: fetchCurrentManifest,
    queryKey: semanticMapQueryKeys.currentManifest,
  });
}

export function semanticMapRegionTileQueryOptions(
  args: SemanticMapRegionTileQueryArgs,
) {
  return queryOptions({
    queryFn: () => fetchRegionTile(args),
    queryKey: semanticMapQueryKeys.regionTile(args),
  });
}

export function useSemanticMapManifestQuery() {
  return useQuery(semanticMapManifestQueryOptions());
}
