// abstract: Code-based router definition for the shared web app shell and top-level routes.
// out_of_scope: Feature-specific data fetching logic and deep page behavior.

import {
  createBrowserHistory,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  Outlet,
  useRouterState,
} from "@tanstack/react-router";
import type { ComponentType } from "react";

import { AppShell } from "./AppShell";
import { ProtectedRoute } from "./auth/AuthCoordinatorProvider";

function RootRedirect() {
  return <Outlet />;
}

const taxonomyViewRouteComponent = lazyRouteComponent(
  () => import("../features/taxonomy-view/page/TaxonomyViewPage"),
  "TaxonomyViewPage",
);

function protectedRouteComponent(Component: ComponentType) {
  return function ProtectedRouteComponent() {
    const returnTo = useRouterState({
      select: (state) => state.location.href,
    });

    return (
      <ProtectedRoute returnTo={returnTo}>
        <Component />
      </ProtectedRoute>
    );
  };
}

const rootRoute = createRootRoute({
  component: AppShell,
});

const indexRoute = createRoute({
  component: RootRedirect,
  getParentRoute: () => rootRoute,
  path: "/",
});

const overviewRoute = createRoute({
  component: lazyRouteComponent(
    () => import("../features/overview/pages"),
    "OverviewPage",
  ),
  getParentRoute: () => rootRoute,
  path: "overview",
});

const graphRoute = createRoute({
  component: taxonomyViewRouteComponent,
  getParentRoute: () => rootRoute,
  path: "graph",
});

const graphPathRoute = createRoute({
  component: taxonomyViewRouteComponent,
  getParentRoute: () => rootRoute,
  path: "graph/$",
});

const searchRoute = createRoute({
  component: lazyRouteComponent(
    () => import("../features/search/pages"),
    "SearchPage",
  ),
  getParentRoute: () => rootRoute,
  path: "search",
  validateSearch: (search: Record<string, unknown>) => ({
    q: typeof search.q === "string" ? search.q : undefined,
  }),
});

const docsRoute = createRoute({
  component: lazyRouteComponent(
    () => import("../features/docs/pages"),
    "DocsPage",
  ),
  getParentRoute: () => rootRoute,
  path: "docs",
});

const dashboardRoute = createRoute({
  component: protectedRouteComponent(
    lazyRouteComponent(
      () => import("../features/dashboard/pages"),
      "DashboardPage",
    ),
  ),
  getParentRoute: () => rootRoute,
  path: "dashboard",
});

const workspaceRoute = createRoute({
  component: protectedRouteComponent(
    lazyRouteComponent(
      () => import("../features/workspace/pages"),
      "WorkspacePage",
    ),
  ),
  getParentRoute: () => rootRoute,
  path: "workspace",
});

const settingsRoute = createRoute({
  component: protectedRouteComponent(
    lazyRouteComponent(
      () => import("../features/settings/pages"),
      "SettingsPage",
    ),
  ),
  getParentRoute: () => rootRoute,
  path: "settings",
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  overviewRoute,
  graphRoute,
  graphPathRoute,
  searchRoute,
  docsRoute,
  dashboardRoute,
  workspaceRoute,
  settingsRoute,
]);

export interface CreateAppRouterOptions {
  readonly initialEntries?: readonly string[];
}

export function createAppRouter(options?: CreateAppRouterOptions) {
  const history = options?.initialEntries
    ? createMemoryHistory({
        initialEntries: [...options.initialEntries],
      })
    : createBrowserHistory();

  const router = createRouter({
    history,
    routeTree,
  });

  if (history.location.pathname === "/") {
    void router.navigate({
      replace: true,
      to: "/overview",
    });
  }

  return router;
}

export type AppRouter = ReturnType<typeof createAppRouter>;

declare module "@tanstack/react-router" {
  interface Register {
    router: AppRouter;
  }
}
