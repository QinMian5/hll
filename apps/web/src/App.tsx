// abstract: Root app shell for taxonomy-query-driven React Flow browsing.
// out_of_scope: Feature-level data fetching and rendering engine internals.

import { TaxonomyViewPage } from "./features/taxonomy-view/page/TaxonomyViewPage";

export function App() {
  return (
    <div className="app-shell">
      <TaxonomyViewPage />
    </div>
  );
}
