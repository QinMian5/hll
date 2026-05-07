// abstract: Contract tests for taxonomy leaf disclosure rendering and canvas event isolation.
// out_of_scope: deck.gl picking, canvas controller internals, and viewport store behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeafDisclosureOverlay } from "./LeafDisclosureOverlay";
import type { LeafDisclosureState } from "./leafSceneTypes";

type ReadyDisclosureState = Extract<
  LeafDisclosureState,
  { readonly status: "ready" }
>;

afterEach(() => {
  cleanup();
});

function makeDisclosure(
  mode: ReadyDisclosureState["mode"],
): ReadyDisclosureState {
  return {
    mode,
    node: {
      content: "*Equation* content",
      currentVersion: 3,
      graphNodeId: 10,
      id: "leaf-10",
      position: { x: 700, y: 450 },
      scope: "inner",
      title: "Equation \\(E=mc^2\\)",
    },
    status: "ready",
  };
}

describe("LeafDisclosureOverlay", () => {
  it("uses one responsive maximum-height card contract for hover and selected disclosures", () => {
    const classNames: string[] = [];
    const tagNames: string[] = [];

    for (const mode of ["hover", "selected"] as const) {
      const { unmount } = render(
        <LeafDisclosureOverlay
          canvas={{ height: 900, width: 1404 }}
          disclosure={makeDisclosure(mode)}
          viewport={{ target: [700, 450, 0], zoom: 0 }}
        />,
      );

      const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");
      classNames.push(disclosure.className);
      tagNames.push(disclosure.tagName);

      expect(disclosure).toHaveClass("rounded-knowledge-leaf-disclosure");
      expect(disclosure).toHaveClass(
        "w-[min(var(--leaf-disclosure-card-width),calc(100%_-_24px))]",
      );
      expect(disclosure).toHaveClass(
        "max-h-[var(--leaf-disclosure-card-height)]",
      );
      expect(disclosure).not.toHaveClass(
        "h-[var(--leaf-disclosure-card-height)]",
      );
      expect(disclosure).toHaveClass(
        "[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-md)]",
      );
      expect(disclosure).toHaveClass(
        "lg:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-lg)]",
      );
      expect(disclosure).toHaveClass(
        "xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-xl)]",
      );
      expect(disclosure).toHaveClass(
        "2xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-2xl)]",
      );

      const scrollArea = screen.getByTestId(
        "taxonomy-leaf-disclosure-content-scroll-area",
      );

      expect(scrollArea).toHaveClass(
        "max-h-[var(--leaf-disclosure-card-content-height)]",
      );
      expect(scrollArea).not.toHaveClass(
        "h-[var(--leaf-disclosure-card-content-height)]",
      );
      expect(scrollArea).toHaveClass(
        "[--scroll-area-scrollbar-width:var(--spacing-knowledge-leaf-disclosure-scrollbar-width)]",
      );

      unmount();
    }

    expect(classNames[0]).toBe(classNames[1]);
    expect(tagNames).toEqual(["SECTION", "SECTION"]);
  });

  it("lets short content hug its natural height instead of filling the maximum content region", () => {
    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const scrollArea = screen.getByTestId(
      "taxonomy-leaf-disclosure-content-scroll-area",
    );
    const scrollViewport = scrollArea.firstElementChild;

    expect(scrollArea).toHaveClass(
      "max-h-[var(--leaf-disclosure-card-content-height)]",
    );
    expect(scrollViewport).not.toHaveClass("h-full");
  });

  it("wraps long disclosure titles and lets the header grow", () => {
    const disclosure = makeDisclosure("selected");

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={{
          ...disclosure,
          node: {
            ...disclosure.node,
            title:
              "A very long disclosure title that should wrap across lines inside the header",
          },
        }}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const titleHeader = screen.getByTestId("taxonomy-leaf-disclosure-header");
    const titleArea = screen.getByTestId("taxonomy-leaf-disclosure-title-area");
    const titleTrack = screen.getByTestId(
      "taxonomy-leaf-disclosure-title-track",
    );

    expect(titleHeader).toHaveClass("min-h-6");
    expect(titleHeader).not.toHaveClass("h-6");
    expect(titleArea).toHaveClass("whitespace-normal");
    expect(titleArea).toHaveClass("break-words");
    expect(titleArea).not.toHaveClass("overflow-x-auto");
    expect(titleArea).not.toHaveClass("overflow-y-hidden");
    expect(titleTrack).toHaveClass("whitespace-normal");
    expect(titleTrack).toHaveClass("break-words");
    expect(titleTrack).not.toHaveClass("whitespace-nowrap");
  });

  it("renders hover disclosure with title, content, and edit affordance", () => {
    const onSuggestEdit = vi.fn();

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("hover")}
        onSuggestEdit={onSuggestEdit}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");

    expect(disclosure).toHaveAttribute("data-disclosure-mode", "hover");
    expect(disclosure).toHaveTextContent("Equation");
    expect(disclosure).toHaveTextContent("Equation content");

    const editButton = screen.getByTestId(
      "taxonomy-leaf-disclosure-edit-button",
    );

    expect(editButton).toHaveAttribute(
      "aria-label",
      "Suggest edit for Equation \\(E=mc^2\\)",
    );

    fireEvent.click(editButton);

    expect(onSuggestEdit).toHaveBeenCalledWith({
      content: "*Equation* content",
      currentVersion: 3,
      nodeId: 10,
      title: "Equation \\(E=mc^2\\)",
    });
  });

  it("renders selected disclosure with edit affordance and stops canvas click propagation", () => {
    const onCanvasClick = vi.fn();
    const onSuggestEdit = vi.fn();
    document.body.addEventListener("click", onCanvasClick);

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        onSuggestEdit={onSuggestEdit}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");

    expect(disclosure).toHaveAttribute("data-disclosure-mode", "selected");
    expect(disclosure.tagName).toBe("SECTION");
    expect(disclosure).toHaveAttribute("role", "dialog");
    expect(disclosure).toHaveAttribute("aria-label", "Selected knowledge card");
    expect(disclosure).toHaveTextContent("Equation");
    expect(disclosure).toHaveTextContent("Equation content");
    const editButton = screen.getByTestId(
      "taxonomy-leaf-disclosure-edit-button",
    );

    expect(editButton).toHaveAttribute(
      "aria-label",
      "Suggest edit for Equation \\(E=mc^2\\)",
    );

    fireEvent.click(disclosure);
    fireEvent.click(editButton);

    expect(onCanvasClick).not.toHaveBeenCalled();
    expect(onSuggestEdit).toHaveBeenCalledWith({
      content: "*Equation* content",
      currentVersion: 3,
      nodeId: 10,
      title: "Equation \\(E=mc^2\\)",
    });

    document.body.removeEventListener("click", onCanvasClick);
  });

  it("keeps content wheel events inside the disclosure so the canvas does not zoom", () => {
    const canvasWheel = vi.fn((event: WheelEvent) => {
      event.preventDefault();
    });
    const deckHost = document.createElement("div");
    deckHost.addEventListener("wheel", canvasWheel, { passive: false });
    document.body.append(deckHost);

    try {
      render(
        <LeafDisclosureOverlay
          canvas={{ height: 900, width: 1404 }}
          disclosure={makeDisclosure("selected")}
          viewport={{ target: [700, 450, 0], zoom: 0 }}
        />,
        { container: deckHost },
      );

      const scrollArea = screen.getByTestId(
        "taxonomy-leaf-disclosure-content-scroll-area",
      );
      const scrollViewport = scrollArea.firstElementChild;
      const wheelEvent = new WheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        deltaY: 72,
      });

      scrollViewport?.dispatchEvent(wheelEvent);

      expect(canvasWheel).not.toHaveBeenCalled();
      expect(wheelEvent.defaultPrevented).toBe(false);
    } finally {
      deckHost.removeEventListener("wheel", canvasWheel);
      deckHost.remove();
    }
  });

  it("updates position from DeckGL-provided viewport props", () => {
    const { rerender } = render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");

    expect(disclosure.style.transform).toBe("translate3d(510px, 458px, 0px)");

    rerender(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        viewport={{ target: [740, 480, 0], zoom: 0 }}
      />,
    );

    expect(disclosure.style.transform).toBe("translate3d(470px, 428px, 0px)");
  });

  it("does not remeasure layout when DeckGL provides a new viewport", () => {
    const rect = {
      bottom: 208,
      height: 208,
      left: 0,
      right: 416,
      toJSON: () => ({}),
      top: 0,
      width: 416,
      x: 0,
      y: 0,
    } satisfies DOMRect;
    const getBoundingClientRect = vi
      .spyOn(HTMLElement.prototype, "getBoundingClientRect")
      .mockReturnValue(rect);

    const { rerender } = render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    getBoundingClientRect.mockClear();

    rerender(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        viewport={{ target: [740, 480, 0], zoom: 0 }}
      />,
    );

    expect(getBoundingClientRect).not.toHaveBeenCalled();

    getBoundingClientRect.mockRestore();
  });

  it("keeps the card inside the canvas when the projected point is near mobile edges", () => {
    const disclosure = makeDisclosure("selected");
    const edgeDisclosure = {
      ...disclosure,
      node: {
        ...disclosure.node,
        position: { x: 184, y: 270 },
      },
    } satisfies ReadyDisclosureState;

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 560, width: 390 }}
        disclosure={edgeDisclosure}
        viewport={{ target: [0, 0, 0], zoom: 0 }}
      />,
    );

    const disclosureCard = screen.getByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(disclosureCard.style.transform).toBe(
      "translate3d(58px, 382px, 0px)",
    );
  });
});
