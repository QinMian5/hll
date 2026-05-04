// abstract: Minimal shadcn-style textarea primitive for shared multiline entry surfaces.
// out_of_scope: Form state orchestration and validation logic.

import type { TextareaHTMLAttributes } from "react";

import { cn } from "../utils";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function Textarea({ className, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(
        "flex w-full min-w-0 resize-none overflow-hidden border-none bg-transparent text-[14px] leading-5 text-knowledge-text-default outline-none [field-sizing:content] placeholder:text-knowledge-text-muted read-only:cursor-text read-only:text-knowledge-text-default disabled:cursor-not-allowed disabled:opacity-100",
        className,
      )}
      {...props}
    />
  );
}
