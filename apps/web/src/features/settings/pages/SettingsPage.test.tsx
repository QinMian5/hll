// abstract: Route-level tests for the account Settings page profile workflow.
// out_of_scope: Logto network behavior and app-shell navigation behavior.

import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { WebSessionResponse } from "../../../shared/web-api/session";
import { sessionQueryKeys } from "../../../shared/web-api/sessionQueries";
import { SettingsPage } from ".";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: false,
        staleTime: 30_000,
      },
    },
  });
}

function renderSettingsPage() {
  const queryClient = createTestQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );

  return { queryClient };
}

async function findLoadedNameInput(value = "Ada Lovelace") {
  const input = await screen.findByLabelText("Name");

  await waitFor(() => expect(input).toHaveValue(value));

  return input;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("SettingsPage", () => {
  it("renders the authenticated Figma Settings structure without extra account copy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        }),
      ),
    );

    renderSettingsPage();

    expect(await findLoadedNameInput()).toHaveValue("Ada Lovelace");
    expect(screen.getByTestId("settings-route-page")).toHaveClass(
      "px-4",
      "pt-5",
      "lg:px-8",
      "lg:pt-8",
    );
    expect(screen.getByTestId("settings-column")).toHaveClass(
      "max-w-[720px]",
      "gap-4",
      "lg:gap-6",
    );
    expect(screen.getByTestId("settings-name-row")).toHaveClass(
      "grid-cols-1",
      "gap-2",
      "px-4",
      "py-4",
      "lg:h-[72px]",
      "lg:grid-cols-[240px_360px]",
      "lg:gap-[72px]",
      "lg:px-6",
      "lg:py-[18px]",
    );
    expect(await screen.findByLabelText("Name")).toHaveClass(
      "h-9",
      "lg:w-[360px]",
    );
    expect(screen.queryByText("Account")).not.toBeInTheDocument();
    expect(screen.queryByText(/saved/i)).not.toBeInTheDocument();
  });

  it("renders a compact sign-in state for anonymous direct visits", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse(
          {
            error: {
              code: "authentication_required",
              message: "Authentication required.",
            },
          },
          401,
        ),
      ),
    );

    renderSettingsPage();

    expect(
      await screen.findByText("Sign in to manage your account."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
    expect(
      screen.getByRole("button", { name: "Sign in" }).closest("form"),
    ).toHaveAttribute("action", "/web-api/auth/sign-in");
  });

  it("autosaves a changed name on blur and refreshes shared session display data", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        if (
          String(input) === "/web-api/auth/profile" &&
          init?.method === "PATCH"
        ) {
          return jsonResponse({
            email: "grace@example.com",
            id: "user-1",
            name: "Grace Hopper",
          });
        }

        return jsonResponse({
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    const { queryClient } = renderSettingsPage();

    const input = await findLoadedNameInput();
    fireEvent.change(input, { target: { value: "  Grace Hopper  " } });
    fireEvent.blur(input);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/web-api/auth/profile",
        expect.objectContaining({
          body: JSON.stringify({ name: "Grace Hopper" }),
          method: "PATCH",
        }),
      ),
    );
    expect(await screen.findByLabelText("Name")).toHaveValue("Grace Hopper");
    expect(
      queryClient.getQueryData<WebSessionResponse>(sessionQueryKeys.session),
    ).toEqual({
      status: "authenticated",
      user: {
        email: "grace@example.com",
        id: "user-1",
        name: "Grace Hopper",
      },
    });
  });

  it("autosaves with Enter and clears names with a null payload", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        if (
          String(input) === "/web-api/auth/profile" &&
          init?.method === "PATCH"
        ) {
          return jsonResponse({
            email: "ada@example.com",
            id: "user-1",
          });
        }

        return jsonResponse({
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderSettingsPage();

    const input = await findLoadedNameInput();
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/web-api/auth/profile",
        expect.objectContaining({
          body: JSON.stringify({ name: null }),
          method: "PATCH",
        }),
      ),
    );
    expect(await screen.findByLabelText("Name")).toHaveValue("");
  });

  it("skips unchanged normalized values and restores the saved value on Escape", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        jsonResponse({
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderSettingsPage();

    const input = await findLoadedNameInput();
    fireEvent.change(input, { target: { value: "  Ada Lovelace  " } });
    fireEvent.blur(input);
    fireEvent.change(input, { target: { value: "Temporary" } });
    fireEvent.keyDown(input, { key: "Escape" });

    expect(input).toHaveValue("Ada Lovelace");
    expect(
      fetchMock.mock.calls.filter(
        ([path, init]) =>
          String(path) === "/web-api/auth/profile" &&
          (init as RequestInit | undefined)?.method === "PATCH",
      ),
    ).toHaveLength(0);
  });

  it("shows non-inline save errors with invalid field styling", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        if (
          String(input) === "/web-api/auth/profile" &&
          init?.method === "PATCH"
        ) {
          return jsonResponse(
            {
              error: {
                code: "logto_account_profile_unavailable",
                message: "Account profile is unavailable.",
              },
            },
            502,
          );
        }

        return jsonResponse({
          email: "ada@example.com",
          id: "user-1",
          name: "Ada Lovelace",
        });
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    renderSettingsPage();

    const input = await findLoadedNameInput();
    fireEvent.change(input, { target: { value: "Ada Byron" } });
    fireEvent.blur(input);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Account profile is unavailable.",
    );
    expect(input).toHaveValue("Ada Byron");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveClass("border-[#dc2626]");
    expect(
      screen.queryByTestId("settings-name-inline-error"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/saved/i)).not.toBeInTheDocument();
  });
});
