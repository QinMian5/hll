// abstract: Search-specific UI components for the routed search experience.
// out_of_scope: Search ranking, backend integration, and URL state ownership.

import { Search } from "lucide-react";
import type { FormEventHandler } from "react";

import { Input } from "../../../shared/ui";

interface SearchFieldProps {
  readonly defaultValue: string;
  readonly onSubmit: FormEventHandler<HTMLFormElement>;
  readonly placeholder: string;
  readonly size: "compact" | "hero";
}

const fieldFormClasses = {
  compact: "w-[760px] max-w-full shrink-0",
  hero: "w-[760px] max-w-full shrink-0",
} as const;

const fieldContainerClasses = {
  compact:
    "h-12 rounded-2xl border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] py-[10px] pl-6 pr-[10px] shadow-[0_16px_36px_rgba(95,123,185,0.1)]",
  hero: "h-[72px] rounded-[28px] border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] py-[10px] pl-6 pr-[10px] shadow-[0_16px_36px_rgba(95,123,185,0.1)]",
} as const;

const inputClasses = {
  compact:
    "h-full text-[16px] leading-6 font-medium text-[rgba(20,28,46,0.98)] placeholder:text-[rgba(99,114,143,0.72)]",
  hero: "h-full text-[18px] leading-6 font-normal text-[rgba(20,28,46,0.98)] placeholder:text-[rgba(99,114,143,0.72)]",
} as const;

const searchButtonClasses = {
  compact:
    "flex size-11 shrink-0 items-center justify-center rounded-2xl bg-transparent p-0 text-[rgba(20,28,46,0.98)] shadow-none hover:bg-transparent hover:text-[rgba(20,28,46,0.98)]",
  hero: "flex size-11 shrink-0 items-center justify-center rounded-2xl bg-transparent p-0 text-[rgba(20,28,46,0.98)] shadow-none hover:bg-transparent hover:text-[rgba(20,28,46,0.98)]",
} as const;

const searchIconClasses = {
  compact: "h-5 w-5",
  hero: "h-5 w-5",
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
    <div className="flex h-full min-h-0 w-full flex-col items-start gap-[14px] overflow-clip rounded-[24px] border border-[rgba(223,232,247,0.98)] bg-[rgba(255,255,255,0.92)] p-5 shadow-[0_14px_28px_rgba(95,123,185,0.1)]">
      <div className="flex h-6 w-full flex-col items-center justify-center">
        <div className="w-full text-[16px] leading-[22px] font-medium text-[rgba(18,23,41,0.96)]">
          {title}
        </div>
      </div>
      <div className="h-px w-full shrink-0 bg-[#dee6f4]" />
      <div className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden">
        <div className="flex min-h-full w-full flex-col items-start">
          <p className="m-0 text-[14px] leading-[22px] font-normal text-[rgba(61,75,103,0.82)]">
            {content}
          </p>
        </div>
      </div>
    </div>
  );
}
