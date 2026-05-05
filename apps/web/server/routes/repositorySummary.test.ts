// abstract: Contract tests for the repository summary BFF route.
// out_of_scope: Browser shell rendering and GitHub service availability.
// @vitest-environment node

import { Router } from "express";
import request from "supertest";
import { describe, expect, it, vi } from "vitest";

import { createApp } from "../app.js";
import { loadWebServerConfig } from "../config.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import { createRepositorySummaryRouter } from "./repositorySummary.js";

const TEST_ENV = createWebServerTestEnv();

async function createTestApp(options: {
  readonly cacheTtlMs?: number;
  readonly fetchGitHub: typeof fetch;
  readonly now?: () => number;
}) {
  const config = loadWebServerConfig(TEST_ENV);
  const webApiRouter = Router();

  webApiRouter.use(
    "/repository-summary",
    createRepositorySummaryRouter({
      cacheTtlMs: options.cacheTtlMs,
      fetchGitHub: options.fetchGitHub,
      now: options.now,
    }),
  );

  return await createApp({
    config,
    runtime: {
      indexHtml: '<html><body><div id="root"></div></body></html>',
      kind: "production",
    },
    webApiRouter,
  });
}

describe("repository summary route", () => {
  it("returns GitHub star count from repository metadata", async () => {
    const fetchGitHub = vi.fn(async () =>
      Response.json({
        html_url: "https://github.com/QinMian5/hll",
        stargazers_count: 7,
      }),
    );
    const app = await createTestApp({ fetchGitHub });

    const response = await request(app).get("/web-api/repository-summary");

    expect(response.status).toBe(200);
    expect(fetchGitHub).toHaveBeenCalledWith(
      "https://api.github.com/repos/QinMian5/hll",
      {
        headers: {
          Accept: "application/vnd.github+json",
          "User-Agent": "knowledge-web-bff",
          "X-GitHub-Api-Version": "2022-11-28",
        },
      },
    );
    expect(response.body).toEqual({
      repositoryUrl: "https://github.com/QinMian5/hll",
      stars: 7,
    });
  });

  it("caches successful repository metadata responses", async () => {
    let currentTimeMs = 10_000;
    const fetchGitHub = vi.fn(async () =>
      Response.json({
        html_url: "https://github.com/QinMian5/hll",
        stargazers_count: 1,
      }),
    );
    const app = await createTestApp({
      cacheTtlMs: 60_000,
      fetchGitHub,
      now: () => currentTimeMs,
    });

    const first = await request(app).get("/web-api/repository-summary");
    currentTimeMs += 30_000;
    const second = await request(app).get("/web-api/repository-summary");

    expect(first.body).toEqual({
      repositoryUrl: "https://github.com/QinMian5/hll",
      stars: 1,
    });
    expect(second.body).toEqual(first.body);
    expect(fetchGitHub).toHaveBeenCalledTimes(1);
  });

  it("returns a safe unavailable error when GitHub metadata cannot be loaded", async () => {
    const fetchGitHub = vi.fn(async () =>
      Response.json({ message: "rate limit exceeded" }, { status: 403 }),
    );
    const app = await createTestApp({ fetchGitHub });

    const response = await request(app).get("/web-api/repository-summary");

    expect(response.status).toBe(503);
    expect(response.body).toEqual({
      error: {
        code: "repository_summary_unavailable",
        message: "Repository summary unavailable.",
      },
    });
    expect(response.text).not.toContain("rate limit exceeded");
  });
});
