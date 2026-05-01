// abstract: Contract tests for the Search route related-result item.
// out_of_scope: Search page route state and backend related-title generation.

import "@testing-library/jest-dom/vitest";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RelatedResultItem } from "./RelatedResultItem";

afterEach(() => {
  cleanup();
});

describe("RelatedResultItem", () => {
  it("uses the Figma-projected hug-height wrapping item structure", () => {
    render(
      <RelatedResultItem
        onSelect={vi.fn()}
        title="Principal component analysis with a long related title"
      />,
    );

    const item = screen.getByTestId("related-result-item");
    const title = screen.getByTestId("related-result-item-title");
    const icon = screen.getByTestId("related-result-item-icon");

    expect(item).toHaveClass(
      "min-h-[42px]",
      "items-center",
      "gap-2",
      "px-3",
      "py-2",
      "text-[14px]",
      "leading-5",
      "font-medium",
    );
    expect(item).not.toHaveClass("h-[38px]", "md:h-[42px]", "overflow-hidden");
    expect(title).toHaveClass("whitespace-normal", "break-words");
    expect(title).not.toHaveClass("truncate", "whitespace-nowrap");
    expect(icon).toHaveClass(
      "size-6",
      "items-center",
      "justify-center",
      "shrink-0",
    );
  });

  it("matches the Search card hover and sibling dimming affordance model", () => {
    render(<RelatedResultItem onSelect={vi.fn()} title="Matrix norm" />);

    const item = screen.getByTestId("related-result-item");
    const hoverIcon = screen.getByTestId("related-result-item-hover-icon");

    expect(item).toHaveClass(
      "group-hover/search-suggestions-list:opacity-80",
      "group-focus-within/search-suggestions-list:opacity-80",
      "hover:border-[#006bff]/40",
      "hover:bg-[rgba(255,255,255,0.88)]",
      "focus-visible:border-[#006bff]/40",
      "focus-visible:bg-[rgba(255,255,255,0.88)]",
    );
    expect(hoverIcon).toHaveClass(
      "rounded-full",
      "bg-[#006bff]",
      "opacity-0",
      "group-hover/related-result:opacity-100",
      "group-focus-visible/related-result:opacity-100",
    );
  });

  it("selects the visible related title", () => {
    const onSelect = vi.fn();
    render(<RelatedResultItem onSelect={onSelect} title="Matrix norm" />);

    fireEvent.click(screen.getByRole("button", { name: "Matrix norm" }));

    expect(onSelect).toHaveBeenCalledWith("Matrix norm");
  });
});
