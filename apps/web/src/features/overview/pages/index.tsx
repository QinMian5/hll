// abstract: Routed project-introduction page for the public Overview view.
// out_of_scope: Live product metrics, backend data integration, and repository documentation content.

import { Link } from "@tanstack/react-router";
import {
  BookOpen,
  CircleDot,
  Gauge,
  GitPullRequest,
  type LucideIcon,
  Network,
  Search,
} from "lucide-react";

interface EntryPoint {
  readonly description: string;
  readonly Icon: LucideIcon;
  readonly title: string;
  readonly to: "/dashboard" | "/docs" | "/graph" | "/search" | "/workspace";
}

interface OverviewImageProps {
  readonly alt: string;
  readonly height: number;
  readonly loading?: "eager" | "lazy";
  readonly src: string;
  readonly width: number;
}

interface Principle {
  readonly description: string;
  readonly title: string;
}

const principles: readonly Principle[] = [
  {
    description:
      "Train models to find sources instead of carrying every fact in their parameters.",
    title: "Retrieval over memorization",
  },
  {
    description:
      "Proposals pass through review before they shape the formal knowledge network.",
    title: "Human-reviewed updates",
  },
  {
    description:
      "Query paths show which links and structures deserve attention.",
    title: "Usage-informed structure",
  },
];

const entryPoints: readonly EntryPoint[] = [
  {
    description: "Query knowledge cards and discover connected concepts.",
    Icon: Search,
    title: "Search",
    to: "/search",
  },
  {
    description: "Browse taxonomy branches and local graph context.",
    Icon: Network,
    title: "Graph View",
    to: "/graph",
  },
  {
    description: "Connect agent clients to the public MCP search surface.",
    Icon: BookOpen,
    title: "Docs",
    to: "/docs",
  },
  {
    description: "Manage MCP tokens and inspect account quota after sign-in.",
    Icon: Gauge,
    title: "Dashboard",
    to: "/dashboard",
  },
  {
    description: "Track human-originated card proposals after sign-in.",
    Icon: GitPullRequest,
    title: "Workspace",
    to: "/workspace",
  },
];

function OverviewImage({
  alt,
  height,
  loading = "lazy",
  src,
  width,
}: OverviewImageProps) {
  return (
    <img
      alt={alt}
      className="block h-auto w-full self-center rounded-lg border border-knowledge-border-card bg-knowledge-surface-card-solid"
      decoding="async"
      height={height}
      loading={loading}
      src={src}
      width={width}
    />
  );
}

function PrincipleList() {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {principles.map((principle) => (
        <article
          className="rounded-lg border border-knowledge-border-card bg-knowledge-surface-card p-4"
          key={principle.title}
        >
          <CircleDot
            aria-hidden="true"
            className="mb-3 size-5 text-knowledge-brand"
            strokeWidth={2}
          />
          <h3 className="m-0 text-knowledge-overview-card-title font-semibold text-knowledge-text-default">
            {principle.title}
          </h3>
          <p className="mt-2 mb-0 text-knowledge-caption text-knowledge-text-muted">
            {principle.description}
          </p>
        </article>
      ))}
    </div>
  );
}

function EntryPointGrid() {
  return (
    <section
      aria-labelledby="overview-entry-points-title"
      className="flex flex-col gap-3"
    >
      <div>
        <h2
          className="m-0 text-knowledge-overview-section-title font-semibold text-knowledge-text-default"
          id="overview-entry-points-title"
        >
          What you can use now
        </h2>
        <p className="mt-1 mb-0 text-knowledge-body text-knowledge-text-muted">
          The current product surface is small, but each route maps to a real
          project boundary.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {entryPoints.map((entry) => {
          const Icon = entry.Icon;

          return (
            <Link
              aria-label={`Open ${entry.title} from Overview`}
              className="group flex min-h-knowledge-overview-entry-height flex-col justify-between rounded-lg border border-knowledge-border-card bg-knowledge-surface-card p-4 text-left no-underline transition-colors hover:border-docs-border-accent hover:bg-knowledge-surface-accent-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              key={entry.title}
              to={entry.to}
            >
              <span className="flex items-center gap-3">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-knowledge-surface-accent-soft text-knowledge-brand group-hover:bg-knowledge-surface-card-solid">
                  <Icon aria-hidden="true" className="size-5" strokeWidth={2} />
                </span>
                <span className="text-knowledge-overview-card-title font-semibold text-knowledge-text-default">
                  {entry.title}
                </span>
              </span>
              <span className="text-knowledge-caption text-knowledge-text-muted">
                {entry.description}
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

function CurrentLimits() {
  return (
    <section
      aria-labelledby="overview-limits-title"
      className="rounded-lg border border-knowledge-border-card bg-knowledge-surface-card-solid p-4 lg:p-5"
    >
      <h2
        className="m-0 text-knowledge-overview-section-title font-semibold text-knowledge-text-default"
        id="overview-limits-title"
      >
        Current limits
      </h2>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {[
          "The first corpus is Wikipedia-derived, so the initial knowledge is not novel by itself.",
          "Card creation still depends on AI-assisted extraction, which does not yet match the long-term principle of human-maintained quality.",
          "This is an architecture experiment, not proof that the knowledge quality problem is already solved.",
        ].map((limit) => (
          <p
            className="m-0 rounded-lg bg-knowledge-muted-surface p-3 text-knowledge-caption text-knowledge-text-muted"
            key={limit}
          >
            {limit}
          </p>
        ))}
      </div>
    </section>
  );
}

export function OverviewPage() {
  return (
    <main
      className="h-full min-h-0 overflow-y-auto px-knowledge-page-padding-x pt-knowledge-page-padding-top pb-knowledge-page-padding-bottom lg:px-knowledge-page-padding-x-desktop lg:pt-knowledge-page-padding-top-desktop lg:pb-knowledge-page-padding-bottom-desktop"
      data-testid="overview-route-page"
    >
      <div className="mx-auto flex w-full max-w-knowledge-overview-rail-width flex-col gap-knowledge-page-content-gap">
        <section className="grid gap-5">
          <div className="flex min-w-0 flex-col justify-center rounded-lg border border-knowledge-border-card bg-knowledge-surface-card-solid p-5 lg:p-6">
            <h1 className="m-0 max-w-knowledge-overview-hero-title-width text-knowledge-overview-hero-title font-semibold text-knowledge-text-default lg:text-knowledge-overview-hero-title-desktop">
              Humanity's Last Library
            </h1>
            <p className="mt-4 mb-0 max-w-none text-knowledge-overview-subtitle font-medium text-knowledge-text-default">
              A human-maintained knowledge network for agents to search, cite,
              and use.
            </p>
          </div>

          <OverviewImage
            alt="Knowledge Loop diagram showing human review upstream of atomic knowledge, the knowledge network, agent retrieval, and query-path usage signals"
            height={1024}
            loading="eager"
            src="/overview/knowledge-loop.png"
            width={1536}
          />
        </section>

        <section aria-labelledby="overview-thesis-title" className="grid gap-5">
          <div className="flex flex-col gap-3">
            <div>
              <h2
                className="m-0 text-knowledge-overview-section-title font-semibold text-knowledge-text-default"
                id="overview-thesis-title"
              >
                Project thesis
              </h2>
              <p className="mt-1 mb-0 text-knowledge-body text-knowledge-text-muted">
                Models reason, humans maintain, and the network carries
                incrementally updated facts.
              </p>
            </div>
            <PrincipleList />
          </div>

          <OverviewImage
            alt="From Memorization to Retrieval diagram comparing memorized facts in model parameters with search over a human-maintained knowledge network"
            height={1086}
            src="/overview/from-memorization-to-retrieval.png"
            width={1448}
          />
        </section>

        <EntryPointGrid />
        <CurrentLimits />

        <section className="rounded-lg border border-knowledge-border-card bg-knowledge-surface-accent-soft p-4 lg:p-5">
          <h2 className="m-0 text-knowledge-overview-section-title font-semibold text-knowledge-text-default">
            Why it matters
          </h2>
          <p className="mt-2 mb-0 max-w-knowledge-overview-summary-width text-knowledge-body text-knowledge-text-muted">
            If knowledge can be updated as a maintained network, new facts,
            corrections, and better structure become incremental updates instead
            of model retraining events.
          </p>
        </section>
      </div>
    </main>
  );
}
