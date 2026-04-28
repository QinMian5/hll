// abstract: Shared routed app shell with sidebar, mobile drawer, and route body outlet.
// out_of_scope: Feature-specific page content and backend data orchestration.

import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { House, LayoutDashboard, Menu, Network, Search, X } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { useEffect, useState } from "react";

import {
  fetchWebSession,
  type WebSessionResponse,
} from "../shared/web-api/session";

interface NavItem {
  readonly icon: ComponentType<SVGProps<SVGSVGElement>>;
  readonly label: string;
  readonly to: "/overview" | "/graph" | "/search";
}

const navItems: readonly NavItem[] = [
  { icon: House, label: "Overview", to: "/overview" },
  { icon: Network, label: "Graph View", to: "/graph" },
  { icon: Search, label: "Search", to: "/search" },
];

const placeholderNavItems = [
  { icon: LayoutDashboard, label: "Dashboard" },
] as const;

const actionButtonClasses =
  "inline-flex h-10 w-full items-center justify-center rounded-lg bg-[#006bff] px-3 text-[13px] leading-[18px] font-medium text-white transition-colors hover:bg-[#005fe0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]";

function GithubMark() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 24 24">
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

function BrandMark() {
  return (
    <div
      aria-hidden="true"
      className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[#006bff] text-[16px] leading-5 font-black text-white"
    >
      K
    </div>
  );
}

function BrandRow({ withClose }: { readonly withClose?: () => void }) {
  return (
    <div className="flex h-[52px] w-full items-center gap-3 bg-white p-2">
      <BrandMark />
      <span className="min-w-0 flex-1 truncate text-[14px] leading-5 font-black text-[#131c2d]">
        Knowledge Graph
      </span>
      {withClose ? (
        <button
          aria-label="Close navigation"
          className="flex size-8 shrink-0 items-center justify-center rounded-lg text-[#475569] hover:bg-[#eff6ff] hover:text-[#0f172a] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
          onClick={withClose}
          type="button"
        >
          <X aria-hidden="true" className="size-[18px]" strokeWidth={2} />
        </button>
      ) : null}
    </div>
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
      <div className="flex w-full min-w-0 flex-col gap-2">
        <span className="truncate text-center text-[13px] leading-5 font-medium text-[#475569]">
          {displayName}
        </span>
        <form action="/web-api/auth/sign-out" method="post">
          <button className={actionButtonClasses} type="submit">
            Sign out
          </button>
        </form>
      </div>
    );
  }

  return (
    <form action="/web-api/auth/sign-in" method="post">
      <button className={actionButtonClasses} type="submit">
        Sign in
      </button>
    </form>
  );
}

function GithubButton() {
  return (
    <button
      aria-label="GitHub 0 stars"
      className="flex h-10 w-full shrink-0 cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-[#e0e4eb] bg-[rgba(255,255,255,0.72)] px-3 text-[13px] leading-[18px] font-medium text-[#131c2d] disabled:opacity-100"
      disabled
      type="button"
    >
      <GithubMark />
      <span>0 stars</span>
    </button>
  );
}

function NavigationItems({
  onNavigate,
  pathname,
}: {
  readonly onNavigate?: () => void;
  readonly pathname: string;
}) {
  return (
    <div className="flex w-full flex-1 flex-col gap-2">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.to;

        return (
          <Link
            className={
              isActive
                ? "flex h-10 w-full items-center gap-3 rounded-lg bg-[#eff6ff] px-3 text-[14px] leading-5 font-medium text-[#0f172a] no-underline"
                : "flex h-10 w-full items-center gap-3 rounded-lg px-3 text-[14px] leading-5 font-medium text-[#475569] no-underline hover:bg-[#f1f5f9] hover:text-[#0f172a]"
            }
            data-nav-state={isActive ? "active" : "inactive"}
            key={item.to}
            onClick={onNavigate}
            to={item.to}
          >
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate">{item.label}</span>
          </Link>
        );
      })}
      {placeholderNavItems.map((item) => {
        const Icon = item.icon;

        return (
          <button
            className="flex h-10 w-full cursor-not-allowed items-center gap-3 rounded-lg px-3 text-left text-[14px] leading-5 font-medium text-[#475569] disabled:opacity-100"
            disabled
            key={item.label}
            type="button"
          >
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function SidebarContent({
  onClose,
  pathname,
  surface = "sidebar",
}: {
  readonly onClose?: () => void;
  readonly pathname: string;
  readonly surface?: "drawer" | "sidebar";
}) {
  const surfaceClass =
    surface === "drawer" ? "bg-white" : "bg-[rgba(255,255,255,0.72)]";

  return (
    <div
      className={`flex h-full w-full flex-col gap-2 overflow-hidden border-[#e0e4eb] p-2 ${surfaceClass}`}
    >
      <BrandRow withClose={onClose} />
      <NavigationItems onNavigate={onClose} pathname={pathname} />
      <div className="flex h-24 w-full shrink-0 flex-col gap-2 pt-2">
        <GithubButton />
        <ShellAuthAction />
      </div>
    </div>
  );
}

export function AppShell() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });

  function closeDrawer() {
    setIsDrawerOpen(false);
  }

  return (
    <div
      className="flex h-screen min-h-screen w-full bg-[#f8fafc] font-['Geist',sans-serif]"
      data-testid="app-shell"
    >
      <aside
        className="hidden h-screen shrink-0 border-r border-[#e0e4eb] lg:flex lg:w-[320px]"
        data-testid="app-shell-sidebar"
      >
        <SidebarContent pathname={pathname} />
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header
          className="flex h-16 w-full shrink-0 items-center gap-3 border-b border-[#e0e4eb] bg-[rgba(255,255,255,0.72)] px-4 lg:hidden"
          data-testid="app-shell-mobile-header"
        >
          <button
            aria-label="Open navigation"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white text-[#0f172a] hover:bg-[#eff6ff] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
            onClick={() => {
              setIsDrawerOpen(true);
            }}
            type="button"
          >
            <Menu aria-hidden="true" className="size-[18px]" strokeWidth={2} />
          </button>
          <BrandMark />
          <span className="min-w-0 flex-1 truncate text-[14px] leading-5 font-black text-[#131c2d]">
            Knowledge Graph
          </span>
        </header>
        <div className="min-h-0 flex-1">
          <Outlet />
        </div>
      </div>
      {isDrawerOpen ? (
        <div
          className="fixed inset-0 z-50 flex bg-transparent lg:hidden"
          data-testid="app-shell-mobile-overlay"
        >
          <aside
            className="h-full w-[320px] shrink-0 bg-white"
            data-testid="app-shell-mobile-drawer"
          >
            <SidebarContent
              onClose={closeDrawer}
              pathname={pathname}
              surface="drawer"
            />
          </aside>
          <button
            aria-label="Close navigation scrim"
            className="min-w-0 flex-1 cursor-default bg-black/10"
            onClick={closeDrawer}
            type="button"
          />
        </div>
      ) : null}
    </div>
  );
}
