// abstract: Figma-aligned related-result item button for the Search route.
// out_of_scope: Search page query state and backend related-title generation.

import { ArrowRight, ChevronRight } from "lucide-react";
import { Skeleton } from "../../../shared/ui/skeleton";

interface RelatedResultItemProps {
  readonly onSelect: (title: string) => void;
  readonly title: string;
}

export function RelatedResultItem({ onSelect, title }: RelatedResultItemProps) {
  return (
    <button
      className="group/related-result relative flex min-h-search-related-result-height w-full shrink-0 items-center gap-search-related-result-gap rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-card-muted px-search-related-result-padding-x py-search-related-result-padding-y text-left text-knowledge-search-input font-medium text-knowledge-text-default transition-[opacity,transform,border-color,background-color] duration-150 will-change-transform group-hover/search-suggestions-list:opacity-80 group-focus-within/search-suggestions-list:opacity-80 hover:z-10 hover:-translate-y-0.5 hover:scale-[var(--scale-search-related-result-hover)] hover:border-knowledge-brand-hover-soft hover:bg-knowledge-surface-card hover:opacity-100 focus-visible:z-10 focus-visible:-translate-y-0.5 focus-visible:scale-[var(--scale-search-related-result-hover)] focus-visible:border-knowledge-brand-hover-soft focus-visible:bg-knowledge-surface-card focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
      data-testid="related-result-item"
      onClick={() => {
        onSelect(title);
      }}
      type="button"
    >
      <span
        className="min-w-0 flex-1 whitespace-normal break-words text-left"
        data-testid="related-result-item-title"
      >
        {title}
      </span>
      <span
        aria-hidden="true"
        className="relative flex size-search-related-result-icon-size shrink-0 items-center justify-center"
        data-testid="related-result-item-icon"
      >
        <ChevronRight
          aria-hidden="true"
          className="size-4 text-knowledge-text-muted transition-opacity duration-150 group-hover/related-result:opacity-0 group-focus-visible/related-result:opacity-0"
          strokeWidth={2}
        />
        <span
          className="absolute inset-0 flex items-center justify-center rounded-full border border-white/90 bg-knowledge-brand text-knowledge-text-inverse opacity-0 shadow-knowledge-card-hover-affordance transition-opacity duration-150 group-hover/related-result:opacity-100 group-focus-visible/related-result:opacity-100"
          data-testid="related-result-item-hover-icon"
        >
          <ArrowRight aria-hidden="true" className="size-3" strokeWidth={1.5} />
        </span>
      </span>
    </button>
  );
}

export function RelatedResultItemSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex min-h-search-related-result-height w-full shrink-0 items-center justify-between gap-search-related-result-gap rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-card-muted px-search-related-result-padding-x py-search-related-result-padding-y"
      data-testid="related-result-item-skeleton"
    >
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1 overflow-hidden">
        <Skeleton className="h-3 w-[58%] max-w-36 shrink-0" />
        <Skeleton className="h-2 w-[40%] max-w-24 shrink-0" />
      </div>
      <Skeleton className="size-search-related-result-icon-size shrink-0" />
    </div>
  );
}
