// abstract: Contract tests for the DOM-based rich-text card overlay in taxonomy leaf view.
// out_of_scope: deck.gl point and edge layer rendering behavior.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  type RenderResult,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LeafRichTextCardsOverlay } from "./LeafRichTextCardsOverlay";
import type { LeafSceneCardNode } from "./leafSceneTypes";

afterEach(() => {
  cleanup();
});

function makeCardNode(): LeafSceneCardNode {
  return {
    content: "*Equation* content",
    graphNodeId: 10,
    id: "card-10",
    label: "Equation \\(E=mc^2\\)",
    position: { x: 700, y: 450 },
    scope: "inner",
    size: {
      height: 80,
      width: 200,
    },
  };
}

describe("LeafRichTextCardsOverlay", () => {
  it("anchors rich-text cards to projected viewport coordinates", () => {
    render(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[makeCardNode()]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onHoverChange={vi.fn()}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const card = screen.getByTestId("taxonomy-leaf-rich-text-card-10");

    expect(
      screen.getByTestId("taxonomy-leaf-rich-text-cards-overlay"),
    ).toBeInTheDocument();
    expect(document.querySelector(".katex")).not.toBeNull();
    expect(card).toHaveStyle({
      left: "702px",
      top: "450px",
      transform: "translate(-50%, -50%)",
    });
  });

  it("reports hover anchors from the DOM card host", () => {
    const onHoverChange = vi.fn();

    render(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[makeCardNode()]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onHoverChange={onHoverChange}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    fireEvent.mouseEnter(screen.getByTestId("taxonomy-leaf-rich-text-card-10"));

    expect(onHoverChange).toHaveBeenCalledWith(
      expect.objectContaining({
        anchorBottomY: 490,
        anchorTopY: 410,
      }),
    );
  });

  it("uses natural card height instead of forcing a fixed equal-height shell", () => {
    render(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[makeCardNode()]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onCardMeasurementsChange={vi.fn()}
        onHoverChange={vi.fn()}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const card = screen.getByTestId("taxonomy-leaf-rich-text-card-10");

    expect(card.style.height).toBe("");
    expect(card.style.minHeight).toBe("80px");
  });

  it("reports measured DOM card boxes back to the layout owner", async () => {
    const onCardMeasurementsChange = vi.fn();
    const getBoundingClientRectSpy = vi
      .spyOn(HTMLElement.prototype, "getBoundingClientRect")
      .mockImplementation(function mockGetBoundingClientRect(
        this: HTMLElement,
      ) {
        const testId = this.getAttribute("data-testid");

        if (testId === "taxonomy-leaf-rich-text-cards-overlay") {
          return {
            bottom: 900,
            height: 900,
            left: 0,
            right: 1404,
            top: 0,
            width: 1404,
            x: 0,
            y: 0,
            toJSON: () => ({}),
          } as DOMRect;
        }

        if (testId === "taxonomy-leaf-rich-text-card-10") {
          return {
            bottom: 498,
            height: 88,
            left: 602,
            right: 826,
            top: 410,
            width: 224,
            x: 602,
            y: 410,
            toJSON: () => ({}),
          } as DOMRect;
        }

        return {
          bottom: 0,
          height: 0,
          left: 0,
          right: 0,
          top: 0,
          width: 0,
          x: 0,
          y: 0,
          toJSON: () => ({}),
        } as DOMRect;
      });

    render(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[makeCardNode()]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onCardMeasurementsChange={onCardMeasurementsChange}
        onHoverChange={vi.fn()}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    expect(onCardMeasurementsChange).toHaveBeenCalledWith([
      { graphNodeId: 10, height: 88, width: 224 },
    ]);

    getBoundingClientRectSpy.mockRestore();
  });

  it("does not remeasure cards when only projected position changes", () => {
    const onCardMeasurementsChange = vi.fn();
    const getBoundingClientRectSpy = vi
      .spyOn(HTMLElement.prototype, "getBoundingClientRect")
      .mockImplementation(function mockGetBoundingClientRect(
        this: HTMLElement,
      ) {
        const testId = this.getAttribute("data-testid");

        if (testId === "taxonomy-leaf-rich-text-cards-overlay") {
          return {
            bottom: 900,
            height: 900,
            left: 0,
            right: 1404,
            top: 0,
            width: 1404,
            x: 0,
            y: 0,
            toJSON: () => ({}),
          } as DOMRect;
        }

        if (testId === "taxonomy-leaf-rich-text-card-10") {
          return {
            bottom: 498,
            height: 88,
            left: 602,
            right: 826,
            top: 410,
            width: 224,
            x: 602,
            y: 410,
            toJSON: () => ({}),
          } as DOMRect;
        }

        return {
          bottom: 0,
          height: 0,
          left: 0,
          right: 0,
          top: 0,
          width: 0,
          x: 0,
          y: 0,
          toJSON: () => ({}),
        } as DOMRect;
      });

    const rendered: RenderResult = render(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[makeCardNode()]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onCardMeasurementsChange={onCardMeasurementsChange}
        onHoverChange={vi.fn()}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    rendered.rerender(
      <LeafRichTextCardsOverlay
        canvas={{ height: 900, width: 1404 }}
        cardNodes={[{ ...makeCardNode(), position: { x: 740, y: 480 } }]}
        hoveredNodeId={null}
        neighborNodeIdsByNodeId={new Map()}
        onCardMeasurementsChange={onCardMeasurementsChange}
        onHoverChange={vi.fn()}
        viewport={{ target: [740, 480, 0], zoom: 0.1 }}
      />,
    );

    expect(onCardMeasurementsChange).toHaveBeenCalledTimes(1);

    getBoundingClientRectSpy.mockRestore();
  });
});
