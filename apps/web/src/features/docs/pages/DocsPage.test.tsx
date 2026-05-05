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
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { DocsPage } from ".";

const MCP_PUBLIC_BASE_URL = "http://localhost:8002/mcp";
const CODEX_ADD_COMMAND = `codex mcp add knowledge --url ${MCP_PUBLIC_BASE_URL}`;
const CODEX_CONFIG = `[mcp_servers.knowledge]\nurl = "${MCP_PUBLIC_BASE_URL}"\nhttp_headers = { Authorization = "Bearer <Dashboard PAT>" }`;
const CLAUDE_ADD_COMMAND = `claude mcp add --transport http knowledge ${MCP_PUBLIC_BASE_URL} --header "Authorization: Bearer <Dashboard PAT>"`;
const OPENCLAW_SET_COMMAND = `openclaw mcp set knowledge '{"url":"${MCP_PUBLIC_BASE_URL}","transport":"streamable-http","headers":{"Authorization":"Bearer <Dashboard PAT>"}}'`;

function getCodeBlock(text: string): HTMLElement {
  return screen.getByText(
    (_content, element) =>
      element?.tagName.toLowerCase() === "code" && element.textContent === text,
  );
}

beforeEach(() => {
  Object.defineProperty(window, "__KNOWLEDGE_RUNTIME_CONFIG__", {
    configurable: true,
    value: {
      mcpPublicBaseUrl: MCP_PUBLIC_BASE_URL,
      searchMaxConnected: 20,
      searchMaxMatched: 6,
    },
  });
});

afterEach(() => {
  cleanup();
  Reflect.deleteProperty(window, "__KNOWLEDGE_RUNTIME_CONFIG__");
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
        name: `Copy command: ${CODEX_ADD_COMMAND}`,
      }),
    ).toHaveClass(
      "size-docs-icon-button-size",
      "rounded-docs-icon-button",
      "text-docs-terminal-action",
      "hover:bg-docs-terminal-action-hover-bg",
      "hover:text-docs-terminal-action-hover",
    );

    expect(within(panel).getAllByTestId("docs-setup-step")).toHaveLength(5);
    const instructionBlock = within(panel).getByTestId(
      "docs-instruction-block",
    );
    expect(instructionBlock).toHaveClass(
      "border-docs-instruction-border",
      "bg-docs-instruction-bg",
      "px-docs-instruction-padding-x",
      "py-docs-instruction-padding-y",
    );
    expect(
      within(instructionBlock).getByText(
        "Dashboard > Tokens > Create Token > Copy token",
      ),
    ).not.toHaveClass("font-mono");
    expect(
      within(instructionBlock).queryByRole("button"),
    ).not.toBeInTheDocument();

    expect(screen.getByTestId("docs-client-scroll-area")).toHaveClass(
      "min-h-0",
      "w-full",
      "flex-1",
      "overflow-hidden",
    );
    expect(screen.getByTestId("docs-steps-scroll-area")).toHaveClass(
      "min-h-0",
      "w-full",
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
    expect(getCodeBlock(CODEX_ADD_COMMAND)).toHaveClass("font-mono");
    expect(getCodeBlock(CODEX_CONFIG)).toHaveClass("font-mono");
    expect(getCodeBlock("codex mcp get knowledge")).toHaveClass("font-mono");
    expect(getCodeBlock("codex mcp list")).toHaveClass("font-mono");
    expect(
      screen.queryByText("codex mcp login knowledge"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/OAuth/i)).not.toBeInTheDocument();
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
      within(screen.getByTestId("docs-setup-panel")).getAllByTestId(
        "docs-setup-step",
      ),
    ).toHaveLength(4);
    expect(getCodeBlock(CLAUDE_ADD_COMMAND)).toHaveClass("font-mono");
    expect(getCodeBlock("claude mcp get knowledge")).toHaveClass("font-mono");
    expect(getCodeBlock("claude mcp list")).toHaveClass("font-mono");
    expect(screen.queryByText("/mcp")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "OpenClaw" }));
    expect(screen.getByRole("button", { name: "OpenClaw" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "OpenClaw Configuration" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("docs-setup-panel")).getAllByTestId(
        "docs-setup-step",
      ),
    ).toHaveLength(4);
    expect(getCodeBlock(OPENCLAW_SET_COMMAND)).toHaveClass("font-mono");
    expect(getCodeBlock("openclaw mcp show knowledge --json")).toHaveClass(
      "font-mono",
    );
    expect(getCodeBlock("openclaw mcp list")).toHaveClass("font-mono");
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
    expect(clientViewport).toHaveClass("w-full");
    expect(stepsViewport).toHaveClass("w-full");

    expect(
      screen.getByRole("button", {
        name: `Copy command: ${CODEX_ADD_COMMAND}`,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /^Copy configuration: \[mcp_servers\.knowledge\]/,
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Copy / })).toHaveLength(4);
  });

  it("resets the setup steps scroll position when switching clients", () => {
    render(<DocsPage />);

    const stepsViewport = screen.getByTestId("docs-steps-scroll-area")
      .firstElementChild as HTMLElement;

    stepsViewport.scrollTop = 160;

    fireEvent.click(screen.getByRole("button", { name: "Claude Code" }));

    expect(stepsViewport.scrollTop).toBe(0);
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Claude Code Configuration",
      }),
    ).toBeInTheDocument();
  });
});
