// abstract: Icon-only token row action controls for dashboard lifecycle actions.
// out_of_scope: Dialog state ownership and token list data fetching.

import { Copy, Pencil, Trash2 } from "lucide-react";

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
        "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[#606e87] transition-colors hover:bg-[rgba(226,234,246,0.58)] hover:text-[#131c2d]",
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
  onCopy,
  token,
}: TokenActionProps & {
  readonly onCopy: (token: DashboardTokenRow) => void;
}) {
  return (
    <TokenActionButton
      aria-label={`Copy ${token.name}`}
      onClick={() => onCopy(token)}
      title="Copy token"
    >
      <Copy aria-hidden="true" size={16} strokeWidth={2} />
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
      className="text-[#d83232] hover:bg-[rgba(216,50,50,0.08)] hover:text-[#bf2525]"
      onClick={() => onDelete(token)}
      title="Delete token"
    >
      <Trash2 aria-hidden="true" size={16} strokeWidth={2} />
    </TokenActionButton>
  );
}
