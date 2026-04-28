// abstract: Route-shell tests for the shared app navigation and root redirect behavior.
// out_of_scope: Feature-specific page content behavior and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "./router";

vi.mock("../features/taxonomy-view/page/TaxonomyViewPage", () => ({
  TaxonomyViewPage: () => <div data-testid="mock-graph-page">Graph page</div>,
}));

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
}

function stubSessionResponse(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => jsonResponse(body)),
  );
}

function renderWithRoute(pathname: string) {
  const router = createAppRouter({
    initialEntries: [pathname],
  });

  render(<RouterProvider router={router} />);

  return { router };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.scrollTo = vi.fn();
  stubSessionResponse({ status: "anonymous" });
});

describe("AppShell", () => {
  it("redirects the root route to overview and highlights only overview", async () => {
    const { router } = renderWithRoute("/");

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/overview"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("app-shell")).toBeInTheDocument(),
    );

    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "inactive",
    );
    expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute(
      "data-nav-state",
      "inactive",
    );
  });

  it("renders the shared top navigation with anonymous sign-in action", async () => {
    renderWithRoute("/graph");

    await waitFor(() =>
      expect(screen.getAllByText("Knowledge Graph").length).toBeGreaterThan(0),
    );
    expect(screen.getByTestId("app-shell")).toHaveClass(
      "bg-[#f8fafc]",
      "font-['Geist',sans-serif]",
      "min-h-screen",
      "w-full",
    );
    expect(screen.getByTestId("app-shell-sidebar")).toHaveClass(
      "hidden",
      "lg:flex",
      "lg:w-[320px]",
    );
    expect(screen.getByTestId("app-shell-mobile-header")).toHaveClass(
      "h-16",
      "lg:hidden",
    );
    expect(
      screen.getByTestId("app-shell-mobile-header").parentElement,
    ).toHaveClass("min-h-0");
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "href",
      "/overview",
    );
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute(
      "href",
      "/search",
    );
    expect(screen.getByRole("button", { name: "Dashboard" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "GitHub 0 stars" })).toHaveClass(
      "h-10",
      "rounded-lg",
    );
    const signInButton = screen.getByRole("button", { name: "Sign in" });

    expect(signInButton).toBeEnabled();
    expect(signInButton.closest("form")).toHaveAttribute(
      "action",
      "/web-api/auth/sign-in",
    );
    expect(signInButton.closest("form")).toHaveAttribute("method", "post");
  });

  it("opens and closes the mobile drawer from the shell header", async () => {
    renderWithRoute("/graph");

    await waitFor(() =>
      expect(screen.getByTestId("app-shell-mobile-header")).toBeInTheDocument(),
    );
    expect(
      screen.queryByTestId("app-shell-mobile-drawer"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));

    expect(screen.getByTestId("app-shell-mobile-drawer")).toHaveClass(
      "w-[320px]",
      "bg-white",
    );
    expect(
      screen.getByRole("button", { name: "Close navigation" }),
    ).toBeInTheDocument();
    expect(
      screen
        .getByTestId("app-shell-mobile-drawer")
        .querySelector('[data-nav-state="active"]'),
    ).toHaveTextContent("Graph View");

    fireEvent.click(screen.getByRole("button", { name: "Close navigation" }));

    expect(
      screen.queryByTestId("app-shell-mobile-drawer"),
    ).not.toBeInTheDocument();
  });

  it("renders authenticated user state with sign-out action", async () => {
    stubSessionResponse({
      status: "authenticated",
      user: {
        email: "ada@example.com",
        id: "user-1",
        name: "Ada Lovelace",
      },
    });

    renderWithRoute("/overview");

    await waitFor(() =>
      expect(screen.getByText("Ada Lovelace")).toBeInTheDocument(),
    );
    const signOutButton = screen.getByRole("button", { name: "Sign out" });

    expect(signOutButton).toBeEnabled();
    expect(signOutButton.closest("form")).toHaveAttribute(
      "action",
      "/web-api/auth/sign-out",
    );
    expect(signOutButton.closest("form")).toHaveAttribute("method", "post");
  });
});
