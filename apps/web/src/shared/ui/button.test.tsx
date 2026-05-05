// abstract: Component-level tests for the shared shadcn-style button primitive.
// out_of_scope: Feature-specific button workflows or form submission behavior.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { Button } from "./button";

afterEach(() => {
  cleanup();
});

describe("Button", () => {
  it("projects the default Figma Button states to semantic Tailwind tokens", () => {
    render(<Button>Submit</Button>);

    const button = screen.getByRole("button", { name: "Submit" });

    expect(button).toHaveClass(
      "bg-knowledge-brand",
      "hover:bg-knowledge-brand-hover",
      "active:bg-knowledge-brand-pressed",
      "disabled:bg-knowledge-brand-disabled",
      "focus-visible:outline-knowledge-brand",
    );
  });

  it("projects secondary and danger variants with pressed and disabled states", () => {
    render(
      <>
        <Button variant="secondary">Cancel</Button>
        <Button variant="danger">Delete</Button>
        <Button disabled variant="danger">
          Disabled delete
        </Button>
      </>,
    );

    expect(screen.getByRole("button", { name: "Cancel" })).toHaveClass(
      "bg-knowledge-surface-control",
      "hover:bg-knowledge-surface-control-hover",
      "active:bg-knowledge-surface-control-pressed",
      "disabled:bg-knowledge-muted-surface",
    );
    expect(screen.getByRole("button", { name: "Delete" })).toHaveClass(
      "bg-knowledge-danger",
      "hover:bg-knowledge-danger-hover",
      "active:bg-knowledge-danger-pressed",
    );
    expect(screen.getByRole("button", { name: "Disabled delete" })).toHaveClass(
      "disabled:bg-knowledge-muted-surface",
      "disabled:text-knowledge-text-muted",
      "disabled:hover:bg-knowledge-muted-surface",
    );
  });

  it("keeps destructive as a compatibility alias for the danger variant", () => {
    render(<Button variant="destructive">Remove</Button>);

    expect(screen.getByRole("button", { name: "Remove" })).toHaveClass(
      "bg-knowledge-danger",
      "hover:bg-knowledge-danger-hover",
      "active:bg-knowledge-danger-pressed",
    );
  });
});
