// abstract: Search-specific UI components for the routed search experience.
// out_of_scope: Search ranking, backend integration, and URL state ownership.

import { Search } from "lucide-react";
import type { FormEventHandler } from "react";

import { Input, KnowledgeRichText } from "../../../shared/ui";

interface SearchFieldProps {
  readonly defaultValue: string;
  readonly onSubmit: FormEventHandler<HTMLFormElement>;
  readonly placeholder: string;
  readonly size: "compact" | "hero";
}

const fieldFormClasses = {
  compact: "w-full max-w-[760px] shrink-0",
  hero: "w-full max-w-[760px] shrink-0",
} as const;

const fieldContainerClasses = {
  compact:
    "h-14 rounded-2xl border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] py-2 pl-[18px] pr-2 shadow-[0_16px_36px_rgba(95,123,185,0.1)] md:h-16 md:py-[10px] md:pl-[22px] md:pr-[10px]",
  hero: "h-14 rounded-2xl border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] py-2 pl-[18px] pr-2 shadow-[0_16px_36px_rgba(95,123,185,0.1)] md:h-16 md:py-[10px] md:pl-[22px] md:pr-[10px]",
} as const;

const inputClasses = {
  compact:
    "h-[22px] text-[14px] leading-5 font-normal text-[#131c2d] placeholder:text-[#131c2d] md:h-6 md:text-[16px] md:leading-6",
  hero: "h-[22px] text-[14px] leading-5 font-normal text-[#131c2d] placeholder:text-[#131c2d] md:h-6 md:text-[16px] md:leading-6",
} as const;

const searchButtonClasses = {
  compact:
    "flex size-10 shrink-0 items-center justify-center rounded-2xl bg-transparent p-0 text-black shadow-none hover:bg-transparent hover:text-black md:size-11",
  hero: "flex size-10 shrink-0 items-center justify-center rounded-2xl bg-transparent p-0 text-black shadow-none hover:bg-transparent hover:text-black md:size-11",
} as const;

const searchIconClasses = {
  compact: "size-[18px] md:size-5",
  hero: "size-[18px] md:size-5",
} as const;

export function SearchField({
  defaultValue,
  onSubmit,
  placeholder,
  size,
}: SearchFieldProps) {
  return (
    <form className={fieldFormClasses[size]} onSubmit={onSubmit}>
      <div
        className={`flex items-center justify-between ${fieldContainerClasses[size]}`}
      >
        <Input
          className={inputClasses[size]}
          data-testid="search-input"
          defaultValue={defaultValue}
          name="q"
          placeholder={placeholder}
          type="search"
        />
        <button
          aria-label="Search"
          className={searchButtonClasses[size]}
          data-testid="search-icon-button"
          type="submit"
        >
          <Search
            absoluteStrokeWidth
            className={searchIconClasses[size]}
            strokeWidth={2}
          />
        </button>
      </div>
    </form>
  );
}

interface SearchResultCardProps {
  readonly content: string;
  readonly title: string;
}

export function SearchResultCard({ content, title }: SearchResultCardProps) {
  return (
    <div
      className="flex h-[220px] w-full shrink-0 flex-col items-start gap-2.5 overflow-hidden rounded-lg border border-[rgba(214,227,247,0.86)] bg-[rgba(255,255,255,0.88)] pt-4 pr-3.5 pb-3.5 pl-4 shadow-[0_18px_52px_rgba(107,132,189,0.09)] md:h-[300px] md:gap-3 md:pt-[18px] md:pr-[18px] md:pb-4 md:pl-5 lg:h-[379px]"
      data-testid="search-result-card"
    >
      <div className="flex h-10 w-full shrink-0 flex-col items-start justify-start overflow-hidden md:h-6">
        <div className="w-full">
          <KnowledgeRichText text={title} variant="title" />
        </div>
      </div>
      <div className="h-px w-full shrink-0 bg-[rgba(214,227,247,0.74)]" />
      <div
        className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden"
        data-testid="search-result-card-content"
      >
        <KnowledgeRichText text={content} variant="content" />
      </div>
    </div>
  );
}
