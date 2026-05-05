---
abstract: Human-readable licensing guide for software, documentation, and knowledge data in the public repository.
out_of_scope: Legal advice, contribution policy enforcement, and third-party license inventory automation.
---

# Licensing

Humanity's Last Library uses separate license boundaries for code and knowledge
data.

## Software

Repository software is licensed under the Apache License, Version 2.0. This
includes source code, scripts, configuration, generated contract clients, Docker
assets, and developer documentation unless a file or directory states otherwise.

Apache-2.0 is the project default because this repository is infrastructure for
public web and MCP access surfaces. The license is permissive, widely accepted,
and includes an explicit patent grant.

## Data and Knowledge Content

Knowledge-card content, source-derived datasets, exported database snapshots,
and archived data artifacts are not covered by the Apache-2.0 code license.
They are governed by `DATA_LICENSE.md`.

The repository default for distributed knowledge content and source-derived data
is Creative Commons Attribution-ShareAlike 4.0 International unless a more
specific source license or artifact-level notice applies.

## Wikipedia-Derived Material

The first corpus is bootstrapped from Wikipedia-derived material and
AI-assisted extraction. Reusers should preserve available source attribution,
including page URLs, source URLs, page identifiers, revision metadata, and
artifact notices when present.

## Trademarks

The Apache-2.0 license does not grant trademark rights. Project names, service
names, logos, and domain names may be used only as needed to identify the origin
of the software or as otherwise permitted by the project owner.

## Summary

- Code: Apache-2.0.
- Knowledge content and source-derived data: see `DATA_LICENSE.md`.
- Third-party source material: comply with the original source license and
  attribution requirements.
