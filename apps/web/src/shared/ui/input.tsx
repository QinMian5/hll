// abstract: Minimal shadcn-style input primitive for shared text entry surfaces.
// out_of_scope: Form state orchestration and validation logic.

import type { InputHTMLAttributes } from "react";

import { cn } from "../utils";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, type = "text", ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex w-full min-w-0 border-none bg-transparent outline-none disabled:cursor-not-allowed disabled:opacity-100",
        className,
      )}
      type={type}
      {...props}
    />
  );
}
