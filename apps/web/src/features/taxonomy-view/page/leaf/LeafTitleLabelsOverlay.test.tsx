// abstract: Contract tests for the DOM-based title label overlay in taxonomy leaf view.
// out_of_scope: deck.gl point and edge rendering behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it } from "vitest";

import {
  LeafTitleLabelsOverlay,
  type LeafTitleLabelsOverlayHandle,
} from "./LeafTitleLabelsOverlay";
import type { LeafSceneTitleLabelNode } from "./leafSceneTypes";

afterEach(() => {
  cleanup();
});

function makeTitleLabelNode(): LeafSceneTitleLabelNode {
  return {
    graphNodeId: 10,
    id: "leaf-10",
    position: { x: 700, y: 450 },
    scope: "inner",
    title: "Equation \\(E=mc^2\\)",
  };
}

describe("LeafTitleLabelsOverlay", () => {
  it("anchors display-only rich-text labels below projected point coordinates", () => {
    render(
      <LeafTitleLabelsOverlay
        canvas={{ height: 900, width: 1404 }}
        hiddenLabelNodeId={null}
        titleLabelNodes={[makeTitleLabelNode()]}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const label = screen.getByTestId("taxonomy-leaf-title-label-10");

    expect(
      screen.getByTestId("taxonomy-leaf-title-labels-overlay"),
    ).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(label).toHaveClass("pointer-events-none", { exact: false });
    expect(label).toHaveStyle({
      left: "0px",
      opacity: "1",
      top: "0px",
      transform: "translate3d(702px, 464px, 0px) translate(-50%, 0%)",
    });
  });

  it("updates rendered label positions from imperative live viewport sync", () => {
    const overlayRef = createRef<LeafTitleLabelsOverlayHandle>();

    render(
      <LeafTitleLabelsOverlay
        canvas={{ height: 900, width: 1404 }}
        hiddenLabelNodeId={null}
        ref={overlayRef}
        titleLabelNodes={[makeTitleLabelNode()]}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const label = screen.getByTestId("taxonomy-leaf-title-label-10");

    expect(label.style.transform).toContain("702px");
    expect(label.style.transform).toContain("464px");

    overlayRef.current?.syncViewport({
      target: [740, 480, 0],
      zoom: 0,
    });

    expect(label.style.transform).toContain("662px");
    expect(label.style.transform).toContain("434px");
  });

  it("hides only the selected node label when selected disclosure owns the title", () => {
    render(
      <LeafTitleLabelsOverlay
        canvas={{ height: 900, width: 1404 }}
        hiddenLabelNodeId={10}
        titleLabelNodes={[makeTitleLabelNode()]}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    expect(screen.getByTestId("taxonomy-leaf-title-label-10")).toHaveStyle({
      opacity: "0",
    });
  });
});
