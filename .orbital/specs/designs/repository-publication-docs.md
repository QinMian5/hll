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
- **Purpose:** Define the public repository documentation and licensing boundary for the first public release of Humanity's Last Library.
- **Scope/Boundaries:** Covers the root README, repository developer docs, repository MCP docs, repository licensing docs, and the relationship between repository docs, web product docs, and active Orbital specs.
- **Related Requirements:** R-001, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Repository documentation must support one consistent contributor entrypoint, keep active docs synchronized with current truth, and preserve the distinction between public product access surfaces and internal service APIs.
- **Detail Commitments:** The root README is the concise public release entrypoint for Humanity's Last Library. Repository `docs/` files carry contributor, integration, and licensing detail. The web app `/docs` route carries end-user MCP client setup guidance. Active `.orbital/specs/` documents remain implementation truth for project maintainers and are not the primary public-reader documentation entrypoint.
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
  - Repository licensing documentation that separates software code licensing from knowledge-content and data licensing.
  - Explicit links that keep detailed runbook material out of the README.
- **Artifacts:**
  - `README.md`
  - `LICENSE`
  - `NOTICE`
  - `DATA_LICENSE.md`
  - `docs/development.md`
  - `docs/mcp.md`
  - `docs/licensing.md`
  - Web app `/docs` product route for end-user MCP client setup.

## Design Approach
- **Approach:** Use a vision-first, technical-proof-second README. The README introduces the project as agent-era knowledge infrastructure, states the current limits clearly, summarizes the public workflow briefly, and links out to detailed docs.
- **Key Elements:**
  - **Project name:** The public name is `Humanity's Last Library`.
  - **Subtitle:** The public subtitle is `A human-maintained knowledge network that agents can search, cite, and use.`
  - **Top presentation:** The README starts with a centered GitHub-renderable header containing the project name, subtitle, and a Website link.
  - **README role:** The README explains what the project is, why it exists, the project bet, how the system works, current public capabilities, current limits, documentation entrypoints, licensing, and project status.
  - **Visual placement:** The README does not use a standalone visual-overview block at the top. The memorization-to-retrieval visual appears inside `The Bet`, and the knowledge-loop visual appears inside `How It Works`.
  - **Code license:** Repository software source, configuration, generated contract clients, scripts, and developer documentation are licensed under Apache-2.0 unless a file or directory states otherwise.
  - **Data license boundary:** Knowledge-card content, source-derived datasets, exported database snapshots, and archived data artifacts are governed separately by `DATA_LICENSE.md`.
  - **Default knowledge-content license:** Repository-distributed knowledge content and source-derived datasets default to CC BY-SA 4.0 unless a more specific source license or artifact-level notice applies.
  - **Project-bet rule:** The README states the hypothesis that large models may perform better when more factual knowledge lives in an external, incrementally updateable, maintained knowledge network and the model learns how to retrieve, judge, and use that context instead of memorizing every fact in parameters.
  - **Current-limits rule:** The README states that the first corpus is bootstrapped from Wikipedia-derived material and that AI-assisted extraction is a real limitation relative to the long-term principle of human-maintained quality.
  - **No overclaiming rule:** The README must not claim that the initial corpus creates novel knowledge, solves knowledge quality immediately, or has a mature optimization loop beyond current MCP usage ledger and agent-search analytics capture.
  - **How-it-works scope:** The README describes human review, the knowledge network, agent retrieval, and query-path signals as the top-level public workflow.
  - **Capabilities scope:** The README presents capabilities from a public reader and agent-user perspective. Private service APIs, generated internal clients, source-pipeline internals, and detailed runbooks belong in linked docs rather than the root README.
  - **Repository docs boundary:** `docs/development.md` owns local setup, environment, command, contract, and test guidance.
  - **MCP docs boundary:** `docs/mcp.md` owns the repository-level public MCP service overview and integration notes.
  - **Licensing docs boundary:** `docs/licensing.md` owns the public human-readable license summary, while `LICENSE`, `NOTICE`, and `DATA_LICENSE.md` own the operative repository license notices.
  - **Web docs boundary:** The web app `/docs` route remains the end-user MCP client setup surface for Codex, Claude Code, and OpenClaw, and README links to the production docs route.
  - **Specs boundary:** `.orbital/specs/` remains active design truth for maintainers and is not presented as the main public documentation path.
- **Interactions:**
  1. A public reader starts at `README.md`.
  2. A contributor follows README links to `docs/development.md`.
  3. An integrator follows README links to `docs/mcp.md`.
  4. An end user follows the web app `/docs` route for client-specific MCP setup.
  5. A reuser follows README links to `docs/licensing.md`, then reads `LICENSE`, `NOTICE`, and `DATA_LICENSE.md` for license details.
  6. Maintainers use `.orbital/specs/` when changing behavior or architecture.

## Validation
- **Checks:**
  - README title, subtitle, and positioning match the accepted project framing.
  - README project-bet section frames parameter-memory reduction, external retrieval, responsibility separation, and incremental knowledge updates as a working hypothesis rather than a settled claim.
  - README current-limits section states the AI-assisted bootstrap and Wikipedia-derived corpus limitations without presenting them as solved.
  - README links to the public website, repository developer docs, repository MCP docs, and the web product docs boundary.
  - README links to the licensing guide and states the software/data license split without treating source-derived knowledge data as Apache-licensed code.
  - `LICENSE`, `NOTICE`, `DATA_LICENSE.md`, and `docs/licensing.md` exist and do not contradict the accepted code/data boundary.
  - Repository docs do not contradict the root Makefile or repository script command contracts.
  - No generated contract, source code, runtime behavior, or API behavior changes are introduced by this documentation and licensing update.
- **Evidence:**
  - Markdown files contain complete front matter where repository templates require it.
  - Repository documentation is organized into README, `docs/development.md`, `docs/mcp.md`, and `docs/licensing.md`.
  - Repository licensing is organized into root code license, NOTICE, and data-license boundary files.
  - Active specs remain synchronized with the accepted publication documentation boundary.
