// abstract: Component-level tests for the Figma-aligned Search card proposal dialog.
// out_of_scope: Search page integration and backend proposal persistence.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SearchCardProposalDialog } from "./SearchCardProposalDialog";

afterEach(() => {
  cleanup();
});

const card = {
  content:
    "SVD factors a matrix into orthogonal bases and singular values. It is used for compression, denoising, and latent structure discovery.",
  currentVersion: 3,
  nodeId: 10,
  title: "Singular value decomposition",
};

describe("SearchCardProposalDialog", () => {
  it("renders the add-card proposal as an entry-only create dialog", () => {
    render(
      <SearchCardProposalDialog
        initialMode="create"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", {
      name: "Card Proposal - Add Card",
    });

    expect(
      within(dialog).getByRole("heading", {
        name: "Card Proposal - Add Card",
      }),
    ).toBeInTheDocument();
    expect(
      within(dialog).queryByTestId("search-proposal-mode-tabs"),
    ).toBeNull();
    expect(within(dialog).queryByRole("button", { name: "Add" })).toBeNull();
    expect(within(dialog).queryByRole("button", { name: "Edit" })).toBeNull();
    expect(within(dialog).queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("limits in-dialog mode switching to equal-width edit and delete tabs", () => {
    render(
      <SearchCardProposalDialog
        card={card}
        initialMode="edit"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    const dialog = screen.getByRole("dialog", { name: "Card Proposal" });
    const tabs = within(dialog).getByTestId("search-proposal-mode-tabs");

    expect(tabs).toHaveClass("grid-cols-2");
    expect(within(tabs).queryByRole("button", { name: "Add" })).toBeNull();
    expect(within(tabs).getByRole("button", { name: "Edit" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      within(tabs).getByRole("button", { name: "Delete" }),
    ).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(within(tabs).getByRole("button", { name: "Delete" }));

    expect(within(tabs).getByRole("button", { name: "Edit" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(
      within(tabs).getByRole("button", { name: "Delete" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(within(dialog).getByText("Current card")).toBeInTheDocument();
  });

  it("keeps form scrolling on the form panel while textarea controls expand without their own vertical scroll", () => {
    render(
      <SearchCardProposalDialog
        card={card}
        initialMode="edit"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    const formPanel = screen.getByTestId("search-card-proposal-form-panel");
    const viewport = formPanel.firstElementChild;
    const contentTextarea = screen.getByLabelText("Content");
    const rationaleTextarea = screen.getByLabelText("Rationale");

    expect(formPanel).toHaveClass(
      "[--scroll-area-padding-right:var(--spacing-knowledge-dialog-scrollbar-gap)]",
      "[--scroll-area-scrollbar-width:var(--spacing-docs-scrollbar-width)]",
    );
    expect(viewport).toHaveClass(
      "overflow-y-auto",
      "overflow-x-clip",
      "pr-[var(--scroll-area-padding-right,0.5rem)]",
    );
    expect(contentTextarea).toHaveClass("overflow-hidden");
    expect(rationaleTextarea).toHaveClass("overflow-hidden");
    expect(contentTextarea).not.toHaveClass("overflow-y-auto");
    expect(rationaleTextarea).not.toHaveClass("overflow-y-auto");
  });
});
