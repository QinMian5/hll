// abstract: Behavior tests for semantic-map page empty-state handling.
// out_of_scope: deck.gl rendering internals and end-to-end browser behavior.

import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../../app/providers";
import { SemanticMapPage } from "./SemanticMapPage";

describe("SemanticMapPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the empty state when no snapshot is available", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND",
              details: {},
              hint: "Rebuild semantic-map artifacts and retry.",
              message: "No semantic-map snapshot is currently available.",
              request_id: "req_test_snapshot_missing",
            },
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 404,
          },
        ),
      ),
    );

    render(
      <AppProviders>
        <SemanticMapPage />
      </AppProviders>,
    );

    expect(
      await screen.findByText(/snapshot unavailable/i),
    ).toBeInTheDocument();
  });
});
