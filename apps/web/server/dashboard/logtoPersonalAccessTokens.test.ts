// abstract: Contract tests for the Logto Management API PAT adapter.
// out_of_scope: Browser-facing route validation and OAuth token acquisition.
// @vitest-environment node

import { describe, expect, it, vi } from "vitest";

import {
  createLogtoPersonalAccessTokensClient,
  type LogtoPersonalAccessTokenError,
} from "./logtoPersonalAccessTokens.js";

const LOGTO_TOKEN = {
  createdAt: Date.parse("2026-04-28T10:00:00.000Z"),
  expiresAt: Date.parse("2026-05-28T10:00:00.000Z"),
  name: "Laptop",
  value: "kg_pat_plaintext_value",
};

const TOKEN = {
  createdAt: "2026-04-28T10:00:00.000Z",
  expiresAt: "2026-05-28T10:00:00.000Z",
  name: "Laptop",
  value: "kg_pat_plaintext_value",
};

function createClient(fetchLogto: typeof fetch) {
  return createLogtoPersonalAccessTokensClient({
    accessToken: async () => "management-token",
    apiBaseUrl: "https://logto.example/api",
    fetch: fetchLogto,
  });
}

describe("Logto personal access token client", () => {
  it("lists personal access tokens for a Logto user", async () => {
    const fetchLogto = vi.fn(async () => {
      return Response.json([LOGTO_TOKEN]);
    });
    const client = createClient(fetchLogto);

    await expect(client.listPersonalAccessTokens("user-1")).resolves.toEqual([
      TOKEN,
    ]);

    expect(fetchLogto).toHaveBeenCalledWith(
      "https://logto.example/api/users/user-1/personal-access-tokens",
      {
        headers: { authorization: "Bearer management-token" },
        method: "GET",
      },
    );
  });

  it("creates a named personal access token for a Logto user", async () => {
    const fetchLogto = vi.fn(async () => {
      return Response.json(LOGTO_TOKEN, { status: 201 });
    });
    const client = createClient(fetchLogto);

    await expect(
      client.createPersonalAccessToken("user-1", "Laptop"),
    ).resolves.toEqual(TOKEN);

    expect(fetchLogto).toHaveBeenCalledWith(
      "https://logto.example/api/users/user-1/personal-access-tokens",
      {
        body: JSON.stringify({ name: "Laptop" }),
        headers: {
          authorization: "Bearer management-token",
          "content-type": "application/json",
        },
        method: "POST",
      },
    );
  });

  it("accepts Logto personal access token responses with metadata fields", async () => {
    const fetchLogto = vi.fn(async () => {
      return Response.json(
        {
          ...LOGTO_TOKEN,
          tenantId: "default",
          userId: "user-1",
        },
        { status: 201 },
      );
    });
    const client = createClient(fetchLogto);

    await expect(
      client.createPersonalAccessToken("user-1", "Laptop"),
    ).resolves.toEqual(TOKEN);
  });

  it("renames a personal access token with Logto currentName semantics", async () => {
    const renamed = { ...LOGTO_TOKEN, name: "Workstation" };
    const expected = { ...TOKEN, name: "Workstation" };
    const fetchLogto = vi.fn(async () => {
      return Response.json(renamed);
    });
    const client = createClient(fetchLogto);

    await expect(
      client.renamePersonalAccessToken("user-1", "Laptop", "Workstation"),
    ).resolves.toEqual(expected);

    expect(fetchLogto).toHaveBeenCalledWith(
      "https://logto.example/api/users/user-1/personal-access-tokens",
      {
        body: JSON.stringify({
          currentName: "Laptop",
          name: "Workstation",
        }),
        headers: {
          authorization: "Bearer management-token",
          "content-type": "application/json",
        },
        method: "PATCH",
      },
    );
  });

  it("deletes a personal access token by name", async () => {
    const fetchLogto = vi.fn(async () => {
      return new Response(null, { status: 204 });
    });
    const client = createClient(fetchLogto);

    await expect(
      client.deletePersonalAccessToken("user-1", "Laptop"),
    ).resolves.toBeUndefined();

    expect(fetchLogto).toHaveBeenCalledWith(
      "https://logto.example/api/users/user-1/personal-access-tokens/Laptop",
      {
        headers: { authorization: "Bearer management-token" },
        method: "DELETE",
      },
    );
  });

  it("maps Logto conflict responses to a typed adapter error", async () => {
    const fetchLogto = vi.fn(async () => {
      return Response.json({ message: "already exists" }, { status: 409 });
    });
    const client = createClient(fetchLogto);

    await expect(
      client.createPersonalAccessToken("user-1", "Laptop"),
    ).rejects.toMatchObject({
      code: "dashboard_token_name_conflict",
      name: "LogtoPersonalAccessTokenError",
      status: 409,
    } satisfies Partial<LogtoPersonalAccessTokenError>);
  });

  it("maps Logto duplicate-name validation responses to a conflict error", async () => {
    const fetchLogto = vi.fn(async () => {
      return Response.json(
        {
          code: "user.personal_access_token_name_exists",
          message: "Personal access token name already exists.",
        },
        { status: 422 },
      );
    });
    const client = createClient(fetchLogto);

    await expect(
      client.createPersonalAccessToken("user-1", "Laptop"),
    ).rejects.toMatchObject({
      code: "dashboard_token_name_conflict",
      name: "LogtoPersonalAccessTokenError",
      status: 409,
    } satisfies Partial<LogtoPersonalAccessTokenError>);
  });
});
