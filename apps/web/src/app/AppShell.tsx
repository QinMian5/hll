// abstract: Shared routed app shell with brand, top navigation, and route body outlet.
// out_of_scope: Feature-specific page content and backend data orchestration.

import { Link, Outlet, useRouterState } from "@tanstack/react-router";

const navItems = [
  { label: "Overview", to: "/overview" as const },
  { label: "Graph View", to: "/graph" as const },
  { label: "Search", to: "/search" as const },
];

export function AppShell() {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });

  return (
    <div
      className="flex h-screen flex-col overflow-hidden bg-white"
      data-testid="app-shell"
    >
      <header className="flex h-16 items-center justify-between border-b border-[rgba(15,23,42,0.08)] px-4">
        <div className="flex items-center gap-[14px]">
          <div
            aria-hidden="true"
            className="h-12 w-12 rounded-[10px] bg-[#30CBFF]"
          />
          <span className="text-[14px] leading-[19px] font-normal text-[#111827]">
            Knowledge Graph
          </span>
        </div>
        <nav
          aria-label="Primary"
          className="grid h-[30px] w-[324px] grid-cols-3 gap-3"
          data-testid="app-shell-nav"
        >
          {navItems.map((item) => {
            const isActive = pathname === item.to;

            return (
              <Link
                className="grid h-[30px] w-full place-items-center no-underline"
                data-nav-state={isActive ? "active" : "inactive"}
                key={item.to}
                to={item.to}
              >
                <span
                  className={
                    isActive
                      ? "relative inline-flex h-6 items-start text-center text-[12px] leading-6 font-normal text-[rgba(17,24,39,0.96)] after:absolute after:bottom-[-6px] after:left-1/2 after:h-[2px] after:w-full after:-translate-x-1/2 after:rounded-full after:bg-[#5087FF] after:content-['']"
                      : "relative inline-flex h-6 items-start text-center text-[12px] leading-6 font-normal text-[rgba(100,116,139,0.82)]"
                  }
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3">
          <button
            className="inline-flex h-10 min-w-[92px] cursor-not-allowed items-center justify-center rounded-lg bg-[#171717] px-6 text-[12px] leading-4 font-medium text-[#FAFAFA] disabled:opacity-100"
            disabled
            type="button"
          >
            GitHub
          </button>
          <button
            className="inline-flex h-10 min-w-[92px] cursor-not-allowed items-center justify-center rounded-lg bg-[#171717] px-6 text-[12px] leading-4 font-medium text-[#FAFAFA] disabled:opacity-100"
            disabled
            type="button"
          >
            Login
          </button>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
