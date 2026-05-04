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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(15,23,42,0.22)] px-4">
      <section
        aria-modal="true"
        aria-label="Suggest edit"
        className="flex w-full max-w-[560px] flex-col gap-4 rounded-lg border border-[#e0e4eb] bg-white p-4 shadow-[0_24px_80px_rgba(38,51,82,0.22)]"
        role="dialog"
      >
        <div className="flex items-center gap-3">
          <h2 className="m-0 min-w-0 flex-1 text-[18px] leading-6 font-semibold text-[#131c2d]">
            Suggest edit
          </h2>
          <button
            aria-label="Close suggest edit dialog"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-[#606e87] hover:bg-[#eff6ff] hover:text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
        <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
          <label className="flex flex-col gap-1 text-[13px] leading-[18px] font-medium text-[#131c2d]">
            Suggested title
            <input
              className="h-10 rounded-lg border border-[#d6e3f7] px-3 text-[14px] leading-5 font-normal text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
              onChange={(event) => {
                setSuggestedTitle(event.currentTarget.value);
              }}
              value={suggestedTitle}
            />
          </label>
          <label className="flex flex-col gap-1 text-[13px] leading-[18px] font-medium text-[#131c2d]">
            Suggested content
            <textarea
              className="min-h-[180px] resize-y rounded-lg border border-[#d6e3f7] px-3 py-2 text-[14px] leading-5 font-normal text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
              onChange={(event) => {
                setSuggestedContent(event.currentTarget.value);
              }}
              value={suggestedContent}
            />
          </label>
          <label className="flex flex-col gap-1 text-[13px] leading-[18px] font-medium text-[#131c2d]">
            Reason
            <textarea
              className="min-h-[80px] resize-y rounded-lg border border-[#d6e3f7] px-3 py-2 text-[14px] leading-5 font-normal text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
              onChange={(event) => {
                setReason(event.currentTarget.value);
              }}
              placeholder="Explain why you recommend editing this card."
              value={reason}
            />
          </label>
          {errorMessage ? (
            <p className="m-0 rounded-md bg-[#fff1f2] px-3 py-2 text-[13px] leading-[18px] font-medium text-[#be123c]">
              {errorMessage}
            </p>
          ) : null}
          <div className="flex justify-end gap-2 pt-1">
            <button
              className="h-10 rounded-lg border border-[#e0e4eb] bg-white px-4 text-[14px] leading-5 font-medium text-[#131c2d] hover:bg-[#f8fafc] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>
            <button
              className="h-10 rounded-lg bg-[#006bff] px-4 text-[14px] leading-5 font-medium text-white hover:bg-[#005fe0] disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
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
