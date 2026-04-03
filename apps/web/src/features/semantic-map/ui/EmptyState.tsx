// abstract: Empty-state panel for missing semantic-map snapshots.
// out_of_scope: Query orchestration and deck.gl canvas rendering.

export function EmptyState() {
  return (
    <section
      className="empty-state"
      aria-labelledby="semantic-map-empty-state-title"
    >
      <p className="page-eyebrow">Semantic Map</p>
      <h2 id="semantic-map-empty-state-title">Snapshot unavailable</h2>
      <p>
        No semantic-map snapshot is currently available. Rebuild the
        semantic-map artifacts and reload this page.
      </p>
    </section>
  );
}
