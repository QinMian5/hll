// abstract: Unit tests for same-origin validation on state-changing web API requests.
// out_of_scope: Feature route behavior and browser CORS policy.
// @vitest-environment node

import type { NextFunction, Request, Response } from "express";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadWebServerConfig } from "../config.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import { createWebApiOriginGuard } from "./webApiOriginGuard.js";

const config = loadWebServerConfig(createWebServerTestEnv());

function createResponse(): Response {
  return {
    json: vi.fn(),
    status: vi.fn(function status(this: Response) {
      return this;
    }),
  } as unknown as Response;
}

function createRequest(options: {
  readonly headers?: Record<string, string>;
  readonly method: string;
  readonly originalUrl?: string;
}): Request {
  return {
    get: (name: string) => options.headers?.[name.toLowerCase()],
    method: options.method,
    originalUrl: options.originalUrl ?? "/web-api/auth/sign-in",
  } as unknown as Request;
}

describe("createWebApiOriginGuard", () => {
  let next: NextFunction;

  beforeEach(() => {
    next = vi.fn();
  });

  it("does not block safe read methods", () => {
    const response = createResponse();

    createWebApiOriginGuard(config)(
      createRequest({ method: "GET" }),
      response,
      next,
    );

    expect(next).toHaveBeenCalledOnce();
    expect(response.status).not.toHaveBeenCalled();
  });

  it("accepts same-origin Origin headers", () => {
    const response = createResponse();

    createWebApiOriginGuard(config)(
      createRequest({
        headers: { origin: "http://localhost:5173" },
        method: "POST",
      }),
      response,
      next,
    );

    expect(next).toHaveBeenCalledOnce();
    expect(response.status).not.toHaveBeenCalled();
  });

  it("accepts same-origin Referer fallback when Origin is absent", () => {
    const response = createResponse();

    createWebApiOriginGuard(config)(
      createRequest({
        headers: { referer: "http://localhost:5173/search?q=science" },
        method: "PATCH",
      }),
      response,
      next,
    );

    expect(next).toHaveBeenCalledOnce();
    expect(response.status).not.toHaveBeenCalled();
  });

  it("rejects cross-origin mutations without invoking downstream handlers", () => {
    const response = createResponse();

    createWebApiOriginGuard(config)(
      createRequest({
        headers: { origin: "https://evil.example" },
        method: "POST",
      }),
      response,
      next,
    );

    expect(next).not.toHaveBeenCalled();
    expect(response.status).toHaveBeenCalledWith(403);
    expect(response.json).toHaveBeenCalledWith({
      error: {
        code: "csrf_origin_rejected",
        message: "Request origin is not allowed.",
      },
    });
  });

  it("rejects mutations without Origin or Referer metadata", () => {
    const response = createResponse();

    createWebApiOriginGuard(config)(
      createRequest({ method: "POST" }),
      response,
      next,
    );

    expect(next).not.toHaveBeenCalled();
    expect(response.status).toHaveBeenCalledWith(403);
  });
});
