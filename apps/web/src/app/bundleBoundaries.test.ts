// abstract: Architecture tests that keep heavy browser-only features out of the initial route bundle.
// out_of_scope: Runtime rendering behavior and exact production chunk byte budgets.

import { describe, expect, it } from "vitest";

import viteConfigSource from "../../vite.config.ts?raw";
import searchPageSource from "../features/search/pages/index.tsx?raw";
import leafRendererSource from "../features/taxonomy-view/page/leaf/LeafRenderer.tsx?raw";
import taxonomySource from "../features/taxonomy-view/page/TaxonomyViewPage.tsx?raw";
import globalCss from "../index.css?raw";
import richTextSource from "../shared/ui/knowledge-rich-text.tsx?raw";
import routerSource from "./router.tsx?raw";

describe("browser bundle boundaries", () => {
  it("keeps route components behind TanStack lazy route boundaries", () => {
    expect(routerSource).toContain("lazyRouteComponent");
    expect(routerSource).not.toContain(
      'import { OverviewPage } from "../features/overview/pages"',
    );
    expect(routerSource).not.toContain(
      'import { SearchPage } from "../features/search/pages"',
    );
    expect(routerSource).not.toContain(
      'import { TaxonomyViewPage } from "../features/taxonomy-view/page/TaxonomyViewPage"',
    );
    expect(routerSource).toContain('import("../features/overview/pages")');
    expect(routerSource).toContain('import("../features/search/pages")');
    expect(routerSource).toContain(
      'import("../features/taxonomy-view/page/TaxonomyViewPage")',
    );
  });

  it("loads search result rich-text rendering only for populated search results", () => {
    expect(searchPageSource).toContain("lazy(");
    expect(searchPageSource).toContain(
      'import("../components/SearchResultCard")',
    );
    expect(searchPageSource).not.toContain('from "../components"');
    expect(searchPageSource).not.toContain("SearchResultCard } from");
  });

  it("keeps leaf deck rendering and KaTeX CSS out of the global startup path", () => {
    expect(taxonomySource).toContain("lazy(");
    expect(taxonomySource).toContain('import("./leaf/LeafRenderer")');
    expect(taxonomySource).not.toContain(
      'import { LeafRenderer } from "./leaf/LeafRenderer"',
    );
    expect(globalCss).not.toContain("katex/dist/katex.min.css");
    expect(richTextSource).toContain('import "katex/dist/katex.min.css"');
  });

  it("loads the deck.gl scene implementation only inside leaf mode", () => {
    expect(leafRendererSource).toContain("lazy(");
    expect(leafRendererSource).toContain('import("./LeafDeckScene")');
    expect(leafRendererSource).not.toContain(
      'import { LeafDeckScene } from "./LeafDeckScene"',
    );
  });

  it("uses real code splitting instead of hiding chunk warnings", () => {
    expect(viteConfigSource).toContain("codeSplitting");
    expect(viteConfigSource).toContain("leaf-scene-vendor");
    expect(viteConfigSource).toContain("maxSize");
    expect(viteConfigSource).toContain("includeDependenciesRecursively: false");
    expect(viteConfigSource).toContain("strictExecutionOrder: true");
    expect(viteConfigSource).not.toContain("test: /node_modules/");
    expect(viteConfigSource).not.toContain("chunkSizeWarningLimit");
  });
});
