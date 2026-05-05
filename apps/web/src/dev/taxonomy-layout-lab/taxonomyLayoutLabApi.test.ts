// abstract: Unit tests for taxonomy layout lab HTTP client helpers.
// out_of_scope: React rendering and production web API transport.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchLayoutLabDefaultParams,
  fetchLayoutLabFixtures,
  solveLayoutLab,
} from "./taxonomyLayoutLabApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("taxonomyLayoutLabApi", () => {
  it("fetches fixture summaries from the configured local API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ name: "obsidian-sample" }]), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      fetchLayoutLabFixtures({ apiBaseUrl: "http://127.0.0.1:8765" }),
    ).resolves.toEqual([{ name: "obsidian-sample" }]);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8765/fixtures", {
      signal: undefined,
    });
  });

  it("posts parameter overrides to the solve endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ layout_version: "taxonomy-card-scope-layout-v1" }),
        {
          status: 200,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await solveLayoutLab({
      apiBaseUrl: "http://127.0.0.1:8765/",
      fixtureName: "obsidian-sample",
      params: { simulation_ticks: 1 },
    });

    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8765/solve", {
      body: JSON.stringify({
        fixtureName: "obsidian-sample",
        params: { simulation_ticks: 1 },
      }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
      signal: undefined,
    });
  });

  it("fetches default parameter values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ simulation_ticks: 220 }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      fetchLayoutLabDefaultParams({ apiBaseUrl: "http://127.0.0.1:8765" }),
    ).resolves.toEqual({ simulation_ticks: 220 });
  });

  it("raises a useful error when the lab API returns an error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "bad params" }), {
        status: 422,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      fetchLayoutLabDefaultParams({ apiBaseUrl: "http://127.0.0.1:8765" }),
    ).rejects.toThrow("bad params");
  });
});
