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
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(0,0,0,0.32)] px-4 py-8 lg:items-center">
      <section
        aria-labelledby={labelledBy}
        aria-modal="true"
        className="w-full max-w-[408px] rounded-lg border border-[#e0e4eb] bg-white p-6 shadow-[0_18px_26px_rgba(107,132,189,0.09)]"
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
      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <div className="flex h-8 items-center justify-between gap-4">
          <h2
            className="m-0 text-[16px] leading-6 font-semibold text-[#131c2d]"
            id={titleId}
          >
            {title}
          </h2>
          <button
            aria-label="Close dialog"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[#606e87] transition-colors hover:bg-[rgba(226,234,246,0.58)] hover:text-[#131c2d]"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="flex flex-col gap-2">
          <label
            className="text-[14px] leading-5 font-medium text-[#131c2d]"
            htmlFor={inputId}
          >
            Token name
          </label>
          <div className="flex h-10 items-center rounded-lg border border-[#e5e5e5] px-4 shadow-[0_1px_2px_rgba(16,24,40,0.04)]">
            <Input
              autoFocus
              className="h-full text-[14px] leading-5 font-normal text-[#131c2d] placeholder:text-[#8a94a6]"
              id={inputId}
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </div>
          {errorMessage ? (
            <p
              className="m-0 text-[13px] leading-[18px] text-[#bf2525]"
              role="alert"
            >
              {errorMessage}
            </p>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Button
            className="h-10 rounded-lg border border-[#e0e4eb] bg-white px-4 text-[14px] leading-5 font-medium text-[#131c2d] hover:bg-[rgba(241,245,251,0.72)] disabled:hover:bg-white"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancel
          </Button>
          <Button
            className="h-10 rounded-lg bg-[#006aff] px-4 text-[14px] leading-5 font-medium text-white hover:bg-[#005ee0] disabled:hover:bg-[#006aff]"
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
      <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
        <div className="flex h-8 items-center justify-between gap-4">
          <h2
            className="m-0 text-[16px] leading-6 font-semibold text-[#131c2d]"
            id={titleId}
          >
            Delete Token
          </h2>
          <button
            aria-label="Close dialog"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[#606e87] transition-colors hover:bg-[rgba(226,234,246,0.58)] hover:text-[#131c2d]"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </div>

        <div className="rounded-lg border border-[rgba(214,227,247,0.86)] bg-[rgba(248,250,253,0.9)] px-4 py-3 text-[14px] leading-5 font-medium text-[#131c2d]">
          {tokenName}
        </div>
        {errorMessage ? (
          <p
            className="m-0 text-[13px] leading-[18px] text-[#bf2525]"
            role="alert"
          >
            {errorMessage}
          </p>
        ) : null}

        <div className="grid grid-cols-2 gap-2">
          <Button
            className="h-10 rounded-lg border border-[#e0e4eb] bg-white px-4 text-[14px] leading-5 font-medium text-[#131c2d] hover:bg-[rgba(241,245,251,0.72)] disabled:hover:bg-white"
            disabled={isSubmitting}
            onClick={onClose}
            type="button"
          >
            Cancel
          </Button>
          <Button
            className="h-10 rounded-lg bg-[#d83232] px-4 text-[14px] leading-5 font-medium text-white hover:bg-[#bf2525] disabled:hover:bg-[#d83232]"
            disabled={isSubmitting}
            type="submit"
          >
            Delete Token
          </Button>
        </div>
      </form>
    </DialogFrame>
  );
}
