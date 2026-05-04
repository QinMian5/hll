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
    expect(screen.getByLabelText("Content")).toHaveAttribute(
      "placeholder",
      "Write the proposed card content.",
    );
    expect(screen.getByLabelText("Reason")).toHaveAttribute(
      "placeholder",
      "Explain why you recommend adding this card.",
    );
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
    expect(within(dialog).queryByText("Current card")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue(
      "Singular value decomposition",
    );
    expect(screen.getByLabelText("Title")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Content")).toHaveValue(card.content);
    expect(screen.getByLabelText("Content")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Reason")).toHaveAttribute(
      "placeholder",
      "Explain why you recommend deleting this card.",
    );
  });

  it("uses edit-specific proposal placeholders", () => {
    render(
      <SearchCardProposalDialog
        card={card}
        initialMode="edit"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Content")).toHaveAttribute(
      "placeholder",
      "Write the revised card content.",
    );
    expect(screen.getByLabelText("Reason")).toHaveAttribute(
      "placeholder",
      "Explain why you recommend editing this card.",
    );
  });

  it("requires a reason for create, edit, and delete submissions", async () => {
    const onSubmit = vi.fn(async () => {});
    const { rerender } = render(
      <SearchCardProposalDialog
        initialMode="create"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "New card" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "New card content." },
    });
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "This card fills a knowledge gap." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toHaveBeenCalledWith({
      content: "New card content.",
      mode: "create",
      reason: "This card fills a knowledge gap.",
      title: "New card",
    });

    onSubmit.mockClear();
    rerender(
      <SearchCardProposalDialog
        card={card}
        initialMode="edit"
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "Updated card content." },
    });
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "The current explanation omits common uses." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toHaveBeenCalledWith({
      content: "Updated card content.",
      mode: "edit",
      reason: "The current explanation omits common uses.",
      title: card.title,
    });

    onSubmit.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "The card duplicates another entry." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit).toHaveBeenCalledWith({
      mode: "delete",
      reason: "The card duplicates another entry.",
    });
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
    const reasonTextarea = screen.getByLabelText("Reason");

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
    expect(reasonTextarea).toHaveClass("overflow-hidden");
    expect(contentTextarea.closest("div")).not.toHaveClass(
      "min-h-knowledge-dialog-textarea-min-height",
    );
    expect(reasonTextarea.closest("div")).not.toHaveClass(
      "min-h-knowledge-dialog-textarea-min-height",
    );
    expect(contentTextarea).not.toHaveClass("overflow-y-auto");
    expect(reasonTextarea).not.toHaveClass("overflow-y-auto");
  });
});
