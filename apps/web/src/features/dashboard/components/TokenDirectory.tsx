// abstract: Figma-aligned token directory table with a fixed header and scrollable row viewport.
// out_of_scope: Token mutation dialog state and BFF request orchestration.

import { Button } from "../../../shared/ui/button";
import { ScrollArea } from "../../../shared/ui/scroll-area";
import { cn } from "../../../shared/utils";
import type { DashboardTokenRow } from "../types";
import {
  CopyTokenButton,
  DeleteTokenButton,
  RenameTokenButton,
} from "./TokenActions";

interface TokenDirectoryProps {
  readonly copiedTokenName: string | null;
  readonly errorMessage?: string | null;
  readonly isLoading: boolean;
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onCreate: () => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly tokens: readonly DashboardTokenRow[];
  readonly usageAvailable: boolean;
}

const tokenTableGridClasses =
  "grid-cols-[var(--knowledge-dashboard-table-grid-mobile)] grid-rows-[var(--knowledge-dashboard-table-row-template-mobile)] lg:grid-cols-[var(--knowledge-dashboard-table-grid-desktop)] lg:grid-rows-[var(--knowledge-dashboard-table-row-template-desktop)]";
const tokenTableRowClasses = cn(
  "grid h-knowledge-dashboard-table-row-height w-full shrink-0 overflow-hidden py-knowledge-dashboard-table-row-padding-y",
  "gap-x-knowledge-dashboard-table-row-gap gap-y-knowledge-dashboard-table-row-gap",
  "lg:h-knowledge-dashboard-table-row-height-desktop lg:gap-x-0 lg:gap-y-0 lg:py-0",
  tokenTableGridClasses,
);
const tokenTableScrollAreaTheme =
  "[--scroll-area-padding-right:var(--spacing-knowledge-dashboard-scrollbar-width)] [--scroll-area-scrollbar-width:var(--spacing-knowledge-dashboard-scrollbar-width)]";

export function formatUsageCount(value: number | null): string {
  if (value === null) {
    return "Unavailable";
  }

  if (value >= 1000) {
    const formatted = (value / 1000).toFixed(value >= 10_000 ? 1 : 1);
    return `${formatted.replace(/\.0$/, "")}k`;
  }

  return value.toLocaleString("en-US");
}

export function formatLastUsedAt(value: string | null): string {
  if (value === null) {
    return "Unused";
  }

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}

function DirectoryState({
  children,
  role,
}: {
  readonly children: React.ReactNode;
  readonly role?: "alert";
}) {
  return (
    <div
      className="flex min-h-knowledge-dashboard-empty-state-height items-center justify-center rounded-knowledge-surface border border-dashed border-knowledge-border-card text-knowledge-body text-knowledge-text-muted"
      role={role}
    >
      {children}
    </div>
  );
}

function LoadingRows() {
  return (
    <>
      {[0, 1, 2].map((index) => (
        <div
          className="flex w-full shrink-0 flex-col items-start overflow-hidden"
          key={index}
        >
          <div className={cn(tokenTableRowClasses, "animate-pulse")}>
            <span className="col-start-1 row-start-1 h-3 rounded-full bg-knowledge-surface-hover lg:col-start-1 lg:row-start-1" />
            <span className="col-span-2 col-start-1 row-start-2 h-3 rounded-full bg-knowledge-surface-hover lg:col-span-1 lg:col-start-2 lg:row-start-1" />
            <span className="col-start-1 row-start-3 h-3 rounded-full bg-knowledge-surface-hover lg:col-start-3 lg:row-start-1" />
            <span className="col-start-2 row-start-3 h-3 rounded-full bg-knowledge-surface-hover lg:col-start-4 lg:row-start-1" />
          </div>
          {index < 2 ? (
            <div className="h-px w-full shrink-0 bg-knowledge-divider-subtle" />
          ) : null}
        </div>
      ))}
    </>
  );
}

function TokenRowGroup({
  copiedTokenName,
  isLast,
  onCopy,
  onDelete,
  onRename,
  token,
}: {
  readonly copiedTokenName: string | null;
  readonly isLast: boolean;
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly token: DashboardTokenRow;
}) {
  return (
    <div
      className="flex w-full shrink-0 flex-col items-start overflow-hidden"
      data-testid="dashboard-token-row-group"
    >
      <div className={cn(tokenTableRowClasses, "text-knowledge-text-default")}>
        <div className="col-start-1 row-start-1 flex min-w-0 items-center gap-knowledge-dashboard-table-row-gap overflow-hidden lg:col-start-1 lg:row-start-1">
          <span className="truncate text-knowledge-dashboard-card-title font-semibold text-knowledge-text-default lg:text-knowledge-body lg:font-normal">
            {token.name}
          </span>
          <RenameTokenButton onRename={onRename} token={token} />
        </div>
        <div className="col-span-2 col-start-1 row-start-2 flex min-w-0 items-center gap-knowledge-dashboard-table-row-gap overflow-hidden lg:col-span-1 lg:col-start-2 lg:row-start-1">
          <span className="min-w-0 truncate text-knowledge-dashboard-card-body font-normal text-knowledge-text-muted lg:text-knowledge-body">
            {token.maskedToken}
          </span>
          <CopyTokenButton
            isCopied={copiedTokenName === token.name}
            onCopy={onCopy}
            token={token}
          />
        </div>
        <div className="col-start-1 row-start-3 flex min-w-0 items-center overflow-hidden lg:col-start-3 lg:row-start-1">
          <span className="min-w-0 flex-1 truncate text-knowledge-caption font-medium text-knowledge-text-default lg:text-knowledge-body lg:font-normal">
            {formatUsageCount(token.usageCount)}
          </span>
        </div>
        <div className="col-start-2 row-start-3 flex min-w-0 items-center justify-end overflow-hidden lg:col-start-4 lg:row-start-1 lg:justify-start">
          <span className="min-w-0 flex-1 truncate text-right text-knowledge-caption font-medium text-knowledge-text-muted lg:text-left lg:text-knowledge-body lg:font-normal">
            {formatLastUsedAt(token.lastUsedAt)}
          </span>
        </div>
        <div className="col-start-2 row-start-1 flex min-w-0 items-center justify-end overflow-hidden lg:col-start-5 lg:row-start-1">
          <DeleteTokenButton onDelete={onDelete} token={token} />
        </div>
      </div>
      {!isLast ? (
        <div
          className="h-px w-full shrink-0 bg-knowledge-divider-subtle"
          data-testid="dashboard-token-row-divider"
        />
      ) : null}
    </div>
  );
}

function TokenTable({ children }: { readonly children: React.ReactNode }) {
  return (
    <div
      className="flex h-knowledge-dashboard-table-height w-full shrink-0 flex-col items-start overflow-hidden lg:h-knowledge-dashboard-table-height-desktop"
      data-testid="dashboard-token-table"
    >
      <div
        className="flex h-knowledge-dashboard-table-header-height w-full shrink-0 items-start overflow-hidden lg:h-knowledge-dashboard-table-header-height-desktop"
        data-testid="dashboard-token-table-fixed-header"
      >
        <div
          aria-hidden="true"
          className="h-full min-w-0 flex-1 overflow-hidden lg:hidden"
        />
        <div className="hidden h-full min-w-0 flex-1 flex-col items-start overflow-hidden lg:flex">
          <div
            className={cn(
              "grid h-knowledge-dashboard-table-header-row-height w-full shrink-0 overflow-hidden text-knowledge-button font-medium text-knowledge-text-muted",
              "grid-cols-[var(--knowledge-dashboard-table-grid-desktop)] grid-rows-[var(--knowledge-dashboard-table-row-template-desktop)]",
            )}
          >
            <span className="col-start-1 row-start-1 flex min-w-0 items-center overflow-hidden">
              Name
            </span>
            <span className="col-start-2 row-start-1 flex min-w-0 items-center overflow-hidden">
              Token
            </span>
            <span className="col-start-3 row-start-1 flex min-w-0 items-center overflow-hidden">
              Usage
            </span>
            <span className="col-start-4 row-start-1 flex min-w-0 items-center overflow-hidden">
              Last used
            </span>
            <span className="col-start-5 row-start-1" />
          </div>
          <div className="h-px w-full shrink-0 bg-knowledge-divider-subtle" />
        </div>
        <div
          aria-hidden="true"
          className="h-full w-knowledge-dashboard-scrollbar-width shrink-0"
          data-testid="dashboard-token-table-scrollbar-gutter"
        />
      </div>
      <ScrollArea
        className={cn(
          "flex min-h-0 w-full flex-1 items-start",
          tokenTableScrollAreaTheme,
        )}
        data-testid="dashboard-token-table-scroll-area"
        viewportClassName="flex h-full min-h-0 w-full flex-col items-start overflow-x-hidden overflow-y-auto"
      >
        {children}
      </ScrollArea>
    </div>
  );
}

function TokenRows({
  copiedTokenName,
  onCopy,
  onDelete,
  onRename,
  tokens,
}: {
  readonly copiedTokenName: string | null;
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly tokens: readonly DashboardTokenRow[];
}) {
  return (
    <>
      {tokens.map((token, index) => (
        <TokenRowGroup
          copiedTokenName={copiedTokenName}
          isLast={index === tokens.length - 1}
          key={token.name}
          onCopy={onCopy}
          onDelete={onDelete}
          onRename={onRename}
          token={token}
        />
      ))}
    </>
  );
}

export function TokenDirectory({
  copiedTokenName,
  errorMessage,
  isLoading,
  onCopy,
  onCreate,
  onDelete,
  onRename,
  tokens,
  usageAvailable,
}: TokenDirectoryProps) {
  const hasTokens = tokens.length > 0;

  return (
    <section
      className="flex min-h-0 flex-1 flex-col gap-knowledge-dashboard-section-gap overflow-hidden rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-knowledge-dashboard-surface-padding"
      data-testid="dashboard-token-directory"
    >
      <div className="flex h-knowledge-dashboard-toolbar-height shrink-0 items-center justify-between gap-knowledge-dashboard-section-gap overflow-hidden">
        <h2 className="m-0 min-w-0 flex-1 text-knowledge-dashboard-card-title font-semibold text-knowledge-text-default lg:text-knowledge-dashboard-card-title-desktop">
          Tokens
        </h2>
        <Button className="shrink-0" onClick={onCreate}>
          Create Token
        </Button>
      </div>

      {!usageAvailable ? (
        <p className="m-0 rounded-knowledge-control bg-knowledge-warning-surface px-3 py-2 text-knowledge-caption text-knowledge-warning-text">
          Usage data is unavailable.
        </p>
      ) : null}

      {errorMessage ? (
        <DirectoryState role="alert">{errorMessage}</DirectoryState>
      ) : null}

      {isLoading ? (
        <TokenTable>
          <LoadingRows />
        </TokenTable>
      ) : null}

      {!errorMessage && !isLoading && !hasTokens ? (
        <DirectoryState>No tokens</DirectoryState>
      ) : null}

      {!errorMessage && !isLoading && hasTokens ? (
        <TokenTable>
          <TokenRows
            copiedTokenName={copiedTokenName}
            onCopy={onCopy}
            onDelete={onDelete}
            onRename={onRename}
            tokens={tokens}
          />
        </TokenTable>
      ) : null}
    </section>
  );
}
