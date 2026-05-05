// abstract: Figma-aligned loading skeleton for Search result cards.
// out_of_scope: Loaded card rich-text rendering and interactive card behavior.

import { Skeleton } from "../../../shared/ui/skeleton";

export function SearchResultCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="relative flex h-search-result-card-height w-full shrink-0 flex-col items-start gap-2 overflow-hidden rounded-lg border border-knowledge-border-card bg-knowledge-surface-card p-2"
      data-testid="search-result-card-skeleton"
    >
      <div className="flex h-6 w-full shrink-0 items-center justify-between overflow-hidden">
        <Skeleton className="h-4 w-[52%] max-w-[184px] shrink-0" />
        <Skeleton className="size-6 shrink-0" />
      </div>
      <Skeleton className="h-px w-full shrink-0" />
      <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-3 overflow-hidden pt-2">
        <Skeleton className="h-3 w-[90%] max-w-[304px] shrink-0" />
        <Skeleton className="h-3 w-[98%] max-w-[328px] shrink-0" />
        <Skeleton className="h-3 w-[84%] max-w-[280px] shrink-0" />
        <Skeleton className="h-3 w-[64%] max-w-[216px] shrink-0" />
      </div>
    </div>
  );
}
