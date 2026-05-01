// abstract: Modal dialogs for dashboard token create, rename, and delete flows.
// out_of_scope: Query invalidation and token directory row rendering.

import { X } from "lucide-react";
import { type FormEvent, useEffect, useId, useState } from "react";

import { Button } from "../../../shared/ui/button";
import { Input } from "../../../shared/ui/input";

type TokenDialogMode = "create" | "rename";

interface TokenDialogProps {
  readonly errorMessage?: string | null;
  readonly initialName?: string;
  readonly isSubmitting: boolean;
  readonly mode: TokenDialogMode;
  readonly onClose: () => void;
  readonly onSubmit: (name: string) => Promise<void>;
}

function DialogFrame({
  children,
  labelledBy,
}: {
  readonly children: React.ReactNode;
  readonly labelledBy: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-knowledge-overlay-scrim px-knowledge-dashboard-dialog-overlay-padding-x py-knowledge-dashboard-dialog-overlay-padding-y">
      <section
        aria-labelledby={labelledBy}
        aria-modal="true"
        className="w-full max-w-[var(--spacing-knowledge-dialog-width)] rounded-knowledge-surface border border-knowledge-border-subtle bg-knowledge-surface-dialog p-knowledge-dialog-padding shadow-knowledge-dialog"
        role="dialog"
      >
        {children}
      </section>
    </div>
  );
}

export function TokenDialog({
  errorMessage,
  initialName = "",
  isSubmitting,
  mode,
  onClose,
  onSubmit,
}: TokenDialogProps) {
  const [name, setName] = useState(initialName);
  const titleId = useId();
  const inputId = useId();
  const title = mode === "create" ? "Create Token" : "Rename Token";

  useEffect(() => {
    setName(initialName);
  }, [initialName]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();

    if (trimmedName.length === 0) {
      return;
    }

    await onSubmit(trimmedName);
  }

  return (
    <DialogFrame labelledBy={titleId}>
      <form
        className="flex flex-col gap-knowledge-dashboard-dialog-gap"
        onSubmit={handleSubmit}
      >
        <div className="flex h-knowledge-dashboard-dialog-header-height items-center justify-between gap-knowledge-dashboard-section-gap">
          <h2
            className="m-0 text-knowledge-dialog-title font-semibold text-knowledge-text-default"
            id={titleId}
          >
            {title}
          </h2>
          <button
            aria-label="Close dialog"
            className="inline-flex h-knowledge-dashboard-dialog-close-size w-knowledge-dashboard-dialog-close-size items-center justify-center rounded-knowledge-control text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="flex flex-col gap-knowledge-dashboard-dialog-field-gap">
          <label
            className="text-knowledge-button font-medium text-knowledge-text-default"
            htmlFor={inputId}
          >
            Name
          </label>
          <div className="flex h-knowledge-control items-center rounded-knowledge-control border border-knowledge-border-input px-knowledge-action-button-x shadow-knowledge-input">
            <Input
              autoFocus
              className="h-full text-knowledge-button font-normal text-knowledge-text-default placeholder:text-knowledge-input-placeholder"
              id={inputId}
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </div>
          {errorMessage ? (
            <p
              className="m-0 text-knowledge-caption text-knowledge-danger-hover"
              role="alert"
            >
              {errorMessage}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-knowledge-dashboard-dialog-footer-gap">
          <Button
            className="w-full"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
            variant="secondary"
          >
            Cancel
          </Button>
          <Button
            className="w-full"
            disabled={isSubmitting || name.trim().length === 0}
            type="submit"
          >
            {title}
          </Button>
        </div>
      </form>
    </DialogFrame>
  );
}

interface DeleteTokenDialogProps {
  readonly errorMessage?: string | null;
  readonly isSubmitting: boolean;
  readonly onClose: () => void;
  readonly onConfirm: () => Promise<void>;
  readonly tokenName: string;
}

export function DeleteTokenDialog({
  errorMessage,
  isSubmitting,
  onClose,
  onConfirm,
  tokenName,
}: DeleteTokenDialogProps) {
  const titleId = useId();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onConfirm();
  }

  return (
    <DialogFrame labelledBy={titleId}>
      <form
        className="flex flex-col gap-knowledge-dashboard-dialog-gap"
        onSubmit={handleSubmit}
      >
        <div className="flex h-knowledge-dashboard-dialog-header-height items-center justify-between gap-knowledge-dashboard-section-gap">
          <h2
            className="m-0 text-knowledge-dialog-title font-semibold text-knowledge-text-default"
            id={titleId}
          >
            Delete Token
          </h2>
          <button
            aria-label="Close dialog"
            className="inline-flex h-knowledge-dashboard-dialog-close-size w-knowledge-dashboard-dialog-close-size items-center justify-center rounded-knowledge-control text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="rounded-knowledge-control border border-knowledge-border-card bg-knowledge-muted-surface px-knowledge-dashboard-dialog-token-preview-padding-x py-knowledge-dashboard-dialog-token-preview-padding-y text-knowledge-button font-medium text-knowledge-text-default">
          {tokenName}
        </div>
        {errorMessage ? (
          <p
            className="m-0 text-knowledge-caption text-knowledge-danger-hover"
            role="alert"
          >
            {errorMessage}
          </p>
        ) : null}

        <div className="grid grid-cols-2 gap-knowledge-dashboard-dialog-footer-gap">
          <Button
            className="w-full"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
            variant="secondary"
          >
            Cancel
          </Button>
          <Button
            className="w-full"
            disabled={isSubmitting}
            type="submit"
            variant="destructive"
          >
            Delete Token
          </Button>
        </div>
      </form>
    </DialogFrame>
  );
}
