// abstract: Search card proposal dialog for create, edit, and delete proposal modes.
// out_of_scope: Proposal review queue behavior and backend authorization.

import { SquarePen, Trash2, X } from "lucide-react";
import {
  type ComponentType,
  type FormEvent,
  type SVGProps,
  useEffect,
  useState,
} from "react";

import { Button } from "../../../shared/ui/button";
import { FieldControl } from "../../../shared/ui/field-control";
import { Input } from "../../../shared/ui/input";
import { ScrollArea } from "../../../shared/ui/scroll-area";
import { Textarea } from "../../../shared/ui/textarea";
import { cn } from "../../../shared/utils";
import type { SearchResultCardEditPayload } from "./SearchResultCard";

export type SearchCardProposalMode = "create" | "edit" | "delete";

interface SearchCardProposalDialogProps {
  readonly card?: SearchResultCardEditPayload;
  readonly errorMessage?: string;
  readonly initialMode: SearchCardProposalMode;
  readonly isSubmitting: boolean;
  readonly onClose: () => void;
  readonly onSubmit: (
    payload: SearchCardProposalSubmitPayload,
  ) => Promise<void>;
}

export type SearchCardProposalSubmitPayload =
  | {
      readonly content: string;
      readonly mode: "create";
      readonly reason: string;
      readonly title: string;
    }
  | {
      readonly content: string;
      readonly mode: "edit";
      readonly reason: string;
      readonly title: string;
    }
  | {
      readonly mode: "delete";
      readonly reason: string;
    };

const modeItems: readonly {
  readonly icon: ComponentType<SVGProps<SVGSVGElement>>;
  readonly label: string;
  readonly mode: Exclude<SearchCardProposalMode, "create">;
}[] = [
  { icon: SquarePen, label: "Edit", mode: "edit" },
  { icon: Trash2, label: "Delete", mode: "delete" },
];

function FieldLabel({
  children,
  htmlFor,
}: {
  readonly children: string;
  readonly htmlFor: string;
}) {
  return (
    <label
      className="text-knowledge-caption font-medium text-knowledge-text-default"
      htmlFor={htmlFor}
    >
      {children}
    </label>
  );
}

export function SearchCardProposalDialog({
  card,
  errorMessage,
  initialMode,
  isSubmitting,
  onClose,
  onSubmit,
}: SearchCardProposalDialogProps) {
  const [mode, setMode] = useState<SearchCardProposalMode>(initialMode);
  const [title, setTitle] = useState(
    initialMode === "edit" && card ? card.title : "",
  );
  const [content, setContent] = useState(
    initialMode === "edit" && card ? card.content : "",
  );
  const [reason, setReason] = useState("");

  useEffect(() => {
    setMode(initialMode);
    setTitle(initialMode === "edit" && card ? card.title : "");
    setContent(initialMode === "edit" && card ? card.content : "");
    setReason("");
  }, [card, initialMode]);

  const isReasonEmpty = reason.trim() === "";
  const isEditNoop =
    mode === "edit" &&
    card !== undefined &&
    title.trim() === card.title.trim() &&
    content.trim() === card.content.trim();
  const isSubmitDisabled =
    isSubmitting ||
    (mode === "create" &&
      (title.trim() === "" || content.trim() === "" || isReasonEmpty)) ||
    isEditNoop ||
    (mode !== "create" && isReasonEmpty);
  const dialogTitle =
    mode === "create" ? "Card Proposal - Add Card" : "Card Proposal";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "delete") {
      await onSubmit({ mode, reason });
      return;
    }

    await onSubmit({ content, mode, reason, title });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-knowledge-overlay-scrim px-4 py-8">
      <section
        aria-modal="true"
        aria-label={dialogTitle}
        className="flex h-[min(var(--spacing-knowledge-dialog-lg-height-mobile),calc(100vh-32px))] w-[min(var(--spacing-knowledge-dialog-lg-width-mobile),calc(100vw-32px))] flex-col gap-knowledge-dialog-content-gap rounded-xl border border-knowledge-border-subtle bg-knowledge-surface-dialog p-knowledge-dialog-padding shadow-[0_18px_21px_rgba(5,10,20,0.12)] md:h-knowledge-dialog-lg-height-desktop md:w-knowledge-dialog-lg-width-desktop md:gap-knowledge-dialog-content-gap-desktop"
        role="dialog"
      >
        <div className="flex h-knowledge-dialog-header-height shrink-0 items-center justify-between">
          <h2 className="m-0 min-w-0 flex-1 text-knowledge-dialog-title font-semibold text-knowledge-text-default">
            {dialogTitle}
          </h2>
          <button
            aria-label="Close card proposal dialog"
            className="flex size-8 shrink-0 items-center justify-center rounded-knowledge-control text-knowledge-text-muted hover:bg-knowledge-surface-hover hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
        <form
          className="flex min-h-0 flex-1 flex-col gap-4"
          onSubmit={handleSubmit}
        >
          {mode === "create" ? null : (
            <div
              className="grid h-8 shrink-0 grid-cols-2 gap-2"
              data-testid="search-proposal-mode-tabs"
            >
              {modeItems.map((item) => {
                const Icon = item.icon;
                const isSelected = mode === item.mode;
                return (
                  <button
                    aria-pressed={isSelected}
                    className={cn(
                      "inline-flex min-w-0 items-center justify-center gap-2 rounded-knowledge-control px-knowledge-dialog-mode-tab-padding-x text-[13px] leading-5 font-medium text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand",
                      isSelected &&
                        "border border-docs-border-accent bg-knowledge-surface-accent-soft font-semibold text-knowledge-brand hover:bg-knowledge-surface-accent-soft hover:text-knowledge-brand",
                    )}
                    key={item.mode}
                    onClick={() => {
                      setMode(item.mode);
                      setReason("");
                    }}
                    type="button"
                  >
                    <Icon aria-hidden="true" className="size-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          )}
          <ScrollArea
            className="relative flex-1 [--scroll-area-padding-right:var(--spacing-knowledge-dialog-scrollbar-gap)] [--scroll-area-scrollbar-width:var(--spacing-docs-scrollbar-width)] [--scroll-area-thumb-color:var(--color-docs-scrollbar-thumb)] [--scroll-area-track-color:var(--color-docs-scrollbar-track)]"
            data-testid="search-card-proposal-form-panel"
            viewportClassName="overflow-y-auto overflow-x-clip"
          >
            {mode === "delete" ? (
              <div className="flex flex-col gap-knowledge-dialog-content-gap">
                {card ? (
                  <>
                    <div className="flex flex-col gap-knowledge-dialog-field-gap">
                      <FieldLabel htmlFor="card-proposal-delete-title">
                        Title
                      </FieldLabel>
                      <FieldControl>
                        <Input
                          id="card-proposal-delete-title"
                          readOnly
                          value={card.title}
                        />
                      </FieldControl>
                    </div>
                    <div className="flex flex-col gap-knowledge-dialog-field-gap">
                      <FieldLabel htmlFor="card-proposal-delete-content">
                        Content
                      </FieldLabel>
                      <FieldControl className="items-start">
                        <Textarea
                          id="card-proposal-delete-content"
                          readOnly
                          rows={1}
                          value={card.content}
                        />
                      </FieldControl>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col gap-knowledge-dialog-field-gap">
                    <FieldLabel htmlFor="card-proposal-delete-title">
                      Title
                    </FieldLabel>
                    <FieldControl>
                      <Input
                        id="card-proposal-delete-title"
                        readOnly
                        value=""
                      />
                    </FieldControl>
                  </div>
                )}
                <div className="flex flex-col gap-knowledge-dialog-field-gap">
                  <FieldLabel htmlFor="card-proposal-delete-reason">
                    Reason
                  </FieldLabel>
                  <FieldControl className="items-start">
                    <Textarea
                      id="card-proposal-delete-reason"
                      onChange={(event) => {
                        setReason(event.currentTarget.value);
                      }}
                      placeholder="Explain why you recommend deleting this card."
                      rows={1}
                      value={reason}
                    />
                  </FieldControl>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-knowledge-dialog-content-gap">
                <div className="flex flex-col gap-knowledge-dialog-field-gap">
                  <FieldLabel htmlFor="card-proposal-title">Title</FieldLabel>
                  <FieldControl>
                    <Input
                      id="card-proposal-title"
                      onChange={(event) => {
                        setTitle(event.currentTarget.value);
                      }}
                      placeholder="New knowledge card title"
                      value={title}
                    />
                  </FieldControl>
                </div>
                <div className="flex flex-col gap-knowledge-dialog-field-gap">
                  <FieldLabel htmlFor="card-proposal-content">
                    Content
                  </FieldLabel>
                  <FieldControl className="items-start">
                    <Textarea
                      id="card-proposal-content"
                      onChange={(event) => {
                        setContent(event.currentTarget.value);
                      }}
                      placeholder={
                        mode === "create"
                          ? "Write the proposed card content."
                          : "Write the revised card content."
                      }
                      rows={1}
                      value={content}
                    />
                  </FieldControl>
                </div>
                <div className="flex flex-col gap-knowledge-dialog-field-gap">
                  <FieldLabel htmlFor="card-proposal-reason">Reason</FieldLabel>
                  <FieldControl className="items-start">
                    <Textarea
                      id="card-proposal-reason"
                      onChange={(event) => {
                        setReason(event.currentTarget.value);
                      }}
                      placeholder={
                        mode === "create"
                          ? "Explain why you recommend adding this card."
                          : "Explain why you recommend editing this card."
                      }
                      rows={1}
                      value={reason}
                    />
                  </FieldControl>
                </div>
              </div>
            )}
          </ScrollArea>
          {errorMessage ? (
            <p className="m-0 rounded-md bg-knowledge-danger-soft px-3 py-2 text-[13px] leading-[18px] font-medium text-knowledge-danger">
              {errorMessage}
            </p>
          ) : null}
          <div className="grid h-knowledge-dialog-footer-height shrink-0 grid-cols-2 gap-knowledge-dialog-footer-gap">
            <Button className="min-w-0" onClick={onClose} variant="secondary">
              Cancel
            </Button>
            <Button
              className="min-w-0 gap-2"
              disabled={isSubmitDisabled}
              type="submit"
              variant={mode === "delete" ? "destructive" : "default"}
            >
              {mode === "delete" ? (
                <Trash2 aria-hidden="true" className="size-4" />
              ) : null}
              Submit
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}
