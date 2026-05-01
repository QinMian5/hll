// abstract: Behavior tests for the taxonomy page shell and branch/leaf renderer routing.
// out_of_scope: Browser-level rendering fidelity and backend query execution.

import "@testing-library/jest-dom/vitest";

import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", () => ({
  Background: () => <div data-testid="reactflow-background" />,
  ReactFlow: ({
    children,
    nodeTypes = {},
    nodes,
    onNodeClick,
  }: MockReactFlowProps) => (
    <div data-testid="reactflow-mock">
      {nodes.map((node) => {
        const BubbleNode = node.type ? nodeTypes[node.type] : undefined;

        return (
          /* biome-ignore lint/a11y/noStaticElementInteractions: test-only container proxies node click behavior. */
          /* biome-ignore lint/a11y/useKeyWithClickEvents: keyboard behavior is outside the scope of this structural mock. */
          <div
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
          </div>
        );
      })}
      {children}
    </div>
  ),
}));

vi.mock("./leaf/LeafRenderer", () => ({
  LeafRenderer: ({
    leafView,
    onSuggestEdit,
  }: {
    readonly leafView: { readonly current_node: { readonly name: string } };
    readonly onSuggestEdit?: (card: {
      readonly content: string;
      readonly currentVersion: number;
      readonly nodeId: number;
      readonly title: string;
    }) => void;
  }) => (
    <div data-testid="taxonomy-leaf-renderer">
      {leafView.current_node.name}
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
  readonly nodeTypes?: Record<
    string,
    ComponentType<MockFlowNodeComponentProps>
  >;
  readonly nodes: Array<{
    readonly data: {
      readonly depth?: number;
      readonly label: string;
      readonly renderMode?: "bubble" | "point";
      readonly scope?: "branch" | "inner" | "outer";
      readonly targetNodeId?: number | null;
      readonly targetRoutePath?: string;
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
        readonly targetRoutePath?: string;
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

function makeQueryResult<T>(
  overrides: Partial<MockQueryResult<T>>,
): MockQueryResult<T> {
  return {
    data: undefined,
    error: null,
    isError: false,
    isPending: false,
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
    current_node: {
      depth: 2,
      id: 2,
      is_leaf: true,
      name: "Algebra",
      parent_id: 1,
      route_path: "math",
      route_slug: "math",
    },
    edge_count: 1,
    generated_at: "2026-04-29T00:00:00Z",
    layout_version: "taxonomy-leaf-layout-v2",
    node_kind: "leaf",
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
    current_node: {
      depth: 1,
      id: 1,
      is_leaf: false,
      name: "Mathematics",
      parent_id: null,
      route_path: "math",
      route_slug: "math",
    },
    node_kind: "branch",
    ...overrides,
  } as TaxonomyNodeView;
}

beforeEach(() => {
  mutateSuggestedEdit = vi.fn(async () => undefined);
  rootQueryState = makeQueryResult({
    data: makeRootView({
      children: [
        {
          depth: 0,
          descendant_card_count: 20,
          id: 1,
          is_leaf: false,
          name: "Math",
          parent_id: null,
          route_path: "math",
          route_slug: "math",
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
              id: 1,
              is_leaf: false,
              name: "Math",
              parent_id: null,
              route_path: "math",
              route_slug: "math",
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

function createTaxonomyTestRouter(pathname: string) {
  const rootRoute = createRootRoute({
    component: TestRoot,
  });
  const graphRoute = createRoute({
    component: TaxonomyViewPage,
    getParentRoute: () => rootRoute,
    path: "graph",
  });
  const graphPathRoute = createRoute({
    component: TaxonomyViewPage,
    getParentRoute: () => rootRoute,
    path: "graph/$",
  });
  const routeTree = rootRoute.addChildren([graphRoute, graphPathRoute]);

  return createRouter({
    history: createMemoryHistory({ initialEntries: [pathname] }),
    routeTree,
  });
}

async function renderWithRoute(pathname = "/graph") {
  const router = createTaxonomyTestRouter(pathname);
  const result = render(<RouterProvider router={router} />);

  await screen.findByTestId("taxonomy-canvas");

  return { ...result, router };
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

    fireEvent.change(within(dialog).getByLabelText("Suggested content"), {
      target: { value: "Updated leaf content" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Submit suggestion" }),
    );

    expect(mutateSuggestedEdit).toHaveBeenCalledWith({
      baseVersion: 4,
      nodeId: 10,
      suggestedContent: "Updated leaf content",
      suggestedTitle: "Leaf card",
    });
  });

  it("renders a readable deep link without first visiting the root graph", async () => {
    await renderWithRoute("/graph/math");

    expect(mockUseTaxonomyRootViewQuery).toHaveBeenCalledWith({
      enabled: false,
    });
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
            id: 4,
            is_leaf: true,
            name: "Unclassified",
            parent_id: 3,
            route_path: "unclassified",
            route_slug: "unclassified",
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
              id: 3,
              is_leaf: false,
              name: "Root",
              parent_id: null,
              route_path: "",
              route_slug: "root",
            },
            {
              depth: 1,
              id: 4,
              is_leaf: true,
              name: "Unclassified",
              parent_id: 3,
              route_path: "unclassified",
              route_slug: "unclassified",
            },
          ],
          current_node: {
            depth: 1,
            id: 4,
            is_leaf: true,
            name: "Unclassified",
            parent_id: 3,
            route_path: "unclassified",
            route_slug: "unclassified",
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
              id: 2,
              is_leaf: false,
              name: "Science",
              parent_id: null,
              route_path: "science",
              route_slug: "science",
            },
            {
              depth: 1,
              id: 1,
              is_leaf: false,
              name: "Mathematics",
              parent_id: 2,
              route_path: "science/mathematics",
              route_slug: "mathematics",
            },
          ],
          current_node: {
            depth: 1,
            id: 1,
            is_leaf: false,
            name: "Mathematics",
            parent_id: 2,
            route_path: "science/mathematics",
            route_slug: "mathematics",
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
