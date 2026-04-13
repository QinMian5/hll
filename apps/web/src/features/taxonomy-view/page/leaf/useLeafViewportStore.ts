// abstract: Local viewport store that separates high-frequency deck camera updates from bounded React snapshots.
// out_of_scope: World-model layout computation and DOM card overlay rendering.

import { useCallback, useEffect, useRef, useState } from "react";

import { LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS } from "./leafRendererConfig";
import type { LeafOrthographicViewport } from "./leafSceneTypes";

function cloneViewport(
  viewport: LeafOrthographicViewport,
): LeafOrthographicViewport {
  return {
    target: [...viewport.target] as const,
    zoom: viewport.zoom,
  };
}

function equalViewport(
  left: LeafOrthographicViewport,
  right: LeafOrthographicViewport,
) {
  return (
    left.zoom === right.zoom &&
    left.target[0] === right.target[0] &&
    left.target[1] === right.target[1] &&
    left.target[2] === right.target[2]
  );
}

interface UseLeafViewportStoreOptions {
  readonly initialViewport: LeafOrthographicViewport;
  readonly onViewportSnapshotChange: (
    viewport: LeafOrthographicViewport,
  ) => void;
}

export function useLeafViewportStore({
  initialViewport,
  onViewportSnapshotChange,
}: UseLeafViewportStoreOptions) {
  const latestViewportRef = useRef(cloneViewport(initialViewport));
  const snapshotViewportRef = useRef(cloneViewport(initialViewport));
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [viewState, setViewState] = useState(() =>
    cloneViewport(initialViewport),
  );

  const clearScheduledSnapshot = useCallback(() => {
    if (timeoutRef.current === null) {
      return;
    }

    clearTimeout(timeoutRef.current);
    timeoutRef.current = null;
  }, []);

  const commitViewportSnapshot = useCallback(
    (viewport: LeafOrthographicViewport) => {
      if (equalViewport(snapshotViewportRef.current, viewport)) {
        return;
      }

      const snapshot = cloneViewport(viewport);
      snapshotViewportRef.current = snapshot;
      onViewportSnapshotChange(snapshot);
    },
    [onViewportSnapshotChange],
  );

  const flushScheduledSnapshot = useCallback(() => {
    timeoutRef.current = null;
    commitViewportSnapshot(latestViewportRef.current);
  }, [commitViewportSnapshot]);

  const scheduleViewportSnapshot = useCallback(() => {
    if (timeoutRef.current !== null) {
      return;
    }

    timeoutRef.current = setTimeout(
      flushScheduledSnapshot,
      LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS,
    );
  }, [flushScheduledSnapshot]);

  const publishViewport = useCallback(
    (viewport: LeafOrthographicViewport) => {
      const nextViewport = cloneViewport(viewport);

      latestViewportRef.current = nextViewport;
      setViewState((currentViewport) => {
        if (equalViewport(currentViewport, nextViewport)) {
          return currentViewport;
        }

        return nextViewport;
      });
      scheduleViewportSnapshot();
    },
    [scheduleViewportSnapshot],
  );

  useEffect(() => {
    const nextViewport = cloneViewport(initialViewport);

    clearScheduledSnapshot();
    latestViewportRef.current = nextViewport;
    snapshotViewportRef.current = nextViewport;
    setViewState(nextViewport);
    onViewportSnapshotChange(nextViewport);
  }, [clearScheduledSnapshot, initialViewport, onViewportSnapshotChange]);

  useEffect(() => {
    return () => {
      clearScheduledSnapshot();
    };
  }, [clearScheduledSnapshot]);

  return {
    publishViewport,
    viewState,
  };
}
