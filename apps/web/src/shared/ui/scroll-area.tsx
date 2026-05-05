// abstract: Minimal shadcn-style scroll area wrapper with viewport-owned scrolling.
// out_of_scope: Virtualization, custom drag handles, and scroll synchronization.

import { type HTMLAttributes, useLayoutEffect, useRef } from "react";

import { cn } from "../utils";

interface ScrollAreaProps extends HTMLAttributes<HTMLDivElement> {
  readonly resetScrollKey?: string | number;
  readonly viewportFillsContainer?: boolean;
  readonly viewportClassName?: string;
}

export function ScrollArea({
  children,
  className,
  resetScrollKey,
  viewportFillsContainer = true,
  viewportClassName,
  ...props
}: ScrollAreaProps) {
  const viewportRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (resetScrollKey === undefined || viewportRef.current === null) {
      return;
    }

    viewportRef.current.scrollTop = 0;
  }, [resetScrollKey]);

  return (
    <div className={cn("min-h-0 overflow-hidden", className)} {...props}>
      <div
        ref={viewportRef}
        className={cn(
          viewportFillsContainer ? "h-full" : undefined,
          "overflow-auto pr-[var(--scroll-area-padding-right,0.5rem)] [scrollbar-color:var(--scroll-area-thumb-color)_var(--scroll-area-track-color)] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-[var(--scroll-area-scrollbar-width,0.25rem)] [&::-webkit-scrollbar-track]:rounded-full [&::-webkit-scrollbar-track]:bg-[var(--scroll-area-track-color)] [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-[var(--scroll-area-thumb-color)]",
          viewportClassName,
        )}
      >
        {children}
      </div>
    </div>
  );
}
