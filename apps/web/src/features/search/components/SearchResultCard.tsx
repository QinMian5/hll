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
      className="group/card relative flex h-search-result-card-height w-full shrink-0 flex-col items-start gap-2 overflow-visible rounded-lg border border-[rgba(214,227,247,0.86)] bg-[rgba(255,255,255,0.88)] px-2 py-2 shadow-none transition-[opacity,transform,border-color] duration-150 will-change-transform group-hover/search-results-grid:opacity-80 hover:z-10 hover:-translate-y-1 hover:scale-[1.008] hover:border-[#006bff]/40 hover:opacity-100 focus-within:z-10 focus-within:-translate-y-1 focus-within:scale-[1.008] focus-within:border-[#006bff]/40 focus-within:opacity-100"
      data-testid="search-result-card"
    >
      <span
        aria-hidden="true"
        className="pointer-events-none absolute top-[-8px] right-[-12px] z-20 flex size-6 items-center justify-center rounded-full border border-white/90 bg-[#006bff] text-white opacity-0 shadow-[0_6px_14px_rgba(0,107,255,0.2)] transition-opacity duration-150 group-hover/card:opacity-100 group-focus-within/card:opacity-100"
        data-testid="search-result-card-search-hint"
      >
        <ArrowUpRight aria-hidden="true" className="size-3" strokeWidth={1.5} />
      </span>
      <div
        className="flex min-h-10 w-full shrink-0 items-start justify-start gap-2 md:min-h-6 [&_[data-testid=knowledge-rich-text-title]]:text-[15px] [&_[data-testid=knowledge-rich-text-title]]:leading-5 [&_[data-testid=knowledge-rich-text-title]]:font-semibold md:[&_[data-testid=knowledge-rich-text-title]]:text-[16px] md:[&_[data-testid=knowledge-rich-text-title]]:leading-[22px]"
        data-testid="search-result-card-header"
      >
        <a
          aria-label={`Search for ${title}`}
          className="min-w-0 flex-1 whitespace-normal break-words rounded-md text-left no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
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
          className="relative z-30 flex size-6 shrink-0 items-center justify-center rounded-md text-[#606e87] transition-colors hover:bg-[#eff6ff] hover:text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
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
      <div className="h-px w-full shrink-0 bg-[rgba(214,227,247,0.74)]" />
      <div
        className="relative min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent [&_[data-testid=knowledge-rich-text-content]]:text-[13px] [&_[data-testid=knowledge-rich-text-content]]:leading-[19px] md:[&_[data-testid=knowledge-rich-text-content]]:text-[14px] md:[&_[data-testid=knowledge-rich-text-content]]:leading-[22px]"
        data-testid="search-result-card-content"
      >
        <a
          aria-label={`Search body for ${title}`}
          className="absolute inset-0 z-10 cursor-pointer rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
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
