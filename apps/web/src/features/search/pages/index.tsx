// abstract: Routed Search page with Figma-aligned empty and results states owned by URL search state.
// out_of_scope: Backend search integration and ranking semantics.

import { useNavigate, useSearch } from "@tanstack/react-router";
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
          className="flex h-full min-h-0 items-center justify-center overflow-clip rounded-[32px] bg-[linear-gradient(137.03deg,rgba(254,254,255,1)_14.099%,rgba(245,249,255,1)_45.692%,rgba(249,251,255,1)_85.901%)] px-10 py-12 shadow-[0_18px_52px_rgba(107,133,189,0.09)]"
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
        <div className="flex h-full min-h-0 w-full flex-col items-start gap-6 p-6">
          <div
            className="relative flex h-12 w-full shrink-0 items-center justify-center"
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
          <div className="relative grid min-h-0 w-full flex-1 grid-cols-[minmax(0,3fr)_minmax(0,1fr)] grid-rows-[48px_minmax(0,1fr)] gap-x-8 gap-y-4">
            <h1 className="col-start-1 row-start-1 m-0 flex h-12 shrink-0 items-center justify-self-stretch self-stretch text-[18px] leading-6 font-semibold text-[rgba(18,23,41,0.98)]">
              Search Results
            </h1>
            <h2 className="col-start-2 row-start-1 m-0 flex h-12 shrink-0 items-center justify-self-stretch self-stretch text-[18px] leading-[22px] font-semibold text-[rgba(18,23,41,0.98)]">
              You may also be interested in
            </h2>
            <div className="relative col-start-1 row-start-2 flex min-h-0 shrink-0 flex-col items-center justify-center justify-self-stretch self-stretch">
              <div
                className="grid min-h-px min-w-px w-full flex-1 grid-cols-3 grid-rows-2 gap-[18px]"
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
            <div
              className="relative col-start-2 row-start-2 flex min-h-0 shrink-0 flex-col items-start justify-self-stretch self-stretch"
              data-testid="search-suggestions-panel"
            >
              <div className="flex min-h-0 min-w-0 w-full flex-1 flex-col gap-3 overflow-y-auto overflow-x-hidden">
                {connectedTitles.map((suggestion) => (
                  <button
                    className="flex h-12 w-full shrink-0 items-center justify-between overflow-clip rounded-[16px] border border-[rgba(223,232,247,0.98)] bg-[rgba(255,255,255,0.84)] px-4 text-left text-[15px] leading-5 font-medium text-[rgba(20,28,46,0.94)] shadow-none"
                    key={suggestion}
                    onClick={() => {
                      void navigate({
                        search: { q: suggestion },
                        to: "/search",
                      });
                    }}
                    type="button"
                  >
                    <span className="min-h-px min-w-px flex-1 text-left">
                      {suggestion}
                    </span>
                    <span
                      aria-hidden="true"
                      className="shrink-0 text-center text-[14px] leading-[18px] text-[rgba(98,118,153,0.8)]"
                    >
                      →
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
