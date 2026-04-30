// abstract: Contract tests for selected and hover disclosure rendering in taxonomy leaf view.
// out_of_scope: deck.gl picking and viewport store behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  LeafDisclosureOverlay,
  type LeafDisclosureOverlayHandle,
} from "./LeafDisclosureOverlay";
import type { LeafDisclosureState } from "./leafSceneTypes";

afterEach(() => {
  cleanup();
});

function makeDisclosure(
  mode: LeafDisclosureState["mode"],
): LeafDisclosureState {
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
  };
}

describe("LeafDisclosureOverlay", () => {
  it("uses one responsive maximum-height card contract for hover and selected disclosures", () => {
    const classNames: string[] = [];

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
  });

  it("allows long disclosure titles to scroll horizontally", () => {
    const disclosure = makeDisclosure("selected");

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={{
          ...disclosure,
          node: {
            ...disclosure.node,
            title:
              "A very long disclosure title that should remain on one line and overflow horizontally inside the header",
          },
        }}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const titleScrollArea = screen.getByTestId(
      "taxonomy-leaf-disclosure-title-scroll-area",
    );
    const titleTrack = screen.getByTestId(
      "taxonomy-leaf-disclosure-title-track",
    );

    expect(titleScrollArea).toHaveClass("overflow-x-auto");
    expect(titleScrollArea).toHaveClass("overflow-y-hidden");
    expect(titleTrack).toHaveClass("whitespace-nowrap");
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

  it("updates position from imperative live viewport sync", () => {
    const overlayRef = createRef<LeafDisclosureOverlayHandle>();

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        ref={overlayRef}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    const disclosure = screen.getByTestId("taxonomy-leaf-disclosure-overlay");

    expect(disclosure.style.transform).toBe(
      "translate3d(702px, 466px, 0px) translate(-50%, 0%)",
    );

    overlayRef.current?.syncViewport({
      target: [740, 480, 0],
      zoom: 0,
    });

    expect(disclosure.style.transform).toBe(
      "translate3d(662px, 436px, 0px) translate(-50%, 0%)",
    );
  });

  it("does not remeasure layout during imperative viewport sync", () => {
    const overlayRef = createRef<LeafDisclosureOverlayHandle>();
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

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={makeDisclosure("selected")}
        ref={overlayRef}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    getBoundingClientRect.mockClear();

    overlayRef.current?.syncViewport({
      target: [740, 480, 0],
      zoom: 0,
    });

    expect(getBoundingClientRect).not.toHaveBeenCalled();

    getBoundingClientRect.mockRestore();
  });

  it("keeps the card centered to the projected point near the canvas edge", () => {
    const overlayRef = createRef<LeafDisclosureOverlayHandle>();
    const disclosure = makeDisclosure("selected");
    const edgeDisclosure = {
      ...disclosure,
      node: {
        ...disclosure.node,
        position: { x: 1300, y: 450 },
      },
    } satisfies LeafDisclosureState;

    render(
      <LeafDisclosureOverlay
        canvas={{ height: 900, width: 1404 }}
        disclosure={edgeDisclosure}
        ref={overlayRef}
        viewport={{ target: [700, 450, 0], zoom: 0 }}
      />,
    );

    overlayRef.current?.syncViewport({
      target: [700, 450, 0],
      zoom: 0,
    });

    const disclosureCard = screen.getByTestId(
      "taxonomy-leaf-disclosure-overlay",
    );

    expect(disclosureCard.style.transform).toBe(
      "translate3d(1302px, 466px, 0px) translate(-50%, 0%)",
    );
  });
});
