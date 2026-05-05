---
abstract: Public repository documentation design for README, developer docs, MCP docs, and product docs boundaries.
out_of_scope: Product feature behavior, deployment topology internals, and active module design specifications.
---

# Design: repository-publication-docs

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the public repository documentation boundary for the first public release of Humanity's Last Library.
- **Scope/Boundaries:** Covers the root README, repository developer docs, repository MCP docs, and the relationship between repository docs, web product docs, and active Orbital specs.
- **Related Requirements:** R-001, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Repository documentation must support one consistent contributor entrypoint, keep active docs synchronized with current truth, and preserve the distinction between public product access surfaces and internal service APIs.
- **Detail Commitments:** The root README is the concise public release entrypoint for Humanity's Last Library. Repository `docs/` files carry contributor and integration detail. The web app `/docs` route carries end-user MCP client setup guidance. Active `.orbital/specs/` documents remain implementation truth for project maintainers and are not the primary public-reader documentation entrypoint.
- **Update Rule:** Requirement-level governance remains stable while publication structure, README positioning, and repository docs placement stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Accepted project positioning: Humanity's Last Library is an upstream knowledge network for agents, maintained by humans.
  - Current system definition, module boundary, MCP public search, source-pipeline, and web docs design truth.
  - Current root Makefile and repository script command contracts.
- **Outputs:**
  - A concise root README for public release readers.
  - Repository developer documentation for local setup, command usage, contracts, and tests.
  - Repository MCP documentation for service boundary, tool surface, authentication model, and integration notes.
  - Explicit links that keep detailed runbook material out of the README.
- **Artifacts:**
  - `README.md`
  - `docs/development.md`
  - `docs/mcp.md`
  - Web app `/docs` product route for end-user MCP client setup.

## Design Approach
- **Approach:** Use a vision-first, technical-proof-second README. The README introduces the project as agent-era knowledge infrastructure, states the current limits clearly, summarizes the architecture briefly, and links out to detailed docs.
- **Key Elements:**
  - **Project name:** The public name is `Humanity's Last Library`.
  - **Subtitle:** The public subtitle is `An upstream knowledge network for agents, maintained by humans.`
  - **README role:** The README explains why the project exists, the project bet, how the system works, current capabilities, current limits, architecture at a glance, documentation entrypoints, development quickstart, and project status.
  - **Project-bet rule:** The README states the hypothesis that large models may perform better when more factual knowledge lives in an external, incrementally updateable, maintained knowledge network and the model learns how to retrieve, judge, and use that context instead of memorizing every fact in parameters.
  - **Current-limits rule:** The README states that the first corpus is bootstrapped from Wikipedia-derived material and that AI-assisted extraction is a real limitation relative to the long-term principle of human-maintained quality.
  - **No overclaiming rule:** The README must not claim that the initial corpus creates novel knowledge, solves knowledge quality immediately, or has a mature optimization loop beyond current MCP usage ledger and agent-search analytics capture.
  - **How-it-works scope:** The README describes atomic cards, relations, human proposal/review maintenance, MCP/Search agent consumption, and agent usage signals as the top-level mechanisms.
  - **Repository docs boundary:** `docs/development.md` owns local setup, environment, command, contract, and test guidance.
  - **MCP docs boundary:** `docs/mcp.md` owns the repository-level public MCP service overview and integration notes.
  - **Web docs boundary:** The web app `/docs` route remains the end-user MCP client setup surface for Codex, Claude Code, and OpenClaw, and README links to the production docs route.
  - **Specs boundary:** `.orbital/specs/` remains active design truth for maintainers and is not presented as the main public documentation path.
- **Interactions:**
  1. A public reader starts at `README.md`.
  2. A contributor follows README links to `docs/development.md`.
  3. An integrator follows README links to `docs/mcp.md`.
  4. An end user follows the web app `/docs` route for client-specific MCP setup.
  5. Maintainers use `.orbital/specs/` when changing behavior or architecture.

## Validation
- **Checks:**
  - README title, subtitle, and positioning match the accepted project framing.
  - README project-bet section frames parameter-memory reduction, external retrieval, responsibility separation, and incremental knowledge updates as a working hypothesis rather than a settled claim.
  - README current-limits section states the AI-assisted bootstrap and Wikipedia-derived corpus limitations without presenting them as solved.
  - README links to repository developer docs, repository MCP docs, and the web product docs boundary.
  - Repository docs do not contradict the root Makefile or repository script command contracts.
  - No generated contract, source code, runtime behavior, or API behavior changes are introduced by this documentation update.
- **Evidence:**
  - Markdown files contain complete front matter where repository templates require it.
  - Repository documentation is organized into README, `docs/development.md`, and `docs/mcp.md`.
  - Active specs remain synchronized with the accepted publication documentation boundary.
