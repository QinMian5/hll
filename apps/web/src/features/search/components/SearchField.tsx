// abstract: Search input form control for the routed search experience.
// out_of_scope: Search result rendering, backend integration, and URL state ownership.

import { Search } from "lucide-react";
import type { FormEventHandler } from "react";

import { Input } from "../../../shared/ui/input";

interface SearchFieldProps {
  readonly defaultValue: string;
  readonly onSubmit: FormEventHandler<HTMLFormElement>;
  readonly placeholder: string;
  readonly size: "compact" | "hero";
}

const fieldFormClasses = {
  compact: "w-full max-w-knowledge-search-field-width shrink-0",
  hero: "w-full max-w-knowledge-search-field-width shrink-0",
} as const;

const fieldContainerClasses = {
  compact:
    "h-12 rounded-lg border border-knowledge-border-input bg-knowledge-surface-card-solid px-4 py-2 shadow-knowledge-input-strong",
  hero: "h-12 rounded-lg border border-knowledge-border-input bg-knowledge-surface-card-solid px-4 py-2 shadow-knowledge-input-strong",
} as const;

const inputClasses = {
  compact:
    "h-5 text-knowledge-search-input font-normal text-knowledge-text-strong placeholder:text-knowledge-text-muted",
  hero: "h-5 text-knowledge-search-input font-normal text-knowledge-text-strong placeholder:text-knowledge-text-muted",
} as const;

const searchButtonClasses = {
  compact:
    "flex size-5 shrink-0 items-center justify-center rounded bg-transparent p-0 text-knowledge-text-strong shadow-none hover:bg-transparent hover:text-knowledge-text-strong",
  hero: "flex size-5 shrink-0 items-center justify-center rounded bg-transparent p-0 text-knowledge-text-strong shadow-none hover:bg-transparent hover:text-knowledge-text-strong",
} as const;

const searchIconClasses = {
  compact: "size-4",
  hero: "size-4",
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
