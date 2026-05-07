// abstract: Taxonomy-query-driven page shell that routes branch rendering to React Flow and leaf rendering to deck.gl.
// out_of_scope: Backend taxonomy read orchestration and deck.gl scene internals.

import "@xyflow/react/dist/style.css";

import { useNavigate, useRouterState } from "@tanstack/react-router";
import { type Node, ReactFlow } from "@xyflow/react";
import { ChevronRight } from "lucide-react";
import {
  lazy,
  Suspense,
  startTransition,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import type { SearchResultCardEditPayload } from "../../search/components/SearchResultCard";
import { SignInRequiredDialog } from "../../search/components/SignInRequiredDialog";
import { SuggestEditDialog } from "../../search/components/SuggestEditDialog";
import { useCreateSuggestedEditMutation } from "../../search/data/searchQueries";
import { suggestedEditErrorMessage } from "../../search/suggestedEditErrors";
import {
  type TaxonomyNodeView,
  type TaxonomyRootView,
  useTaxonomyNodeViewByPathQuery,
  useTaxonomyRootViewQuery,
} from "../data/taxonomyViewQueries";

export {
  LEAF_HYDRATION_OVERSCAN,
  LEAF_POINT_TITLE_ACTIVATION_ZOOM,
} from "./leaf/leafRendererConfig";

import {
  BRANCH_DESKTOP_REFERENCE_VIEWPORT,
  buildBranchLayout,
} from "./layout/buildBranchLayout";
import type {
  BranchInitialViewport,
  LayoutViewport,
  TaxonomyLayoutNodeData,
} from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

const DEFAULT_CANVAS_VIEWPORT = BRANCH_DESKTOP_REFERENCE_VIEWPORT;
const DEFAULT_BRANCH_VIEWPORT = { x: 0, y: 0, zoom: 1 } as const;
const breadcrumbMutedClasses =
  "text-knowledge-taxonomy-breadcrumb font-normal text-knowledge-taxonomy-breadcrumb-muted transition-colors hover:text-knowledge-taxonomy-breadcrumb-hover focus-visible:outline-0";
const breadcrumbCurrentClasses =
  "text-knowledge-taxonomy-breadcrumb font-medium text-knowledge-taxonomy-breadcrumb-active transition-colors hover:text-knowledge-taxonomy-breadcrumb-hover focus-visible:outline-0";
const errorActionClasses =
  "mt-4 inline-flex h-10 items-center justify-center rounded-lg bg-knowledge-brand px-4 text-knowledge-shell-action font-medium text-knowledge-text-inverse transition-colors hover:bg-knowledge-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

interface BranchFlowGraph {
  readonly initialViewport: BranchInitialViewport;
  readonly layoutIdentity: string;
  readonly nodes: BubbleFlowNode[];
}

const nodeTypes = {
  bubble: TaxonomyFlowNode,
};

const LeafRenderer = lazy(() =>
  import("./leaf/LeafRenderer").then((module) => ({
    default: module.LeafRenderer,
  })),
);

const graphRoutePrefix = "/graph/";

function routePathFromGraphPathname(pathname: string) {
  if (pathname === "/graph") {
    return "";
  }

  if (!pathname.startsWith(graphRoutePrefix)) {
    return "";
  }

  return pathname.slice(graphRoutePrefix.length);
}

function toFlowNode(
  node: ReturnType<typeof buildBranchLayout>["nodes"][number],
): BubbleFlowNode {
  return {
    ariaLabel: node.data.tooltip || node.data.label,
    data: node.data,
    draggable: false,
    id: node.id,
    position: node.position,
    selectable: false,
    style: node.style,
    type: node.type,
  };
}

function measuredViewportFromElement(element: HTMLElement | null) {
  if (!element) {
    return DEFAULT_CANVAS_VIEWPORT;
  }

  const rect = element.getBoundingClientRect();

  if (rect.width <= 0 || rect.height <= 0) {
    return DEFAULT_CANVAS_VIEWPORT;
  }

  return {
    height: Math.round(rect.height),
    width: Math.round(rect.width),
  };
}

type TaxonomyViewBranch = Extract<
  TaxonomyNodeView,
  { readonly node_kind: "branch" }
>;
type TaxonomyViewChild = TaxonomyViewBranch["children"][number];
type TaxonomyViewScope = TaxonomyViewBranch["breadcrumb"][number];
type VisibleTaxonomyView = TaxonomyRootView | TaxonomyNodeView;
interface SettledTaxonomyView {
  readonly data: VisibleTaxonomyView;
  readonly dataIdentity: string;
  readonly routePath: string;
}

interface RouteTransitionTarget {
  readonly label: string;
  readonly routePath: string;
}

function taxonomyScopeKey(scope: TaxonomyViewScope) {
  return `${scope.scope_kind}:${scope.taxonomy_node_id ?? scope.route_path}`;
}

function taxonomyChildLayoutId(child: TaxonomyViewChild) {
  return `${child.scope_kind}:${child.taxonomy_node_id ?? child.route_path}`;
}

function isTaxonomyNodeView(
  view: VisibleTaxonomyView | undefined,
): view is TaxonomyNodeView {
  return view !== undefined && "node_kind" in view;
}

function isTaxonomyBranchView(
  view: VisibleTaxonomyView | undefined,
): view is TaxonomyRootView | TaxonomyViewBranch {
  return (
    view !== undefined &&
    (!isTaxonomyNodeView(view) || view.node_kind === "branch")
  );
}

function taxonomyViewDataIdentity(view: VisibleTaxonomyView) {
  if (!isTaxonomyNodeView(view)) {
    return `root:${view.children.map(taxonomyChildLayoutId).join("|")}`;
  }

  const currentScopeKey = taxonomyScopeKey(view.current_scope);

  if (view.node_kind === "branch") {
    return `branch:${currentScopeKey}:${view.children
      .map(taxonomyChildLayoutId)
      .join("|")}`;
  }

  return [
    "card_scope",
    currentScopeKey,
    view.layout_version,
    view.generated_at,
    view.layout_status,
    view.node_count,
    view.edge_count,
  ].join(":");
}

function toBranchLayoutChildren(children: readonly TaxonomyViewChild[]) {
  return children.map((child) => ({
    ...child,
    id: taxonomyChildLayoutId(child),
    taxonomy_node_id: child.taxonomy_node_id ?? null,
  }));
}

function sameViewport(left: LayoutViewport, right: LayoutViewport) {
  return left.height === right.height && left.width === right.width;
}

function emptyBranchFlowGraph(layoutIdentity: string): BranchFlowGraph {
  return {
    initialViewport: DEFAULT_BRANCH_VIEWPORT,
    layoutIdentity,
    nodes: [],
  };
}

function branchLayoutIdentity(
  branchLayout: ReturnType<typeof buildBranchLayout>,
) {
  const roundedBounds = [
    Math.round(branchLayout.bounds.minX),
    Math.round(branchLayout.bounds.minY),
    Math.round(branchLayout.bounds.maxX),
    Math.round(branchLayout.bounds.maxY),
  ].join(":");

  return `ready:${roundedBounds}:${branchLayout.nodes
    .map((node) => node.id)
    .join("|")}`;
}

function isTaxonomyRoutePathNotFound(error: Error | null): boolean {
  return (
    error instanceof WebApiRequestError &&
    error.status === 404 &&
    error.code === "taxonomy_route_path_not_found"
  );
}

function isQuotaExceeded(error: Error | null): boolean {
  return (
    error instanceof WebApiRequestError &&
    error.status === 429 &&
    error.code === "quota_exceeded"
  );
}

function isLayoutNotReady(error: Error | null): error is WebApiRequestError {
  return (
    error instanceof WebApiRequestError &&
    error.status === 503 &&
    error.code === "layout_not_ready"
  );
}

export function TaxonomyViewPage() {
  const navigate = useNavigate();
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const activeRoutePath = routePathFromGraphPathname(pathname);
  const rootMode = activeRoutePath === "";
  const session = useWebSession();
  const createSuggestedEditMutation = useCreateSuggestedEditMutation();
  const canvasRef = useRef<HTMLElement | null>(null);
  const [canvasViewport, setCanvasViewport] = useState<LayoutViewport>(
    DEFAULT_CANVAS_VIEWPORT,
  );
  const [editingCard, setEditingCard] =
    useState<SearchResultCardEditPayload | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | undefined>();
  const [isSignInDialogOpen, setIsSignInDialogOpen] = useState(false);
  const [lastSettledView, setLastSettledView] =
    useState<SettledTaxonomyView | null>(null);
  const [routeTransitionTarget, setRouteTransitionTarget] =
    useState<RouteTransitionTarget | null>(null);

  const rootQuery = useTaxonomyRootViewQuery({
    enabled: rootMode,
  });
  const pathQuery = useTaxonomyNodeViewByPathQuery(activeRoutePath, {
    enabled: !rootMode,
  });

  const activeQuery = rootMode ? rootQuery : pathQuery;
  const activeData = rootMode ? rootQuery.data : pathQuery.data;
  const visibleTaxonomyView =
    activeQuery.isPending && !activeData ? lastSettledView?.data : activeData;
  const breadcrumbs = visibleTaxonomyView?.breadcrumb ?? [];
  const displayBreadcrumbs =
    breadcrumbs[0]?.parent_taxonomy_node_id === null &&
    breadcrumbs[0].name === "Root"
      ? breadcrumbs.slice(1)
      : breadcrumbs;
  const rootBreadcrumbIsCurrent = rootMode && displayBreadcrumbs.length === 0;
  const currentBreadcrumbKey =
    displayBreadcrumbs.length > 0
      ? taxonomyScopeKey(displayBreadcrumbs[displayBreadcrumbs.length - 1])
      : undefined;
  const activeTransitionTarget =
    routeTransitionTarget?.routePath === activeRoutePath
      ? routeTransitionTarget
      : null;
  const loadingTitle = activeTransitionTarget
    ? `Opening ${activeTransitionTarget.label}`
    : "Loading taxonomy view";
  const loadingDescription = activeTransitionTarget
    ? "Keeping your current taxonomy layer visible while the next view loads."
    : "Fetching the latest taxonomy hierarchy snapshot from API.";
  const layoutCenter = useMemo(
    () => ({
      x: canvasViewport.width / 2,
      y: canvasViewport.height / 2,
    }),
    [canvasViewport],
  );

  useLayoutEffect(() => {
    const updateViewport = () => {
      const nextViewport = measuredViewportFromElement(canvasRef.current);

      setCanvasViewport((currentViewport) =>
        sameViewport(currentViewport, nextViewport)
          ? currentViewport
          : nextViewport,
      );
    };

    updateViewport();

    if (!canvasRef.current || !globalThis.ResizeObserver) {
      return;
    }

    const observer = new ResizeObserver(updateViewport);
    observer.observe(canvasRef.current);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (activeQuery.isPending || activeQuery.isError || !activeData) {
      return;
    }

    const dataIdentity = taxonomyViewDataIdentity(activeData);
    setLastSettledView((currentView) =>
      currentView?.routePath === activeRoutePath &&
      currentView.dataIdentity === dataIdentity
        ? currentView
        : { data: activeData, dataIdentity, routePath: activeRoutePath },
    );
    setRouteTransitionTarget((currentTarget) =>
      currentTarget?.routePath === activeRoutePath ? null : currentTarget,
    );
  }, [activeQuery.isError, activeQuery.isPending, activeRoutePath, activeData]);

  function handleSuggestEdit(card: SearchResultCardEditPayload) {
    if (session.status === "loading") {
      return;
    }

    if (session.status !== "authenticated") {
      setIsSignInDialogOpen(true);
      return;
    }

    setEditingCard(card);
    setSuggestionError(undefined);
  }

  function navigateToGraphPath(routePath: string, label: string) {
    setRouteTransitionTarget({ label, routePath });
    startTransition(() => {
      if (routePath === "") {
        void navigate({ to: "/graph" });
        return;
      }

      void navigate({
        params: { _splat: routePath },
        to: "/graph/$",
      });
    });
  }

  async function handleSubmitSuggestion(payload: {
    readonly reason: string;
    readonly suggestedContent: string;
    readonly suggestedTitle: string;
  }) {
    if (editingCard === null) {
      return;
    }

    try {
      await createSuggestedEditMutation.mutateAsync({
        baseVersion: editingCard.currentVersion,
        nodeId: editingCard.nodeId,
        reason: payload.reason,
        suggestedContent: payload.suggestedContent,
        suggestedTitle: payload.suggestedTitle,
      });
      setEditingCard(null);
      setSuggestionError(undefined);
    } catch (error) {
      setSuggestionError(suggestedEditErrorMessage(error));
    }
  }

  const branchFlowGraph = useMemo(() => {
    if (activeQuery.isError) {
      return emptyBranchFlowGraph("error");
    }

    if (!isTaxonomyBranchView(visibleTaxonomyView)) {
      return emptyBranchFlowGraph("no-data");
    }

    const branchLayout = buildBranchLayout({
      center: layoutCenter,
      children: toBranchLayoutChildren(visibleTaxonomyView.children),
      viewport: canvasViewport,
    });

    return {
      initialViewport: branchLayout.initialViewport,
      layoutIdentity: branchLayoutIdentity(branchLayout),
      nodes: branchLayout.nodes.map(toFlowNode),
    };
  }, [activeQuery.isError, canvasViewport, layoutCenter, visibleTaxonomyView]);
  const routePathNotFound =
    activeQuery.isError && isTaxonomyRoutePathNotFound(activeQuery.error);
  const quotaExceeded =
    activeQuery.isError && isQuotaExceeded(activeQuery.error);
  const layoutNotReadyError =
    activeQuery.isError && isLayoutNotReady(activeQuery.error)
      ? activeQuery.error
      : null;
  const layoutNotReady = layoutNotReadyError !== null;
  const layoutRetryAfterSeconds = layoutNotReadyError?.retryAfterSeconds;

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-knowledge-page-bg"
      data-testid="taxonomy-shell-body"
    >
      <section
        aria-label="taxonomy canvas"
        className="relative min-h-0 flex-1 overflow-hidden bg-knowledge-page-bg"
        data-figma-desktop-node="702:3845"
        data-figma-mobile-node="702:3950"
        data-testid="taxonomy-canvas"
        ref={canvasRef}
      >
        <nav
          aria-label="taxonomy breadcrumb"
          className="absolute top-5 left-5 z-20 flex max-w-[calc(100%-var(--spacing-knowledge-taxonomy-edge-inset))] flex-wrap items-center gap-1.5 lg:top-6 lg:left-6 lg:max-w-[calc(100%-var(--spacing-knowledge-taxonomy-edge-inset-desktop))]"
          data-breadcrumb-style="inline-text"
          data-testid="taxonomy-breadcrumb-overlay"
        >
          <button
            aria-current={rootBreadcrumbIsCurrent ? "page" : undefined}
            className={
              rootBreadcrumbIsCurrent
                ? breadcrumbCurrentClasses
                : breadcrumbMutedClasses
            }
            onClick={() => navigateToGraphPath("", "Root")}
            type="button"
          >
            Root
          </button>
          {displayBreadcrumbs.flatMap((item) => [
            <ChevronRight
              aria-hidden="true"
              className="size-3.5 shrink-0 text-knowledge-text-subtle"
              data-testid="taxonomy-breadcrumb-separator"
              key={`${taxonomyScopeKey(item)}-separator`}
            />,
            <button
              aria-current={
                taxonomyScopeKey(item) === currentBreadcrumbKey
                  ? "page"
                  : undefined
              }
              className={
                taxonomyScopeKey(item) === currentBreadcrumbKey
                  ? breadcrumbCurrentClasses
                  : breadcrumbMutedClasses
              }
              key={taxonomyScopeKey(item)}
              onClick={() => navigateToGraphPath(item.route_path, item.name)}
              type="button"
            >
              {item.name}
            </button>,
          ])}
        </nav>
        {activeQuery.isPending && lastSettledView ? (
          <div
            aria-hidden="true"
            className="absolute inset-0 z-20 bg-knowledge-page-bg/62 backdrop-blur-[2px] backdrop-saturate-50"
            data-testid="taxonomy-transition-scrim"
          />
        ) : null}
        {activeQuery.isPending ? (
          <section
            aria-busy="true"
            aria-live="polite"
            className="absolute top-1/2 left-1/2 z-30 flex w-[min(var(--spacing-knowledge-taxonomy-toast-width),calc(100%-var(--spacing-knowledge-taxonomy-edge-inset)))] -translate-x-1/2 -translate-y-1/2 items-start gap-3 rounded-xl border border-knowledge-overlay-toast-border bg-knowledge-surface-card-glass px-4 py-4 text-left shadow-knowledge-overlay-toast backdrop-blur-md"
            data-testid="taxonomy-loading-overlay"
          >
            <span
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0 rounded-full border-2 border-knowledge-spinner-soft border-t-knowledge-spinner motion-safe:animate-spin motion-reduce:border-knowledge-spinner-muted"
            />
            <span>
              <h2 className="m-0 text-knowledge-taxonomy-state-title font-medium text-knowledge-text-default">
                {loadingTitle}
              </h2>
              <p className="mt-1 mb-0 text-knowledge-taxonomy-state-body text-knowledge-text-muted">
                {loadingDescription}
              </p>
            </span>
          </section>
        ) : null}
        {activeQuery.isError ? (
          <section
            className="absolute top-1/2 left-1/2 z-20 w-[min(var(--spacing-knowledge-taxonomy-empty-width),calc(100%-var(--spacing-knowledge-taxonomy-edge-inset)))] -translate-x-1/2 -translate-y-1/2 rounded-knowledge-overlay border border-knowledge-overlay-panel-border bg-knowledge-surface-card-overlay p-6 text-left shadow-knowledge-overlay-panel"
            data-testid="taxonomy-error-overlay"
            role="alert"
          >
            <h2 className="m-0 text-knowledge-dialog-title font-semibold text-knowledge-text-default">
              {routePathNotFound
                ? "Graph path not found"
                : quotaExceeded
                  ? "Too many graph requests"
                  : layoutNotReady
                    ? "Taxonomy layout unavailable"
                    : "Taxonomy view unavailable"}
            </h2>
            <p className="mt-2 mb-0 text-knowledge-body text-knowledge-text-muted">
              {routePathNotFound
                ? "This taxonomy path does not exist."
                : quotaExceeded
                  ? "Try again shortly."
                  : layoutNotReady
                    ? layoutRetryAfterSeconds
                      ? `Try again in about ${layoutRetryAfterSeconds} seconds.`
                      : "Try again shortly."
                    : activeQuery.error.message}
            </p>
            {routePathNotFound ? (
              <button
                className={errorActionClasses}
                onClick={() => navigateToGraphPath("", "Root")}
                type="button"
              >
                Back to Root
              </button>
            ) : null}
            {layoutNotReady ? (
              <button
                className={errorActionClasses}
                onClick={() => {
                  void activeQuery.refetch();
                }}
                type="button"
              >
                Retry
              </button>
            ) : null}
          </section>
        ) : null}
        <div className="taxonomy-flow-shell absolute inset-0 overflow-hidden">
          {isTaxonomyNodeView(visibleTaxonomyView) &&
          visibleTaxonomyView.node_kind === "card_scope" ? (
            <Suspense fallback={null}>
              <LeafRenderer
                key={`${taxonomyScopeKey(visibleTaxonomyView.current_scope)}:${visibleTaxonomyView.layout_version}:${visibleTaxonomyView.generated_at}`}
                leafView={visibleTaxonomyView}
                onSuggestEdit={handleSuggestEdit}
                viewport={canvasViewport}
              />
            </Suspense>
          ) : (
            <div
              className="h-full w-full"
              data-testid="taxonomy-branch-reactflow"
            >
              <ReactFlow
                defaultViewport={branchFlowGraph.initialViewport}
                key={[
                  activeRoutePath || "root",
                  canvasViewport.width,
                  canvasViewport.height,
                  branchFlowGraph.layoutIdentity,
                ].join(":")}
                minZoom={Math.min(0.2, branchFlowGraph.initialViewport.zoom)}
                nodeTypes={nodeTypes}
                nodes={branchFlowGraph.nodes}
                onNodeClick={(_, node) => {
                  const targetRoutePath = node.data.targetRoutePath;
                  if (typeof targetRoutePath !== "string") {
                    return;
                  }
                  navigateToGraphPath(targetRoutePath, node.data.label);
                }}
                proOptions={{ hideAttribution: true }}
              ></ReactFlow>
            </div>
          )}
        </div>
      </section>
      {editingCard ? (
        <SuggestEditDialog
          card={editingCard}
          errorMessage={suggestionError}
          isSubmitting={createSuggestedEditMutation.isPending}
          onClose={() => {
            setEditingCard(null);
            setSuggestionError(undefined);
          }}
          onSubmit={handleSubmitSuggestion}
        />
      ) : null}
      {isSignInDialogOpen ? (
        <SignInRequiredDialog
          onClose={() => {
            setIsSignInDialogOpen(false);
          }}
        />
      ) : null}
    </main>
  );
}
