// abstract: Semantic-map landing page with manifest bootstrap and empty-state flow.
// out_of_scope: deck.gl rendering engine internals and point-level inspection UI.

import { lazy, Suspense } from "react";

import { useSemanticMapManifestQuery } from "../data/semanticMapQueries";
import { EmptyState } from "../ui/EmptyState";

const LazySemanticMapExplorer = lazy(async () => {
  const module = await import("../engine/SemanticMapExplorer");

  return { default: module.SemanticMapExplorer };
});

export function SemanticMapPage() {
  const manifestQuery = useSemanticMapManifestQuery();

  if (manifestQuery.isPending) {
    return (
      <main className="semantic-map-page">
        <section className="loading-state" aria-busy="true" aria-live="polite">
          <p className="page-eyebrow">Semantic Map</p>
          <h2>Loading snapshot</h2>
          <p>Fetching the latest semantic-map manifest.</p>
        </section>
      </main>
    );
  }

  if (manifestQuery.isError) {
    return (
      <main className="semantic-map-page">
        <section className="error-state" role="alert">
          <p className="page-eyebrow">Semantic Map</p>
          <h2>Semantic map unavailable</h2>
          <p>{manifestQuery.error.message}</p>
        </section>
      </main>
    );
  }

  if (!manifestQuery.data) {
    return (
      <main className="semantic-map-page">
        <EmptyState />
      </main>
    );
  }

  return (
    <main className="semantic-map-page semantic-map-page--engine">
      <p className="page-eyebrow">Semantic Map</p>
      <h1 className="page-title">Semantic map explorer</h1>
      <p className="page-copy">
        Region and label rendering are now driven by the current semantic-map
        snapshot. Semantic zoom follows backend-defined levels instead of
        hard-coded frontend thresholds.
      </p>
      <Suspense
        fallback={
          <section
            aria-busy="true"
            aria-live="polite"
            className="loading-state semantic-map-engine-fallback"
          >
            <h2>Loading map engine</h2>
            <p>Preparing the deck.gl explorer bundle for this snapshot.</p>
          </section>
        }
      >
        <LazySemanticMapExplorer manifest={manifestQuery.data} />
      </Suspense>
    </main>
  );
}
