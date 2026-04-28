// abstract: Unit tests for the browser same-origin web API JSON client.
// out_of_scope: Feature-specific query adapters and server route behavior.

import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchWebApiJson } from "./client";
import { WebApiRequestError } from "./errors";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchWebApiJson", () => {
  it("sends PATCH JSON requests to same-origin web API paths", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchWebApiJson<{ readonly ok: true }>(
      "/web-api/dashboard/tokens",
      {
        body: { currentName: "Old", name: "New" },
        method: "PATCH",
      },
    );

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/dashboard/tokens",
      expect.objectContaining({
        body: JSON.stringify({ currentName: "Old", name: "New" }),
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }),
    );
  });

  it("returns undefined for empty 204 responses", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      fetchWebApiJson<void>("/web-api/dashboard/tokens/delete", {
        body: { name: "Research" },
        method: "POST",
      }),
    ).resolves.toBeUndefined();
  });

  it("rejects non-web-api paths before calling fetch", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchWebApiJson("/api/v1/search")).rejects.toThrow(
      "Web API requests must use same-origin /web-api paths.",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("raises typed request errors from web API error payloads", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        {
          error: {
            code: "dashboard_auth_required",
            message: "Authentication is required.",
          },
        },
        401,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchWebApiJson("/web-api/dashboard/tokens")).rejects.toEqual(
      new WebApiRequestError({
        code: "dashboard_auth_required",
        message: "Authentication is required.",
        status: 401,
      }),
    );
  });
});
