// abstract: Unit tests for browser session and account profile web API adapters.
// out_of_scope: React query cache orchestration and settings page rendering.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchAccountProfile,
  fetchWebSession,
  updateAccountProfile,
} from "./session";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("web session adapters", () => {
  it("fetches the same-origin BFF session endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        status: "authenticated",
        user: { id: "user-1", name: "Ada" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchWebSession();

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/auth/session",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      status: "authenticated",
      user: { id: "user-1", name: "Ada" },
    });
  });

  it("fetches the account profile without exposing token fields", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        email: "ada@example.com",
        id: "user-1",
        name: "Ada",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAccountProfile();

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/auth/profile",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
    expect(result).toEqual({
      email: "ada@example.com",
      id: "user-1",
      name: "Ada",
    });
    expect(JSON.stringify(result)).not.toContain("token");
  });

  it("patches account profile names through the BFF endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        email: "ada@example.com",
        id: "user-1",
        name: "Grace Hopper",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await updateAccountProfile({ name: "Grace Hopper" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/web-api/auth/profile",
      expect.objectContaining({
        body: JSON.stringify({ name: "Grace Hopper" }),
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        method: "PATCH",
      }),
    );
    expect(result).toEqual({
      email: "ada@example.com",
      id: "user-1",
      name: "Grace Hopper",
    });
  });
});
