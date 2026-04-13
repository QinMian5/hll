// abstract: Contract tests for the shared knowledge-card rich-text renderer.
// out_of_scope: Feature-specific card layout and route-level integration behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen, within } from "@testing-library/react";
import { Profiler, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeRichText } from "./knowledge-rich-text";

afterEach(() => {
  cleanup();
});

describe("KnowledgeRichText", () => {
  it("normalizes inline math and renders common content markdown", () => {
    render(
      <KnowledgeRichText
        text={"Energy \\(E=mc^2\\)\n\n- conserved\n\n`scalar`"}
        variant="content"
      />,
    );

    expect(document.querySelector(".katex")).not.toBeNull();
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.getByText("conserved")).toBeInTheDocument();
    expect(screen.getByText("scalar").tagName).toBe("CODE");
  });

  it("normalizes display math blocks authored with square-bracket delimiters", () => {
    render(
      <KnowledgeRichText
        text={
          "A derivation gives \\[(\\hbar^2\\,\\partial_t^2+c^2\\hbar^2\\nabla^2+m^2c^4)\\psi=0\\] before the final simplification."
        }
        variant="content"
      />,
    );

    const content = screen.getByTestId("knowledge-rich-text-content");

    expect(content).toHaveTextContent("A derivation gives");
    expect(content.querySelector(".katex-display")).not.toBeNull();
    expect(content).toHaveTextContent("before the final simplification.");
    expect(content).not.toHaveTextContent("\\[");
  });

  it("keeps title rendering compact instead of introducing paragraph blocks", () => {
    render(<KnowledgeRichText text={"Energy \\(E=mc^2\\)"} variant="title" />);

    const title = screen.getByTestId("knowledge-rich-text-title");

    expect(document.querySelector(".katex")).not.toBeNull();
    expect(within(title).queryByText("Energy")).toBeInTheDocument();
    expect(title.querySelector("p")).toBeNull();
  });

  it("does not interpret raw html as rendered markup", () => {
    render(
      <KnowledgeRichText
        text={"Literal <em>unsafe</em> html"}
        variant="content"
      />,
    );

    const content = screen.getByTestId("knowledge-rich-text-content");

    expect(content.querySelector("em")).toBeNull();
    expect(content).toHaveTextContent("Literal unsafe html");
  });

  it("does not rerender the rich-text subtree when parent state changes without text changes", () => {
    const onRender = vi.fn();

    function Harness() {
      const [count, setCount] = useState(0);

      return (
        <>
          <button
            onClick={() => setCount((currentCount) => currentCount + 1)}
            type="button"
          >
            Rerender
          </button>
          <span>{count}</span>
          <Profiler id="knowledge-rich-text" onRender={onRender}>
            <KnowledgeRichText
              text={"Energy \\(E=mc^2\\)\n\n- conserved"}
              variant="content"
            />
          </Profiler>
        </>
      );
    }

    render(<Harness />);

    screen.getByRole("button", { name: "Rerender" }).click();

    expect(onRender).toHaveBeenCalledTimes(1);
  });
});
