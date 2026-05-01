// abstract: Figma-aligned dashboard quota summary panel.
// out_of_scope: Dashboard quota fetching and token directory rendering.

import type { DashboardQuotaSummary, DashboardQuotaWindow } from "../types";

interface QuotaSummaryProps {
  readonly errorMessage?: string | null;
  readonly isLoading: boolean;
  readonly quota: DashboardQuotaSummary | null;
  readonly quotaAvailable: boolean;
}

function formatQuotaNumber(value: number): string {
  return value.toLocaleString("en-US");
}

function quotaValue(window: DashboardQuotaWindow): string {
  return `${formatQuotaNumber(window.used)} / ${formatQuotaNumber(
    window.limit,
  )}`;
}

function resetCopy(resetAt: string | null): string | null {
  if (resetAt === null) {
    return null;
  }

  const diffMs = new Date(resetAt).getTime() - Date.now();

  if (!Number.isFinite(diffMs) || diffMs <= 0) {
    return "resets soon";
  }

  const totalMinutes = Math.ceil(diffMs / 60_000);
  const totalHours = Math.ceil(totalMinutes / 60);

  if (totalHours >= 48) {
    return `resets in ${Math.ceil(totalHours / 24)}d`;
  }

  if (totalHours >= 1) {
    return `resets in ${totalHours}h`;
  }

  return `resets in ${totalMinutes}m`;
}

function progressPercent(window: DashboardQuotaWindow): number {
  if (window.limit <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(100, (window.used / window.limit) * 100));
}

function QuotaMetric({
  label,
  window,
}: {
  readonly label: "Daily" | "Weekly";
  readonly window: DashboardQuotaWindow;
}) {
  const resetText = resetCopy(window.resetAt);

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-knowledge-dashboard-quota-metric-gap overflow-hidden">
      <div className="flex min-w-0 items-center">
        <span className="min-w-0 flex-1 text-knowledge-dashboard-quota-label font-medium text-knowledge-text-muted lg:text-knowledge-caption">
          {label}
        </span>
      </div>
      <span className="min-w-0 text-knowledge-dashboard-quota-value font-semibold text-knowledge-text-default lg:text-knowledge-dashboard-quota-value-desktop">
        {quotaValue(window)}
      </span>
      <div className="h-1.5 w-full overflow-hidden rounded-knowledge-control bg-knowledge-surface-accent-soft">
        <div
          aria-label={`${label} quota usage`}
          className="h-1.5 rounded-knowledge-control bg-knowledge-brand"
          role="progressbar"
          style={{ width: `${progressPercent(window)}%` }}
        />
      </div>
      {resetText !== null ? (
        <span className="min-w-0 truncate text-knowledge-dashboard-microcopy text-knowledge-text-muted lg:text-knowledge-dashboard-microcopy-desktop">
          {resetText}
        </span>
      ) : null}
    </div>
  );
}

function QuotaPlaceholder({
  children,
}: {
  readonly children: React.ReactNode;
}) {
  return (
    <div className="flex h-knowledge-dashboard-quota-metric-height items-center justify-center text-knowledge-caption text-knowledge-text-muted lg:h-knowledge-dashboard-quota-metric-height-desktop lg:text-knowledge-body">
      {children}
    </div>
  );
}

export function QuotaSummary({
  errorMessage,
  isLoading,
  quota,
  quotaAvailable,
}: QuotaSummaryProps) {
  const showUnavailable =
    errorMessage !== null || !quotaAvailable || (!isLoading && quota === null);

  return (
    <section
      className="flex shrink-0 flex-col gap-knowledge-dashboard-section-gap overflow-hidden rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-knowledge-dashboard-surface-padding"
      data-testid="dashboard-quota-summary"
    >
      <div className="flex h-knowledge-dashboard-toolbar-height shrink-0 items-center overflow-hidden">
        <h2 className="m-0 min-w-0 flex-1 text-knowledge-dashboard-card-title font-semibold text-knowledge-text-default lg:text-knowledge-dashboard-card-title-desktop">
          Quota
        </h2>
      </div>

      {isLoading ? <QuotaPlaceholder>Loading quota</QuotaPlaceholder> : null}
      {!isLoading && showUnavailable ? (
        <QuotaPlaceholder>
          {errorMessage ?? "Quota unavailable."}
        </QuotaPlaceholder>
      ) : null}
      {!isLoading && !showUnavailable && quota !== null ? (
        <div className="grid h-knowledge-dashboard-quota-metric-height min-w-0 grid-cols-[var(--knowledge-dashboard-quota-grid)] items-center gap-knowledge-dashboard-section-gap overflow-hidden lg:h-knowledge-dashboard-quota-metric-height-desktop">
          <QuotaMetric label="Daily" window={quota.daily} />
          <div className="h-full w-px bg-knowledge-border-subtle" />
          <QuotaMetric label="Weekly" window={quota.weekly} />
        </div>
      ) : null}
    </section>
  );
}
