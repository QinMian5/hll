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
      className="flex min-h-[160px] items-center justify-center rounded-lg border border-dashed border-[rgba(214,227,247,0.86)] text-[14px] leading-5 text-[#606e87]"
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
          className="grid h-14 grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(5rem,1.5fr)_minmax(7rem,2fr)_1.5rem] items-center gap-4 border-t border-[rgba(214,227,247,0.72)]"
          key={index}
        >
          {[0, 1, 2, 3].map((cellIndex) => (
            <span
              className="h-3 rounded-full bg-[rgba(226,234,246,0.86)]"
              key={cellIndex}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function DesktopTokenRow({
  onCopy,
  onDelete,
  onRename,
  token,
}: {
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly token: DashboardTokenRow;
}) {
  return (
    <div className="grid h-14 grid-cols-[minmax(0,3fr)_minmax(0,5fr)_minmax(5rem,1.5fr)_minmax(7rem,2fr)_1.5rem] items-center gap-4 border-t border-[rgba(214,227,247,0.72)] text-[14px] leading-[22px] text-[#131c2d]">
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate font-medium">{token.name}</span>
        <RenameTokenButton onRename={onRename} token={token} />
      </div>
      <div className="flex min-w-0 items-center gap-2 text-[#606e87]">
        <span className="truncate font-normal">{token.maskedToken}</span>
        <CopyTokenButton onCopy={onCopy} token={token} />
      </div>
      <span className="min-w-0 truncate text-[#606e87]">
        {formatUsageCount(token.usageCount)}
      </span>
      <span className="min-w-0 truncate text-[#606e87]">
        {formatLastUsedAt(token.lastUsedAt)}
      </span>
      <DeleteTokenButton onDelete={onDelete} token={token} />
    </div>
  );
}

function MobileTokenRow({
  onCopy,
  onDelete,
  onRename,
  token,
}: {
  readonly onCopy: (token: DashboardTokenRow) => void;
  readonly onDelete: (token: DashboardTokenRow) => void;
  readonly onRename: (token: DashboardTokenRow) => void;
  readonly token: DashboardTokenRow;
}) {
  return (
    <div className="grid h-24 grid-rows-[1.25rem_1.25rem_1.125rem] gap-2 border-t border-[rgba(214,227,247,0.72)] py-3">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate text-[15px] leading-5 font-semibold text-[#131c2d]">
            {token.name}
          </span>
          <RenameTokenButton onRename={onRename} token={token} />
        </div>
        <DeleteTokenButton onDelete={onDelete} token={token} />
      </div>
      <div className="flex min-w-0 items-center gap-2">
        <span className="min-w-0 truncate text-[13px] leading-[19px] text-[#606e87]">
          {token.maskedToken}
        </span>
        <CopyTokenButton onCopy={onCopy} token={token} />
      </div>
      <div className="grid grid-cols-2 gap-3 text-[13px] leading-[18px] font-medium text-[#606e87]">
        <span className="truncate">{formatUsageCount(token.usageCount)}</span>
        <span className="truncate text-right">
          {formatLastUsedAt(token.lastUsedAt)}
        </span>
      </div>
    </div>
  );
}

export function TokenDirectory({
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
      className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden rounded-lg border border-[rgba(214,227,247,0.86)] bg-[rgba(255,255,255,0.88)] p-4 lg:p-6"
      data-testid="dashboard-token-directory"
    >
      <div className="flex h-10 shrink-0 items-center justify-between gap-4">
        <h2 className="m-0 text-[15px] leading-5 font-semibold text-[#131c2d] lg:text-[16px] lg:leading-[22px]">
          Tokens
        </h2>
        <Button
          className="h-10 w-[120px] rounded-lg bg-[#006aff] px-4 text-[14px] leading-5 font-medium text-white hover:bg-[#005ee0] disabled:hover:bg-[#006aff]"
          onClick={onCreate}
        >
          Create Token
        </Button>
      </div>

      {!usageAvailable ? (
        <p className="m-0 rounded-lg bg-[rgba(255,244,229,0.78)] px-3 py-2 text-[13px] leading-[18px] text-[#8a5a00]">
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
                "border-b border-[rgba(214,227,247,0.86)] text-[13px] leading-[18px] font-medium text-[#606e87]",
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
