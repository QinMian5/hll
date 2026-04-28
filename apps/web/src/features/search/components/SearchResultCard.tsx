// abstract: Search result card with rich-text title and body rendering.
// out_of_scope: Search route state management, search input handling, and backend query orchestration.

import { KnowledgeRichText } from "../../../shared/ui/knowledge-rich-text";

interface SearchResultCardProps {
  readonly content: string;
  readonly title: string;
}

export function SearchResultCard({ content, title }: SearchResultCardProps) {
  return (
    <div
      className="flex h-[176px] w-full shrink-0 flex-col items-start gap-3 overflow-hidden rounded-lg border border-[rgba(214,227,247,0.86)] bg-[rgba(255,255,255,0.88)] px-4 pt-4 pb-4 shadow-[0_18px_52px_rgba(107,132,189,0.09)]"
      data-testid="search-result-card"
    >
      <div className="flex h-10 w-full shrink-0 flex-col items-start justify-start overflow-hidden md:h-6 [&_[data-testid=knowledge-rich-text-title]]:text-[15px] [&_[data-testid=knowledge-rich-text-title]]:leading-5 [&_[data-testid=knowledge-rich-text-title]]:font-semibold md:[&_[data-testid=knowledge-rich-text-title]]:text-[16px] md:[&_[data-testid=knowledge-rich-text-title]]:leading-[22px]">
        <div className="w-full">
          <KnowledgeRichText text={title} variant="title" />
        </div>
      </div>
      <div className="h-px w-full shrink-0 bg-[rgba(214,227,247,0.74)]" />
      <div
        className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent [&_[data-testid=knowledge-rich-text-content]]:text-[13px] [&_[data-testid=knowledge-rich-text-content]]:leading-[19px] md:[&_[data-testid=knowledge-rich-text-content]]:text-[14px] md:[&_[data-testid=knowledge-rich-text-content]]:leading-[22px]"
        data-testid="search-result-card-content"
      >
        <KnowledgeRichText text={content} variant="content" />
      </div>
    </div>
  );
}
