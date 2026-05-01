---
abstract: Shared frontend app shell design for the web client with Figma-first sidebar navigation, mobile drawer navigation, Docs placement, Search route composition, card suggestion interactions, and signed-in account actions.
out_of_scope: Taxonomy renderer internals, backend search ranking semantics, Logto session implementation, and suggestion review UI.
---

# Design: web-app-shell-navigation

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the shared web app shell for the frontend so `Overview`, route-addressable `Graph View`, `Search`, `Docs`, `Dashboard`, and `Settings` render inside one consistent route-driven layout with Figma-first navigation, Docs route placement, Search presentation, Search card suggestion interactions, and Dashboard route placement.
- **Scope/Boundaries:** Covers route ownership, default entry routing, shared desktop sidebar, shared mobile header and drawer, shared body spacing, Docs primary navigation placement, Graph View route shape, Search page empty/results composition, Search card edit/suggestion dialogs, Dashboard shell placement, and shell-level visual behavior for `apps/web`. Excludes taxonomy graph rendering rules, backend search semantics, Docs content authoring pipelines, suggestion review UI, Dashboard token lifecycle internals, and Logto session implementation.
- **Related Requirements:** R-001, R-003, R-004, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Frontend behavior remains within the unified web client boundary, uses BFF-owned web data adapters for browser-visible application data, preserves explicit module boundaries, and keeps behavior-changing page-structure decisions synchronized in active specs.
- **Detail Commitments:** The frontend uses one shared app shell for `Overview`, `Graph View`, `Search`, `Docs`, `Dashboard`, and `Settings`. The root route redirects to `Overview`. Desktop uses a persistent left navigation sidebar with Tailwind-default breakpoint sizing. Mobile uses a compact top header with a menu trigger and a route-driven drawer overlay. The shared shell follows Figma file `WBYs6P9HMxe21TSYQL637r`, desktop signed-in frame `456:21`, mobile signed-in frame `456:58`, and account-menu-open frames `461:53` and `461:103`. The Graph View route follows the approved Graph View page frames `702:3845` and `702:3950`, uses `/graph` for the taxonomy root, and uses `/graph/<canonical-lcc-slug-path>` for branch and leaf nodes. The Search route follows the approved Search page frames under the same Figma file, including Suggest Edit Dialog frames `437:106` and `437:274`, and Sign In Required Dialog frames `561:453` and `561:610`. The Docs route follows the unified documentation design in `web-docs.md` and is reached from primary navigation. The Dashboard route follows the token-management design in `web-dashboard-token-management.md` and is reached from the authenticated account menu rather than primary navigation. The Settings route follows the account settings design in `web-account-settings.md`. The web client loads and uses Geist as the app-wide primary font for browser default text and Tailwind font-family tokens. Shell styling is expressed primarily through Tailwind utility classes instead of page-owned handwritten CSS, and account-menu typography, color, spacing, radius, and elevation values are carried by Tailwind theme tokens rather than hardcoded arbitrary utilities. Approved Figma auto-layout and grid structure is the primary source of truth for page composition; implementation should translate those structures directly instead of approximating them through unrelated wrappers or ad hoc spacing offsets.
- **Update Rule:** Requirements remain stable at the repository-governance layer while route ownership, shell structure, navigation state rules, and Search page presentation stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Shared browser entrypoint and route mounting in `apps/web`.
  - Approved Figma reference for shared shell and account menu: file `WBYs6P9HMxe21TSYQL637r`, desktop signed-in frame `456:21`, mobile signed-in frame `456:58`, desktop account-menu frame `461:53`, and mobile account-menu frame `461:103`.
  - Approved Figma reference for Search results composition: file `WBYs6P9HMxe21TSYQL637r`, Search desktop and mobile frames under the shared shell page, Search desktop no-hover frame `702:4065`, Search desktop card-hover frame `885:1412`, Search Result Card component set `882:601`, and Related Result Item component set `1273:803`.
  - Approved Figma reference for Search suggestion dialogs: file `WBYs6P9HMxe21TSYQL637r`, Suggest Edit Dialog frames `437:106` and `437:274`, and Sign In Required Dialog frames `561:453` and `561:610`.
  - Approved Figma reference for Graph View composition: file `WBYs6P9HMxe21TSYQL637r`, desktop frame `702:3845` and mobile frame `702:3950`.
  - Approved Figma reference for Settings composition: file `WBYs6P9HMxe21TSYQL637r`, Settings canvas node `474:84`.
  - Taxonomy graph page mounted under the shared shell as the `Graph View` route.
- **Outputs:**
  - One shared shell with desktop sidebar navigation, mobile header, mobile drawer, and body content slot.
  - One route set for `/overview`, `/graph`, `/graph/<canonical-lcc-slug-path>`, `/search`, `/docs`, `/dashboard`, and `/settings`, with `/` redirecting to `/overview`.
  - One Search page with URL-driven empty/results state behavior.
  - One Search card edit interaction model with authenticated suggestion submission and anonymous sign-in-required dialog state.
  - One shell action area for the `GitHub` repository link and auth/account action slot.
- **Artifacts:**
  - `apps/web/src/main.tsx`
  - `apps/web/src/App.tsx`
  - `apps/web/src/app/router.tsx`
  - `apps/web/src/app/AppShell.tsx`
  - `apps/web/src/app/bundleBoundaries.test.ts`
  - `apps/web/src/features/search/components/SearchField.tsx`
  - `apps/web/src/features/search/components/SearchResultCard.tsx`
  - `apps/web/src/features/search/components/SuggestEditDialog.tsx`
  - `apps/web/src/features/search/components/SignInRequiredDialog.tsx`
  - `apps/web/src/features/search/pages/index.tsx`
  - `apps/web/src/features/docs/pages/index.tsx`
  - `apps/web/src/features/taxonomy-view/page/TaxonomyViewPage.tsx`
  - `apps/web/src/features/taxonomy-view/page/leaf/LeafRenderer.tsx`
  - `apps/web/vite.config.ts`
  - `apps/web/src/features/dashboard/pages/index.tsx`
  - `apps/web/src/features/settings/pages/index.tsx`
  - Additional shell-level frontend components under `apps/web/src/` when implementation begins.

## Design Approach
- **Approach:** The web client renders one shared `AppShell` that owns desktop sidebar navigation, mobile header and drawer navigation, signed-in account actions, and the body content slot. Route resolution decides whether the shell body renders the `Overview`, `Graph View`, `Search`, `Docs`, `Dashboard`, or `Settings` page. `Search` remains a single route and uses URL query state to switch between its empty and results layouts so the page supports deep links, refresh restoration, and browser history navigation without introducing separate empty/results route branches. App-shell and Search composition are derived from approved Figma auto-layout and grid structures first, then translated into Tailwind utilities.
- **Key Elements:**
  - **Route ownership:** The frontend exposes `/overview`, `/graph`, `/graph/<canonical-lcc-slug-path>`, `/search`, `/docs`, `/dashboard`, and `/settings`. The root route redirects to `/overview`.
  - **Shared shell:** Every page renders within one shell that owns the route navigation, body slot, viewport composition, and responsive navigation mode.
  - **Desktop sidebar:** Medium and larger screens use a persistent left navigation region with regular Tailwind breakpoint widths: `240px` at `md`, `256px` at `lg`, `288px` at `xl`, and `320px` at `2xl`. The `320px` size remains the Figma full-desktop endpoint rather than the default width for every desktop viewport. The sidebar surface fills the viewport height, uses a translucent white header surface with a subtle right border, and contains a `52px` brand row, a flexible main navigation panel, and a `104px` footer. The brand mark is a `36px` blue rounded square with the `K` initial. Navigation rows are `40px` tall with `16px` icons, `12px` horizontal padding, `12px` icon/text gap, `8px` radius for the active item, muted text for inactive items, and blue-tinted active background with medium label weight for the current route.
  - **Desktop sidebar actions:** The footer contains a `40px` GitHub repository link and the auth/account action. When anonymous, the auth action renders a `40px` Sign in button that posts to the BFF sign-in endpoint with the current route as `return_to`. When authenticated, the footer renders a `48px` user account button with a `32px` avatar, display name, email/identifier, and an upward chevron because the menu opens above the button. Opening the account button shows a `304px` wide account menu owned by the footer, positioned above the account button, and containing `Dashboard`, `Settings`, and `Sign out`.
  - **Mobile header:** Mobile uses a `64px` top header with `16px` horizontal padding, `12px` gap, a `36px` menu trigger, a `36px` brand mark, and a single-line brand label. The header uses the approved translucent white surface and subtle bottom border.
  - **Mobile drawer:** The menu trigger opens a `320px` drawer overlay containing the same brand, route navigation, GitHub repository link, and auth/account action slot as the desktop sidebar. The drawer includes a close button and a page-color scrim at the Figma-approved opacity outside the drawer. Route navigation and account-menu navigation close the drawer after selection.
  - **Navigation items:** Primary route navigation contains enabled `Overview`, `Graph View`, `Search`, and `Docs` items. `Dashboard` and `Settings` are not primary navigation items; they are reached from the authenticated account menu.
  - **Overview route:** `Overview` renders as a true page route inside the shared shell. The first version is a placeholder page and does not define future Overview feature structure beyond that route-owned placeholder state.
  - **Docs route:** `Docs` renders the unified documentation hub inside the shared shell body. Docs owns project explanation, MCP access guidance, Codex setup guidance, and Claude Code setup guidance. Dashboard remains responsible for authenticated token and quota management.
  - **Graph View route:** `Graph View` renders the taxonomy browsing experience inside the shared shell body. `/graph` displays the taxonomy root. `/graph/<canonical-lcc-slug-path>` displays the branch or leaf node resolved by the taxonomy path endpoint. Desktop uses the responsive sidebar and a fill-sized Graph View content slot; the approved `320px` sidebar plus `1120px x 1024px` content slot remains the `2xl` full-desktop reference. Mobile uses the approved `64px` header plus `440px x 892px` Graph View content slot. Graph-specific renderer, LCC path semantics, and layout rules remain governed by taxonomy design documents.
  - **Dashboard route:** `Dashboard` is an enabled authenticated account-menu route inside the shared shell. The route renders the authenticated token-management page defined in `web-dashboard-token-management.md`.
  - **Settings route:** `Settings` is an enabled account-menu route inside the shared shell. The route renders the authenticated account settings page defined in `web-account-settings.md`.
  - **Search route:** `Search` renders a Figma-aligned page rather than a graph canvas. It supports two states within one route:
    - **Empty state:** The content slot presents the search bar as the primary centered control inside the shared shell body.
    - **Results state:** The page shows a top search bar row, a left-side results grid, and a right-side related-results panel.
  - **Projection rule:** Route content is projected from the approved desktop and mobile Figma frames as responsive layout structure rather than fixed viewport reproduction. Desktop uses the `1440px x 1024px` frame family as the full-size visual reference with the `320px` sidebar and `1120px` main content region at `2xl`; narrower desktop widths use the regular `240px`, `256px`, and `288px` sidebar steps at `md`, `lg`, and `xl`. Mobile uses the `440px x 956px` frame family with the `64px` header and stacked routed body below `md`.
  - **Search bar structure:** The search bar follows the approved component hierarchy. Desktop and mobile empty/results states use a `48px` high input, `8px` radius, white input fill, subtle neutral border, `16px` horizontal padding, `14px` text, and a `16px` search icon in a right decoration slot. Desktop constrains the search bar to `760px`; mobile fills the available content width.
  - **Search results structure:** Results stay stacked below the large breakpoint so medium-width screens can use the available width for the results grid instead of squeezing a sidebar. From the large breakpoint upward, results use the approved Figma `ResultsContent / Adaptive Grid` structure with a left results track and right related-results track. In the approved `1440px` desktop frame, the `320px` sidebar leaves an `1120px` main region; the content grid therefore uses a `3fr / 1fr` track relationship while the results card grid remains two columns. Three result-card columns are reserved for wider viewports where the left track can preserve the same visual card density without compressing card bodies. The right related-results panel must be a grid track participant with fill sizing, not a fixed-width sidebar. The results card list uses explicit responsive column counts that preserve one column on mobile, two result columns on small through standard desktop widths, and three result columns only when the available main region is wide enough to preserve the approved card proportions. Mobile and medium results use a stacked content area with related results below the results list. Search result cards and result-grid rows use a fixed `200px` height; if a title wraps and grows the header, the card body absorbs the remaining height through its own vertical overflow. Related-result items are componentized, use Hug-height behavior without an explicit minimum height token, wrap long labels inside the available title width, keep a tokenized `24px` right icon slot vertically centered against the full item height, and expand each list row instead of clipping or introducing horizontal title scrolling. Their `12px` horizontal padding, `8px` vertical padding, and `8px` internal gap are Figma variables mirrored by Tailwind theme tokens and are the source of the row's compact vertical rhythm. Results lists, related-results lists, and card bodies use content-driven overflow containers with thin native/themed scrollbar treatment where supported. The results grid includes an internal hover safe area so lifted and scaled cards plus the top-right arrow affordance remain visible inside the results scroll area, with an `8px` left inset so the first result column does not sit flush against the scroll viewport edge. Search result cards have no card shadow in default, hover, focus, or dimmed states so grid gaps remain the same page background color; cards and suggestions inherit their radius, border, typography, and internal vertical rhythm from the approved Figma structures rather than from generic shared surface defaults.
  - **Search edit affordance:** Search result cards include a `24px` edit icon button in the title row. The icon follows the approved square-pen/edit Figma component and uses an accessible label for suggesting edits.
  - **Search result-card query affordance:** Search result cards are clickable search affordances as well as suggestion surfaces. Activating the card body or title navigates to `/search` with the card title as the query, using the same URL query-state behavior as the related-results list. The edit icon remains a separate control for suggestion submission and does not trigger card-title search navigation.
  - **Search result-card title wrapping:** Search result card titles stay inside the title row width, wrap across lines when needed, and let the card header grow to fit wrapped title text. The edit icon remains fixed at the header's top-right edge, and the title search affordance remains active without introducing a horizontal title scrollbar.
  - **Search result-card hover state:** Result cards expose `Default`, `Hover`, and `Dimmed` visual states matching the approved Search Result Card Figma component set. In a populated result grid, hovering or focusing one result card slightly lifts and scales that card, strengthens its blue border emphasis, and shows a `24px` blue arrow affordance positioned at the card's top-right corner without adding a card shadow. Non-active sibling result cards remain readable at approximately `80%` opacity while the active card remains fully opaque. Keyboard focus on the card search affordance uses the same visual emphasis as pointer hover and preserves a visible focus outline.
  - **Related-result item hover state:** Related-result items expose `Default`, `Hover`, and `Dimmed` visual states matching the approved Related Result Item Figma component set. Hover or keyboard focus uses the same interaction language as Search result cards with a smaller lift and scale, strengthens the item border to the same blue emphasis, raises the white surface opacity, swaps the default gray chevron for a `24px` blue circular right-arrow affordance, and keeps non-active sibling related items readable at approximately `80%` opacity. The related-results scroll area keeps a small top/right safe area so this lower-amplitude motion does not clip against the scroll viewport.
  - **Authenticated suggestion dialog:** Authenticated edit activation opens the approved `Suggest edit` dialog, prefilled with the visible card title and content. The dialog submits `base_version`, `suggested_title`, and `suggested_content` through the Search web API adapter and never submits user identity.
  - **Anonymous sign-in-required dialog:** Anonymous edit activation opens the approved Sign In Required Dialog. Desktop uses Figma node `561:453`; mobile uses Figma node `561:610`. The dialog title is `Sign in to suggest edits`, the body is `Sign in to suggest changes and help improve this knowledge card.`, the primary action is `Sign in`, the sign-in form posts the current `/search` URL including query state as `return_to`, and the dialog includes close and scrim-dismiss behavior.
  - **Suggestion base-version state:** Search result contract data includes `node_id` and `current_version`. The frontend stores the card's `current_version` as the suggestion form `base_version` when the user opens or submits the edit flow.
  - **Search card text rule:** Search result card `title` and `content` render through the shared knowledge-card rich-text contract defined in `web-knowledge-card-rich-text.md`.
  - **Bundle loading boundaries:** The router lazy-loads route components so the startup bundle does not eagerly load Search rich-text rendering, React Flow, or deck.gl leaf rendering. The Search route lazy-loads result cards only when populated results render. `TaxonomyViewPage` lazy-loads leaf rendering only for leaf mode, and `LeafRenderer` lazy-loads the deck.gl scene implementation behind the leaf renderer. KaTeX CSS is loaded with the rich-text renderer rather than the global app stylesheet. Vite/Rolldown chunk configuration may split leaf-scene vendor dependencies to keep generated chunks below the production warning threshold, but it must not hide the issue by raising `chunkSizeWarningLimit`.
  - **Search state ownership:** Search state is URL-addressable. The absence of an effective query renders the empty state. The presence of a query renders the results layout.
  - **Visual language:** The shared shell uses a restrained product-shell style: Geist typography across default text and Tailwind font-family utilities, light sidebar/header surfaces, subtle dividers, large whitespace, quiet surfaces, and no extra decorative chrome beyond the approved Figma direction.
  - **Tailwind-first implementation rule:** Shared shell layout, navigation presentation, and Search page presentation are carried primarily through Tailwind utility classes colocated with the React tree. Handwritten CSS is reserved only for library-level overrides or effects that cannot be expressed cleanly through utilities.
- **Interactions:**
  - Navigating between `Overview`, `Graph View`, `Search`, and `Docs` uses primary route changes rather than local tab state.
  - Browser refresh and deep linking preserve the active route and the active Graph View taxonomy path.
  - The Graph View primary navigation item is active for `/graph` and every `/graph/<canonical-lcc-slug-path>` descendant route.
  - The mobile menu trigger opens the drawer; the close button, scrim, and route navigation close it.
  - Search query updates preserve the `/search` route and change only URL query state plus in-page layout state.
  - Activating a Search result card body or title updates the `/search` query state to the visible card title.
  - Activating the Search result card edit button opens the suggestion flow without changing the `/search` query state.
  - Search edit activation branches on browser-readable session state: authenticated users see the suggestion dialog; anonymous users see the sign-in-required dialog.
  - Suggestion submission posts through the BFF web API adapter and leaves the user's draft intact on failure.
  - The `GitHub` action links to the repository and displays the current Figma-approved star-count label until live star-count integration is added.
  - Anonymous auth action starts sign-in through the BFF endpoint with the current route as `return_to` so successful sign-in returns to the pre-login page. Authenticated account action opens a Figma-aligned menu. Clicking outside both the account button and the account menu closes the menu. `Dashboard` routes to `/dashboard`; `Settings` routes to `/settings`; `Sign out` posts to the BFF sign-out endpoint.

## Validation
- **Checks:**
  - The frontend uses one shared shell for `Overview`, `Graph View`, `Search`, `Docs`, `Dashboard`, and `Settings`.
  - Visiting `/` lands on `/overview`.
  - Desktop navigation renders from `md` upward as a persistent left sidebar with the approved brand, route navigation, footer actions, active route styling, and responsive `240px`, `256px`, `288px`, and `320px` widths at `md`, `lg`, `xl`, and `2xl`.
  - Mobile navigation renders below `md` as a `64px` header with a menu trigger and opens a `320px` drawer overlay with route navigation, footer actions, close behavior, and scrim close behavior.
  - Route navigation contains enabled `Overview`, `Graph View`, `Search`, and `Docs` links with only the active route highlighted.
  - The signed-in account button opens a menu with `Dashboard` navigation, `Settings` navigation, and a BFF-backed `Sign out` action.
  - The web client uses Geist as the app-wide primary font for browser default text and Tailwind font-family tokens.
  - `Overview` exists as a true routed placeholder page.
  - `Docs` exists as a true routed documentation hub page and is lazy-loaded behind the router boundary.
  - `Dashboard` renders the authenticated token-management page within the shared shell.
  - `Settings` renders the authenticated account settings page within the shared shell.
  - `Graph View` renders within the shared shell rather than owning a separate top-level header.
  - Visiting `/graph` renders the taxonomy root.
  - Visiting `/graph/<canonical-lcc-slug-path>` renders the branch or leaf node resolved by the taxonomy path endpoint.
  - Refreshing a deep Graph View path preserves the active taxonomy node when the path still resolves.
  - `Graph View` uses the approved desktop and mobile content-slot geometry from Figma frames `702:3845` and `702:3950`.
  - `Search` uses one route with URL-driven empty/results state switching instead of separate routes for each visual state.
  - The Search empty state uses the approved shell and places the search bar as the primary centered control.
  - The Search results state matches the approved top search row plus left results grid plus right related-results layout.
  - The Search results state uses responsive grid proportions and card vertical rhythm derived from the approved desktop and mobile Figma frames without fixed desktop card widths that can force horizontal overflow.
  - Search result cards and result-grid rows use the approved fixed `200px` height while the internal body region flexes below wrapped titles.
  - Search results, related results, and card-body scrolling are controlled by content overflow rather than static scrollbar decoration.
  - Search result card `title` and `content` use the shared knowledge-card rich-text renderer instead of raw string rendering.
  - Search result card titles wrap inside the title row and let the header grow for long titles without adding a horizontal title scrollbar.
  - Search result cards render edit icon buttons with accessible labels.
  - Search result cards expose the approved hover/focus presentation with lift, scale, blue border emphasis, top-right arrow affordance, no card shadow, and sibling cards dimmed to approximately `80%` opacity.
  - Related-result items wrap long labels, grow each item row to fit the wrapped text, keep tokenized padding/gap/icon sizing aligned with Figma variables, keep the right icon slot vertically centered, and expose hover/focus plus sibling-dim states aligned with the Search result card visual language.
  - Search result card hover and focus affordances remain visible inside the results scroll area for cards at the top edge and right edge of the grid.
  - Search result card body/title activation updates the `/search` URL query to the visible card title.
  - Search result card edit activation does not update the `/search` URL query.
  - Authenticated Search card edit activation opens a prefilled Suggest Edit Dialog.
  - Anonymous Search card edit activation opens the approved Sign In Required Dialog.
  - Suggestion submission payload includes `base_version`, `suggested_title`, and `suggested_content`, and excludes user identity fields.
  - Route components, Search result cards, leaf rendering, deck.gl scene code, and KaTeX styling stay behind explicit lazy-loading boundaries so unrelated routes do not pay those startup costs.
  - Production build emits no Vite chunk-size warning without increasing `chunkSizeWarningLimit`.
  - The Search icon is centered inside the approved right decoration slot rather than positioned through ad hoc offset utilities.
  - Shell-level styling is carried primarily by Tailwind utilities rather than large handwritten CSS blocks.
- **Evidence:**
  - Updated frontend route and page-shell implementation in `apps/web` reflects the shared shell contract.
  - Frontend verification covers route mounting, active-nav state, drawer behavior, and Search empty/results rendering.
  - Visual inspection confirms alignment with the approved Figma page structure.
