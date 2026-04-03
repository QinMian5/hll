// abstract: Debug overlay for semantic-map snapshot, level, and tile metadata.
// out_of_scope: DeckGL rendering internals and transport-query ownership.

import type { SemanticMapLevelViewModel } from "../data/mappers";
import type { VisibleTileState } from "../model/viewState";

interface DebugHudProps {
  readonly activeSemanticLevel: SemanticMapLevelViewModel;
  readonly isTileLoading: boolean;
  readonly onResetView: () => void;
  readonly regionCount: number;
  readonly version: string;
  readonly visibleTile: VisibleTileState;
}

export function DebugHud({
  activeSemanticLevel,
  isTileLoading,
  onResetView,
  regionCount,
  version,
  visibleTile,
}: DebugHudProps) {
  return (
    <aside className="debug-hud" aria-label="Semantic map debug metadata">
      <dl className="debug-hud-grid">
        <div>
          <dt>Current version</dt>
          <dd>{version}</dd>
        </div>
        <div>
          <dt>Active semantic level</dt>
          <dd>
            {activeSemanticLevel.displayName} ({activeSemanticLevel.stableId})
          </dd>
        </div>
        <div>
          <dt>Visible tile</dt>
          <dd>
            z{visibleTile.z} / {visibleTile.x}, {visibleTile.y}
          </dd>
        </div>
        <div>
          <dt>Tile status</dt>
          <dd>{isTileLoading ? "Loading" : `${regionCount} regions`}</dd>
        </div>
      </dl>
      <button className="debug-hud-reset" onClick={onResetView} type="button">
        Reset view
      </button>
    </aside>
  );
}
