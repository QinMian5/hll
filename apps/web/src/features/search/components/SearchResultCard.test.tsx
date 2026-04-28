// abstract: Contract tests for Search result card rich-text rendering behavior.
// out_of_scope: Search route state management and backend query orchestration.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SearchResultCard } from "./SearchResultCard";

afterEach(() => {
  cleanup();
});

describe("SearchResultCard", () => {
  it("renders title math and content markdown through the shared rich-text renderer", () => {
    render(
      <SearchResultCard
        content={"*Important*\n\n- conserved\n\n`scalar`"}
        currentVersion={1}
        nodeId={10}
        onSuggestEdit={vi.fn()}
        title={"Energy \\(E=mc^2\\)"}
      />,
    );

    expect(document.querySelector(".katex")).not.toBeNull();
    expect(screen.getByText("Important")).toBeInTheDocument();
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.getByText("scalar").tagName).toBe("CODE");
  });

  it("keeps the scrollable content region when rich text expands vertically", () => {
    render(
      <SearchResultCard
        content={"Paragraph one.\n\nParagraph two.\n\n- item"}
        currentVersion={1}
        nodeId={10}
        onSuggestEdit={vi.fn()}
        title="Scrollable body"
      />,
    );

    const card = screen.getByTestId("search-result-card");
    const contentRegion = within(card).getByTestId(
      "search-result-card-content",
    );

    expect(contentRegion).toBeInTheDocument();
    expect(within(card).getByText("Paragraph one.")).toBeInTheDocument();
    expect(within(card).getByText("Paragraph two.")).toBeInTheDocument();
    expect(within(card).getByRole("list")).toBeInTheDocument();
  });

  it("uses the latest Figma-projected card sizing without fixed desktop width", () => {
    render(
      <SearchResultCard
        content="Projected content."
        currentVersion={1}
        nodeId={10}
        onSuggestEdit={vi.fn()}
        title="Projected"
      />,
    );

    const card = screen.getByTestId("search-result-card");
    const contentRegion = within(card).getByTestId(
      "search-result-card-content",
    );

    expect(card).toHaveClass("h-[176px]");
    expect(card).not.toHaveClass("md:w-[316px]");
    expect(contentRegion).toHaveClass(
      "min-h-0",
      "flex-1",
      "w-full",
      "overflow-y-auto",
      "overflow-x-hidden",
    );
    expect(contentRegion).not.toHaveClass(
      "md:h-[296px]",
      "[scrollbar-width:none]",
    );
    expect(
      Array.from(contentRegion.children).some(
        (child) => child.getAttribute("aria-hidden") === "true",
      ),
    ).toBe(false);
  });

  it("calls edit handler with card identity and visible version", async () => {
    const onSuggestEdit = vi.fn();
    render(
      <SearchResultCard
        content="Editable content."
        currentVersion={3}
        nodeId={42}
        onSuggestEdit={onSuggestEdit}
        title="Editable"
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Suggest edit for Editable" }),
    );

    expect(onSuggestEdit).toHaveBeenCalledWith({
      content: "Editable content.",
      currentVersion: 3,
      nodeId: 42,
      title: "Editable",
    });
  });
});
