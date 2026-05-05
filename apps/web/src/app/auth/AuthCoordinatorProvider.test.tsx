// abstract: Unit tests for shared browser auth coordinator state and recovery.
// out_of_scope: App route layout, Logto network behavior, and BFF route contracts.

import "@testing-library/jest-dom/vitest";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { type PropsWithChildren, type ReactElement, useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  accountProfileQueryKeys,
  sessionQueryKeys,
} from "../../shared/web-api/sessionQueries";
import {
  AuthCoordinatorProvider,
  ProtectedRoute,
  useAuthCoordinator,
} from "./AuthCoordinatorProvider";
import * as authTransport from "./authTransport";

vi.mock("./authTransport", () => ({
  startSilentSignIn: vi.fn(async () => "failed"),
  submitInteractiveSignIn: vi.fn(),
  submitSignOut: vi.fn(),
}));

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

function renderWithCoordinator(
  ui: ReactElement,
  options: { readonly queryClient?: QueryClient } = {},
) {
  const queryClient = options.queryClient ?? createTestQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <AuthCoordinatorProvider>{ui}</AuthCoordinatorProvider>
    </QueryClientProvider>,
  );

  return { queryClient };
}

function StatusProbe() {
  const auth = useAuthCoordinator();

  return <div data-testid="auth-status">{auth.status}</div>;
}

function SilentProbe({ returnTo }: { readonly returnTo: string }) {
  const auth = useAuthCoordinator();

  useEffect(() => {
    if (auth.status === "anonymous") {
      void auth.attemptSilentSignIn(returnTo);
    }
  }, [auth, returnTo]);

  return <div data-testid="auth-status">{auth.status}</div>;
}

function GuardedContent({ children }: PropsWithChildren) {
  return <ProtectedRoute returnTo="/dashboard">{children}</ProtectedRoute>;
}

describe("AuthCoordinatorProvider", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ status: "anonymous" })),
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
  });

  it("starts in checking instead of anonymous while the session query is pending", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          await new Promise<Response>(() => {
            return;
          }),
      ),
    );

    renderWithCoordinator(<StatusProbe />);

    expect(screen.getByTestId("auth-status")).toHaveTextContent("checking");
  });

  it("resolves authenticated browser-safe session data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          status: "authenticated",
          user: { email: "ada@example.com", id: "user-1", name: "Ada" },
        }),
      ),
    );

    renderWithCoordinator(<StatusProbe />);

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "authenticated",
      ),
    );
  });

  it("attempts silent sign-in once per tab and refetches session after success", async () => {
    vi.mocked(authTransport.startSilentSignIn).mockResolvedValueOnce("success");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "anonymous" }))
      .mockResolvedValueOnce(
        jsonResponse({
          status: "authenticated",
          user: { id: "user-1" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    renderWithCoordinator(<SilentProbe returnTo="/overview" />);

    await waitFor(() =>
      expect(authTransport.startSilentSignIn).toHaveBeenCalledWith({
        returnTo: "/overview",
        timeoutMs: 10_000,
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "authenticated",
      ),
    );

    expect(
      window.sessionStorage.getItem("knowledge.auth.silent-attempted"),
    ).toBe("1");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("leaves public routes anonymous after silent sign-in failure", async () => {
    vi.mocked(authTransport.startSilentSignIn).mockResolvedValueOnce("failed");

    renderWithCoordinator(<SilentProbe returnTo="/docs" />);

    await waitFor(() =>
      expect(authTransport.startSilentSignIn).toHaveBeenCalledOnce(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent("anonymous"),
    );
  });

  it("keeps session check failures distinct from anonymous state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("network down");
      }),
    );

    renderWithCoordinator(<StatusProbe />);

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent("error"),
    );
  });

  it("clears auth caches and marks the session expired on global auth events", async () => {
    const queryClient = createTestQueryClient();

    queryClient.setQueryData(sessionQueryKeys.session, {
      status: "authenticated",
      user: { id: "user-1" },
    });
    queryClient.setQueryData(accountProfileQueryKeys.profile, { id: "user-1" });
    renderWithCoordinator(<StatusProbe />, { queryClient });

    window.dispatchEvent(
      new CustomEvent("knowledge.web-auth-error", {
        detail: {
          code: "session_expired",
          message: "Session expired.",
          status: 401,
        },
      }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("auth-status")).toHaveTextContent("expired"),
    );
    expect(queryClient.getQueryData(sessionQueryKeys.session)).toEqual({
      status: "anonymous",
    });
    expect(queryClient.getQueryData(accountProfileQueryKeys.profile)).toBe(
      undefined,
    );
  });

  it("starts interactive sign-in for protected anonymous routes once", async () => {
    renderWithCoordinator(
      <GuardedContent>
        <div data-testid="protected-content">Dashboard</div>
      </GuardedContent>,
    );

    await waitFor(() =>
      expect(authTransport.submitInteractiveSignIn).toHaveBeenCalledWith(
        "/dashboard",
      ),
    );
    expect(authTransport.submitInteractiveSignIn).toHaveBeenCalledOnce();
    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });

  it("renders protected content only after authentication is confirmed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          status: "authenticated",
          user: { id: "user-1" },
        }),
      ),
    );

    renderWithCoordinator(
      <GuardedContent>
        <div data-testid="protected-content">Dashboard</div>
      </GuardedContent>,
    );

    expect(await screen.findByTestId("protected-content")).toBeInTheDocument();
    expect(authTransport.submitInteractiveSignIn).not.toHaveBeenCalled();
  });

  it("does not loop protected sign-in while a form submission is already pending", async () => {
    const queryClient = createTestQueryClient();

    queryClient.setQueryData(sessionQueryKeys.session, { status: "anonymous" });
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <AuthCoordinatorProvider>
          <GuardedContent>
            <div>Dashboard</div>
          </GuardedContent>
        </AuthCoordinatorProvider>
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(authTransport.submitInteractiveSignIn).toHaveBeenCalledOnce(),
    );

    rerender(
      <QueryClientProvider client={queryClient}>
        <AuthCoordinatorProvider>
          <GuardedContent>
            <div>Dashboard</div>
          </GuardedContent>
        </AuthCoordinatorProvider>
      </QueryClientProvider>,
    );

    expect(authTransport.submitInteractiveSignIn).toHaveBeenCalledOnce();
  });
});
