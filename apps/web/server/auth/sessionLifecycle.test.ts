// abstract: Unit tests for BFF authenticated session lifecycle helpers.
// out_of_scope: Logto SDK behavior and Redis session persistence.
// @vitest-environment node

import type { Request, Response } from "express";
import { describe, expect, it, vi } from "vitest";

import {
  destroyLocalSession,
  markAuthenticatedSession,
  readExpiredSessionReason,
  regenerateSessionPreserving,
  touchAuthenticatedSession,
  WEB_AUTH_ABSOLUTE_SESSION_MS,
  WEB_AUTH_IDLE_SESSION_MS,
} from "./sessionLifecycle.js";

interface FakeSession {
  [key: string]: unknown;
  destroy: (callback: (error?: Error) => void) => void;
  regenerate: (callback: (error?: Error) => void) => void;
}

function createRequest(session: FakeSession): Request {
  return { session } as unknown as Request;
}

describe("session lifecycle helpers", () => {
  it("marks authenticated session metadata only after successful authentication", () => {
    const session: FakeSession = {
      destroy: vi.fn(),
      regenerate: vi.fn(),
    };

    markAuthenticatedSession(createRequest(session), 1_000);

    expect(session.webAuth).toEqual({
      authenticatedAt: 1_000,
      lastSeenAt: 1_000,
    });
  });

  it("detects idle and absolute authenticated session expiration", () => {
    const session: FakeSession = {
      destroy: vi.fn(),
      regenerate: vi.fn(),
      webAuth: {
        authenticatedAt: 1_000,
        lastSeenAt: 2_000,
      },
    };

    expect(
      readExpiredSessionReason(
        createRequest(session),
        2_000 + WEB_AUTH_IDLE_SESSION_MS + 1,
      ),
    ).toBe("idle");
    expect(
      readExpiredSessionReason(
        createRequest({
          ...session,
          webAuth: {
            authenticatedAt: 1_000,
            lastSeenAt: 1_000 + WEB_AUTH_ABSOLUTE_SESSION_MS - 1,
          },
        }),
        1_000 + WEB_AUTH_ABSOLUTE_SESSION_MS + 1,
      ),
    ).toBe("absolute");
  });

  it("touches authenticated session metadata without extending absolute lifetime", () => {
    const session: FakeSession = {
      destroy: vi.fn(),
      regenerate: vi.fn(),
      webAuth: {
        authenticatedAt: 1_000,
        lastSeenAt: 2_000,
      },
    };

    touchAuthenticatedSession(createRequest(session), 3_000);

    expect(session.webAuth).toEqual({
      authenticatedAt: 1_000,
      lastSeenAt: 3_000,
    });
  });

  it("regenerates the session while preserving selected keys", async () => {
    const session: FakeSession = {
      authReturnTo: "/dashboard",
      destroy: vi.fn(),
      logtoKey: "sdk-state",
      regenerate: vi.fn((callback) => {
        delete session.authReturnTo;
        delete session.logtoKey;
        delete session.unrelated;
        session.regenerated = true;
        callback();
      }),
      unrelated: "drop",
    };

    await regenerateSessionPreserving(createRequest(session), [
      "authReturnTo",
      "logtoKey",
    ]);

    expect(session.regenerate).toHaveBeenCalledOnce();
    expect(session).toMatchObject({
      authReturnTo: "/dashboard",
      logtoKey: "sdk-state",
      regenerated: true,
    });
    expect(session.unrelated).toBeUndefined();
  });

  it("destroys local session data and clears the session cookie", async () => {
    const session: FakeSession = {
      destroy: vi.fn((callback) => {
        callback();
      }),
      regenerate: vi.fn(),
      webAuth: {
        authenticatedAt: 1_000,
        lastSeenAt: 1_000,
      },
    };
    const response = {
      clearCookie: vi.fn(),
    } as unknown as Response;

    await destroyLocalSession(createRequest(session), response);

    expect(session.destroy).toHaveBeenCalledOnce();
    expect(response.clearCookie).toHaveBeenCalledWith("knowledge.sid");
  });
});
