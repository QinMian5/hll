// abstract: Browser-facing BFF route for public repository metadata.
// out_of_scope: Browser shell rendering and GitHub authentication.

import { Router } from "express";
import { z } from "zod";

const GITHUB_REPOSITORY_API_URL = "https://api.github.com/repos/QinMian5/hll";
const DEFAULT_CACHE_TTL_MS = 10 * 60 * 1000;

const GitHubRepositoryMetadataSchema = z.object({
  html_url: z.string().url(),
  stargazers_count: z.number().int().nonnegative(),
});

export interface RepositorySummary {
  readonly repositoryUrl: string;
  readonly stars: number;
}

export interface CreateRepositorySummaryRouterOptions {
  readonly cacheTtlMs?: number;
  readonly fetchGitHub?: typeof fetch;
  readonly now?: () => number;
}

interface CachedRepositorySummary {
  readonly expiresAtMs: number;
  readonly summary: RepositorySummary;
}

async function fetchRepositorySummary(
  fetchGitHub: typeof fetch,
): Promise<RepositorySummary> {
  const response = await fetchGitHub(GITHUB_REPOSITORY_API_URL, {
    headers: {
      Accept: "application/vnd.github+json",
      "User-Agent": "knowledge-web-bff",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });

  if (!response.ok) {
    throw new Error("GitHub repository metadata request failed.");
  }

  const metadata = GitHubRepositoryMetadataSchema.parse(await response.json());

  return {
    repositoryUrl: metadata.html_url,
    stars: metadata.stargazers_count,
  };
}

export function createRepositorySummaryRouter(
  options: CreateRepositorySummaryRouterOptions = {},
): Router {
  const router = Router();
  const cacheTtlMs = options.cacheTtlMs ?? DEFAULT_CACHE_TTL_MS;
  const fetchGitHub = options.fetchGitHub ?? fetch;
  const now = options.now ?? Date.now;
  let cache: CachedRepositorySummary | undefined;

  router.get("/", async (_request, response) => {
    const currentTimeMs = now();

    if (cache !== undefined && cache.expiresAtMs > currentTimeMs) {
      response.json(cache.summary);
      return;
    }

    try {
      const summary = await fetchRepositorySummary(fetchGitHub);
      cache = {
        expiresAtMs: currentTimeMs + cacheTtlMs,
        summary,
      };
      response.json(summary);
    } catch (_error) {
      response.status(503).json({
        error: {
          code: "repository_summary_unavailable",
          message: "Repository summary unavailable.",
        },
      });
    }
  });

  return router;
}
