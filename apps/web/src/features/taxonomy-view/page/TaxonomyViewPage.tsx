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
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import type { SearchResultCardEditPayload } from "../../search/components/SearchResultCard";
import { SignInRequiredDialog } from "../../search/components/SignInRequiredDialog";
import { SuggestEditDialog } from "../../search/components/SuggestEditDialog";
import { useCreateSuggestedEditMutation } from "../../search/data/searchQueries";
import {
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
  LayoutViewport,
  TaxonomyLayoutNodeData,
} from "./layout/taxonomyLayoutTypes";
import { TaxonomyFlowNode } from "./TaxonomyFlowNode";

const DEFAULT_CANVAS_VIEWPORT = BRANCH_DESKTOP_REFERENCE_VIEWPORT;
const breadcrumbMutedClasses =
  "text-[13px] leading-[18px] font-normal text-[rgba(92,107,138,0.74)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";
const breadcrumbCurrentClasses =
  "text-[13px] leading-[18px] font-medium text-[rgba(33,43,64,0.96)] transition-colors hover:text-[rgba(55,72,102,0.92)] focus-visible:outline-0";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

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

function sameViewport(left: LayoutViewport, right: LayoutViewport) {
  return left.height === right.height && left.width === right.width;
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

  const rootQuery = useTaxonomyRootViewQuery({
    enabled: rootMode,
  });
  const pathQuery = useTaxonomyNodeViewByPathQuery(activeRoutePath, {
    enabled: !rootMode,
  });

  const activeQuery = rootMode ? rootQuery : pathQuery;
  const breadcrumbs = rootMode ? [] : (pathQuery.data?.breadcrumb ?? []);
  const displayBreadcrumbs =
    breadcrumbs[0]?.parent_id === null && breadcrumbs[0].name === "Root"
      ? breadcrumbs.slice(1)
      : breadcrumbs;
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

  function navigateToGraphPath(routePath: string) {
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
        suggestedContent: payload.suggestedContent,
        suggestedTitle: payload.suggestedTitle,
      });
      setEditingCard(null);
      setSuggestionError(undefined);
    } catch {
      setSuggestionError("Could not submit the suggestion. Try again.");
    }
  }

  const branchFlowGraph = useMemo(() => {
    if (activeQuery.isPending) {
      return { nodes: [] as BubbleFlowNode[] };
    }

    if (rootMode) {
      const branchLayout = buildBranchLayout({
        center: layoutCenter,
        children: rootQuery.data?.children ?? [],
        viewport: canvasViewport,
      });

      return {
        nodes: branchLayout.nodes.map(toFlowNode),
      };
    }

    const branchLayout = buildBranchLayout({
      center: layoutCenter,
      children:
        pathQuery.data?.node_kind === "branch" ? pathQuery.data.children : [],
      viewport: canvasViewport,
    });

    return {
      nodes: branchLayout.nodes.map(toFlowNode),
    };
  }, [
    activeQuery.isPending,
    canvasViewport,
    layoutCenter,
    pathQuery.data,
    rootMode,
    rootQuery.data?.children,
  ]);

  return (
    <main
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#f8fafc]"
      data-testid="taxonomy-shell-body"
    >
      <section
        aria-label="taxonomy canvas"
        className="relative min-h-0 flex-1 overflow-hidden bg-[#f8fafc]"
        data-figma-desktop-node="702:3845"
        data-figma-mobile-node="702:3950"
        data-testid="taxonomy-canvas"
        ref={canvasRef}
      >
        <nav
          aria-label="taxonomy breadcrumb"
          className="absolute top-5 left-5 z-20 flex max-w-[calc(100%-40px)] flex-wrap items-center gap-1.5 lg:top-6 lg:left-6 lg:max-w-[calc(100%-48px)]"
          data-breadcrumb-style="inline-text"
          data-testid="taxonomy-breadcrumb-overlay"
        >
          <button
            aria-current={rootMode ? "page" : undefined}
            className={
              rootMode ? breadcrumbCurrentClasses : breadcrumbMutedClasses
            }
            onClick={() => navigateToGraphPath("")}
            type="button"
          >
            Root
          </button>
          {displayBreadcrumbs.flatMap((item) => [
            <ChevronRight
              aria-hidden="true"
              className="size-3.5 shrink-0 text-[rgba(117,133,161,0.56)]"
              data-testid="taxonomy-breadcrumb-separator"
              key={`${item.id}-separator`}
            />,
            <button
              aria-current={
                item.id === displayBreadcrumbs.at(-1)?.id ? "page" : undefined
              }
              className={
                item.id === displayBreadcrumbs.at(-1)?.id
                  ? breadcrumbCurrentClasses
                  : breadcrumbMutedClasses
              }
              key={item.id}
              onClick={() => navigateToGraphPath(item.route_path)}
              type="button"
            >
              {item.name}
            </button>,
          ])}
        </nav>
        {activeQuery.isPending ? (
          <section
            aria-busy="true"
            aria-live="polite"
            className="absolute top-1/2 left-1/2 z-20 w-[min(420px,calc(100%-40px))] -translate-x-1/2 -translate-y-1/2 rounded-[20px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-[22px] text-left shadow-[0_18px_40px_rgba(15,23,42,0.14)]"
            data-testid="taxonomy-loading-overlay"
          >
            <h2 className="m-0 text-[1.1rem] text-[#0F172A]">
              Loading taxonomy view
            </h2>
            <p className="mt-2.5 mb-0 text-[#475569]">
              Fetching the latest taxonomy hierarchy snapshot from API.
            </p>
          </section>
        ) : null}
        {activeQuery.isError ? (
          <section
            className="absolute top-1/2 left-1/2 z-20 w-[min(420px,calc(100%-40px))] -translate-x-1/2 -translate-y-1/2 rounded-[20px] border border-[rgba(148,163,184,0.24)] bg-[rgba(255,255,255,0.94)] p-[22px] text-left shadow-[0_18px_40px_rgba(15,23,42,0.14)]"
            data-testid="taxonomy-error-overlay"
            role="alert"
          >
            <h2 className="m-0 text-[1.1rem] text-[#0F172A]">
              Taxonomy view unavailable
            </h2>
            <p className="mt-2.5 mb-0 text-[#475569]">
              {activeQuery.error.message}
            </p>
          </section>
        ) : null}
        <div className="taxonomy-flow-shell absolute inset-0 overflow-hidden">
          {pathQuery.data?.node_kind === "leaf" ? (
            <Suspense fallback={null}>
              <LeafRenderer
                key={`${pathQuery.data.current_node.id}:${pathQuery.data.layout_version}:${pathQuery.data.generated_at}`}
                leafView={pathQuery.data}
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
                fitView
                fitViewOptions={{
                  padding: canvasViewport.width < 640 ? 0.12 : 0.08,
                }}
                key={activeRoutePath || "root"}
                minZoom={0.2}
                nodeTypes={nodeTypes}
                nodes={branchFlowGraph.nodes}
                onNodeClick={(_, node) => {
                  const targetRoutePath = node.data.targetRoutePath;
                  if (typeof targetRoutePath !== "string") {
                    return;
                  }
                  navigateToGraphPath(targetRoutePath);
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
