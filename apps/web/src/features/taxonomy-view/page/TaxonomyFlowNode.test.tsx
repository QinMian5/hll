// abstract: Renderer tests for taxonomy flow bubble nodes.
// out_of_scope: React Flow integration, layout math, and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

type TaxonomyFlowNodeProps = Parameters<typeof TaxonomyFlowNode>[0];

function makeNodeProps(data: TaxonomyLayoutNodeData): TaxonomyFlowNodeProps {
  return {
    data,
    deletable: false,
    draggable: false,
    dragging: false,
    dragHandle: undefined,
    height: 160,
    id: "bubble-1",
    isConnectable: false,
    parentId: undefined,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
    selected: false,
    selectable: true,
    sourcePosition: undefined,
    targetPosition: undefined,
    type: "bubble",
    width: 160,
    zIndex: 0,
  };
}

describe("TaxonomyFlowNode branch renderer", () => {
  it("renders branch nodes as layered figma bubbles without auxiliary affordance copy", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          depth: 1,
          label: "Mathematics",
          scope: "branch",
          targetNodeId: 2,
          tooltip: "Mathematics · 12 cards",
        })}
      />,
    );

    expect(screen.queryByText("Open")).not.toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-bubble-halo")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-bubble-surface")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-bubble-core-glow")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-bubble-sheen")).toBeInTheDocument();
    const label = screen.getByTestId("taxonomy-bubble-label");

    expect(label).toHaveAttribute("data-bubble-tone", "branch");
    expect(label.className).toContain("absolute");
    expect(label.className).toContain("inset-[18%]");
    expect(label.className).toContain("flex");
    expect(label.className).toContain("items-center");
    expect(label.className).toContain("justify-center");
  });
});

describe("TaxonomyFlowNode leaf renderer", () => {
  it("keeps leaf nodes in the shared bubble family and reveals content through disclosure only on hover", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          content: "Equation content",
          depth: 2,
          label: "Equation",
          scope: "inner",
          targetNodeId: null,
          tooltip: "Equation",
        })}
      />,
    );

    const leafNode = screen
      .getByText("Equation")
      .closest("[data-node-scope='inner']");

    expect(leafNode).toHaveAttribute("data-bubble-family", "taxonomy");
    expect(leafNode).toHaveAttribute("data-bubble-variant", "inner");
    expect(screen.queryByText("Equation content")).not.toBeInTheDocument();

    fireEvent.mouseEnter(leafNode as HTMLElement);

    expect(screen.getByTestId("taxonomy-bubble-disclosure")).toHaveTextContent(
      "Equation content",
    );
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.mouseLeave(leafNode as HTMLElement);
    expect(
      screen.queryByTestId("taxonomy-bubble-disclosure"),
    ).not.toBeInTheDocument();
  });

  it("renders outer leaf nodes through the same bubble family with restrained emphasis changes only", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          content: "Proof content",
          depth: 2,
          label: "Proof",
          scope: "outer",
          targetNodeId: null,
          tooltip: "Proof",
        })}
      />,
    );

    const outerLeafNode = screen
      .getByText("Proof")
      .closest("[data-node-scope='outer']");

    expect(outerLeafNode).toHaveAttribute("data-bubble-family", "taxonomy");
    expect(outerLeafNode).toHaveAttribute("data-bubble-variant", "outer");
    expect(
      within(outerLeafNode as HTMLElement).getByTestId("taxonomy-bubble-halo"),
    ).toBeInTheDocument();
    expect(
      within(outerLeafNode as HTMLElement).getByTestId(
        "taxonomy-bubble-surface",
      ),
    ).toBeInTheDocument();
    expect(
      within(outerLeafNode as HTMLElement).getByTestId("taxonomy-bubble-label"),
    ).toHaveAttribute("data-bubble-tone", "leaf");
  });
});
