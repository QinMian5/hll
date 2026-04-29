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
        onSearchTitle={vi.fn()}
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
        onSearchTitle={vi.fn()}
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
        onSearchTitle={vi.fn()}
        onSuggestEdit={vi.fn()}
        title="Projected"
      />,
    );

    const card = screen.getByTestId("search-result-card");
    const contentRegion = within(card).getByTestId(
      "search-result-card-content",
    );

    expect(card).toHaveClass("h-[176px]");
    expect(card).toHaveClass("shadow-none");
    expect(card).not.toHaveClass("md:w-[316px]");
    expect(card).not.toHaveClass("shadow-[0_18px_52px_rgba(107,132,189,0.09)]");
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
        onSearchTitle={vi.fn()}
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

  it("calls search handler when the card body or title search affordance is activated", () => {
    const onSearchTitle = vi.fn();
    render(
      <SearchResultCard
        content="Searchable content."
        currentVersion={1}
        nodeId={10}
        onSearchTitle={onSearchTitle}
        onSuggestEdit={vi.fn()}
        title="Singular value decomposition"
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Search for Singular value decomposition",
      }),
    );

    expect(onSearchTitle).toHaveBeenCalledWith("Singular value decomposition");
    expect(onSearchTitle).toHaveBeenCalledTimes(1);

    fireEvent.click(
      screen.getByRole("link", {
        name: "Search body for Singular value decomposition",
      }),
    );

    expect(onSearchTitle).toHaveBeenCalledWith("Singular value decomposition");
    expect(onSearchTitle).toHaveBeenCalledTimes(2);
  });

  it("keeps edit activation separate from card-title search activation", () => {
    const onSearchTitle = vi.fn();
    const onSuggestEdit = vi.fn();
    render(
      <SearchResultCard
        content="Editable content."
        currentVersion={3}
        nodeId={42}
        onSearchTitle={onSearchTitle}
        onSuggestEdit={onSuggestEdit}
        title="Editable"
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Suggest edit for Editable" }),
    );

    expect(onSearchTitle).not.toHaveBeenCalled();
    expect(onSuggestEdit).toHaveBeenCalledWith({
      content: "Editable content.",
      currentVersion: 3,
      nodeId: 42,
      title: "Editable",
    });
  });

  it("exposes the Figma hover search hint and no-shadow transition state classes", () => {
    render(
      <SearchResultCard
        content="Projected content."
        currentVersion={1}
        nodeId={10}
        onSearchTitle={vi.fn()}
        onSuggestEdit={vi.fn()}
        title="Projected"
      />,
    );

    const card = screen.getByTestId("search-result-card");
    const searchHint = screen.getByTestId("search-result-card-search-hint");

    expect(searchHint).toHaveAttribute("aria-hidden", "true");
    expect(card).toHaveClass(
      "transition-[opacity,transform,border-color]",
      "group-hover/search-results-grid:opacity-80",
      "hover:opacity-100",
      "hover:-translate-y-1",
      "hover:scale-[1.008]",
      "hover:border-[#006bff]/40",
      "focus-within:opacity-100",
      "focus-within:-translate-y-1",
      "focus-within:scale-[1.008]",
      "focus-within:border-[#006bff]/40",
      "shadow-none",
    );
    expect(card).not.toHaveClass(
      "shadow-[0_18px_52px_rgba(107,132,189,0.09)]",
      "hover:shadow-[0_4px_14px_rgba(20,39,79,0.08),0_24px_58px_rgba(107,133,189,0.18)]",
      "focus-within:shadow-[0_4px_14px_rgba(20,39,79,0.08),0_24px_58px_rgba(107,133,189,0.18)]",
    );
    expect(searchHint).toHaveClass(
      "absolute",
      "top-[-8px]",
      "right-[-12px]",
      "opacity-0",
      "group-hover/card:opacity-100",
      "group-focus-within/card:opacity-100",
    );
  });
});
