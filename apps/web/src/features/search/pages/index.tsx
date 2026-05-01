// abstract: Routed Search page with Figma-aligned empty and results states owned by URL search state.
// out_of_scope: Backend search integration and ranking semantics.

import { useNavigate, useSearch } from "@tanstack/react-router";
import { type FormEvent, lazy, Suspense, useState } from "react";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import { useWebSession } from "../../../shared/web-api/useWebSession";
import { RelatedResultItem } from "../components/RelatedResultItem";
import { SearchField } from "../components/SearchField";
import type { SearchResultCardEditPayload } from "../components/SearchResultCard";
import { SignInRequiredDialog } from "../components/SignInRequiredDialog";
import { SuggestEditDialog } from "../components/SuggestEditDialog";
import {
  useCreateSuggestedEditMutation,
  useSearchQuery,
} from "../data/searchQueries";
import { suggestedEditErrorMessage } from "../suggestedEditErrors";

const SearchResultCard = lazy(() =>
  import("../components/SearchResultCard").then((module) => ({
    default: module.SearchResultCard,
  })),
);

function normalizeQuery(value: string | undefined): string {
  return value?.trim() ?? "";
}

function searchErrorCopy(error: Error | null): {
  readonly body: string;
  readonly title: string;
} {
  if (error instanceof WebApiRequestError && error.code === "quota_exceeded") {
    return {
      body: "Try again shortly.",
      title: "Too many searches",
    };
  }

  return {
    body: error?.message ?? "Search could not be loaded.",
    title: "Search unavailable",
  };
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
  const errorCopy = searchQuery.isError
    ? searchErrorCopy(searchQuery.error)
    : null;

  function navigateToSearchQuery(nextQuery: string) {
    const normalizedNextQuery = normalizeQuery(nextQuery);

    void navigate({
      search: {
        q: normalizedNextQuery === "" ? undefined : normalizedNextQuery,
      },
      to: "/search",
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const rawValue = formData.get("q");
    const nextQuery =
      typeof rawValue === "string" ? normalizeQuery(rawValue) : "";

    navigateToSearchQuery(nextQuery);
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
    } catch (error) {
      setSuggestionError(suggestedEditErrorMessage(error));
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
          className="flex h-full min-h-0 w-full flex-col items-center gap-4 overflow-hidden px-4 py-4 lg:p-6"
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
            className="relative grid min-h-0 w-full flex-1 grid-cols-1 gap-2 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)] lg:gap-4"
            data-testid="search-results-section"
          >
            <section className="flex min-h-0 min-w-0 flex-col gap-2 lg:h-full lg:gap-4">
              <h1 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                Search results
              </h1>
              <div
                className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden pt-4 pr-4 pb-1 pl-2 [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent"
                data-testid="search-results-scroll-area"
              >
                {errorCopy ? (
                  <section
                    className="flex min-h-[200px] w-full flex-col justify-center rounded-lg border border-[#e0e4eb] bg-white px-5 py-4"
                    data-testid="search-error-state"
                    role="alert"
                  >
                    <h2 className="m-0 text-[16px] leading-6 font-semibold text-[#131c2d]">
                      {errorCopy.title}
                    </h2>
                    <p className="mt-2 mb-0 text-[14px] leading-5 text-[#606e87]">
                      {errorCopy.body}
                    </p>
                  </section>
                ) : (
                  <div
                    className="group/search-results-grid grid w-full auto-rows-[200px] grid-cols-1 gap-2 pb-1 sm:grid-cols-2 lg:auto-rows-[200px] lg:grid-cols-2 lg:gap-4 min-[1680px]:grid-cols-3"
                    data-testid="search-results-grid"
                  >
                    <Suspense fallback={null}>
                      {matchedCards.map((card) => (
                        <SearchResultCard
                          content={card.content}
                          currentVersion={card.current_version}
                          key={card.node_id}
                          nodeId={card.node_id}
                          onSearchTitle={navigateToSearchQuery}
                          onSuggestEdit={handleSuggestEdit}
                          title={card.title}
                        />
                      ))}
                    </Suspense>
                  </div>
                )}
              </div>
            </section>
            <section
              className="flex h-[200px] min-h-0 min-w-0 flex-col gap-2 lg:h-full lg:gap-4"
              data-testid="search-suggestions-panel"
            >
              <h2 className="m-0 flex h-6 w-full shrink-0 items-center text-[16px] leading-6 font-semibold text-[#131c2d] md:h-12 md:text-[18px] md:leading-[48px]">
                Related results
              </h2>
              <div
                className="group/search-suggestions-list flex min-h-0 w-full flex-1 flex-col gap-2 overflow-y-auto overflow-x-hidden [scrollbar-color:#e5e5e5_transparent] [scrollbar-width:thin] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-sm [&::-webkit-scrollbar-thumb]:bg-[#e5e5e5] [&::-webkit-scrollbar-track]:bg-transparent"
                data-testid="search-suggestions-scroll-area"
              >
                {connectedTitles.map((suggestion) => (
                  <RelatedResultItem
                    key={suggestion}
                    onSelect={navigateToSearchQuery}
                    title={suggestion}
                  />
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
