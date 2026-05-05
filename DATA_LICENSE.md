---
abstract: Licensing boundary for knowledge content, source-derived datasets, snapshots, and archived data artifacts.
out_of_scope: Software source code, runtime service behavior, and legal advice.
---

# Data License

This document defines the repository-level licensing boundary for data and
knowledge content. It is not legal advice.

## Code vs. Data

The root `LICENSE` applies to software source, configuration, generated contract
clients, scripts, and developer documentation unless a file, directory, or
accompanying notice states otherwise.

This document applies to non-code materials, including:

- knowledge-card titles, content, versions, relation data, taxonomy assignment
  data, and graph snapshots;
- exported database snapshots such as API bootstrap dumps when they contain
  knowledge content;
- source-derived corpus records, source-selection outputs, and archived data
  artifacts;
- metadata that is distributed as part of a knowledge dataset rather than as
  software configuration.

## Default Knowledge Content License

Unless a more specific source license or artifact-level notice applies,
repository-distributed knowledge content and source-derived datasets are
provided under the Creative Commons Attribution-ShareAlike 4.0 International
License:

https://creativecommons.org/licenses/by-sa/4.0/

Reusers must comply with that license, including attribution and share-alike
requirements.

## Wikipedia-Derived Material

The first corpus is bootstrapped from Wikipedia-derived material and
AI-assisted extraction. Wikipedia text is generally available under Creative
Commons Attribution-ShareAlike terms and may also carry additional attribution
or source-specific requirements.

When reusing or redistributing repository data that is derived from Wikipedia or
other third-party sources, preserve available source attribution such as page
URLs, source URLs, page identifiers, revision metadata, and artifact notices.
If an upstream source requires different or additional terms, those upstream
terms govern that source-derived portion.

## Contributions

By contributing knowledge content or source-derived data to this repository, you
represent that you have the rights needed to submit it and that it can be
distributed under CC BY-SA 4.0 or a compatible license unless explicitly marked
otherwise before submission.

Contributions of software source remain governed by the root `LICENSE`.

## No Warranty

Data and knowledge content are provided as-is. The project does not warrant that
knowledge content is complete, accurate, non-infringing, or suitable for any
particular use.
