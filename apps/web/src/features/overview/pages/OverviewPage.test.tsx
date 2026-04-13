// abstract: Route-level tests for the Overview placeholder page inside the shared app shell.
// out_of_scope: Future Overview feature behavior beyond the approved placeholder state.

import "@testing-library/jest-dom/vitest";

import { RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../../../app/router";

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  window.scrollTo = vi.fn();
});

describe("OverviewPage", () => {
  it("renders a true routed placeholder page inside the shared shell", async () => {
    const router = createAppRouter({
      initialEntries: ["/overview"],
    });

    render(<RouterProvider router={router} />);

    await waitFor(() =>
      expect(screen.getByTestId("overview-route-page")).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("heading", { name: "Overview" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Overview content is not implemented yet."),
    ).toBeInTheDocument();
  });
});
