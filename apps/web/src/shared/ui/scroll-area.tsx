// abstract: Minimal shadcn-style scroll area wrapper with viewport-owned scrolling.
// out_of_scope: Virtualization, custom drag handles, and scroll synchronization.

import type { HTMLAttributes } from "react";

import { cn } from "../utils";

interface ScrollAreaProps extends HTMLAttributes<HTMLDivElement> {
  readonly viewportClassName?: string;
}

export function ScrollArea({
  children,
  className,
  viewportClassName,
  ...props
}: ScrollAreaProps) {
  return (
    <div className={cn("min-h-0 overflow-hidden", className)} {...props}>
      <div
        className={cn(
          "h-full overflow-auto pr-[var(--scroll-area-padding-right,0.5rem)] [scrollbar-color:rgba(127,145,179,0.9)_rgba(222,230,244,1)] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-[var(--scroll-area-scrollbar-width,0.25rem)] [&::-webkit-scrollbar-track]:rounded-full [&::-webkit-scrollbar-track]:bg-[#dee6f4] [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[rgba(127,145,179,0.9)]",
          viewportClassName,
        )}
      >
        {children}
      </div>
    </div>
  );
}
