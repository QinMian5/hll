// abstract: Contract tests for the bounded leaf viewport store used by the deck scene.
// out_of_scope: deck.gl integration details and DOM card overlay rendering.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS } from "./leafRendererConfig";
import { useLeafViewportStore } from "./useLeafViewportStore";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
});

describe("useLeafViewportStore", () => {
  it("publishes the latest viewport snapshot on a bounded cadence", () => {
    const onViewportSnapshotChange = vi.fn();

    function Harness() {
      const { publishViewport, viewState } = useLeafViewportStore({
        initialViewport: INITIAL_VIEWPORT,
        onViewportSnapshotChange,
      });

      return (
        <div>
          <div data-testid="leaf-viewport-zoom">{viewState.zoom}</div>
          <button
            onClick={() =>
              publishViewport({
                target: [710, 460, 0],
                zoom: 0.2,
              })
            }
            type="button"
          >
            Publish first viewport
          </button>
          <button
            onClick={() =>
              publishViewport({
                target: [720, 470, 0],
                zoom: 0.4,
              })
            }
            type="button"
          >
            Publish second viewport
          </button>
        </div>
      );
    }

    render(<Harness />);
    onViewportSnapshotChange.mockClear();

    fireEvent.click(
      screen.getByRole("button", { name: "Publish first viewport" }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Publish second viewport" }),
    );

    expect(screen.getByTestId("leaf-viewport-zoom")).toHaveTextContent("0.4");
    expect(onViewportSnapshotChange).not.toHaveBeenCalled();

    vi.advanceTimersByTime(LEAF_VIEWPORT_SNAPSHOT_INTERVAL_MS);

    expect(onViewportSnapshotChange).toHaveBeenCalledTimes(1);
    expect(onViewportSnapshotChange).toHaveBeenCalledWith({
      target: [720, 470, 0],
      zoom: 0.4,
    });
  });
});

const INITIAL_VIEWPORT = {
  target: [700, 450, 0],
  zoom: 0,
} as const;
