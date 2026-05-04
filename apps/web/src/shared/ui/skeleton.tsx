// abstract: shadcn-style skeleton primitive backed by Knowledge design tokens.
// out_of_scope: Feature-specific loading layouts and shimmer animations.

import type { HTMLAttributes } from "react";

import { cn } from "../utils";

export function Skeleton({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("rounded-full bg-knowledge-skeleton", className)}
      {...props}
    />
  );
}
