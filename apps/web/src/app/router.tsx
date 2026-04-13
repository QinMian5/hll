// abstract: Code-based router definition for the shared web app shell and top-level routes.
// out_of_scope: Feature-specific data fetching logic and deep page behavior.

import {
  createBrowserHistory,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";

import { OverviewPage } from "../features/overview/pages";
import { SearchPage } from "../features/search/pages";
import { TaxonomyViewPage } from "../features/taxonomy-view/page/TaxonomyViewPage";
import { AppShell } from "./AppShell";

function RootRedirect() {
  return <Outlet />;
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
  component: OverviewPage,
  getParentRoute: () => rootRoute,
  path: "overview",
});

const graphRoute = createRoute({
  component: TaxonomyViewPage,
  getParentRoute: () => rootRoute,
  path: "graph",
});

const searchRoute = createRoute({
  component: SearchPage,
  getParentRoute: () => rootRoute,
  path: "search",
  validateSearch: (search: Record<string, unknown>) => ({
    q: typeof search.q === "string" ? search.q : undefined,
  }),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  overviewRoute,
  graphRoute,
  searchRoute,
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
