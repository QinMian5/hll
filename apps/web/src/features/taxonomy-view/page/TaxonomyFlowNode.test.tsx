// abstract: Renderer tests for taxonomy flow bubble nodes.
// out_of_scope: React Flow integration, layout math, and browser-level visual fidelity.

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
    expect(screen.getByTestId("taxonomy-bubble-label")).toHaveAttribute(
      "data-bubble-tone",
      "branch",
    );
  });
});
