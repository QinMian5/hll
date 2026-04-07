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
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", () => ({
  Background: () => <div data-testid="reactflow-background" />,
  ReactFlow: ({ children, nodes, onNodeClick }: MockReactFlowProps) => (
    <div data-testid="reactflow-mock">
      {nodes.map((node) => (
        <button
          key={node.id}
          onClick={() => onNodeClick?.({}, node)}
          type="button"
        >
          {String(node.data.label)}
        </button>
      ))}
      {children}
    </div>
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
  readonly nodes: Array<{
    readonly data: { readonly label: string };
    readonly id: string;
  }>;
  readonly onNodeClick?: (
    event: unknown,
    node: {
      readonly data: { readonly label: string };
      readonly id: string;
    },
  ) => void;
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

beforeEach(() => {
  rootQueryState = makeQueryResult({
    data: makeRootView({}),
  });
  nodeQueryStates = new Map<number, MockQueryResult<TaxonomyNodeView>>();

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
});

afterEach(() => {
  cleanup();
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

    expect(screen.getByText("Knowledge Graph")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GitHub" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Login" })).toBeDisabled();
    expect(screen.getByLabelText("taxonomy flow canvas")).toBeInTheDocument();
    expect(screen.getByLabelText("taxonomy breadcrumb")).toBeInTheDocument();
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
          nodes: [
            {
              content: "Equation content",
              id: 10,
              scope: "inner",
              title: "Equation",
            },
          ],
        }),
      }),
    );

    render(<TaxonomyViewPage />);

    const canvas = screen.getByTestId("taxonomy-canvas-shell");
    fireEvent.click(screen.getByRole("button", { name: "Math" }));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
    expect(
      within(canvas).getByRole("button", { name: "Algebra" }),
    ).toBeInTheDocument();

    fireEvent.click(within(canvas).getByRole("button", { name: "Algebra" }));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
    expect(within(canvas).getByText("Equation")).toBeInTheDocument();

    fireEvent.click(within(canvas).getByRole("button", { name: "Root" }));
    expect(screen.getByTestId("taxonomy-canvas-shell")).toBe(canvas);
  });
});
