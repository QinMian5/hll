// abstract: Unit tests for anonymous browser identity cookie handling.
// out_of_scope: Quota policy evaluation and Redis persistence.
// @vitest-environment node

import express from "express";
import request from "supertest";
import { describe, expect, it } from "vitest";

import { loadWebServerConfig } from "../config.js";
import { createWebServerTestEnv } from "../testSupport/webServerEnv.js";
import { ensureAnonymousIdentity } from "./anonymousIdentity.js";

const TEST_ENV = createWebServerTestEnv();

describe("ensureAnonymousIdentity", () => {
  it("sets an httpOnly anonymous identity cookie when the request has none", async () => {
    const app = express();
    const config = loadWebServerConfig(TEST_ENV);

    app.get("/test", (request, response) => {
      response.json({
        anonymousId: ensureAnonymousIdentity(request, response, config, {
          generateId: () => "anon-1",
        }),
      });
    });

    const response = await request(app).get("/test");

    expect(response.body).toEqual({ anonymousId: "anon-1" });
    expect(response.headers["set-cookie"]).toEqual([
      expect.stringContaining("knowledge.anonymous_id=anon-1;"),
    ]);
    expect(response.headers["set-cookie"][0]).toContain("HttpOnly");
    expect(response.headers["set-cookie"][0]).toContain("SameSite=Lax");
  });

  it("reuses an existing anonymous identity cookie without resetting it", async () => {
    const app = express();
    const config = loadWebServerConfig(TEST_ENV);

    app.get("/test", (request, response) => {
      response.json({
        anonymousId: ensureAnonymousIdentity(request, response, config, {
          generateId: () => "new-anon",
        }),
      });
    });

    const response = await request(app)
      .get("/test")
      .set("Cookie", "knowledge.anonymous_id=existing-anon");

    expect(response.body).toEqual({ anonymousId: "existing-anon" });
    expect(response.headers["set-cookie"]).toBeUndefined();
  });
});
