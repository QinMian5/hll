// abstract: Anonymous Search card edit sign-in prompt dialog.
// out_of_scope: Logto callback handling and authenticated suggestion form behavior.

import { useRouterState } from "@tanstack/react-router";
import { X } from "lucide-react";

interface SignInRequiredDialogProps {
  readonly onClose: () => void;
}

export function SignInRequiredDialog({ onClose }: SignInRequiredDialogProps) {
  const returnTo = useRouterState({
    select: (state) => state.location.href,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-knowledge-overlay-scrim px-4">
      <button
        aria-label="Close sign-in required dialog scrim"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        type="button"
      />
      <section
        aria-modal="true"
        aria-label="Sign in to suggest edits"
        className="relative flex w-full max-w-knowledge-dialog-width-compact flex-col gap-5 rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-dialog p-6 shadow-knowledge-dialog-strong"
        role="dialog"
      >
        <div className="flex items-center gap-3">
          <h2 className="m-0 min-w-0 flex-1 text-knowledge-dialog-title font-semibold text-knowledge-text-default">
            Sign in to suggest edits
          </h2>
          <button
            aria-label="Close sign-in required dialog"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-knowledge-text-muted hover:bg-knowledge-surface-accent-soft hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
        <p className="m-0 text-knowledge-body text-knowledge-text-muted">
          Sign in to suggest changes and help improve this knowledge card.
        </p>
        <form action="/web-api/auth/sign-in" method="post">
          <input name="return_to" type="hidden" value={returnTo} />
          <button
            className="h-10 w-full rounded-lg bg-knowledge-brand px-4 text-knowledge-button font-medium text-knowledge-text-inverse hover:bg-knowledge-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
            type="submit"
          >
            Sign in
          </button>
        </form>
      </section>
    </div>
  );
}
