// abstract: Route-level tests for the Figma-projected MCP client setup Docs page.
// out_of_scope: Markdown rendering engines, docs search indexing, and external client runtime behavior.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DocsPage } from ".";

afterEach(() => {
  cleanup();
});

describe("DocsPage", () => {
  it("projects the Figma MCP client setup layout with responsive scroll containers", () => {
    render(<DocsPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "MCP Client Setup" }),
    ).toHaveClass("text-knowledge-page-title");

    expect(screen.getByTestId("docs-route-page")).toHaveClass(
      "h-full",
      "overflow-hidden",
      "bg-docs-page-bg",
      "gap-docs-page-gap",
      "p-4",
      "md:px-8",
      "md:pt-6",
      "md:pb-8",
    );

    expect(screen.getByTestId("docs-workspace")).toHaveClass(
      "grid",
      "grid-rows-[minmax(0,1fr)_minmax(0,2fr)]",
      "lg:grid-cols-[256px_minmax(0,1fr)]",
      "xl:grid-cols-[288px_minmax(0,1fr)]",
      "2xl:grid-cols-[320px_minmax(0,1fr)]",
      "lg:grid-rows-none",
    );

    const clientsRegion = screen.getByRole("region", { name: "Clients" });
    expect(
      within(clientsRegion).getByRole("heading", {
        level: 2,
        name: "Clients",
      }),
    ).toHaveClass("text-docs-section-title");

    const configurationRegion = screen.getByRole("region", {
      name: "Codex Configuration",
    });
    expect(
      within(configurationRegion).getByRole("heading", {
        level: 2,
        name: "Codex Configuration",
      }),
    ).toHaveClass("text-docs-section-title");

    const panel = screen.getByTestId("docs-setup-panel");
    expect(
      within(panel).getByTestId("docs-setup-panel-header"),
    ).toHaveTextContent("Connect Knowledge to Codex");
    expect(within(panel).getByText("Connect Knowledge to Codex")).toHaveClass(
      "text-docs-panel-title",
    );
    expect(
      screen.getByRole("button", {
        name: "Copy command: codex mcp add knowledge --url https://<your-host>/mcp",
      }),
    ).toHaveClass(
      "size-docs-icon-button-size",
      "rounded-docs-icon-button",
      "text-docs-terminal-action",
      "hover:bg-docs-terminal-action-hover-bg",
      "hover:text-docs-terminal-action-hover",
    );
    expect(screen.getByTestId("docs-client-scroll-area")).toHaveClass(
      "min-h-0",
      "flex-1",
      "overflow-hidden",
    );
    expect(screen.getByTestId("docs-steps-scroll-area")).toHaveClass(
      "min-h-0",
      "flex-1",
      "overflow-hidden",
    );
  });

  it("renders Codex setup by default and switches to other client pages", () => {
    render(<DocsPage />);

    expect(screen.getByRole("button", { name: "Codex" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByText("codex mcp add knowledge --url https://<your-host>/mcp"),
    ).toBeInTheDocument();
    expect(screen.queryByText("/mcp")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Claude Code" }));
    expect(screen.getByRole("button", { name: "Claude Code" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Claude Code Configuration",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "claude mcp add --transport http knowledge https://<your-host>/mcp",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("/mcp")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "OpenClaw" }));
    expect(screen.getByRole("button", { name: "OpenClaw" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "OpenClaw Configuration" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        `openclaw mcp set knowledge '{"url":"https://<your-host>/mcp"}'`,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("openclaw mcp show knowledge --json"),
    ).toBeInTheDocument();
  });

  it("uses shadcn-style scroll areas and lucide copy controls", () => {
    render(<DocsPage />);

    const clientViewport = screen.getByTestId(
      "docs-client-scroll-area",
    ).firstElementChild;
    const stepsViewport = screen.getByTestId(
      "docs-steps-scroll-area",
    ).firstElementChild;

    expect(clientViewport).toHaveClass("overflow-auto");
    expect(stepsViewport).toHaveClass("overflow-auto");

    expect(
      screen.getByRole("button", {
        name: "Copy command: codex mcp add knowledge --url https://<your-host>/mcp",
      }),
    ).toBeInTheDocument();
  });
});
