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

function jsonResponseWithHeaders(
  body: unknown,
  status: number,
  headers: HeadersInit,
): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json", ...headers },
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
            code: "authentication_required",
            message: "Authentication is required.",
          },
        },
        401,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const authErrorListener = vi.fn();

    window.addEventListener("knowledge.web-auth-error", authErrorListener);

    await expect(fetchWebApiJson("/web-api/dashboard/tokens")).rejects.toEqual(
      new WebApiRequestError({
        code: "authentication_required",
        message: "Authentication is required.",
        status: 401,
      }),
    );
    expect(authErrorListener).toHaveBeenCalledOnce();
    expect(
      (authErrorListener.mock.calls[0]?.[0] as CustomEvent).detail,
    ).toEqual({
      code: "authentication_required",
      message: "Authentication is required.",
      status: 401,
    });
    window.removeEventListener("knowledge.web-auth-error", authErrorListener);
  });

  it("does not emit auth events for non-auth request errors", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse(
        {
          error: {
            code: "layout_not_ready",
            message: "Taxonomy leaf layout is being prepared.",
          },
        },
        503,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const authErrorListener = vi.fn();

    window.addEventListener("knowledge.web-auth-error", authErrorListener);

    await expect(
      fetchWebApiJson("/web-api/taxonomy/view/path/math"),
    ).rejects.toBeInstanceOf(WebApiRequestError);
    expect(authErrorListener).not.toHaveBeenCalled();
    window.removeEventListener("knowledge.web-auth-error", authErrorListener);
  });

  it("preserves retry-after hints on typed request errors", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponseWithHeaders(
        {
          error: {
            code: "layout_not_ready",
            message: "Taxonomy leaf layout is being prepared.",
          },
        },
        503,
        { "Retry-After": "10" },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      fetchWebApiJson("/web-api/taxonomy/view/path/math"),
    ).rejects.toEqual(
      new WebApiRequestError({
        code: "layout_not_ready",
        message: "Taxonomy leaf layout is being prepared.",
        retryAfterSeconds: 10,
        status: 503,
      }),
    );
  });
});
