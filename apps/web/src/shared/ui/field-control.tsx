// abstract: Shared field-control frame for input and textarea primitives.
// out_of_scope: Form state orchestration and feature-specific field labels.

import type { HTMLAttributes } from "react";

import { cn } from "../utils";

export type FieldControlProps = HTMLAttributes<HTMLDivElement>;

export function FieldControl({
  children,
  className,
  ...props
}: FieldControlProps) {
  return (
    <div
      className={cn(
        "flex w-full items-center justify-center rounded-knowledge-control border border-knowledge-border-control bg-knowledge-surface-input px-knowledge-dialog-input-padding-x py-knowledge-dialog-input-padding-y shadow-knowledge-input",
        "has-[:read-only]:border-knowledge-border-input-readonly has-[:read-only]:bg-knowledge-surface-input-readonly has-[:read-only]:shadow-none",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
