// abstract: Component tests for the Figma-aligned taxonomy leaf zoom control.
// out_of_scope: deck.gl viewport publication and browser-level visual regression.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeafZoomControl } from "./LeafZoomControl.tsx";
import { leafZoomTrackValueToPercent } from "./leafZoomControl";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderControl(zoomPercent = 125) {
  const onZoomPercentChange = vi.fn();
  const onZoomPercentCommit = vi.fn();

  render(
    <LeafZoomControl
      onZoomPercentChange={onZoomPercentChange}
      onZoomPercentCommit={onZoomPercentCommit}
      zoomPercent={zoomPercent}
    />,
  );

  return { onZoomPercentChange, onZoomPercentCommit };
}

function mockTrackRect(
  track: HTMLElement,
  rect: Pick<DOMRect, "height" | "left" | "top" | "width">,
) {
  vi.spyOn(track, "getBoundingClientRect").mockReturnValue({
    bottom: rect.top + rect.height,
    height: rect.height,
    left: rect.left,
    right: rect.left + rect.width,
    toJSON: () => undefined,
    top: rect.top,
    width: rect.width,
    x: rect.left,
    y: rect.top,
  });
}

describe("LeafZoomControl", () => {
  it("renders the Figma-aligned map control without visible percentages", () => {
    renderControl(125);

    const slider = screen.getByRole("slider", { name: "Leaf zoom" });
    expect(slider).toHaveAttribute("aria-valuemin", "25");
    expect(slider).toHaveAttribute("aria-valuemax", "400");
    expect(slider).toHaveAttribute("aria-valuenow", "125");
    expect(slider).toHaveAttribute("aria-valuetext", "125%");

    const control = screen.getByTestId("leaf-zoom-control");
    expect(control).toHaveAttribute(
      "data-desktop-frame",
      "52x400-right-24-bottom-24",
    );
    expect(control).toHaveAttribute(
      "data-mobile-frame",
      "408x56-center-bottom-16-min-side-16",
    );
    expect(control).toHaveClass(
      "left-1/2",
      "w-knowledge-leaf-zoom-width",
      "max-w-[calc(100%_-_2rem)]",
      "-translate-x-1/2",
      "md:landscape:translate-x-0",
    );
    expect(control).not.toHaveClass("md:right-6", "md:flex-col");
    expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
    const thresholdTick = within(control).getByTestId(
      "leaf-zoom-threshold-tick",
    );
    const ticks = [
      ...within(control).getAllByTestId("leaf-zoom-snap-tick"),
      thresholdTick,
    ].sort(
      (left, right) =>
        Number(left.getAttribute("data-zoom-percent")) -
        Number(right.getAttribute("data-zoom-percent")),
    );
    expect(ticks).toHaveLength(5);
    expect(
      ticks.map((tick) => tick.getAttribute("data-track-position")),
    ).toEqual(["0", "0.25", "0.5", "0.75", "1"]);
    expect(thresholdTick).toHaveAttribute("data-zoom-percent", "100");
    expect(
      screen.getByRole("button", { name: "Zoom in" }),
    ).not.toHaveTextContent("Zoom in");
    expect(
      screen.getByRole("button", { name: "Zoom out" }),
    ).not.toHaveTextContent("Zoom out");
  });

  it("publishes continuous slider changes and only snaps commits inside the magnetic radius", () => {
    const { onZoomPercentChange, onZoomPercentCommit } = renderControl(125);
    const slider = screen.getByRole("slider", { name: "Leaf zoom" });

    fireEvent.change(slider, { target: { value: "1" } });
    expect(onZoomPercentChange).toHaveBeenLastCalledWith(200);

    const continuousPercent = leafZoomTrackValueToPercent(0.24);
    const nearSnapPercent = leafZoomTrackValueToPercent(0.02);

    cleanup();
    render(
      <LeafZoomControl
        onZoomPercentChange={onZoomPercentChange}
        onZoomPercentCommit={onZoomPercentCommit}
        zoomPercent={continuousPercent}
      />,
    );
    fireEvent.change(screen.getByRole("slider", { name: "Leaf zoom" }), {
      target: { value: "0.24" },
    });
    fireEvent.blur(screen.getByRole("slider", { name: "Leaf zoom" }));
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(continuousPercent);

    cleanup();
    render(
      <LeafZoomControl
        onZoomPercentChange={onZoomPercentChange}
        onZoomPercentCommit={onZoomPercentCommit}
        zoomPercent={nearSnapPercent}
      />,
    );
    fireEvent.change(screen.getByRole("slider", { name: "Leaf zoom" }), {
      target: { value: "0.02" },
    });
    fireEvent.blur(screen.getByRole("slider", { name: "Leaf zoom" }));
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(100);
  });

  it("clicks the horizontal track through the same coordinate system as ticks", () => {
    const { onZoomPercentChange, onZoomPercentCommit } = renderControl(100);
    const track = screen.getByTestId("leaf-zoom-track-hit-area");
    mockTrackRect(track, { height: 16, left: 0, top: 0, width: 240 });

    fireEvent.pointerDown(track, { clientX: 180, clientY: 8, pointerId: 1 });
    expect(onZoomPercentChange).toHaveBeenLastCalledWith(200);

    fireEvent.pointerUp(track, { clientX: 180, clientY: 8, pointerId: 1 });
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(200);
  });

  it("clicks the vertical track with top as the maximum zoom stop", () => {
    const { onZoomPercentChange, onZoomPercentCommit } = renderControl(100);
    const track = screen.getByTestId("leaf-zoom-track-hit-area");
    mockTrackRect(track, { height: 276, left: 0, top: 0, width: 24 });

    fireEvent.pointerDown(track, { clientX: 12, clientY: 69, pointerId: 1 });
    expect(onZoomPercentChange).toHaveBeenLastCalledWith(200);

    fireEvent.pointerUp(track, { clientX: 12, clientY: 69, pointerId: 1 });
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(200);
  });

  it("centers landscape desktop vertical ticks and thumb on their bottom-positioned track coordinates", () => {
    renderControl(100);

    const control = screen.getByTestId("leaf-zoom-control");
    const verticalMarkers = [
      ...within(control).getAllByTestId("leaf-zoom-snap-tick"),
      within(control).getByTestId("leaf-zoom-threshold-tick"),
      within(control).getByTestId("leaf-zoom-thumb"),
    ];

    for (const marker of verticalMarkers) {
      expect(marker).toHaveClass("md:landscape:translate-y-1/2");
    }
    expect(within(control).getByTestId("leaf-zoom-active-range")).toHaveClass(
      "md:landscape:translate-y-0",
    );
  });

  it("steps plus and minus controls to adjacent snap stops", () => {
    const { onZoomPercentChange, onZoomPercentCommit } = renderControl(125);

    fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
    expect(onZoomPercentChange).toHaveBeenLastCalledWith(200);
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(200);

    fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));
    expect(onZoomPercentChange).toHaveBeenLastCalledWith(100);
    expect(onZoomPercentCommit).toHaveBeenLastCalledWith(100);
  });
});
