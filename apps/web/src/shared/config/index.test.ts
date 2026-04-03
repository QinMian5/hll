// abstract: Behavior tests for shared API-base-url resolution rules.
// out_of_scope: React rendering behavior and Vite dev-server proxy wiring.

import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./index";

describe("resolveApiBaseUrl", () => {
  it("prefers an explicitly configured API base URL", () => {
    expect(
      resolveApiBaseUrl({
        VITE_API_BASE_URL: "https://api.example.com/",
      }),
    ).toBe("https://api.example.com");
  });

  it("uses relative requests when no explicit base URL is set", () => {
    expect(
      resolveApiBaseUrl({
        VITE_API_BASE_URL: "   ",
      }),
    ).toBeUndefined();
  });
});
