// abstract: Shared routed app shell with brand, top navigation, and route body outlet.
// out_of_scope: Feature-specific page content and backend data orchestration.

import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import {
  fetchWebSession,
  type WebSessionResponse,
} from "../shared/web-api/session";

const navItems = [
  { label: "Overview", to: "/overview" as const },
  { label: "Graph View", to: "/graph" as const },
  { label: "Search", to: "/search" as const },
];

const buttonClasses =
  "inline-flex h-9 w-[78px] items-center justify-center rounded-xl border border-[rgba(38,48,69,0.84)] bg-[rgba(20,28,46,0.96)] px-3 text-[13px] leading-4 font-medium text-[rgba(250,252,255,0.96)] md:h-10 md:w-[92px] md:px-4 md:text-[14px] md:leading-[18px]";
const activeButtonClasses = `${buttonClasses} cursor-pointer`;

function GithubMark() {
  return (
    <svg
      aria-hidden="true"
      className="size-[17px] md:size-[18px]"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M15.6 21v-3.1c0-.8-.3-1.4-.8-1.8 2.7-.3 5.5-1.3 5.5-6A4.7 4.7 0 0 0 19 6.8c.1-.3.5-1.7-.1-3.3 0 0-1.1-.3-3.5 1.3a12 12 0 0 0-6.4 0C6.6 3.2 5.5 3.5 5.5 3.5c-.6 1.6-.2 3-.1 3.3a4.7 4.7 0 0 0-1.3 3.3c0 4.6 2.8 5.7 5.5 6-.4.4-.7.9-.8 1.6-.8.3-2.7.9-3.9-1.1 0 0-.7-1.3-2.1-1.4 0 0-1.3 0-.1.8 0 0 .9.4 1.5 1.8 0 0 .8 2.6 4.5 1.7V21"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.7"
      />
    </svg>
  );
}

function useWebSession(): WebSessionResponse {
  const [session, setSession] = useState<WebSessionResponse>({
    status: "anonymous",
  });

  useEffect(() => {
    let isMounted = true;

    fetchWebSession()
      .then((nextSession) => {
        if (isMounted) {
          setSession(nextSession);
        }
      })
      .catch(() => {
        if (isMounted) {
          setSession({ status: "anonymous" });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return session;
}

function ShellAuthAction() {
  const session = useWebSession();

  if (session.status === "authenticated") {
    const displayName =
      session.user.name ?? session.user.email ?? session.user.id;

    return (
      <div className="flex min-w-0 items-center gap-2">
        <span className="hidden max-w-[112px] truncate text-right text-[13px] leading-5 font-medium text-[rgba(38,48,71,0.82)] sm:inline">
          {displayName}
        </span>
        <form action="/web-api/auth/sign-out" method="post">
          <button className={activeButtonClasses} type="submit">
            Sign out
          </button>
        </form>
      </div>
    );
  }

  return (
    <form action="/web-api/auth/sign-in" method="post">
      <button className={activeButtonClasses} type="submit">
        Sign in
      </button>
    </form>
  );
}

export function AppShell() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });

  return (
    <div
      className="flex h-screen min-h-screen w-full flex-col bg-[radial-gradient(circle_at_center,_#f2faff_0%,_#fbfcff_55%,_#f6f7fb_100%)] font-['Geist',sans-serif]"
      data-testid="app-shell"
    >
      <header
        className="grid h-[112px] w-full shrink-0 grid-cols-[minmax(0,1fr)_124px] grid-rows-[40px_34px] gap-x-2 gap-y-2.5 bg-[rgba(255,255,255,0.72)] px-[14px] pt-3 pb-2.5 shadow-[0_4px_9px_rgba(51,61,87,0.04)] md:flex md:h-16 md:items-center md:justify-between md:gap-0 md:px-4 md:py-3"
        data-testid="app-shell-header"
      >
        <div className="col-start-1 row-start-1 flex h-9 w-[170px] items-center gap-2.5 self-center justify-self-start md:h-10 md:w-[240px]">
          <div
            aria-hidden="true"
            className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#2563eb] text-[14px] leading-[18px] font-semibold text-white md:size-[30px] md:text-[15px] md:leading-5"
          >
            K
          </div>
          <span className="whitespace-nowrap text-[14px] leading-[18px] font-medium text-[#131c2d] md:text-[15px] md:leading-5">
            Knowledge Graph
          </span>
        </div>
        <nav
          aria-label="Primary"
          className="col-span-2 row-start-2 flex h-[34px] w-[300px] items-center justify-center gap-2.5 self-center justify-self-center md:h-10 md:w-[278px] md:gap-3"
          data-testid="app-shell-nav"
        >
          {navItems.map((item) => {
            const isActive = pathname === item.to;
            const itemWidth =
              item.label === "Graph View" ? "w-[88px]" : "w-[74px]";

            return (
              <Link
                className={`grid h-[30px] ${itemWidth} place-items-center no-underline md:h-[34px]`}
                data-nav-state={isActive ? "active" : "inactive"}
                key={item.to}
                to={item.to}
              >
                <span
                  className={
                    isActive
                      ? "relative inline-flex flex-col items-center gap-1 text-center text-[13px] leading-[17px] font-semibold text-[#131c2d] after:h-[2px] after:w-9 after:rounded-full after:bg-[#2563eb] after:content-[''] md:gap-[5px] md:text-[14px] md:leading-[18px]"
                      : "relative inline-flex flex-col items-center gap-1 text-center text-[13px] leading-[17px] font-medium text-[#606e87] after:h-[2px] after:w-px after:rounded-full after:bg-transparent after:content-[''] md:gap-[5px] md:text-[14px] md:leading-[18px]"
                  }
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="col-start-2 row-start-1 flex h-9 w-[124px] items-center justify-end gap-2 self-center justify-self-end md:h-10 md:w-[240px] md:gap-2.5">
          <button
            aria-label="GitHub"
            className="flex size-9 shrink-0 cursor-not-allowed items-center justify-center rounded-xl border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.62)] text-[#606e87] shadow-[0_8px_18px_rgba(95,123,185,0.08)] disabled:opacity-100 md:size-10"
            disabled
            type="button"
          >
            <GithubMark />
          </button>
          <ShellAuthAction />
        </div>
      </header>
      <div className="min-h-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
