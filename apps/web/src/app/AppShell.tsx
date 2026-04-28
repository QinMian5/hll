// abstract: Shared routed app shell with Figma-aligned sidebar, mobile drawer, and account menu.
// out_of_scope: Feature-specific page content and backend data orchestration.

import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import {
  ChevronRight,
  House,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  Search as SearchIcon,
  Settings,
  X,
} from "lucide-react";
import type { ComponentType, Ref, SVGProps } from "react";
import { useEffect, useRef, useState } from "react";

import { cn } from "../shared/utils";
import type { WebSessionResponse } from "../shared/web-api/session";
import { useWebSessionQuery } from "../shared/web-api/sessionQueries";

type AppRoute = "/overview" | "/graph" | "/search";

interface NavItem {
  readonly icon: ComponentType<SVGProps<SVGSVGElement>>;
  readonly label: string;
  readonly to: AppRoute;
}

interface UserProfile {
  readonly email: string;
  readonly initial: string;
  readonly name: string;
}

const navItems: readonly NavItem[] = [
  { icon: House, label: "Overview", to: "/overview" },
  { icon: Network, label: "Graph View", to: "/graph" },
  { icon: SearchIcon, label: "Search", to: "/search" },
];

const githubRepositoryUrl = "https://github.com/QinMian5/knowledge";

const actionButtonClasses =
  "inline-flex h-10 w-full items-center justify-center rounded-lg bg-[#006bff] px-3 text-[13px] leading-[18px] font-medium text-white transition-colors hover:bg-[#005fe0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]";

const menuItemClasses =
  "flex h-account-menu-item-height w-full items-center gap-account-menu-item-gap rounded-account-menu-item px-account-menu-item-x text-left text-account-menu-item font-normal text-account-menu-text no-underline transition-colors hover:bg-account-menu-item-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-account-menu-focus";

const menuIconClasses = "size-account-menu-icon-size shrink-0";

function GithubMark() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0"
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
    <div className="flex h-[52px] w-full shrink-0 items-center gap-3 overflow-hidden bg-white p-2">
      <BrandMark />
      <span className="min-w-0 flex-1 truncate text-[14px] leading-5 font-black text-[#131c2d]">
        Knowledge Graph
      </span>
      {withClose ? (
        <button
          aria-label="Close navigation"
          className="flex size-8 shrink-0 items-center justify-center bg-white text-[#131c2d] transition-colors hover:bg-[#eff6ff] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
          onClick={withClose}
          type="button"
        >
          <X aria-hidden="true" className="size-[18px]" strokeWidth={2} />
        </button>
      ) : null}
    </div>
  );
}

function profileFromSession(
  session: Extract<WebSessionResponse, { status: "authenticated" }>,
): UserProfile {
  const name = session.user.name ?? session.user.email ?? session.user.id;
  const email = session.user.email ?? session.user.id;
  const initial = name.trim().charAt(0).toUpperCase() || "U";

  return { email, initial, name };
}

function SignInAction() {
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
    <a
      aria-label="GitHub 0 stars"
      className="flex h-10 w-full shrink-0 items-center justify-center gap-2 overflow-hidden rounded-lg border border-[#e0e4eb] bg-[rgba(255,255,255,0.72)] px-3 text-[13px] leading-[18px] font-medium text-[#131c2d] no-underline transition-colors hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
      href={githubRepositoryUrl}
      rel="noreferrer"
      target="_blank"
    >
      <GithubMark />
      <span>0 stars</span>
    </a>
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
    <div className="flex w-full flex-1 flex-col gap-2 overflow-hidden">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.to;

        return (
          <Link
            className={cn(
              "flex h-10 w-full items-center gap-3 overflow-hidden rounded-lg px-3 text-[14px] leading-5 no-underline transition-colors",
              isActive
                ? "bg-[#eff6ff] font-medium text-[#131c2d]"
                : "font-medium text-[#606e87] hover:bg-[#f1f5f9] hover:text-[#131c2d]",
            )}
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
    </div>
  );
}

function AccountMenu({
  menuRef,
  onNavigate,
}: {
  readonly menuRef: Ref<HTMLDivElement>;
  readonly onNavigate?: () => void;
}) {
  return (
    <div
      className="absolute -top-account-menu-offset-y left-0 z-20 flex h-account-menu-height w-full flex-col rounded-account-menu border border-account-menu-border bg-account-menu-surface p-1 drop-shadow-[var(--drop-shadow-account-menu)]"
      ref={menuRef}
      role="menu"
    >
      <Link
        className={menuItemClasses}
        onClick={onNavigate}
        role="menuitem"
        to="/dashboard"
      >
        <LayoutDashboard aria-hidden="true" className={menuIconClasses} />
        <span>Dashboard</span>
      </Link>
      <Link
        className={menuItemClasses}
        onClick={onNavigate}
        role="menuitem"
        to="/settings"
      >
        <Settings aria-hidden="true" className={menuIconClasses} />
        <span>Settings</span>
      </Link>
      <form action="/web-api/auth/sign-out" className="w-full" method="post">
        <button className={menuItemClasses} role="menuitem" type="submit">
          <LogOut aria-hidden="true" className={menuIconClasses} />
          <span>Sign out</span>
        </button>
      </form>
    </div>
  );
}

function UserAccountAction({
  buttonRef,
  isMenuOpen,
  onToggleMenu,
  profile,
}: {
  readonly buttonRef: Ref<HTMLButtonElement>;
  readonly isMenuOpen: boolean;
  readonly onToggleMenu: () => void;
  readonly profile: UserProfile;
}) {
  return (
    <button
      aria-expanded={isMenuOpen}
      aria-label={`User menu, ${profile.name}`}
      className={cn(
        "flex h-12 w-full shrink-0 items-center justify-center gap-2 overflow-hidden rounded-lg border border-[#e0e4eb] pl-2 pr-2.5 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]",
        isMenuOpen
          ? "bg-[#eff6ff]"
          : "bg-[rgba(255,255,255,0.72)] hover:bg-white",
      )}
      onClick={onToggleMenu}
      ref={buttonRef}
      type="button"
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-2xl bg-[#006bff] text-[13px] leading-4 font-semibold text-white">
        {profile.initial}
      </span>
      <span className="flex min-w-0 flex-1 flex-col items-start overflow-hidden">
        <span className="w-full truncate text-[13px] leading-4 font-medium text-[#131c2d]">
          {profile.name}
        </span>
        <span className="w-full truncate text-[11px] leading-[14px] font-normal text-[#606e87]">
          {profile.email}
        </span>
      </span>
      <ChevronRight
        aria-hidden="true"
        className="size-4 shrink-0 -rotate-90 text-[#606e87]"
        strokeWidth={2}
      />
    </button>
  );
}

function SidebarContent({
  onClose,
  pathname,
  session,
}: {
  readonly onClose?: () => void;
  readonly pathname: string;
  readonly session: WebSessionResponse;
}) {
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
  const accountButtonRef = useRef<HTMLButtonElement>(null);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const profile =
    session.status === "authenticated" ? profileFromSession(session) : null;

  useEffect(() => {
    if (!isAccountMenuOpen) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;

      if (!(target instanceof Node)) {
        return;
      }

      if (accountButtonRef.current?.contains(target)) {
        return;
      }

      if (accountMenuRef.current?.contains(target)) {
        return;
      }

      setIsAccountMenuOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [isAccountMenuOpen]);

  function handleNavigate() {
    setIsAccountMenuOpen(false);
    onClose?.();
  }

  return (
    <div className="relative flex h-full w-full flex-col gap-2 overflow-hidden bg-[rgba(255,255,255,0.72)] p-2">
      <BrandRow withClose={onClose} />
      <NavigationItems onNavigate={handleNavigate} pathname={pathname} />
      <div className="relative flex h-[104px] w-full shrink-0 flex-col gap-2 pt-2">
        {profile && isAccountMenuOpen ? (
          <AccountMenu menuRef={accountMenuRef} onNavigate={handleNavigate} />
        ) : null}
        <GithubButton />
        {profile ? (
          <UserAccountAction
            buttonRef={accountButtonRef}
            isMenuOpen={isAccountMenuOpen}
            onToggleMenu={() => {
              setIsAccountMenuOpen((current) => !current);
            }}
            profile={profile}
          />
        ) : (
          <SignInAction />
        )}
      </div>
    </div>
  );
}

export function AppShell() {
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const session = useWebSessionQuery().data ?? { status: "anonymous" };
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });

  function closeDrawer() {
    setIsDrawerOpen(false);
  }

  return (
    <div
      className="flex h-screen min-h-screen w-full overflow-hidden bg-[#f8fafc] font-['Geist',sans-serif]"
      data-testid="app-shell"
    >
      <aside
        className="hidden h-screen shrink-0 border-r border-[#e0e4eb] lg:flex lg:w-[320px]"
        data-testid="app-shell-sidebar"
      >
        <SidebarContent pathname={pathname} session={session} />
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <header
          className="flex h-16 w-full shrink-0 items-center gap-3 overflow-hidden border-b border-[#e0e4eb] bg-[rgba(255,255,255,0.72)] px-4 lg:hidden"
          data-testid="app-shell-mobile-header"
        >
          <button
            aria-label="Open navigation"
            className="flex size-9 shrink-0 items-center justify-center bg-white text-[#131c2d] transition-colors hover:bg-[#eff6ff] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
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
        <div className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </div>
      </div>
      {isDrawerOpen ? (
        <div
          className="fixed inset-0 z-50 flex bg-transparent lg:hidden"
          data-testid="app-shell-mobile-overlay"
        >
          <aside
            className="h-full w-[320px] shrink-0 border-r border-[#e0e4eb] bg-[rgba(255,255,255,0.72)]"
            data-testid="app-shell-mobile-drawer"
          >
            <SidebarContent
              onClose={closeDrawer}
              pathname={pathname}
              session={session}
            />
          </aside>
          <button
            aria-label="Close navigation scrim"
            className="min-w-0 flex-1 cursor-default bg-[rgba(248,250,252,0.18)]"
            onClick={closeDrawer}
            type="button"
          />
        </div>
      ) : null}
    </div>
  );
}
