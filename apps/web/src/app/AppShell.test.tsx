// abstract: Route-shell tests for the shared app navigation and root redirect behavior.
// out_of_scope: Feature-specific page content behavior and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WebSessionResponse } from "../shared/web-api/session";
import { sessionQueryKeys } from "../shared/web-api/sessionQueries";
import { createAppRouter } from "./router";

vi.mock("../features/taxonomy-view/page/TaxonomyViewPage", () => ({
  TaxonomyViewPage: () => <div data-testid="mock-graph-page">Graph page</div>,
}));

vi.mock("../features/docs/pages", () => ({
  DocsPage: () => <div data-testid="mock-docs-page">Docs page</div>,
}));

vi.mock("../features/workspace/pages", () => ({
  WorkspacePage: () => (
    <div data-testid="mock-workspace-page">Workspace page</div>
  ),
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

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
        staleTime: 30_000,
      },
    },
  });
}

function renderWithRoute(
  pathname: string,
  options: { readonly session?: WebSessionResponse } = {},
) {
  const queryClient = createTestQueryClient();
  const router = createAppRouter({
    initialEntries: [pathname],
  });

  if (options.session !== undefined) {
    queryClient.setQueryData(sessionQueryKeys.session, options.session);
  }

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return { queryClient, router };
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
    expect(screen.getByRole("link", { name: "Docs" })).toHaveAttribute(
      "data-nav-state",
      "inactive",
    );
    expect(
      screen.queryByRole("link", { name: "Dashboard" }),
    ).not.toBeInTheDocument();
  });

  it("renders the shared top navigation with anonymous sign-in action", async () => {
    renderWithRoute("/graph");

    await waitFor(() =>
      expect(screen.getAllByText("Knowledge Graph").length).toBeGreaterThan(0),
    );
    expect(screen.getByTestId("app-shell")).toHaveClass(
      "bg-[#f8fafc]",
      "font-sans",
      "min-h-screen",
      "w-full",
    );
    expect(screen.getByTestId("app-shell-sidebar")).toHaveClass(
      "hidden",
      "md:flex",
      "md:w-60",
      "lg:w-64",
      "xl:w-72",
      "2xl:w-80",
    );
    expect(screen.getByTestId("app-shell-mobile-header")).toHaveClass(
      "h-16",
      "md:hidden",
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
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveClass(
      "font-medium",
    );
    expect(screen.getByRole("link", { name: "Graph View" })).not.toHaveClass(
      "font-black",
    );
    expect(screen.getByRole("link", { name: "Search" })).toHaveAttribute(
      "href",
      "/search",
    );
    expect(screen.getByRole("link", { name: "Docs" })).toHaveAttribute(
      "href",
      "/docs",
    );
    expect(
      screen.queryByRole("link", { name: "Dashboard" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "GitHub 0 stars" })).toHaveClass(
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
    expect(signInButton.closest("form")).toHaveFormValues({
      return_to: "/graph",
    });
  });

  it("keeps Graph View active for readable graph route paths", async () => {
    const { router } = renderWithRoute("/graph/science/mathematics");

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/graph/science/mathematics"),
    );
    expect(screen.getByRole("link", { name: "Graph View" })).toHaveAttribute(
      "data-nav-state",
      "active",
    );
    expect(
      screen.getByRole("button", { name: "Sign in" }).closest("form"),
    ).toHaveFormValues({
      return_to: "/graph/science/mathematics",
    });
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
      "bg-[rgba(255,255,255,0.72)]",
    );
    expect(screen.getByTestId("app-shell-mobile-overlay")).toHaveClass(
      "md:hidden",
    );
    expect(
      screen.getByRole("button", { name: "Close navigation" }),
    ).toBeInTheDocument();
    expect(
      screen
        .getByTestId("app-shell-mobile-drawer")
        .querySelector('[data-nav-state="active"]'),
    ).toHaveTextContent("Graph View");
    expect(
      screen
        .getByTestId("app-shell-mobile-drawer")
        .querySelector('a[href="/docs"]'),
    ).toHaveTextContent("Docs");
    expect(
      screen
        .getByTestId("app-shell-mobile-drawer")
        .querySelector('a[href="/dashboard"]'),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close navigation scrim" }),
    ).toHaveClass("bg-[rgba(248,250,252,0.18)]");

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

    const accountButton = await screen.findByRole("button", {
      name: "User menu, Ada Lovelace",
    });

    expect(accountButton).toHaveTextContent("Ada Lovelace");
    expect(accountButton).toHaveTextContent("ada@example.com");
    expect(accountButton.querySelector("svg")).toHaveClass("-rotate-90");
    expect(accountButton.querySelector("svg")).not.toHaveClass("rotate-180");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    fireEvent.click(accountButton);

    expect(screen.getByTestId("app-shell-account-area")).toHaveClass(
      "gap-shell-account-action-gap",
      "pt-shell-account-action-gap",
      "h-auto",
    );
    expect(screen.getByRole("menu")).toHaveClass(
      "bottom-[calc(var(--spacing-account-action-button-height)+var(--spacing-shell-account-action-gap))]",
      "left-0",
      "right-0",
      "w-full",
      "rounded-account-menu",
      "border-account-menu-border",
      "bg-account-menu-surface",
      "p-account-menu-padding",
      "drop-shadow-[var(--drop-shadow-account-menu)]",
    );
    expect(screen.getByRole("menu")).not.toHaveClass(
      "-top-account-menu-offset-y",
      "h-account-menu-height",
    );
    const expectedMenuItemClasses = [
      "h-account-menu-item-height",
      "gap-account-menu-item-gap",
      "rounded-account-menu-item",
      "px-account-menu-item-x",
      "text-account-menu-item",
      "text-account-menu-text",
      "hover:bg-account-menu-item-hover",
      "focus-visible:outline-account-menu-focus",
    ];
    const hardcodedMenuItemClasses = [
      "h-11",
      "gap-2.5",
      "rounded-md",
      "px-3",
      "text-[14px]",
      "text-[#131c2d]",
      "hover:bg-[#eff6ff]",
      "focus-visible:outline-[#006bff]",
    ];
    const dashboardMenuItem = screen.getByRole("menuitem", {
      name: "Dashboard",
    });

    expect(dashboardMenuItem).toHaveAttribute("href", "/dashboard");
    const workspaceMenuItem = screen.getByRole("menuitem", {
      name: "Workspace",
    });

    expect(workspaceMenuItem).toHaveAttribute("href", "/workspace");
    const settingsMenuItem = screen.getByRole("menuitem", { name: "Settings" });

    expect(settingsMenuItem).toHaveAttribute("href", "/settings");
    const signOutButton = screen.getByRole("menuitem", { name: "Sign out" });

    expect(
      screen.getAllByRole("menuitem").map((item) => item.textContent),
    ).toEqual(["Dashboard", "Workspace", "Settings", "Sign out"]);

    for (const menuItem of [
      dashboardMenuItem,
      workspaceMenuItem,
      settingsMenuItem,
      signOutButton,
    ]) {
      expect(menuItem).toHaveClass(...expectedMenuItemClasses);
      expect(menuItem).not.toHaveClass(...hardcodedMenuItemClasses);
    }

    expect(signOutButton).toBeEnabled();
    expect(signOutButton.closest("form")).toHaveAttribute(
      "action",
      "/web-api/auth/sign-out",
    );
    expect(signOutButton.closest("form")).toHaveAttribute("method", "post");

    fireEvent.pointerDown(document.body);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("updates authenticated user state from the shared session query cache", async () => {
    const { queryClient } = renderWithRoute("/overview", {
      session: {
        status: "authenticated",
        user: {
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        },
      },
    });

    expect(
      await screen.findByRole("button", { name: "User menu, Ada Lovelace" }),
    ).toHaveTextContent("ada@example.com");

    act(() => {
      queryClient.setQueryData(sessionQueryKeys.session, {
        status: "authenticated",
        user: {
          email: "grace@example.com",
          id: "user-2",
          name: "Grace Hopper",
        },
      });
    });

    expect(
      await screen.findByRole("button", { name: "User menu, Grace Hopper" }),
    ).toHaveTextContent("grace@example.com");
  });
});
