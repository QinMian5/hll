// abstract: Routed Search page with Figma-aligned empty and results states owned by URL search state.
// out_of_scope: Backend search integration and ranking semantics.

import { useNavigate, useSearch } from "@tanstack/react-router";
import type { FormEvent } from "react";

import { Button } from "../../../shared/ui";
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
      className="h-full min-h-0 overflow-hidden"
      data-testid="search-route-page"
    >
      <section className="flex h-full min-h-0 flex-col overflow-hidden bg-white px-6 pt-6 pb-6">
        {!hasQuery ? (
          <div
            className="flex h-full items-center justify-center px-10 py-12"
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
          <div className="flex h-full min-h-0 flex-col overflow-hidden">
            <div
              className="flex items-center justify-center"
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
            <div className="mt-6 grid min-h-0 flex-1 grid-cols-[minmax(0,3fr)_minmax(0,1fr)] gap-8 overflow-hidden">
              <section className="flex min-h-0 min-w-0 flex-col">
                <h1 className="m-0 h-12 text-[32px] leading-[48px] font-medium text-[#0F172A]">
                  Search Results
                </h1>
                <div className="mt-4 min-h-0 flex-1">
                  <div className="h-full overflow-auto pr-1">
                    <div
                      className="grid h-full min-h-full grid-cols-3 grid-rows-2 auto-rows-[minmax(0,1fr)] gap-[18px]"
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
                </div>
              </section>
              <aside
                className="flex min-h-0 flex-col"
                data-testid="search-suggestions-panel"
              >
                <h2 className="m-0 h-12 text-[32px] leading-[48px] font-medium text-[#0F172A]">
                  You may also be interested in
                </h2>
                <div className="mt-4 min-h-0 flex-1 overflow-auto pr-1">
                  <div className="space-y-3">
                    {connectedTitles.map((suggestion) => (
                      <Button
                        className="flex h-12 w-full items-center justify-between rounded-[20px] border border-[rgba(223,232,247,0.98)] bg-[rgba(255,255,255,0.92)] px-4 text-left text-[15px] leading-5 font-medium text-[#0F172A] shadow-[0_10px_24px_rgba(148,163,184,0.08)]"
                        key={suggestion}
                        onClick={() => {
                          void navigate({
                            search: { q: suggestion },
                            to: "/search",
                          });
                        }}
                        variant="ghost"
                      >
                        <span>{suggestion}</span>
                        <span
                          aria-hidden="true"
                          className="text-[18px] leading-[18px] text-[rgba(148,163,184,0.95)]"
                        >
                          ›
                        </span>
                      </Button>
                    ))}
                  </div>
                </div>
              </aside>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
