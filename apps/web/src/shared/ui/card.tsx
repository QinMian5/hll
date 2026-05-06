// abstract: Minimal shadcn-style card primitives for composable panel layouts.
// out_of_scope: Domain-specific content rendering and interaction logic.

import type { HTMLAttributes } from "react";

import { cn } from "../utils";

type DivProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "rounded-knowledge-card-large border border-knowledge-border-card-strong bg-knowledge-surface-card-strong shadow-knowledge-card",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: DivProps) {
  return (
    <div className={cn("flex h-11 w-full flex-col", className)} {...props} />
  );
}

export function CardTitle({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "text-knowledge-rich-title font-medium text-knowledge-text-emphasis",
        className,
      )}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={cn("min-h-0 flex-1", className)} {...props} />;
}
