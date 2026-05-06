// abstract: Behavior tests for the taxonomy page shell and branch/leaf renderer routing.
// out_of_scope: Browser-level rendering fidelity and backend query execution.

import "@testing-library/jest-dom/vitest";

import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  type RouteComponent,
  RouterProvider,
} from "@tanstack/react-router";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { type ComponentType, type ReactNode, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const reactFlowMockState = vi.hoisted(() => ({
  nextMountId: 1,
}));

vi.mock("@xyflow/react", async () => {
  const React = await import("react");

  return {
    Background: () => <div data-testid="reactflow-background" />,
    ReactFlow: ({
      children,
      defaultViewport,
      fitView,
      minZoom,
      nodeTypes = {},
      nodes,
      onNodeClick,
    }: MockReactFlowProps) => {
      const mountId = React.useMemo(() => reactFlowMockState.nextMountId++, []);

      return (
        <div
          data-default-viewport={JSON.stringify(defaultViewport)}
          data-fit-view={fitView ? "true" : "false"}
          data-min-zoom={String(minZoom)}
          data-mount-id={mountId}
          data-testid="reactflow-mock"
        >
          {nodes.map((node) => {
            const BubbleNode = node.type ? nodeTypes[node.type] : undefined;

            return (
              /* biome-ignore lint/a11y/useKeyWithClickEvents: keyboard behavior is outside the scope of this structural mock. */
              <section
                aria-label={node.ariaLabel}
                data-testid={`reactflow-node-${node.id}`}
                key={node.id}
                onClick={() => onNodeClick?.({}, node)}
              >
                {BubbleNode ? (
                  <BubbleNode
                    data={node.data}
                    dragging={false}
                    id={node.id}
                    isConnectable={false}
                    selected={false}
                    type={node.type}
                    xPos={node.position?.x ?? 0}
                    yPos={node.position?.y ?? 0}
                    zIndex={0}
                  />
                ) : (
                  String(node.data.label)
                )}
              </section>
            );
          })}
          {children}
        </div>
      );
    },
  };
});

vi.mock("./leaf/LeafRenderer", () => ({
  LeafRenderer: ({
    leafView,
    onSuggestEdit,
  }: {
    readonly leafView: {
      readonly current_scope?: { readonly name: string };
    };
    readonly onSuggestEdit?: (card: {
      readonly content: string;
      readonly currentVersion: number;
      readonly nodeId: number;
      readonly title: string;
    }) => void;
  }) => (
    <div data-testid="taxonomy-leaf-renderer">
      {leafView.current_scope?.name}
      <button
        onClick={() => {
          onSuggestEdit?.({
            content: "Leaf content",
            currentVersion: 4,
            nodeId: 10,
            title: "Leaf card",
          });
        }}
        type="button"
      >
        Open leaf edit
      </button>
    </div>
  ),
}));

vi.mock("../data/taxonomyViewQueries", () => ({
  useTaxonomyNodeViewByPathQuery: vi.fn(),
  useTaxonomyNodeViewQuery: vi.fn(),
  useTaxonomyRootViewQuery: vi.fn(),
}));

vi.mock("../../search/data/searchQueries", () => ({
  useCreateSuggestedEditMutation: vi.fn(),
}));

vi.mock("../../../shared/web-api/useWebSession", () => ({
  useWebSession: vi.fn(),
}));

import { WebApiRequestError } from "../../../shared/web-api/errors";
import * as webSession from "../../../shared/web-api/useWebSession";
import * as searchQueries from "../../search/data/searchQueries";
import type {
  TaxonomyNodeView,
  TaxonomyRootView,
} from "../data/taxonomyViewQueries";
import * as taxonomyViewQueries from "../data/taxonomyViewQueries";
import { TaxonomyViewPage } from "./TaxonomyViewPage";

interface MockReactFlowProps {
  readonly children?: ReactNode;
  readonly defaultViewport?: {
    readonly x: number;
    readonly y: number;
    readonly zoom: number;
  };
  readonly fitView?: boolean;
  readonly minZoom?: number;
  readonly nodeTypes?: Record<
    string,
    ComponentType<MockFlowNodeComponentProps>
  >;
  readonly nodes: Array<{
    readonly ariaLabel?: string;
    readonly data: {
      readonly depth?: number;
      readonly label: string;
      readonly renderMode?: "bubble" | "point";
      readonly scope?: "branch" | "inner" | "outer";
      readonly targetNodeId?: number | null;
      readonly targetRoutePath?: string | null;
      readonly tooltip?: string;
    };
    readonly id: string;
    readonly position?: { readonly x: number; readonly y: number };
    readonly style?: {
      readonly height: number;
      readonly width: number;
    };
    readonly type?: string;
  }>;
  readonly onNodeClick?: (
    event: unknown,
    node: {
      readonly data: {
        readonly targetNodeId?: number | null;
        readonly targetRoutePath?: string | null;
      };
      readonly id: string;
    },
  ) => void;
}

interface MockFlowNodeComponentProps {
  readonly data: MockReactFlowProps["nodes"][number]["data"];
  readonly dragging: boolean;
  readonly id: string;
  readonly isConnectable: boolean;
  readonly selected: boolean;
  readonly type?: string;
  readonly xPos: number;
  readonly yPos: number;
  readonly zIndex: number;
}

interface MockQueryResult<T> {
  readonly data: T | undefined;
  readonly error: Error | null;
  readonly isError: boolean;
  readonly isPending: boolean;
  readonly refetch: () => void;
}

const mockUseTaxonomyRootViewQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyRootViewQuery,
);
const mockUseTaxonomyNodeViewByPathQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyNodeViewByPathQuery,
);
const mockUseTaxonomyNodeViewQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyNodeViewQuery,
);
const mockUseCreateSuggestedEditMutation = vi.mocked(
  searchQueries.useCreateSuggestedEditMutation,
);
const mockUseWebSession = vi.mocked(webSession.useWebSession);

let rootQueryState: MockQueryResult<TaxonomyRootView>;
let pathQueryStates: Map<string, MockQueryResult<TaxonomyNodeView>>;
let mutateSuggestedEdit: ReturnType<typeof vi.fn>;
let rerenderTaxonomyPage: (() => void) | undefined;

function makeQueryResult<T>(
  overrides: Partial<MockQueryResult<T>>,
): MockQueryResult<T> {
  return {
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
    refetch: vi.fn(),
    ...overrides,
  };
}

function makeRootView(overrides: Partial<TaxonomyRootView>): TaxonomyRootView {
  return {
    breadcrumb: [],
    children: [],
    ...overrides,
  };
}

function makeLeafNodeView(
  overrides: Partial<TaxonomyNodeView>,
): TaxonomyNodeView {
  return {
    breadcrumb: [],
    current_scope: {
      depth: 2,
      name: "Algebra",
      parent_taxonomy_node_id: 1,
      route_path: "math",
      route_slug: "math",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 2,
    },
    edge_count: 1,
    generated_at: "2026-04-29T00:00:00Z",
    layout_version: "taxonomy-card-scope-layout-v2",
    layout_status: "ready",
    node_kind: "card_scope",
    node_count: 2,
    world_bounds: { max_x: 744, max_y: 484, min_x: 696, min_y: 446 },
    ...overrides,
  } as TaxonomyNodeView;
}

function makeBranchNodeView(
  overrides: Partial<TaxonomyNodeView>,
): TaxonomyNodeView {
  return {
    breadcrumb: [],
    children: [],
    current_scope: {
      depth: 1,
      name: "Mathematics",
      parent_taxonomy_node_id: null,
      route_path: "math",
      route_slug: "math",
      scope_kind: "taxonomy_node",
      taxonomy_node_id: 1,
    },
    node_kind: "branch",
    ...overrides,
  } as TaxonomyNodeView;
}

function rootScope() {
  return {
    depth: 0,
    name: "Root",
    parent_taxonomy_node_id: null,
    route_path: "",
    route_slug: "root",
    scope_kind: "taxonomy_node",
    taxonomy_node_id: 1,
  } as const;
}

function rootQueryStateAsPathQuery(): MockQueryResult<TaxonomyNodeView> {
  return {
    ...rootQueryState,
    data: rootQueryState.data
      ? makeBranchNodeView({
          breadcrumb: [rootScope()],
          children: rootQueryState.data.children,
          current_scope: rootScope(),
        })
      : undefined,
  };
}

beforeEach(() => {
  reactFlowMockState.nextMountId = 1;
  rerenderTaxonomyPage = undefined;
  mutateSuggestedEdit = vi.fn(async () => undefined);
  rootQueryState = makeQueryResult({
    data: makeRootView({
      children: [
        {
          depth: 0,
          descendant_card_count: 20,
          name: "Math",
          node_kind: "branch",
          parent_taxonomy_node_id: null,
          route_path: "math",
          route_slug: "math",
          scope_kind: "taxonomy_node",
          taxonomy_node_id: 1,
        },
      ],
    }),
  });
  pathQueryStates = new Map([
    [
      "math",
      makeQueryResult({
        data: makeLeafNodeView({
          breadcrumb: [
            {
              depth: 0,
              name: "Math",
              parent_taxonomy_node_id: null,
              route_path: "math",
              route_slug: "math",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 1,
            },
          ],
        }),
      }),
    ],
  ]);

  mockUseTaxonomyRootViewQuery.mockImplementation(
    () =>
      rootQueryState as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyRootViewQuery
      >,
  );
  mockUseTaxonomyNodeViewByPathQuery.mockImplementation((routePath) => {
    if (routePath === "") {
      return (pathQueryStates.get("") ??
        rootQueryStateAsPathQuery()) as unknown as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyNodeViewByPathQuery
      >;
    }

    const result = pathQueryStates.get(routePath);
    return (result ??
      makeQueryResult({ isPending: true })) as unknown as ReturnType<
      typeof taxonomyViewQueries.useTaxonomyNodeViewByPathQuery
    >;
  });
  mockUseTaxonomyNodeViewQuery.mockReturnValue(
    makeQueryResult({ isPending: true }) as unknown as ReturnType<
      typeof taxonomyViewQueries.useTaxonomyNodeViewQuery
    >,
  );
  mockUseCreateSuggestedEditMutation.mockReturnValue({
    isPending: false,
    mutateAsync: mutateSuggestedEdit,
  } as unknown as ReturnType<
    typeof searchQueries.useCreateSuggestedEditMutation
  >);
  mockUseWebSession.mockReturnValue({
    status: "authenticated",
    user: {
      email: "editor@example.com",
      id: "user-1",
      name: "Editor",
    },
  } as unknown as ReturnType<typeof webSession.useWebSession>);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function TestRoot() {
  return <Outlet />;
}

function TaxonomyViewPageRerenderHarness() {
  const [, setRenderIndex] = useState(0);
  rerenderTaxonomyPage = () => setRenderIndex((index) => index + 1);

  return <TaxonomyViewPage />;
}

function createTaxonomyTestRouter(
  pathname: string,
  routeComponent: RouteComponent = TaxonomyViewPage,
) {
  const rootRoute = createRootRoute({
    component: TestRoot,
  });
  const graphRoute = createRoute({
    component: routeComponent,
    getParentRoute: () => rootRoute,
    path: "graph",
  });
  const graphPathRoute = createRoute({
    component: routeComponent,
    getParentRoute: () => rootRoute,
    path: "graph/$",
  });
  const routeTree = rootRoute.addChildren([graphRoute, graphPathRoute]);

  return createRouter({
    history: createMemoryHistory({ initialEntries: [pathname] }),
    routeTree,
  });
}

async function renderWithRoute(
  pathname = "/graph",
  routeComponent: RouteComponent = TaxonomyViewPage,
) {
  const router = createTaxonomyTestRouter(pathname, routeComponent);
  const result = render(<RouterProvider router={router} />);

  await screen.findByTestId("taxonomy-canvas");

  return { ...result, router };
}

function parseReactFlowDefaultViewport() {
  const serializedViewport = screen
    .getByTestId("reactflow-mock")
    .getAttribute("data-default-viewport");

  expect(serializedViewport).not.toBeNull();

  return JSON.parse(serializedViewport ?? "") as {
    readonly x: number;
    readonly y: number;
    readonly zoom: number;
  };
}

describe("TaxonomyViewPage", () => {
  it("renders the approved full-slot Figma canvas shell without the old panel", async () => {
    await renderWithRoute();

    expect(
      screen.queryByTestId("taxonomy-header-shell"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Knowledge Graph")).not.toBeInTheDocument();

    const shellBody = screen.getByTestId("taxonomy-shell-body");
    const canvas = screen.getByTestId("taxonomy-canvas");

    expect(shellBody).not.toHaveClass("p-6");
    expect(canvas).toHaveAttribute("data-figma-desktop-node", "702:3845");
    expect(canvas).toHaveAttribute("data-figma-mobile-node", "702:3950");
    expect(
      screen.queryByTestId("taxonomy-canvas-panel"),
    ).not.toBeInTheDocument();
  });

  it("renders loading and error overlays inside the stable canvas shell", async () => {
    rootQueryState = makeQueryResult({ isPending: true });
    mockUseTaxonomyRootViewQuery.mockImplementation(
      () =>
        rootQueryState as unknown as ReturnType<
          typeof taxonomyViewQueries.useTaxonomyRootViewQuery
        >,
    );

    await renderWithRoute();

    expect(screen.getByTestId("taxonomy-canvas")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-loading-overlay")).toBeInTheDocument();

    cleanup();

    rootQueryState = makeQueryResult({
      error: new Error("Taxonomy root view request failed with status 502."),
      isError: true,
    });
    mockUseTaxonomyRootViewQuery.mockImplementation(
      () =>
        rootQueryState as unknown as ReturnType<
          typeof taxonomyViewQueries.useTaxonomyRootViewQuery
        >,
    );

    await renderWithRoute();

    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "Taxonomy root view request failed with status 502.",
    );
  });

  it("shows a quota-specific graph message when taxonomy view requests are rate limited", async () => {
    rootQueryState = makeQueryResult({
      error: new WebApiRequestError({
        code: "quota_exceeded",
        message: "Rate limit exceeded.",
        status: 429,
      }),
      isError: true,
    });
    mockUseTaxonomyRootViewQuery.mockImplementation(
      () =>
        rootQueryState as unknown as ReturnType<
          typeof taxonomyViewQueries.useTaxonomyRootViewQuery
        >,
    );

    await renderWithRoute();

    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "Too many graph requests",
    );
    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "Try again shortly.",
    );
  });

  it("shows a retryable layout readiness message when card-scope layout is not ready", async () => {
    const refetch = vi.fn();
    pathQueryStates.set(
      "unclassified",
      makeQueryResult({
        error: new WebApiRequestError({
          code: "layout_not_ready",
          message: "Taxonomy card-scope layout is being prepared.",
          retryAfterSeconds: 10,
          status: 503,
        }),
        isError: true,
        refetch,
      }),
    );

    await renderWithRoute("/graph/unclassified");

    const overlay = screen.getByTestId("taxonomy-error-overlay");
    expect(overlay).toHaveTextContent("Taxonomy layout unavailable");
    expect(overlay).toHaveTextContent("Try again in about 10 seconds.");

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("loads the root graph route through the path resolver so Root card-scope data can render", async () => {
    pathQueryStates.set(
      "",
      makeQueryResult({
        data: makeLeafNodeView({
          breadcrumb: [
            {
              depth: 0,
              name: "Root",
              parent_taxonomy_node_id: null,
              route_path: "",
              route_slug: "root",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 1,
            },
          ],
          current_scope: {
            depth: 0,
            name: "Root",
            parent_taxonomy_node_id: null,
            route_path: "",
            route_slug: "root",
            scope_kind: "taxonomy_node",
            taxonomy_node_id: 1,
          },
          node_count: 56,
        }),
      }),
    );

    await renderWithRoute("/graph");

    expect(mockUseTaxonomyNodeViewByPathQuery).toHaveBeenCalledWith("", {
      enabled: true,
    });
    expect(
      await screen.findByTestId("taxonomy-leaf-renderer"),
    ).toHaveTextContent("Root");
  });

  it("renders branch mode on React Flow and drills into leaf mode on the dedicated leaf renderer", async () => {
    const { router } = await renderWithRoute();

    expect(screen.getByTestId("taxonomy-branch-reactflow")).toBeInTheDocument();
    expect(
      screen.queryByTestId("taxonomy-leaf-renderer"),
    ).not.toBeInTheDocument();

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);

    await waitFor(() =>
      expect(router.state.location.pathname).toBe("/graph/math"),
    );
    expect(
      await screen.findByTestId("taxonomy-leaf-renderer"),
    ).toHaveTextContent("Algebra");
    expect(
      screen.queryByTestId("taxonomy-branch-reactflow"),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Math" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("starts dense branch flows from the computed initial viewport instead of fitView", async () => {
    rootQueryState = makeQueryResult({
      data: makeRootView({
        children: Array.from({ length: 24 }, (_, index) => ({
          depth: 0,
          descendant_card_count: 300,
          name: `Node ${index + 1}`,
          node_kind: "branch",
          parent_taxonomy_node_id: null,
          route_path: `node-${index + 1}`,
          route_slug: `node-${index + 1}`,
          scope_kind: "taxonomy_node",
          taxonomy_node_id: index + 1,
        })),
      }),
    });

    await renderWithRoute();

    const reactFlow = screen.getByTestId("reactflow-mock");
    const defaultViewport = parseReactFlowDefaultViewport();

    expect(reactFlow).toHaveAttribute("data-fit-view", "false");
    expect(defaultViewport.zoom).toBeLessThan(1);
    expect(reactFlow).toHaveAttribute(
      "data-min-zoom",
      String(Math.min(0.2, defaultViewport.zoom)),
    );
    expect(screen.getAllByText(/^Node \d+$/)).toHaveLength(24);
    expect(
      screen.getByTestId("reactflow-node-taxonomy-taxonomy_node:1"),
    ).toHaveAttribute("aria-label", "Node 1 · 300 cards");
  });

  it("remounts the branch flow when pending branch data resolves to a ready layout", async () => {
    rootQueryState = makeQueryResult({ isPending: true });

    await renderWithRoute("/graph", TaxonomyViewPageRerenderHarness);
    const pendingMountId = screen
      .getByTestId("reactflow-mock")
      .getAttribute("data-mount-id");

    rootQueryState = makeQueryResult({
      data: makeRootView({
        children: [
          {
            depth: 0,
            descendant_card_count: 20,
            name: "Physics",
            node_kind: "branch",
            parent_taxonomy_node_id: null,
            route_path: "physics",
            route_slug: "physics",
            scope_kind: "taxonomy_node",
            taxonomy_node_id: 42,
          },
        ],
      }),
    });

    act(() => {
      rerenderTaxonomyPage?.();
    });

    await screen.findByText("Physics");

    expect(screen.getByTestId("reactflow-mock")).not.toHaveAttribute(
      "data-mount-id",
      pendingMountId ?? "",
    );
  });

  it("opens the shared suggest edit dialog from the leaf disclosure edit action", async () => {
    await renderWithRoute();

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);
    fireEvent.click(
      await screen.findByRole("button", { name: "Open leaf edit" }),
    );

    const dialog = await screen.findByRole("dialog", { name: "Suggest edit" });

    expect(within(dialog).getByLabelText("Suggested title")).toHaveValue(
      "Leaf card",
    );
    expect(within(dialog).getByLabelText("Suggested content")).toHaveValue(
      "Leaf content",
    );
    expect(within(dialog).getByLabelText("Reason")).toHaveAttribute(
      "placeholder",
      "Explain why you recommend editing this card.",
    );

    fireEvent.change(within(dialog).getByLabelText("Suggested content"), {
      target: { value: "Updated leaf content" },
    });
    fireEvent.change(within(dialog).getByLabelText("Reason"), {
      target: { value: "The current card needs clearer wording." },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Submit suggestion" }),
    );

    expect(mutateSuggestedEdit).toHaveBeenCalledWith({
      baseVersion: 4,
      nodeId: 10,
      reason: "The current card needs clearer wording.",
      suggestedContent: "Updated leaf content",
      suggestedTitle: "Leaf card",
    });
  });

  it("shows actionable copy for known leaf suggestion errors", async () => {
    mutateSuggestedEdit.mockRejectedValueOnce(
      new WebApiRequestError({
        code: "DOMAIN_KNOWLEDGE_RULE_VIOLATION",
        message: "Suggested edit must change the card title or content.",
        status: 422,
      }),
    );

    await renderWithRoute();

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);
    fireEvent.click(
      await screen.findByRole("button", { name: "Open leaf edit" }),
    );

    const dialog = await screen.findByRole("dialog", { name: "Suggest edit" });
    fireEvent.change(within(dialog).getByLabelText("Suggested content"), {
      target: { value: "Updated leaf content" },
    });
    fireEvent.change(within(dialog).getByLabelText("Reason"), {
      target: { value: "The current card needs clearer wording." },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Submit suggestion" }),
    );

    expect(
      await screen.findByText("Change the title or content before submitting."),
    ).toBeInTheDocument();
  });

  it("renders a readable deep link without first visiting the root graph", async () => {
    await renderWithRoute("/graph/math");

    expect(mockUseTaxonomyRootViewQuery).not.toHaveBeenCalled();
    expect(mockUseTaxonomyNodeViewByPathQuery).toHaveBeenCalledWith("math", {
      enabled: true,
    });
    expect(
      await screen.findByTestId("taxonomy-leaf-renderer"),
    ).toHaveTextContent("Algebra");
  });

  it("does not duplicate the root crumb when backend breadcrumb already starts at Root", async () => {
    rootQueryState = makeQueryResult({
      data: makeRootView({
        children: [
          {
            depth: 1,
            descendant_card_count: 54,
            name: "Unclassified",
            node_kind: "card_scope",
            parent_taxonomy_node_id: 3,
            route_path: "unclassified",
            route_slug: "unclassified",
            scope_kind: "virtual_unclassified",
            taxonomy_node_id: 3,
          },
        ],
      }),
    });
    pathQueryStates.set(
      "unclassified",
      makeQueryResult({
        data: makeLeafNodeView({
          breadcrumb: [
            {
              depth: 0,
              name: "Root",
              parent_taxonomy_node_id: null,
              route_path: "",
              route_slug: "root",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 3,
            },
            {
              depth: 1,
              name: "Unclassified",
              parent_taxonomy_node_id: 3,
              route_path: "unclassified",
              route_slug: "unclassified",
              scope_kind: "virtual_unclassified",
              taxonomy_node_id: 3,
            },
          ],
          current_scope: {
            depth: 1,
            name: "Unclassified",
            parent_taxonomy_node_id: 3,
            route_path: "unclassified",
            route_slug: "unclassified",
            scope_kind: "virtual_unclassified",
            taxonomy_node_id: 3,
          },
        }),
      }),
    );

    await renderWithRoute();

    const unclassifiedNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Unclassified")
      .closest("[data-node-scope='branch']");

    expect(unclassifiedNode).not.toBeNull();

    fireEvent.click(unclassifiedNode as HTMLElement);

    expect(
      await screen.findByTestId("taxonomy-leaf-renderer"),
    ).toHaveTextContent("Unclassified");
    expect(screen.getAllByRole("button", { name: "Root" })).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "Unclassified" }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByTestId("taxonomy-breadcrumb-separator")).toHaveLength(
      1,
    );
  });

  it("renders branch breadcrumbs with Figma chevrons and responsive offsets", async () => {
    pathQueryStates.set(
      "math",
      makeQueryResult({
        data: makeBranchNodeView({
          breadcrumb: [
            {
              depth: 0,
              name: "Science",
              parent_taxonomy_node_id: null,
              route_path: "science",
              route_slug: "science",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 2,
            },
            {
              depth: 1,
              name: "Mathematics",
              parent_taxonomy_node_id: 2,
              route_path: "science/mathematics",
              route_slug: "mathematics",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 1,
            },
          ],
          current_scope: {
            depth: 1,
            name: "Mathematics",
            parent_taxonomy_node_id: 2,
            route_path: "science/mathematics",
            route_slug: "mathematics",
            scope_kind: "taxonomy_node",
            taxonomy_node_id: 1,
          },
        }),
      }),
    );

    await renderWithRoute();

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);

    const breadcrumb = await screen.findByTestId("taxonomy-breadcrumb-overlay");

    expect(breadcrumb).toHaveClass("top-5", "left-5", "lg:top-6", "lg:left-6");
    expect(screen.getAllByTestId("taxonomy-breadcrumb-separator")).toHaveLength(
      2,
    );
    expect(screen.getByRole("button", { name: "Mathematics" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("preserves the settled branch scene and breadcrumb while the next route is loading", async () => {
    pathQueryStates.set(
      "science/mathematics",
      makeQueryResult({
        data: makeBranchNodeView({
          breadcrumb: [
            {
              depth: 0,
              name: "Science",
              parent_taxonomy_node_id: null,
              route_path: "science",
              route_slug: "science",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 2,
            },
            {
              depth: 1,
              name: "Mathematics",
              parent_taxonomy_node_id: 2,
              route_path: "science/mathematics",
              route_slug: "mathematics",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 1,
            },
          ],
          children: [
            {
              depth: 2,
              descendant_card_count: 16,
              name: "Algebra",
              node_kind: "card_scope",
              parent_taxonomy_node_id: 1,
              route_path: "science/mathematics/algebra",
              route_slug: "algebra",
              scope_kind: "taxonomy_node",
              taxonomy_node_id: 12,
            },
          ],
          current_scope: {
            depth: 1,
            name: "Mathematics",
            parent_taxonomy_node_id: 2,
            route_path: "science/mathematics",
            route_slug: "mathematics",
            scope_kind: "taxonomy_node",
            taxonomy_node_id: 1,
          },
        }),
      }),
    );
    pathQueryStates.set(
      "science/mathematics/algebra",
      makeQueryResult({ isPending: true }),
    );

    const { router } = await renderWithRoute("/graph/science/mathematics");

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Algebra")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        "/graph/science/mathematics/algebra",
      ),
    );

    expect(screen.getByTestId("taxonomy-loading-overlay")).toHaveTextContent(
      "Opening Algebra",
    );
    expect(screen.getByRole("button", { name: "Science" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mathematics" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Algebra")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-transition-scrim")).toBeInTheDocument();
  });

  it("keeps unresolved readable paths in the URL while showing the path error", async () => {
    pathQueryStates.set(
      "science/missing",
      makeQueryResult({
        error: new WebApiRequestError({
          code: "taxonomy_route_path_not_found",
          message: "Taxonomy route path was not found.",
          status: 404,
        }),
        isError: true,
      }),
    );

    const { router } = await renderWithRoute("/graph/science/missing");

    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "Graph path not found",
    );
    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "This taxonomy path does not exist.",
    );
    expect(router.state.location.pathname).toBe("/graph/science/missing");

    fireEvent.click(screen.getByRole("button", { name: "Back to Root" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/graph"));
  });
});
