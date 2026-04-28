// abstract: Icon-only token row action controls for dashboard lifecycle actions.
// out_of_scope: Dialog state ownership and token list data fetching.

import { Check, Copy, Pencil, Trash2 } from "lucide-react";

import { cn } from "../../../shared/utils";
import type { DashboardTokenRow } from "../types";

interface TokenActionButtonProps {
  readonly "aria-label": string;
  readonly children: React.ReactNode;
  readonly className?: string;
  readonly onClick: () => void;
  readonly title: string;
}

function TokenActionButton({
  children,
  className,
  onClick,
  title,
  ...props
}: TokenActionButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex h-knowledge-icon-action w-knowledge-icon-action shrink-0 items-center justify-center rounded-knowledge-control text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default",
        className,
      )}
      onClick={onClick}
      title={title}
      type="button"
      {...props}
    >
      {children}
    </button>
  );
}

interface TokenActionProps {
  readonly token: DashboardTokenRow;
}

export function CopyTokenButton({
  isCopied,
  onCopy,
  token,
}: TokenActionProps & {
  readonly isCopied: boolean;
  readonly onCopy: (token: DashboardTokenRow) => void;
}) {
  return (
    <TokenActionButton
      aria-label={`${isCopied ? "Copied" : "Copy"} ${token.name}`}
      className={isCopied ? "text-knowledge-brand" : undefined}
      onClick={() => onCopy(token)}
      title={isCopied ? "Copied" : "Copy token"}
    >
      {isCopied ? (
        <Check aria-hidden="true" size={16} strokeWidth={2} />
      ) : (
        <Copy aria-hidden="true" size={16} strokeWidth={2} />
      )}
    </TokenActionButton>
  );
}

export function RenameTokenButton({
  onRename,
  token,
}: TokenActionProps & {
  readonly onRename: (token: DashboardTokenRow) => void;
}) {
  return (
    <TokenActionButton
      aria-label={`Rename ${token.name}`}
      onClick={() => onRename(token)}
      title="Rename token"
    >
      <Pencil aria-hidden="true" size={14} strokeWidth={2} />
    </TokenActionButton>
  );
}

export function DeleteTokenButton({
  onDelete,
  token,
}: TokenActionProps & {
  readonly onDelete: (token: DashboardTokenRow) => void;
}) {
  return (
    <TokenActionButton
      aria-label={`Delete ${token.name}`}
      className="text-knowledge-danger hover:bg-knowledge-danger-soft hover:text-knowledge-danger-hover"
      onClick={() => onDelete(token)}
      title="Delete token"
    >
      <Trash2 aria-hidden="true" size={16} strokeWidth={2} />
    </TokenActionButton>
  );
}
