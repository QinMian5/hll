// abstract: Contract tests for Search result card rich-text rendering behavior.
// out_of_scope: Search route state management and backend query orchestration.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SearchResultCard } from "./index";

afterEach(() => {
  cleanup();
});

describe("SearchResultCard", () => {
  it("renders title math and content markdown through the shared rich-text renderer", () => {
    render(
      <SearchResultCard
        content={"*Important*\n\n- conserved\n\n`scalar`"}
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

  it("uses responsive Figma-projected vertical sizing without fixed desktop width", () => {
    render(<SearchResultCard content="Projected content." title="Projected" />);

    const card = screen.getByTestId("search-result-card");
    const contentRegion = within(card).getByTestId(
      "search-result-card-content",
    );

    expect(card).toHaveClass("h-[220px]", "md:h-[300px]", "lg:h-[379px]");
    expect(card).not.toHaveClass("md:w-[316px]");
    expect(contentRegion).toHaveClass("min-h-0", "flex-1", "w-full");
    expect(contentRegion).not.toHaveClass("md:h-[296px]");
  });
});
