// abstract: Contract tests for shared text input primitives.
// out_of_scope: Feature-specific form validation and route-level field composition.

import "@testing-library/jest-dom/vitest";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { FieldControl } from "./field-control";
import { Input } from "./input";
import { Textarea } from "./textarea";

afterEach(() => {
  cleanup();
});

describe("shared text field primitives", () => {
  it("keeps read-only fields selectable while applying the readonly visual state", () => {
    render(
      <>
        <FieldControl data-testid="readonly-title-control">
          <Input aria-label="Readonly title" readOnly value="Title" />
        </FieldControl>
        <FieldControl data-testid="readonly-content-control">
          <Textarea aria-label="Readonly content" readOnly value="Content" />
        </FieldControl>
      </>,
    );

    expect(screen.getByLabelText("Readonly title")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Readonly title")).not.toBeDisabled();
    expect(screen.getByLabelText("Readonly title")).toHaveClass(
      "read-only:cursor-text",
      "read-only:text-knowledge-text-default",
    );
    expect(screen.getByLabelText("Readonly content")).toHaveAttribute(
      "readonly",
    );
    expect(screen.getByLabelText("Readonly content")).not.toBeDisabled();
    expect(screen.getByLabelText("Readonly content")).toHaveClass(
      "read-only:cursor-text",
      "read-only:text-knowledge-text-default",
    );
    expect(screen.getByTestId("readonly-title-control")).toHaveClass(
      "has-[:read-only]:bg-knowledge-surface-input-readonly",
      "has-[:read-only]:border-knowledge-border-input-readonly",
    );
    expect(screen.getByTestId("readonly-content-control")).toHaveClass(
      "has-[:read-only]:bg-knowledge-surface-input-readonly",
      "has-[:read-only]:border-knowledge-border-input-readonly",
    );
  });
});
