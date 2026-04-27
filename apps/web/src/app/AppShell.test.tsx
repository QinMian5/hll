// abstract: Route-shell tests for the shared app navigation and root redirect behavior.
// out_of_scope: Feature-specific page content behavior and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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

    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
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
      expect(screen.getByText("Knowledge Graph")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("app-shell")).toHaveClass(
      "bg-[radial-gradient(circle_at_center,_#f2faff_0%,_#fbfcff_55%,_#f6f7fb_100%)]",
      "font-['Geist',sans-serif]",
      "min-h-screen",
      "w-full",
    );
    expect(screen.getByTestId("app-shell-header")).toHaveClass(
      "h-[112px]",
      "md:h-16",
    );
    expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(screen.getByRole("link", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GitHub" })).toBeDisabled();
    const signInButton = screen.getByRole("button", { name: "Sign in" });

    expect(signInButton).toBeEnabled();
    expect(signInButton.closest("form")).toHaveAttribute(
      "action",
      "/web-api/auth/sign-in",
    );
    expect(signInButton.closest("form")).toHaveAttribute("method", "post");
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
