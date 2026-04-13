// abstract: Minimal shadcn-style card primitives for composable panel layouts.
// out_of_scope: Domain-specific content rendering and interaction logic.

import type { HTMLAttributes } from "react";

import { cn } from "../utils";

type DivProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "rounded-[24px] border border-[rgba(223,232,247,0.98)] bg-[rgba(255,255,255,0.92)] shadow-[0_14px_28px_rgba(95,123,185,0.1)]",
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
        "text-[16px] leading-[22px] font-medium text-[rgba(18,23,41,0.96)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={cn("min-h-0 flex-1", className)} {...props} />;
}
