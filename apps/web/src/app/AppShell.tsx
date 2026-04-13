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
      className="flex h-screen flex-col bg-[radial-gradient(circle_at_center,_#f2faff_0%,_#fbfcff_55%,_#f6f7fb_100%)]"
      data-testid="app-shell"
    >
      <header className="flex h-16 items-center justify-between bg-[rgba(255,255,255,0.72)] px-4 py-[10px] shadow-[0_4px_18px_rgba(51,61,87,0.04)]">
        <div className="flex h-12 w-[184px] items-center gap-[14px]">
          <div
            aria-hidden="true"
            className="size-12 rounded-2xl border border-[rgba(255,255,255,0.4)] bg-[linear-gradient(50.71deg,#45e3ff_14.286%,#3d78ff_85.714%)] shadow-[0_8px_18px_rgba(46,107,255,0.24)]"
          />
          <span className="whitespace-nowrap text-[15px] leading-[18.75px] font-medium tracking-[-0.2px] text-[#121729]">
            Knowledge Graph
          </span>
        </div>
        <nav
          aria-label="Primary"
          className="grid h-[30px] w-[324px] grid-cols-3 gap-x-3"
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
                      ? "relative inline-flex flex-col items-center gap-1 text-center text-[15px] leading-6 font-medium text-[rgba(38,48,71,0.98)] after:h-[2px] after:w-full after:rounded-full after:bg-[#5087ff] after:content-['']"
                      : "relative inline-flex flex-col items-center gap-1 text-center text-[15px] leading-6 font-normal text-[rgba(38,48,71,0.58)] after:h-[2px] after:w-full after:rounded-full after:bg-transparent after:content-['']"
                  }
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="flex h-10 w-[196px] items-center gap-3">
          <button
            className="inline-flex h-10 w-[92px] cursor-not-allowed items-center justify-center rounded-[10px] border border-[rgba(38,48,69,0.84)] bg-[rgba(20,28,46,0.96)] px-4 text-[14px] leading-[15.6px] font-medium text-[rgba(250,252,255,0.96)] disabled:opacity-100"
            disabled
            type="button"
          >
            GitHub
          </button>
          <button
            className="inline-flex h-10 w-[92px] cursor-not-allowed items-center justify-center rounded-[10px] border border-[rgba(38,48,69,0.84)] bg-[rgba(20,28,46,0.96)] px-4 text-[14px] leading-[15.6px] font-medium text-[rgba(250,252,255,0.96)] disabled:opacity-100"
            disabled
            type="button"
          >
            Login
          </button>
        </div>
      </header>
      <div className="min-h-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
