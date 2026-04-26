// abstract: Behavior tests for shared browser runtime configuration rules.
// out_of_scope: React rendering behavior and Vite dev-server proxy wiring.

import { describe, expect, it } from "vitest";

import { resolveBrowserRuntimeConfig } from "./index";

describe("resolveBrowserRuntimeConfig", () => {
  it("does not expose a backend API origin to browser code", () => {
    expect(
      resolveBrowserRuntimeConfig({
        PRIVATE_API_BASE_URL: "https://api.example.com/",
      }),
    ).toEqual({});
  });
});
