// abstract: Root app shell for semantic-map phase-1 bootstrap.
// out_of_scope: Feature-level data fetching and rendering engine internals.

import { SemanticMapPage } from "./features/semantic-map/page/SemanticMapPage";

export function App() {
  return (
    <div className="app-shell">
      <SemanticMapPage />
    </div>
  );
}
