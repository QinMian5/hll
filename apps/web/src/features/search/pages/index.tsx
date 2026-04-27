// abstract: Routed Search page with Figma-aligned empty and results states owned by URL search state.
// out_of_scope: Backend search integration and ranking semantics.

import { useNavigate, useSearch } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import type { FormEvent } from "react";

import { SearchField, SearchResultCard } from "../components";
import { useSearchQuery } from "../data/searchQueries";

function normalizeQuery(value: string | undefined): string {
  return value?.trim() ?? "";
}

export function SearchPage() {
  const navigate = useNavigate({ from: "/search" });
  const search = useSearch({ from: "/search" }) as { q?: string };
  const query = normalizeQuery(search.q);
  const hasQuery = query.length > 0;
  const searchQuery = useSearchQuery(query, {
    enabled: hasQuery,
  });
  const matchedCards = searchQuery.data?.matched_cards ?? [];
  const connectedTitles = searchQuery.data?.connected_titles ?? [];

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const rawValue = formData.get("q");
    const nextQuery =
      typeof rawValue === "string" ? normalizeQuery(rawValue) : "";

    void navigate({
      search: { q: nextQuery === "" ? undefined : nextQuery },
      to: "/search",
    });
  }

  return (
    <main
      className="flex h-full min-h-0 flex-col"
      data-testid="search-route-page"
    >
      {!hasQuery ? (
        <div
          className="flex h-full min-h-0 w-full items-center justify-center overflow-hidden px-4"
          data-testid="search-empty-state"
        >
          <SearchField
            defaultValue={query}
            onSubmit={handleSubmit}
            placeholder="Search topics, concepts, or questions"
            size="hero"
          />
        </div>
      ) : (
        <div
          className="flex h-full min-h-0 w-full flex-col items-center gap-3 overflow-hidden px-4 py-[18px] md:gap-5 md:px-[34px] md:pt-6 md:pb-9"
          data-testid="search-results-frame"
        >
          <div
            className="relative flex h-14 w-full shrink-0 items-center justify-center md:h-16"
            data-testid="search-results-state"
          >
            <SearchField
              defaultValue={query}
              key={query}
              onSubmit={handleSubmit}
              placeholder="Search topics, concepts, or questions"
              size="compact"
            />
          </div>
          <div
            className="relative grid min-h-0 w-full flex-1 grid-cols-1 gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)] lg:gap-7 xl:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]"
            data-testid="search-results-section"
          >
            <section className="flex min-h-0 min-w-0 flex-col gap-3 lg:h-full lg:gap-[14px]">
              <h1 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                Search Results
              </h1>
              <div
                className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden px-1.5 md:px-2"
                data-testid="search-results-scroll-area"
              >
                <div
                  className="grid w-full auto-rows-[220px] grid-cols-1 gap-y-3 sm:grid-cols-2 sm:gap-x-3 md:auto-rows-[300px] lg:auto-rows-[379px] lg:grid-cols-2 lg:gap-[18px] xl:grid-cols-3"
                  data-testid="search-results-grid"
                >
                  {matchedCards.map((card) => (
                    <SearchResultCard
                      content={card.content}
                      key={card.title}
                      title={card.title}
                    />
                  ))}
                </div>
              </div>
            </section>
            <section
              className="flex h-[176px] min-w-0 flex-col gap-3 lg:h-full lg:gap-[14px]"
              data-testid="search-suggestions-panel"
            >
              <h2 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                You may also be interested in
              </h2>
              <div
                className="flex min-h-0 w-full flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden px-1 md:px-0"
                data-testid="search-suggestions-scroll-area"
              >
                {connectedTitles.map((suggestion) => (
                  <button
                    className="flex h-[38px] w-full shrink-0 items-center justify-between overflow-hidden rounded-lg border border-[rgba(214,227,247,0.74)] bg-[rgba(255,255,255,0.7)] py-2 pr-3 pl-[14px] text-left text-[13px] leading-[18px] font-medium text-[#131c2d] md:h-[42px] md:pl-4 md:text-[14px] md:leading-5"
                    key={suggestion}
                    onClick={() => {
                      void navigate({
                        search: { q: suggestion },
                        to: "/search",
                      });
                    }}
                    type="button"
                  >
                    <span className="min-w-0 flex-1 truncate text-left">
                      {suggestion}
                    </span>
                    <ChevronRight
                      aria-hidden="true"
                      className="size-[15px] shrink-0 text-[#606e87] md:size-4"
                    />
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </main>
  );
}
