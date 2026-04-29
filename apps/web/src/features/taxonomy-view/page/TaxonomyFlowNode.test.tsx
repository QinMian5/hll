// abstract: Renderer tests for the branch-only taxonomy React Flow node.
// out_of_scope: Leaf deck.gl rendering, layout math, and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
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

describe("TaxonomyFlowNode", () => {
  it("renders branch nodes as layered figma bubbles without auxiliary affordance copy", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          depth: 1,
          graphNodeId: 2,
          label: "Mathematics",
          renderMode: "bubble",
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
    expect(
      screen.queryByTestId("taxonomy-handle-source"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("taxonomy-handle-target"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("taxonomy-bubble-disclosure"),
    ).not.toBeInTheDocument();

    const label = screen.getByTestId("taxonomy-bubble-label");

    expect(label).toHaveAttribute("data-bubble-tone", "branch");
    expect(label).toHaveClass("tracking-normal");
    expect(label).toHaveStyle({
      fontSize: "var(--taxonomy-bubble-label-font-size)",
      lineHeight: "var(--taxonomy-bubble-label-line-height)",
      maxWidth: "var(--taxonomy-bubble-label-width)",
    });
    expect(label.className).toContain("absolute");
    expect(label.className).toContain("inset-[18%]");
    expect(label.className).toContain("flex");
    expect(label.className).toContain("items-center");
    expect(label.className).toContain("justify-center");
  });

  it("rejects non-branch node payloads", () => {
    expect(() =>
      render(
        <TaxonomyFlowNode
          {...makeNodeProps({
            content: "Equation content",
            depth: 2,
            graphNodeId: 10,
            label: "Equation",
            renderMode: "point",
            scope: "inner",
            targetNodeId: null,
            tooltip: "Equation",
          })}
        />,
      ),
    ).toThrowError("TaxonomyFlowNode only supports branch bubble nodes.");
  });
});
