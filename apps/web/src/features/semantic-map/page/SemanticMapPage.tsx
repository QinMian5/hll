// abstract: Semantic-map landing page with manifest bootstrap and empty-state flow.
// out_of_scope: deck.gl rendering engine internals and point-level inspection UI.

import { useSemanticMapManifestQuery } from "../data/semanticMapQueries";
import { EmptyState } from "../ui/EmptyState";

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

  const manifest = manifestQuery.data;

  return (
    <main className="semantic-map-page">
      <p className="page-eyebrow">Semantic Map</p>
      <h1 className="page-title">Semantic space bootstrap</h1>
      <p className="page-copy">
        Phase 1 starts with a contract-driven manifest read. Region and label
        rendering land in the next slice, but the app shell is already pinned to
        the latest published semantic-map version.
      </p>

      <dl className="semantic-map-summary">
        <div className="summary-card">
          <dt>Current version</dt>
          <dd>{manifest.version}</dd>
        </div>
        <div className="summary-card">
          <dt>Default semantic level</dt>
          <dd>{manifest.defaultSemanticLevel}</dd>
        </div>
        <div className="summary-card">
          <dt>Levels</dt>
          <dd>{manifest.levels.length}</dd>
        </div>
        <div className="summary-card">
          <dt>World bounds</dt>
          <dd>{manifest.worldBounds.join(", ")}</dd>
        </div>
      </dl>
    </main>
  );
}
