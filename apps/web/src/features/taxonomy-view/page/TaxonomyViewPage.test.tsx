// abstract: Behavior tests for the taxonomy page shell and branch/leaf renderer routing.
// out_of_scope: Browser-level rendering fidelity and backend query execution.

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
  }: {
    readonly leafView: { readonly current_node: { readonly name: string } };
  }) => (
    <div data-testid="taxonomy-leaf-renderer">{leafView.current_node.name}</div>
  ),
}));

vi.mock("../data/taxonomyViewQueries", () => ({
  useTaxonomyNodeViewQuery: vi.fn(),
  useTaxonomyRootViewQuery: vi.fn(),
}));

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
      readonly renderMode?: "bubble" | "card" | "point";
      readonly scope?: "branch" | "inner" | "outer";
      readonly targetNodeId?: number | null;
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

let rootQueryState: MockQueryResult<TaxonomyRootView>;
let nodeQueryStates: Map<number, MockQueryResult<TaxonomyNodeView>>;

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
    },
    edges: [[10, 11, 0.8]],
    node_kind: "leaf",
    nodes: [
      { id: 10, scope: "inner" },
      { id: 11, scope: "outer" },
    ],
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
    },
    node_kind: "branch",
    ...overrides,
  } as TaxonomyNodeView;
}

beforeEach(() => {
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
        },
      ],
    }),
  });
  nodeQueryStates = new Map([
    [
      1,
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
  mockUseTaxonomyNodeViewQuery.mockImplementation((nodeId) => {
    const result = nodeQueryStates.get(nodeId);
    return (result ??
      makeQueryResult({ isPending: true })) as unknown as ReturnType<
      typeof taxonomyViewQueries.useTaxonomyNodeViewQuery
    >;
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TaxonomyViewPage", () => {
  it("renders the approved full-slot Figma canvas shell without the old panel", () => {
    render(<TaxonomyViewPage />);

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

  it("renders loading and error overlays inside the stable canvas shell", () => {
    rootQueryState = makeQueryResult({ isPending: true });
    mockUseTaxonomyRootViewQuery.mockImplementation(
      () =>
        rootQueryState as unknown as ReturnType<
          typeof taxonomyViewQueries.useTaxonomyRootViewQuery
        >,
    );

    const { rerender } = render(<TaxonomyViewPage />);

    expect(screen.getByTestId("taxonomy-canvas")).toBeInTheDocument();
    expect(screen.getByTestId("taxonomy-loading-overlay")).toBeInTheDocument();

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

    rerender(<TaxonomyViewPage />);

    expect(screen.getByTestId("taxonomy-error-overlay")).toHaveTextContent(
      "Taxonomy root view request failed with status 502.",
    );
  });

  it("renders branch mode on React Flow and drills into leaf mode on the dedicated leaf renderer", async () => {
    render(<TaxonomyViewPage />);

    expect(screen.getByTestId("taxonomy-branch-reactflow")).toBeInTheDocument();
    expect(
      screen.queryByTestId("taxonomy-leaf-renderer"),
    ).not.toBeInTheDocument();

    const branchNode = within(screen.getByTestId("reactflow-mock"))
      .getByText("Math")
      .closest("[data-node-scope='branch']");

    expect(branchNode).not.toBeNull();

    fireEvent.click(branchNode as HTMLElement);

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

  it("renders branch breadcrumbs with Figma chevrons and responsive offsets", async () => {
    nodeQueryStates.set(
      1,
      makeQueryResult({
        data: makeBranchNodeView({
          breadcrumb: [
            {
              depth: 0,
              id: 2,
              is_leaf: false,
              name: "Science",
              parent_id: null,
            },
            {
              depth: 1,
              id: 1,
              is_leaf: false,
              name: "Mathematics",
              parent_id: 2,
            },
          ],
          current_node: {
            depth: 1,
            id: 1,
            is_leaf: false,
            name: "Mathematics",
            parent_id: 2,
          },
        }),
      }),
    );

    render(<TaxonomyViewPage />);

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
});
