// abstract: Authenticated Search card suggestion dialog.
// out_of_scope: Suggestion review and merge workflows.

import { X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import type { SearchResultCardEditPayload } from "./SearchResultCard";

interface SuggestEditDialogProps {
  readonly card: SearchResultCardEditPayload;
  readonly errorMessage?: string;
  readonly isSubmitting: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (payload: {
    readonly reason: string;
    readonly suggestedContent: string;
    readonly suggestedTitle: string;
  }) => Promise<void>;
}

export function SuggestEditDialog({
  card,
  errorMessage,
  isSubmitting,
  onClose,
  onSubmit,
}: SuggestEditDialogProps) {
  const [suggestedTitle, setSuggestedTitle] = useState(card.title);
  const [suggestedContent, setSuggestedContent] = useState(card.content);
  const [reason, setReason] = useState("");

  useEffect(() => {
    setSuggestedTitle(card.title);
    setSuggestedContent(card.content);
    setReason("");
  }, [card]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ reason, suggestedContent, suggestedTitle });
  }

  const isNoop =
    suggestedTitle.trim() === card.title.trim() &&
    suggestedContent.trim() === card.content.trim();
  const isReasonEmpty = reason.trim() === "";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-knowledge-overlay-scrim px-4">
      <section
        aria-modal="true"
        aria-label="Suggest edit"
        className="flex w-full max-w-knowledge-dialog-width-suggestion flex-col gap-4 rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-dialog p-4 shadow-knowledge-dialog-strong"
        role="dialog"
      >
        <div className="flex items-center gap-3">
          <h2 className="m-0 min-w-0 flex-1 text-knowledge-dialog-title font-semibold text-knowledge-text-default">
            Suggest edit
          </h2>
          <button
            aria-label="Close suggest edit dialog"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-knowledge-text-muted hover:bg-knowledge-surface-accent-soft hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-knowledge-caption font-medium text-knowledge-text-default">
            Suggested title
            <input
              className="h-10 rounded-lg border border-knowledge-border-control px-3 text-knowledge-search-input font-normal text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              onChange={(event) => {
                setSuggestedTitle(event.currentTarget.value);
              }}
              value={suggestedTitle}
            />
          </label>
          <label className="flex flex-col gap-1 text-knowledge-caption font-medium text-knowledge-text-default">
            Suggested content
            <textarea
              className="min-h-knowledge-field-tall-min-height resize-y rounded-lg border border-knowledge-border-control px-3 py-2 text-knowledge-search-input font-normal text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              onChange={(event) => {
                setSuggestedContent(event.currentTarget.value);
              }}
              value={suggestedContent}
            />
          </label>
          <label className="flex flex-col gap-1 text-knowledge-caption font-medium text-knowledge-text-default">
            Reason
            <textarea
              className="min-h-knowledge-field-min-height resize-y rounded-lg border border-knowledge-border-control px-3 py-2 text-knowledge-search-input font-normal text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              onChange={(event) => {
                setReason(event.currentTarget.value);
              }}
              placeholder="Explain why you recommend editing this card."
              value={reason}
            />
          </label>
          {errorMessage ? (
            <p className="m-0 rounded-md bg-knowledge-danger-soft px-3 py-2 text-knowledge-caption font-medium text-knowledge-danger">
              {errorMessage}
            </p>
          ) : null}
          <div className="flex justify-end gap-2 pt-1">
            <button
              className="h-10 rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-card-solid px-4 text-knowledge-button font-medium text-knowledge-text-default hover:bg-knowledge-page-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
            <button
              className="h-10 rounded-lg bg-knowledge-brand px-4 text-knowledge-button font-medium text-knowledge-text-inverse hover:bg-knowledge-brand-hover disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
              disabled={isSubmitting || isNoop || isReasonEmpty}
              type="submit"
            >
              Submit suggestion
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
