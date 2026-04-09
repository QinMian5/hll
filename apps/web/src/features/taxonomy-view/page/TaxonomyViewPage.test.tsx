// abstract: Behavior tests for the taxonomy view page shell and canvas overlays.
// out_of_scope: End-to-end browser rendering fidelity and backend query execution.

import "@testing-library/jest-dom/vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", () => ({
  Background: () => <div data-testid="reactflow-background" />,
  ReactFlow: ({
    children,
    edges = [],
    nodeTypes = {},
    nodes,
    onMoveEnd,
    onNodeClick,
  }: MockReactFlowProps) => (
    <div data-testid="reactflow-mock">
      <button
        onClick={() => onMoveEnd?.({}, { x: 0, y: 0, zoom: 0.5 })}
        type="button"
      >
        Overview viewport
      </button>
      <button
        onClick={() => onMoveEnd?.({}, { x: 0, y: 0, zoom: 1 })}
        type="button"
      >
        Zoomed viewport
      </button>
      {nodes.map((node) => {
        const BubbleNode = node.type ? nodeTypes[node.type] : undefined;

        return (
          /* biome-ignore lint/a11y/noStaticElementInteractions: test-only React Flow mock uses a plain wrapper to mirror production node containers. */
          /* biome-ignore lint/a11y/useKeyWithClickEvents: keyboard interaction is outside the scope of this structural mock. */
          <div
            data-node-x={node.position?.x ?? 0}
            data-node-y={node.position?.y ?? 0}
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
      {edges.map((edge) => (
        <div
          data-testid={`reactflow-edge-${edge.id}`}
          key={edge.id}
        >{`${edge.source}->${edge.target}`}</div>
      ))}
      {children}
    </div>
  ),
}));

vi.mock("../data/taxonomyViewQueries", () => ({
  useTaxonomyLeafNodeDetailsQuery: vi.fn(),
  useTaxonomyNodeViewQuery: vi.fn(),
  useTaxonomyRootViewQuery: vi.fn(),
}));

import type {
  TaxonomyLeafNodeDetailsResponse,
  TaxonomyNodeView,
  TaxonomyRootView,
} from "../data/taxonomyViewQueries";
import * as taxonomyViewQueries from "../data/taxonomyViewQueries";
import {
  BUBBLE_ACTIVATION_ZOOM,
  flowBoundsFromViewport,
  selectLeafHydrationNodeIds,
  TaxonomyViewPage,
} from "./TaxonomyViewPage";

interface MockReactFlowProps {
  readonly children?: ReactNode;
  readonly edges?: Array<{
    readonly id: string;
    readonly source: string;
    readonly target: string;
  }>;
  readonly nodeTypes?: Record<
    string,
    ComponentType<MockFlowNodeComponentProps>
  >;
  readonly nodes: Array<{
    readonly data: {
      readonly content?: string;
      readonly depth?: number;
      readonly label: string;
      readonly scope?: "branch" | "inner" | "outer";
      readonly targetNodeId?: number | null;
      readonly tooltip?: string;
    };
    readonly id: string;
    readonly position?: { readonly x: number; readonly y: number };
    readonly type?: string;
  }>;
  readonly onMoveEnd?: (
    event: unknown,
    viewport: { readonly x: number; readonly y: number; readonly zoom: number },
  ) => void;
  readonly onNodeClick?: (
    event: unknown,
    node: {
      readonly data: {
        readonly content?: string;
        readonly depth?: number;
        readonly label: string;
        readonly scope?: "branch" | "inner" | "outer";
        readonly targetNodeId?: number | null;
        readonly tooltip?: string;
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
const mockUseTaxonomyNodeViewQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyNodeViewQuery,
);
const mockUseTaxonomyLeafNodeDetailsQuery = vi.mocked(
  taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery,
);

let rootQueryState: MockQueryResult<TaxonomyRootView>;
let nodeQueryStates: Map<number, MockQueryResult<TaxonomyNodeView>>;
let leafDetailCalls: Array<{
  readonly enabled: boolean;
  readonly leafId: number;
  readonly nodeIds: readonly number[];
}>;
let leafDetailQueryStates: Map<
  string,
  MockQueryResult<TaxonomyLeafNodeDetailsResponse>
>;

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

function makeBranchNodeView(
  overrides: Partial<TaxonomyNodeView>,
): TaxonomyNodeView {
  return {
    breadcrumb: [],
    children: [],
    current_node: {
      depth: 0,
      id: 0,
      is_leaf: false,
      name: "Root",
      parent_id: null,
    },
    node_kind: "branch",
    ...overrides,
  } as TaxonomyNodeView;
}

function makeLeafNodeView(
  overrides: Partial<TaxonomyNodeView>,
): TaxonomyNodeView {
  return {
    breadcrumb: [],
    current_node: {
      depth: 0,
      id: 0,
      is_leaf: true,
      name: "Leaf",
      parent_id: null,
    },
    edges: [],
    node_kind: "leaf",
    nodes: [],
    ...overrides,
  } as TaxonomyNodeView;
}

function setRootQueryState(result: MockQueryResult<TaxonomyRootView>) {
  rootQueryState = result;
}

function setNodeQueryState(
  nodeId: number,
  result: MockQueryResult<TaxonomyNodeView>,
) {
  nodeQueryStates.set(nodeId, result);
}

function leafDetailStateKey(leafId: number, nodeIds: readonly number[]) {
  return `${leafId}:${[...nodeIds].join(",")}`;
}

function setLeafDetailQueryState(
  leafId: number,
  nodeIds: readonly number[],
  result: MockQueryResult<TaxonomyLeafNodeDetailsResponse>,
) {
  leafDetailQueryStates.set(leafDetailStateKey(leafId, nodeIds), result);
}

beforeEach(() => {
  rootQueryState = makeQueryResult({
    data: makeRootView({}),
  });
  nodeQueryStates = new Map<number, MockQueryResult<TaxonomyNodeView>>();
  leafDetailCalls = [];
  leafDetailQueryStates = new Map<
    string,
    MockQueryResult<TaxonomyLeafNodeDetailsResponse>
  >();

  mockUseTaxonomyRootViewQuery.mockImplementation(
    ({ enabled }: { readonly enabled?: boolean }) =>
      (enabled ?? true)
        ? (rootQueryState as ReturnType<
            typeof taxonomyViewQueries.useTaxonomyRootViewQuery
          >)
        : (makeQueryResult<TaxonomyRootView>({}) as ReturnType<
            typeof taxonomyViewQueries.useTaxonomyRootViewQuery
          >),
  );

  mockUseTaxonomyNodeViewQuery.mockImplementation(
    (nodeId: number, { enabled }: { readonly enabled?: boolean }) =>
      (enabled ?? true)
        ? ((nodeQueryStates.get(nodeId) ??
            makeQueryResult<TaxonomyNodeView>({})) as ReturnType<
            typeof taxonomyViewQueries.useTaxonomyNodeViewQuery
          >)
        : (makeQueryResult<TaxonomyNodeView>({}) as ReturnType<
            typeof taxonomyViewQueries.useTaxonomyNodeViewQuery
          >),
  );

  mockUseTaxonomyLeafNodeDetailsQuery.mockImplementation(
    (
      leafId: number,
      nodeIds: readonly number[],
      { enabled }: { readonly enabled?: boolean },
    ) => {
      leafDetailCalls.push({
        enabled: enabled ?? true,
        leafId,
        nodeIds: [...nodeIds],
      });

      return (
        (enabled ?? true)
          ? (leafDetailQueryStates.get(leafDetailStateKey(leafId, nodeIds)) ??
            makeQueryResult<TaxonomyLeafNodeDetailsResponse>({}))
          : makeQueryResult<TaxonomyLeafNodeDetailsResponse>({})
      ) as ReturnType<
        typeof taxonomyViewQueries.useTaxonomyLeafNodeDetailsQuery
      >;
    },
  );
});

afterEach(() => {
  cleanup();
});

describe("leaf hydration viewport helpers", () => {
  it("converts the current viewport into flow-space bounds", () => {
    expect(
      flowBoundsFromViewport(
        { x: -140.4, y: -90, zoom: BUBBLE_ACTIVATION_ZOOM },
        { height: 900, width: 1404 },
        0,
      ),
    ).toEqual({
      bottom: 1164.7058823529412,
      left: 165.1764705882353,
      right: 1816.9411764705883,
      top: 105.88235294117648,
    });
  });

  it("selects only viewport-plus-overscan leaf node ids for hydration", () => {
    expect(
      selectLeafHydrationNodeIds(
        [
          {
            data: {
              depth: 0,
              graphNodeId: 10,
              label: "",
              renderMode: "point",
              scope: "inner",
              targetNodeId: null,
              tooltip: "",
            },
            id: "card-10",
            position: { x: 620, y: 400 },
            style: { borderRadius: "68px", height: 68, width: 68 },
            type: "bubble",
          },
          {
            data: {
              depth: 0,
              graphNodeId: 11,
              label: "",
              renderMode: "point",
              scope: "outer",
              targetNodeId: null,
              tooltip: "",
            },
            id: "card-11",
            position: { x: 2200, y: 400 },
            style: { borderRadius: "52px", height: 52, width: 52 },
            type: "bubble",
          },
        ],
        { x: -560, y: -360, zoom: 1 },
        { height: 900, width: 1404 },
        40,
      ),
    ).toEqual([10]);
  });
});

describe("TaxonomyViewPage shell contracts", () => {
  it("renders the approved figma shell for the root view", () => {
    setRootQueryState(
      makeQueryResult({
        data: makeRootView({
          children: [
            {
              depth: 0,
              descendant_card_count: 3,
              id: 1,
              is_leaf: false,
              name: "Math",
              parent_id: null,
            },
          ],
        }),
      }),
    );

    render(<TaxonomyViewPage />);

    expect(screen.getByTestId("taxonomy-shell-body")).toHaveClass("p-6");
    expect(screen.getByText("Knowledge Graph")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GitHub" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Login" })).toBeDisabled();
    expect(screen.getByLabelText("taxonomy flow canvas")).toBeInTheDocument();
    expect(screen.getByLabelText("taxonomy breadcrumb")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-canvas-panel")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-canvas-panel")).toHaveClass(
      "absolute",
      "inset-0",
    );
    expect(screen.getByTestId("taxonomy-breadcrumb-overlay")).toHaveAttribute(
      "data-breadcrumb-style",
      "inline-text",
    );
    expect(screen.queryByText("Taxonomy drill-down")).not.toBeInTheDocument();
  });

  it("shows loading inside the persistent canvas overlay", () => {
    setRootQueryState(
      makeQueryResult({
        isPending: true,
      }),
    );

    const { rerender } = render(<TaxonomyViewPage />);

    const canvas = screen.getByTestId("taxonomy-canvas-shell");
    expect(
      within(canvas).getByText("Loading taxonomy view"),
    ).toBeInTheDocument();
    expect(
      within(canvas).getByLabelText("taxonomy breadcrumb"),
    ).toBeInTheDocument();

    setRootQueryState(
      makeQueryResult({
        data: makeRootView({
          children: [],
        }),
      }),
    );
    rerender(<TaxonomyViewPage />);

    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
  });

  it("shows error inside the same canvas overlay", () => {
    setRootQueryState(
      makeQueryResult({
        error: new Error("boom"),
        isError: true,
      }),
    );

    render(<TaxonomyViewPage />);

    const canvas = screen.getByTestId("taxonomy-canvas-shell");
    expect(within(canvas).getByRole("alert")).toHaveTextContent("boom");
  });

  it("keeps branch, leaf, and breadcrumb navigation working inside the shell", () => {
    setRootQueryState(
      makeQueryResult({
        data: makeRootView({
          children: [
            {
              depth: 0,
              descendant_card_count: 3,
              id: 1,
              is_leaf: false,
              name: "Math",
              parent_id: null,
            },
          ],
        }),
      }),
    );
    setNodeQueryState(
      1,
      makeQueryResult({
        data: makeBranchNodeView({
          breadcrumb: [
            {
              depth: 0,
              id: 1,
              is_leaf: false,
              name: "Math",
              parent_id: null,
            },
          ],
          children: [
            {
              depth: 1,
              descendant_card_count: 2,
              id: 2,
              is_leaf: true,
              name: "Algebra",
              parent_id: 1,
            },
          ],
          current_node: {
            depth: 0,
            id: 1,
            is_leaf: false,
            name: "Math",
            parent_id: null,
          },
        }),
      }),
    );
    setNodeQueryState(
      2,
      makeQueryResult({
        data: makeLeafNodeView({
          breadcrumb: [
            {
              depth: 0,
              id: 1,
              is_leaf: false,
              name: "Math",
              parent_id: null,
            },
            {
              depth: 1,
              id: 2,
              is_leaf: true,
              name: "Algebra",
              parent_id: 1,
            },
          ],
          current_node: {
            depth: 1,
            id: 2,
            is_leaf: true,
            name: "Algebra",
            parent_id: 1,
          },
          edges: [
            {
              id: "e-1",
              source_node_id: 10,
              strength: 0.8,
              target_node_id: 11,
            },
          ],
          nodes: [
            {
              id: 10,
              scope: "inner",
            },
            {
              id: 11,
              scope: "outer",
            },
          ],
        }),
      }),
    );
    setLeafDetailQueryState(
      2,
      [10, 11],
      makeQueryResult({
        data: {
          nodes: [
            { content: "Equation content", id: 10, title: "Equation" },
            { content: "Proof content", id: 11, title: "Proof" },
          ],
        },
      }),
    );

    render(<TaxonomyViewPage />);

    const canvas = screen.getByTestId("taxonomy-canvas-shell");
    expect(screen.getByRole("button", { name: "Root" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    const rootBranchNode = within(canvas)
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(rootBranchNode).not.toBeNull();
    expect(rootBranchNode).toHaveAttribute("data-bubble-family", "taxonomy");
    expect(
      within(rootBranchNode as HTMLElement).queryByText("Open"),
    ).not.toBeInTheDocument();

    fireEvent.click(within(rootBranchNode as HTMLElement).getByText("Math"));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
    expect(screen.getByRole("button", { name: "Root" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getByRole("button", { name: "Math" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    const branchNode = within(canvas)
      .getByText("Algebra")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(within(branchNode as HTMLElement).getByText("Algebra"));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
    expect(
      within(canvas).getByTestId("reactflow-edge-e-1"),
    ).toBeInTheDocument();
    expect(within(canvas).queryByText("Equation")).not.toBeInTheDocument();
    expect(
      within(canvas).queryByTestId("taxonomy-bubble-disclosure"),
    ).not.toBeInTheDocument();
    expect(within(canvas).getAllByTestId("taxonomy-point-node")).toHaveLength(
      2,
    );
    expect(
      leafDetailCalls.some(
        (call) => call.leafId === 2 && call.enabled && call.nodeIds.length > 0,
      ),
    ).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: "Zoomed viewport" }));
    expect(screen.getByText("Equation")).toBeInTheDocument();
    expect(
      leafDetailCalls.some(
        (call) =>
          call.leafId === 2 &&
          call.enabled &&
          call.nodeIds.includes(10) &&
          call.nodeIds.includes(11),
      ),
    ).toBe(true);
    const initialHydrationCallCount = leafDetailCalls.filter(
      (call) =>
        call.leafId === 2 &&
        call.enabled &&
        call.nodeIds.includes(10) &&
        call.nodeIds.includes(11),
    ).length;

    const hydratedLeafNode = within(canvas)
      .getByText("Equation")
      .closest("[data-node-scope='inner']");

    expect(hydratedLeafNode).not.toBeNull();
    fireEvent.mouseEnter(hydratedLeafNode as HTMLElement);
    expect(
      within(canvas).getByTestId("taxonomy-bubble-disclosure"),
    ).toHaveTextContent("Equation content");
    fireEvent.mouseLeave(hydratedLeafNode as HTMLElement);
    expect(
      within(canvas).queryByTestId("taxonomy-bubble-disclosure"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Overview viewport" }));
    expect(within(canvas).queryByText("Equation")).not.toBeInTheDocument();
    expect(within(canvas).getAllByTestId("taxonomy-point-node")).toHaveLength(
      2,
    );

    fireEvent.click(screen.getByRole("button", { name: "Zoomed viewport" }));
    expect(within(canvas).getByText("Equation")).toBeInTheDocument();
    expect(
      leafDetailCalls.filter(
        (call) =>
          call.leafId === 2 &&
          call.enabled &&
          call.nodeIds.includes(10) &&
          call.nodeIds.includes(11),
      ),
    ).toHaveLength(initialHydrationCallCount);

    fireEvent.click(within(canvas).getByRole("button", { name: "Root" }));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
  });
});
