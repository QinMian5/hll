// abstract: Contract tests for the Docker-internal FastAPI web BFF client.
// out_of_scope: Browser fetch adapters and feature-specific route validation.
// @vitest-environment node

import { afterEach, describe, expect, it, vi } from "vitest";

import type { WebServerConfig } from "../config.js";
import { createInternalApiClient } from "./client.js";
import type { InternalApiError } from "./errors.js";

const CONFIG = {
  internalApiBaseUrl: "https://api.example",
} as WebServerConfig;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("internal API client", () => {
  it("preserves safe 4xx FastAPI error envelopes for web routes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          {
            error: {
              code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
              details: {},
              hint: "Change the suggested title or content.",
              message: "Suggested edit must change the card title or content.",
              request_id: "req_12345678",
            },
          },
          { status: 422 },
        ),
      ),
    );

    const client = createInternalApiClient(CONFIG);

    await expect(client.search("energy")).rejects.toMatchObject({
      clientMessage: "Suggested edit must change the card title or content.",
      code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
      name: "InternalApiError",
      status: 422,
    } satisfies Partial<InternalApiError>);
  });

  it("preserves taxonomy layout readiness 503 envelopes and retry hints", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          {
            error: {
              code: "layout_not_ready",
              details: {
                route_path: "science/mathematics",
                scope_kind: "taxonomy_node",
                taxonomy_node_id: 7,
              },
              hint: "Retry this request shortly.",
              message: "Taxonomy card-scope layout is being prepared.",
              request_id: "req_12345678",
            },
          },
          {
            headers: { "Retry-After": "10" },
            status: 503,
          },
        ),
      ),
    );

    const client = createInternalApiClient(CONFIG);

    await expect(client.getTaxonomyNodeByPath("science")).rejects.toMatchObject(
      {
        clientMessage: "Taxonomy card-scope layout is being prepared.",
        code: "layout_not_ready",
        name: "InternalApiError",
        retryAfterSeconds: 10,
        status: 503,
      } satisfies Partial<InternalApiError>,
    );
  });
});
