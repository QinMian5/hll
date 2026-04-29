// abstract: Routed Search page with Figma-aligned empty and results states owned by URL search state.
// out_of_scope: Backend search integration and ranking semantics.

import { useNavigate, useSearch } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { type FormEvent, lazy, Suspense, useState } from "react";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import { SearchField } from "../components/SearchField";
import type { SearchResultCardEditPayload } from "../components/SearchResultCard";
import { SignInRequiredDialog } from "../components/SignInRequiredDialog";
import { SuggestEditDialog } from "../components/SuggestEditDialog";
import {
  useCreateSuggestedEditMutation,
  useSearchQuery,
} from "../data/searchQueries";

const SearchResultCard = lazy(() =>
  import("../components/SearchResultCard").then((module) => ({
    default: module.SearchResultCard,
  })),
);

function normalizeQuery(value: string | undefined): string {
  return value?.trim() ?? "";
}

export function SearchPage() {
  const navigate = useNavigate({ from: "/search" });
  const search = useSearch({ from: "/search" }) as { q?: string };
  const query = normalizeQuery(search.q);
  const hasQuery = query.length > 0;
  const session = useWebSession();
  const searchQuery = useSearchQuery(query, {
    enabled: hasQuery,
  });
  const createSuggestedEditMutation = useCreateSuggestedEditMutation();
  const [editingCard, setEditingCard] =
    useState<SearchResultCardEditPayload | null>(null);
  const [suggestionError, setSuggestionError] = useState<string | undefined>();
  const [isSignInDialogOpen, setIsSignInDialogOpen] = useState(false);
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

  function handleSuggestEdit(card: SearchResultCardEditPayload) {
    if (session.status === "loading") {
      return;
    }

    if (session.status !== "authenticated") {
      setIsSignInDialogOpen(true);
      return;
    }

    setEditingCard(card);
    setSuggestionError(undefined);
  }

  async function handleSubmitSuggestion(payload: {
    readonly suggestedContent: string;
    readonly suggestedTitle: string;
  }) {
    if (editingCard === null) {
      return;
    }

    try {
      await createSuggestedEditMutation.mutateAsync({
        baseVersion: editingCard.currentVersion,
        nodeId: editingCard.nodeId,
        suggestedContent: payload.suggestedContent,
        suggestedTitle: payload.suggestedTitle,
      });
      setEditingCard(null);
      setSuggestionError(undefined);
    } catch {
      setSuggestionError("Could not submit the suggestion. Try again.");
    }
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
          className="flex h-full min-h-0 w-full flex-col items-center gap-4 overflow-hidden px-4 py-4 lg:gap-5 lg:px-8 lg:pt-6 lg:pb-8"
          data-testid="search-results-frame"
        >
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
          <div
            className="relative grid min-h-0 w-full flex-1 grid-cols-1 gap-3 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)] lg:gap-7"
            data-testid="search-results-section"
          >
            <section className="flex min-h-0 min-w-0 flex-col gap-3 lg:h-full lg:gap-4">
              <h1 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                Search results
              </h1>
              <div
                className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent"
                data-testid="search-results-scroll-area"
              >
                <div
                  className="grid w-full auto-rows-[176px] grid-cols-1 gap-y-3 sm:grid-cols-2 sm:gap-x-3 lg:auto-rows-[176px] lg:grid-cols-2 lg:gap-4 min-[1680px]:grid-cols-3"
                  data-testid="search-results-grid"
                >
                  <Suspense fallback={null}>
                    {matchedCards.map((card) => (
                      <SearchResultCard
                        content={card.content}
                        currentVersion={card.current_version}
                        key={card.node_id}
                        nodeId={card.node_id}
                        onSuggestEdit={handleSuggestEdit}
                        title={card.title}
                      />
                    ))}
                  </Suspense>
                </div>
              </div>
            </section>
            <section
              className="flex h-[176px] min-h-0 min-w-0 flex-col gap-3 lg:h-full lg:gap-4"
              data-testid="search-suggestions-panel"
            >
              <h2 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                Related results
              </h2>
              <div
                className="flex min-h-0 w-full flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent"
                data-testid="search-suggestions-scroll-area"
              >
                {connectedTitles.map((suggestion) => (
                  <button
                    className="flex h-[38px] w-full shrink-0 items-center justify-between overflow-hidden rounded-lg border border-[#e0e4eb] bg-[rgba(255,255,255,0.7)] py-2 pr-3 pl-3 text-left text-[13px] leading-[18px] font-medium text-[#131c2d] md:h-[42px] md:text-[14px] md:leading-5"
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
      {editingCard ? (
        <SuggestEditDialog
          card={editingCard}
          errorMessage={suggestionError}
          isSubmitting={createSuggestedEditMutation.isPending}
          onClose={() => {
            setEditingCard(null);
            setSuggestionError(undefined);
          }}
          onSubmit={handleSubmitSuggestion}
        />
      ) : null}
      {isSignInDialogOpen ? (
        <SignInRequiredDialog
          onClose={() => {
            setIsSignInDialogOpen(false);
          }}
        />
      ) : null}
    </main>
  );
}
