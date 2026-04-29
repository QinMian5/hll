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
  compact: "w-full max-w-[760px] shrink-0",
  hero: "w-full max-w-[760px] shrink-0",
} as const;

const fieldContainerClasses = {
  compact:
    "h-12 rounded-lg border border-[#e5e5e5] bg-white px-4 py-[9.5px] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
  hero: "h-12 rounded-lg border border-[#e5e5e5] bg-white px-4 py-[9.5px] shadow-[0_1px_2px_rgba(0,0,0,0.05)]",
} as const;

const inputClasses = {
  compact:
    "h-5 text-[14px] leading-5 font-normal text-[#0a0a0a] placeholder:text-[#606e87]",
  hero: "h-5 text-[14px] leading-5 font-normal text-[#0a0a0a] placeholder:text-[#606e87]",
} as const;

const searchButtonClasses = {
  compact:
    "flex size-5 shrink-0 items-center justify-center rounded bg-transparent p-0 text-black shadow-none hover:bg-transparent hover:text-black",
  hero: "flex size-5 shrink-0 items-center justify-center rounded bg-transparent p-0 text-black shadow-none hover:bg-transparent hover:text-black",
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
