// abstract: Unit tests for server-side user access-token refresh retry helpers.
// out_of_scope: Logto network transport and Account API response parsing.
// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  requestWithUserAccessTokenRetry,
  resolveUserAccessTokenWithRetry,
  WebSessionExpiredError,
} from "./tokenResolver.js";

function authRejectedError(): Error & { code: string } {
  return Object.assign(new Error("not authenticated"), {
    code: "not_authenticated",
  });
}

describe("resolveUserAccessTokenWithRetry", () => {
  it("clears cached access token and retries token acquisition once", async () => {
    const client = {
      clearAccessToken: vi.fn(async () => undefined),
      getAccessToken: vi
        .fn()
        .mockRejectedValueOnce(authRejectedError())
        .mockResolvedValueOnce("fresh"),
    };

    await expect(resolveUserAccessTokenWithRetry(client)).resolves.toBe(
      "fresh",
    );
    expect(client.clearAccessToken).toHaveBeenCalledOnce();
    expect(client.getAccessToken).toHaveBeenCalledTimes(2);
  });

  it("maps repeated token acquisition rejection to session expiration", async () => {
    const client = {
      clearAccessToken: vi.fn(async () => undefined),
      getAccessToken: vi.fn(async () => {
        throw authRejectedError();
      }),
    };

    await expect(resolveUserAccessTokenWithRetry(client)).rejects.toThrow(
      WebSessionExpiredError,
    );
    expect(client.clearAccessToken).toHaveBeenCalledOnce();
    expect(client.getAccessToken).toHaveBeenCalledTimes(2);
  });
});

describe("requestWithUserAccessTokenRetry", () => {
  it("clears cached access token and retries the original operation once", async () => {
    class AccountApiUnauthorizedError extends Error {}
    const client = {
      clearAccessToken: vi.fn(async () => undefined),
      getAccessToken: vi
        .fn()
        .mockResolvedValueOnce("cached")
        .mockResolvedValueOnce("fresh"),
    };
    const request = vi
      .fn()
      .mockRejectedValueOnce(new AccountApiUnauthorizedError())
      .mockResolvedValueOnce({ id: "user-1" });

    await expect(
      requestWithUserAccessTokenRetry(client, request, {
        isAccessTokenRejected: (error) =>
          error instanceof AccountApiUnauthorizedError,
      }),
    ).resolves.toEqual({ id: "user-1" });

    expect(request).toHaveBeenNthCalledWith(1, "cached");
    expect(request).toHaveBeenNthCalledWith(2, "fresh");
    expect(client.clearAccessToken).toHaveBeenCalledOnce();
  });

  it("maps a repeated operation token rejection to session expiration", async () => {
    class AccountApiUnauthorizedError extends Error {}
    const client = {
      clearAccessToken: vi.fn(async () => undefined),
      getAccessToken: vi
        .fn()
        .mockResolvedValueOnce("cached")
        .mockResolvedValueOnce("fresh"),
    };
    const request = vi.fn(async () => {
      throw new AccountApiUnauthorizedError();
    });

    await expect(
      requestWithUserAccessTokenRetry(client, request, {
        isAccessTokenRejected: (error) =>
          error instanceof AccountApiUnauthorizedError,
      }),
    ).rejects.toThrow(WebSessionExpiredError);

    expect(request).toHaveBeenCalledTimes(2);
    expect(client.clearAccessToken).toHaveBeenCalledOnce();
  });
});
