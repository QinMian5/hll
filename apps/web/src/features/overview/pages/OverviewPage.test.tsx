// abstract: Route-level tests for the Overview project-introduction page inside the shared app shell.
// out_of_scope: Live product metrics, backend data integration, and browser-level visual fidelity.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { createAppRouter } from "../../../app/router";

vi.mock("../../../app/auth/authTransport", () => ({
  startSilentSignIn: vi.fn(async () => "failed"),
  submitInteractiveSignIn: vi.fn(),
  submitSignOut: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.scrollTo = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ status: "anonymous" }), {
          headers: { "Content-Type": "application/json" },
          status: 200,
        }),
    ),
  );
});

describe("OverviewPage", () => {
  it("explains the project thesis and knowledge flow", async () => {
    const router = createAppRouter({
      initialEntries: ["/overview"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("overview-route-page")).toBeInTheDocument(),
    );
    const page = within(screen.getByTestId("overview-route-page"));

    expect(
      page.getByRole("heading", { name: "Humanity's Last Library" }),
    ).toBeInTheDocument();
    expect(
      page.getByText(
        /A human-maintained knowledge network for agents to search, cite, and use\./,
      ),
    ).toBeInTheDocument();
    expect(
      page.getByText(
        /Models reason, humans maintain, and the network carries incrementally updated facts\./,
      ),
    ).toBeInTheDocument();
    expect(page.getByText("Retrieval over memorization")).toBeInTheDocument();
    expect(page.getByText("Human-reviewed updates")).toBeInTheDocument();
    expect(page.getByText("Usage-informed structure")).toBeInTheDocument();

    expect(
      page.getByRole("img", { name: /Knowledge Loop diagram/ }),
    ).toHaveAttribute("src", "/overview/knowledge-loop.png");
    expect(
      page.getByRole("img", {
        name: /From Memorization to Retrieval diagram/,
      }),
    ).toHaveAttribute("src", "/overview/from-memorization-to-retrieval.png");
    expect(page.queryByText("Knowledge Loop")).not.toBeInTheDocument();
    expect(
      page.queryByText("From Memorization to Retrieval"),
    ).not.toBeInTheDocument();
    expect(
      page.queryByText("Agent-era knowledge infrastructure"),
    ).not.toBeInTheDocument();
  });

  it("surfaces current product entry points and honest limits", async () => {
    const router = createAppRouter({
      initialEntries: ["/overview"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("overview-route-page")).toBeInTheDocument(),
    );
    const page = within(screen.getByTestId("overview-route-page"));

    for (const link of [
      ["Search", "/search"],
      ["Graph View", "/graph"],
      ["Docs", "/docs"],
      ["Dashboard", "/dashboard"],
      ["Workspace", "/workspace"],
    ] as const) {
      expect(
        page.getByRole("link", { name: `Open ${link[0]} from Overview` }),
      ).toHaveAttribute("href", link[1]);
    }

    expect(page.getByText(/Wikipedia-derived/)).toBeInTheDocument();
    expect(page.getByText(/AI-assisted extraction/)).toBeInTheDocument();
    expect(
      page.getByText(/architecture experiment, not proof/),
    ).toBeInTheDocument();
  });
});
