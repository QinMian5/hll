// abstract: Search result card with rich-text title and body rendering.
// out_of_scope: Search route state management, search input handling, and backend query orchestration.

import { ArrowUpRight, SquarePen } from "lucide-react";
import { KnowledgeRichText } from "../../../shared/ui/knowledge-rich-text";

export interface SearchResultCardEditPayload {
  readonly content: string;
  readonly currentVersion: number;
  readonly nodeId: number;
  readonly title: string;
}

interface SearchResultCardProps {
  readonly content: string;
  readonly currentVersion: number;
  readonly nodeId: number;
  readonly onSearchTitle: (title: string) => void;
  readonly onSuggestEdit: (card: SearchResultCardEditPayload) => void;
  readonly title: string;
}

export function SearchResultCard({
  content,
  currentVersion,
  nodeId,
  onSearchTitle,
  onSuggestEdit,
  title,
}: SearchResultCardProps) {
  function handleSearchActivation() {
    onSearchTitle(title);
  }

  const searchHref = `/search?q=${encodeURIComponent(title)}`;

  return (
    <div
      className="group/card relative flex h-search-result-card-height w-full shrink-0 flex-col items-start gap-2 overflow-visible rounded-lg border border-knowledge-border-card bg-knowledge-surface-card px-2 py-2 shadow-none transition-[opacity,transform,border-color] duration-150 will-change-transform group-hover/search-results-grid:opacity-80 hover:z-10 hover:-translate-y-1 hover:scale-[var(--scale-search-result-card-hover)] hover:border-knowledge-brand-hover-soft hover:opacity-100 focus-within:z-10 focus-within:-translate-y-1 focus-within:scale-[var(--scale-search-result-card-hover)] focus-within:border-knowledge-brand-hover-soft focus-within:opacity-100"
      data-testid="search-result-card"
    >
      <span
        aria-hidden="true"
        className="pointer-events-none absolute -top-2 -right-3 z-20 flex size-6 items-center justify-center rounded-full border border-white/90 bg-knowledge-brand text-knowledge-text-inverse opacity-0 shadow-knowledge-card-hover-affordance transition-opacity duration-150 group-hover/card:opacity-100 group-focus-within/card:opacity-100"
        data-testid="search-result-card-search-hint"
      >
        <ArrowUpRight aria-hidden="true" className="size-3" strokeWidth={1.5} />
      </span>
      <div
        className="flex min-h-10 w-full shrink-0 items-start justify-start gap-2 md:min-h-6 [&_[data-testid=knowledge-rich-text-title]]:text-knowledge-rich-title-compact [&_[data-testid=knowledge-rich-text-title]]:font-semibold md:[&_[data-testid=knowledge-rich-text-title]]:text-knowledge-rich-title"
        data-testid="search-result-card-header"
      >
        <a
          aria-label={`Search for ${title}`}
          className="min-w-0 flex-1 whitespace-normal break-words rounded-md text-left no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
          data-testid="search-result-card-title-area"
          href={searchHref}
          onClick={(event) => {
            event.preventDefault();
            handleSearchActivation();
          }}
        >
          <span
            className="block min-w-0 whitespace-normal break-words [&_[data-testid=knowledge-rich-text-title]]:whitespace-normal"
            data-testid="search-result-card-title-track"
          >
            <KnowledgeRichText text={title} variant="title" />
          </span>
        </a>
        <button
          aria-label={`Suggest edit for ${title}`}
          className="relative z-30 flex size-6 shrink-0 items-center justify-center rounded-md text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-accent-soft hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
          onClick={(event) => {
            event.stopPropagation();
            onSuggestEdit({ content, currentVersion, nodeId, title });
          }}
          title="Suggest edit"
          type="button"
        >
          <SquarePen aria-hidden="true" className="size-4" strokeWidth={2} />
        </button>
      </div>
      <div className="h-px w-full shrink-0 bg-knowledge-divider-subtle" />
      <div
        className="relative min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden [scrollbar-color:var(--color-knowledge-scrollbar-thumb)_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-knowledge-scrollbar-width [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-knowledge-scrollbar-thumb [&::-webkit-scrollbar-track]:bg-transparent [&_[data-testid=knowledge-rich-text-content]]:text-knowledge-rich-content-compact md:[&_[data-testid=knowledge-rich-text-content]]:text-knowledge-rich-content"
        data-testid="search-result-card-content"
      >
        <a
          aria-label={`Search body for ${title}`}
          className="absolute inset-0 z-10 cursor-pointer rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
          href={searchHref}
          onClick={(event) => {
            event.preventDefault();
            handleSearchActivation();
          }}
        >
          <span className="sr-only">Search body for {title}</span>
        </a>
        <div className="pointer-events-none relative z-0">
          <KnowledgeRichText text={content} variant="content" />
        </div>
      </div>
    </div>
  );
}
