# Humanity's Last Library

An upstream knowledge network for agents, maintained by humans.

Humanity's Last Library is a knowledge infrastructure project for the agent era.
Agents are the downstream users: they search, retrieve, cite, and act on structured
knowledge. Humans are the upstream maintainers: they review, correct, organize,
and improve the knowledge network.

The long-term goal is a feedback loop: high-quality human-maintained knowledge is
consumed by many agents, and aggregate agent usage signals help improve retrieval,
knowledge structure, and maintenance priorities over time.

## Why It Exists

Most public knowledge is packaged for human reading: pages, articles, search
results, and documentation sites. Agents can use those sources, but they often
need a different upstream shape: stable units of knowledge, explicit relations,
reviewable maintenance, and retrieval surfaces designed for machine consumption.

This project does not try to build another encyclopedia. It explores whether
knowledge can be represented as a maintained network that agents can consume
through explicit protocols, while humans remain responsible for quality.

## The Bet

Large language models carry a great deal of knowledge inside their parameters.
That has made them powerful, but it also makes knowledge updates expensive,
slow, and hard to inspect.

This project explores a different boundary: what if models did not need to
memorize as much factual knowledge, and instead learned how to find the right
knowledge from an external, maintained network?

If knowledge lives in a network of cards, relations, reviews, and usage signals,
then updating knowledge becomes an incremental operation instead of a full
retraining problem. New facts, corrections, and better structure can be added
directly to the knowledge layer. The model's role can shift from remembering
everything to knowing how to retrieve, judge, and use the right context.

## How It Works

- **Atomic knowledge cards:** each card represents one focused knowledge unit.
- **Relations between cards:** links make local context and neighboring concepts
  retrievable instead of leaving every result isolated.
- **Human maintenance:** proposals, reviews, and apply audits keep formal changes
  accountable.
- **Agent consumption:** public MCP search and web-backed search expose the
  knowledge network to downstream users and clients.
- **Usage signals:** successful MCP search calls and agent-search events are
  recorded today so future offline analysis can improve retrieval and knowledge
  organization.

## Current Capabilities

- A public web application for browsing, search, account flows, and docs.
- A public remote MCP service with a `search` tool for agent clients.
- A private FastAPI service that owns search, ingestion, proposals, and graph
  read surfaces.
- Contract-driven internal clients generated from the authoritative OpenAPI
  snapshot.
- A source pipeline for bootstrapping candidate cards from external source
  material.
- MCP usage ledger storage for successful, quota-rejected, and search-error
  outcomes, plus agent-search analytics for successful agent search activity.

## Current Limits

This project does not claim that its first corpus is more original or more
authoritative than the sources it is built from. The initial data is bootstrapped
from Wikipedia-derived material, and much of the card creation process still
depends on AI-assisted extraction.

That is a real limitation. It does not fully match the long-term principle of a
knowledge network maintained by humans.

For now, the project is primarily an architectural experiment: a way to test
whether knowledge can be represented, reviewed, searched, consumed by agents, and
improved through usage signals inside a better system boundary. The bet is not
that the first dataset is special. The bet is that the structure can become
better as humans maintain it and agents use it.

## Architecture At A Glance

- `apps/web` serves the browser application and BFF boundary.
- `apps/mcp` serves the public remote MCP endpoint for agent clients.
- `apps/api` owns the private API for search, ingestion, proposals, and graph
  reads.
- The knowledge graph stores cards, formal versions, relations, proposals,
  reviews, and apply audits.
- `apps/source_pipeline` bootstraps candidate cards and hands accepted cards to
  ingestion.
- `packages/contracts` stores OpenAPI snapshots and generated client artifacts.
- Docker Compose and root `Makefile` commands provide the local execution
  contract.

## Documentation

- [Development guide](docs/development.md): local setup, commands, contracts, and
  tests.
- [MCP integration notes](docs/mcp.md): service boundary, authentication model,
  tool surface, and development endpoint.
- [Web MCP client setup](https://knowledge.orbitalis.org/docs): the product
  docs route for end-user MCP client setup.

## Development Quickstart

```bash
make bootstrap
make dev-up
make test
make check
```

In development, `make dev-up` refreshes development API data from the bootstrap
snapshot and exposes the MCP service at `http://localhost:8002/mcp`.

## Project Status

Humanity's Last Library is under active development and is being prepared for an
early public release. The current public programmatic surface is the MCP `search`
tool. Private REST APIs, internal pipelines, and data models are still project
implementation details unless documented otherwise.

This is a working hypothesis, not a settled claim. The goal is to make the
assumptions inspectable, discussable, and easier to improve.
