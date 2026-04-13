---
abstract: Shared frontend rich-text rendering design for knowledge-card title and content surfaces with Markdown support, inline LaTeX normalization, and KaTeX presentation.
out_of_scope: Backend authoring validation, non-card prose styling, and raw HTML rendering policy outside the shared knowledge-card renderer.
---

# Design: web-knowledge-card-rich-text

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define one shared frontend rendering boundary for knowledge-card `title` and `content` so every web surface that displays card text uses the same Markdown, inline LaTeX normalization, and KaTeX presentation behavior.
- **Scope/Boundaries:** Covers renderer ownership for knowledge-card text in `apps/web`, the accepted Markdown subset, `\(...\)` to `$...$` normalization, KaTeX stylesheet ownership, title/content rendering presets, and soft-failure behavior. Excludes backend content validation, data-model changes, search ranking semantics, and non-card rich-text surfaces.
- **Related Requirements:** R-001, R-003, R-004, R-006.

## Constraint Projection
- **Governing Constraints:** Frontend card rendering remains inside the unified web client, consumes contract-driven `title` and `content` data without transport-specific logic, preserves explicit shared-vs-feature module boundaries, and keeps behavior-changing rendering rules synchronized in active specs.
- **Detail Commitments:** The web client owns one shared knowledge-card rich-text renderer built on `react-markdown`, `remark-math`, and `rehype-katex`. Upstream card text remains authored with inline LaTeX delimiters `\(...\)`, while the renderer normalizes those delimiters to `$...$` before the Markdown math pipeline executes. The renderer supports a controlled common-Markdown subset for card text, does not render raw HTML, and exposes separate presentation presets for title and content while reusing one parsing pipeline. Search result cards, taxonomy leaf hover disclosure, and any future web knowledge-card title/content surfaces consume that shared renderer instead of rendering raw strings directly.
- **Update Rule:** Requirement-level repository and integration constraints remain stable while shared rich-text parsing, normalization, presentation presets, and consuming frontend surfaces are maintained in this design document.

## Inputs & Outputs
- **Inputs:**
  - Contract-derived knowledge-card `title` strings.
  - Contract-derived knowledge-card `content` strings.
  - Existing web feature surfaces that display knowledge-card text, including Search results and taxonomy leaf hover disclosure.
  - Global frontend stylesheet ownership in `apps/web/src/index.css`.
- **Outputs:**
  - One shared renderer entrypoint for knowledge-card text.
  - One deterministic normalization pass from inline `\(...\)` syntax to `$...$` syntax for the Markdown math parser.
  - One controlled Markdown-plus-KaTeX rendering result for title surfaces.
  - One controlled Markdown-plus-KaTeX rendering result for content surfaces.
- **Artifacts:**
  - `/Users/mianqin/Code/knowledge/apps/web/src/shared/ui/`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/search/components/index.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/features/taxonomy-view/page/leaf/LeafHoverOverlay.tsx`
  - `/Users/mianqin/Code/knowledge/apps/web/src/index.css`
  - Focused frontend tests under `apps/web/src/**`

## Design Approach
- **Approach:** Introduce one shared `KnowledgeRichText` rendering boundary in the web shared UI layer. The boundary accepts raw card text plus a presentation variant such as `title` or `content`, normalizes inline LaTeX delimiters, renders through the Markdown math pipeline, and maps the resulting HTML structure onto approved card typography and spacing rules. Feature components continue to own their container layout, but they delegate all card text rendering to the shared renderer.
- **Key Elements:**
  - **Shared renderer boundary:** Knowledge-card rich-text parsing and rendering belong to one shared UI module rather than to Search or taxonomy feature components.
  - **Normalization rule:** Before Markdown parsing, the renderer rewrites supported inline LaTeX spans from `\(...\)` to `$...$`. The accepted first-version rule covers inline math only and does not add display-math support.
  - **Authoring compatibility rule:** Upstream content keeps the existing `\(...\)` authoring convention. Frontend normalization is a compatibility step local to rendering and does not mutate backend payloads or change API contracts.
  - **Markdown subset rule:** The renderer supports common Markdown needed for knowledge cards: paragraphs, explicit line breaks, emphasis, unordered and ordered lists, inline code, and fenced code blocks.
  - **Raw HTML rule:** The renderer does not enable raw HTML rendering. Card text is interpreted through Markdown plus math only.
  - **Variant rule:** The renderer exposes at least two presentation variants:
    - `title`: compact layout, tighter line-height, stronger text tone, and no default block spacing that would break card geometry.
    - `content`: standard reading layout, controlled paragraph/list/code spacing, and overflow-safe wrapping inside scrollable card bodies or overlays.
  - **KaTeX asset rule:** KaTeX stylesheet ownership is centralized at the web app entry styling layer so all consuming card surfaces share one consistent equation presentation.
  - **Soft-failure rule:** Rendering failures must not break the page shell or remove card text entirely. If normalization or rich-text rendering fails for a card field, the frontend falls back to displaying the source text for that field.
  - **Surface adoption rule:** Any web surface that displays knowledge-card `title` or `content` must consume the shared renderer. Feature-specific raw-string rendering for those fields is not an accepted long-term pattern.
  - **DOM host rule:** Surfaces that need Markdown-plus-KaTeX card text must provide a DOM rendering host for the shared renderer. GPU text primitives that can only draw plain strings are not sufficient for adopted knowledge-card title/content surfaces.
  - **Feature-boundary rule:** Search result cards and taxonomy leaf hover disclosure keep ownership of card layout, spacing, scrolling, and interaction state. They do not own Markdown or KaTeX parsing policy.
- **Interactions:**
  1. A web feature receives contract-derived card `title` and `content`.
  2. The feature passes each field into the shared knowledge-card renderer with the appropriate variant.
  3. The shared renderer normalizes inline LaTeX delimiters from `\(...\)` to `$...$`.
  4. The renderer executes the Markdown pipeline with `remark-math` and `rehype-katex`.
  5. The renderer outputs variant-scoped rich text nodes styled for the hosting card surface.
  6. If rendering fails, the feature still shows the original text through the renderer's soft-fallback path instead of throwing a UI-level fatal error.

## Validation
- **Checks:**
  - Search result cards render knowledge-card `title` and `content` through the shared renderer rather than as raw strings.
  - Taxonomy leaf hover disclosure renders card `content` through the shared renderer rather than as a raw string.
  - Shared renderer normalization converts inline `\(...\)` segments into syntax that `remark-math` can parse without changing upstream payload ownership.
  - Title and content variants apply distinct typography/spacing rules while sharing one parsing pipeline.
  - Common Markdown constructs used by cards render correctly inside title/content constraints.
  - Raw HTML is not rendered by the shared card-text pipeline.
  - KaTeX styling is available on every adopted card surface through one centralized stylesheet import.
  - Renderer failure falls back to source text without collapsing the surrounding card layout.
- **Evidence:**
  - Updated frontend design docs keep Search and taxonomy card-text behavior synchronized with this shared rendering contract.
  - Frontend tests cover inline-math normalization, Markdown rendering, shared-renderer adoption by consuming surfaces, and soft-failure fallback behavior.
  - Browser-level inspection confirms equations and common Markdown render consistently across adopted knowledge-card surfaces.
