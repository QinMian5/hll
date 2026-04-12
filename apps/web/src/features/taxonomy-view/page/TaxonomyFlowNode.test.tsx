// abstract: Renderer tests for taxonomy flow bubble nodes.
// out_of_scope: React Flow integration, layout math, and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

vi.mock("@xyflow/react", async () => {
  const actual =
    await vi.importActual<typeof import("@xyflow/react")>("@xyflow/react");

  return {
    ...actual,
    Handle: ({
      className,
      "data-handle-anchor": dataHandleAnchor,
      "data-testid": dataTestId,
      id,
      type,
    }: {
      readonly className?: string;
      readonly "data-handle-anchor"?: string;
      readonly "data-testid"?: string;
      readonly id?: string;
      readonly type?: string;
    }) => (
      <div
        className={className}
        data-handle-anchor={dataHandleAnchor}
        data-handle-id={id}
        data-handle-type={type}
        data-testid={dataTestId}
      />
    ),
  };
});

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
  it("renders hydrated leaf nodes as centered cards and reveals content through disclosure only on hover", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          content: "Equation content",
          depth: 2,
          graphNodeId: 10,
          label: "Equation",
          renderMode: "card",
          scope: "inner",
          targetNodeId: null,
          tooltip: "Equation",
        })}
      />,
    );

    const leafNode = screen
      .getByText("Equation")
      .closest("[data-node-scope='inner']");

    expect(leafNode).toHaveAttribute("data-node-presentation", "card");
    expect(
      within(leafNode as HTMLElement).getByTestId("taxonomy-leaf-card-surface"),
    ).toHaveAttribute("data-node-shape", "card");
    expect(
      within(leafNode as HTMLElement).getByTestId("taxonomy-card-label"),
    ).toHaveClass("text-center");
    expect(
      within(leafNode as HTMLElement).getByTestId("taxonomy-handle-target"),
    ).toHaveAttribute("data-handle-anchor", "center");
    expect(
      within(leafNode as HTMLElement).getByTestId("taxonomy-handle-source"),
    ).toHaveAttribute("data-handle-anchor", "center");
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

  it("renders outer leaf nodes as restrained cards rather than circular bubbles", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          content: "Proof content",
          depth: 2,
          graphNodeId: 11,
          label: "Proof",
          renderMode: "card",
          scope: "outer",
          targetNodeId: null,
          tooltip: "Proof",
        })}
      />,
    );

    const outerLeafNode = screen
      .getByText("Proof")
      .closest("[data-node-scope='outer']");

    expect(
      within(outerLeafNode as HTMLElement).getByTestId(
        "taxonomy-leaf-card-surface",
      ),
    ).toHaveAttribute("data-node-shape", "card");
    expect(
      within(outerLeafNode as HTMLElement).getByTestId("taxonomy-card-label"),
    ).toHaveAttribute("data-bubble-tone", "leaf");
  });

  it("allows hydrated leaf card labels to wrap inside a centered text container", () => {
    const title = "A very long leaf title that should wrap into multiple lines";

    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          content: "Long content",
          depth: 2,
          graphNodeId: 15,
          label: title,
          renderMode: "card",
          scope: "inner",
          targetNodeId: null,
          tooltip: "Long title",
        })}
      />,
    );

    const cardNode = screen
      .getByText(title)
      .closest("[data-node-scope='inner']");
    const label = within(cardNode as HTMLElement).getByTestId(
      "taxonomy-card-label",
    );

    expect(label).toHaveClass("whitespace-normal");
    expect(label).toHaveClass("break-words");
    expect(label).toHaveClass("text-center");
  });

  it("renders non-hydrated leaf nodes as point-mode markers without titles or disclosure", () => {
    render(
      <TaxonomyFlowNode
        {...makeNodeProps({
          depth: 2,
          graphNodeId: 12,
          label: "",
          renderMode: "point",
          scope: "outer",
          targetNodeId: null,
          tooltip: "",
        })}
      />,
    );

    const pointNode = screen
      .getByTestId("taxonomy-point-node")
      .closest("[data-node-scope='outer']");

    expect(pointNode).toHaveAttribute("data-node-presentation", "point");
    expect(
      within(pointNode as HTMLElement).queryByTestId("taxonomy-card-label"),
    ).not.toBeInTheDocument();
    expect(
      within(pointNode as HTMLElement).getByTestId("taxonomy-handle-target"),
    ).toHaveAttribute("data-handle-anchor", "center");
    expect(
      within(pointNode as HTMLElement).getByTestId("taxonomy-handle-source"),
    ).toHaveAttribute("data-handle-anchor", "center");

    fireEvent.mouseEnter(pointNode as HTMLElement);
    expect(
      screen.queryByTestId("taxonomy-bubble-disclosure"),
    ).not.toBeInTheDocument();
  });
});
