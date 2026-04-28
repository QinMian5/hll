// abstract: Figma-aligned token directory table and mobile list for Dashboard.
// out_of_scope: Token mutation dialog state and BFF request orchestration.

import { Button } from "../../../shared/ui/button";
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
      className="flex min-h-[160px] items-center justify-center rounded-knowledge-surface border border-dashed border-knowledge-border-card text-knowledge-body text-knowledge-text-muted"
      role={role}
    >
      {children}
    </div>
  );
}

function LoadingRows() {
  return (
    <div className="flex flex-col">
      {[0, 1, 2].map((index) => (
        <div
          className="grid h-14 grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(5rem,1.5fr)_minmax(7rem,2fr)_1.5rem] items-center gap-4 border-t border-knowledge-divider-subtle"
          key={index}
        >
          {[0, 1, 2, 3].map((cellIndex) => (
            <span
              className="h-3 rounded-full bg-knowledge-surface-hover"
              key={cellIndex}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function DesktopTokenRow({
  copiedTokenName,
  onCopy,
  onDelete,
  onRename,
  token,
}: {
  readonly copiedTokenName: string | null;
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly token: DashboardTokenRow;
}) {
  return (
    <div className="grid h-14 grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(5rem,1.5fr)_minmax(7rem,2fr)_1.5rem] items-center gap-4 border-t border-knowledge-divider-subtle text-knowledge-body text-knowledge-text-default">
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate font-medium">{token.name}</span>
        <RenameTokenButton onRename={onRename} token={token} />
      </div>
      <div className="flex min-w-0 items-center gap-2 text-knowledge-text-muted">
        <span className="truncate font-normal">{token.maskedToken}</span>
        <CopyTokenButton
          isCopied={copiedTokenName === token.name}
          onCopy={onCopy}
          token={token}
        />
      </div>
      <span className="min-w-0 truncate text-knowledge-text-muted">
        {formatUsageCount(token.usageCount)}
      </span>
      <span className="min-w-0 truncate text-knowledge-text-muted">
        {formatLastUsedAt(token.lastUsedAt)}
      </span>
      <DeleteTokenButton onDelete={onDelete} token={token} />
    </div>
  );
}

function MobileTokenRow({
  copiedTokenName,
  onCopy,
  onDelete,
  onRename,
  token,
}: {
  readonly copiedTokenName: string | null;
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly token: DashboardTokenRow;
}) {
  return (
    <div className="grid h-24 grid-rows-[1.25rem_1.25rem_1.125rem] gap-2 border-t border-knowledge-divider-subtle py-3">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-[15px] leading-5 font-semibold text-knowledge-text-default">
            {token.name}
          </span>
          <RenameTokenButton onRename={onRename} token={token} />
        </div>
        <DeleteTokenButton onDelete={onDelete} token={token} />
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <span className="min-w-0 truncate text-[13px] leading-[19px] text-knowledge-text-muted">
          {token.maskedToken}
        </span>
        <CopyTokenButton
          isCopied={copiedTokenName === token.name}
          onCopy={onCopy}
          token={token}
        />
      </div>
      <div className="grid grid-cols-2 gap-3 text-knowledge-caption font-medium text-knowledge-text-muted">
        <span className="truncate">{formatUsageCount(token.usageCount)}</span>
        <span className="truncate text-right">
          {formatLastUsedAt(token.lastUsedAt)}
        </span>
      </div>
    </div>
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
      className="flex min-h-0 flex-1 flex-col gap-knowledge-section-gap overflow-hidden rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-4 lg:p-knowledge-surface-padding"
      data-testid="dashboard-token-directory"
    >
      <div className="flex h-10 shrink-0 items-center justify-between gap-4">
        <h2 className="m-0 text-[15px] leading-5 font-semibold text-knowledge-text-default lg:text-knowledge-title">
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

      {isLoading ? <LoadingRows /> : null}

      {!errorMessage && !isLoading && !hasTokens ? (
        <DirectoryState>No tokens</DirectoryState>
      ) : null}

      {!errorMessage && !isLoading && hasTokens ? (
        <>
          <div
            className="hidden min-h-0 flex-1 overflow-hidden lg:block"
            data-testid="dashboard-token-table"
          >
            <div
              className={cn(
                "grid h-10 grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(5rem,1.5fr)_minmax(7rem,2fr)_1.5rem] items-center gap-4",
                "border-b border-knowledge-border-card text-knowledge-caption font-medium text-knowledge-text-muted",
              )}
            >
              <span>Name</span>
              <span>Token</span>
              <span>Usage</span>
              <span>Last used</span>
              <span />
            </div>
            <div className="min-h-0 overflow-y-auto">
              {tokens.map((token) => (
                <DesktopTokenRow
                  copiedTokenName={copiedTokenName}
                  key={token.name}
                  onCopy={onCopy}
                  onDelete={onDelete}
                  onRename={onRename}
                  token={token}
                />
              ))}
            </div>
          </div>

          <div
            className="min-h-0 overflow-y-auto lg:hidden"
            data-testid="dashboard-mobile-token-list"
          >
            {tokens.map((token) => (
              <MobileTokenRow
                copiedTokenName={copiedTokenName}
                key={token.name}
                onCopy={onCopy}
                onDelete={onDelete}
                onRename={onRename}
                token={token}
              />
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
