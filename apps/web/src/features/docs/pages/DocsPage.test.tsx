// abstract: Route-level tests for the unified Docs page information architecture.
// out_of_scope: Markdown rendering engines, docs search indexing, and external client runtime behavior.

import "@testing-library/jest-dom/vitest";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocsPage } from ".";

describe("DocsPage", () => {
  it("renders the unified documentation hub with project and client setup sections", () => {
    render(<DocsPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Docs" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Guides for understanding Knowledge Graph and connecting model clients.",
      ),
    ).toBeInTheDocument();

    const gettingStarted = screen.getByRole("region", {
      name: "Start here",
    });
    expect(
      within(gettingStarted).getByRole("heading", { name: "Project overview" }),
    ).toBeInTheDocument();
    expect(
      within(gettingStarted).getByRole("heading", { name: "MCP access" }),
    ).toBeInTheDocument();

    const clients = screen.getByRole("region", {
      name: "Client configuration",
    });
    expect(
      within(clients).getByRole("heading", { name: "Codex" }),
    ).toBeInTheDocument();
    expect(
      within(clients).getByRole("heading", { name: "Claude Code" }),
    ).toBeInTheDocument();
  });
});
