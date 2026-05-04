// abstract: Minimal shadcn-style button primitive for shared interactive controls.
// out_of_scope: Feature-specific button behavior or async state orchestration.

import type { ButtonHTMLAttributes } from "react";

import { cn } from "../utils";

const buttonVariantClasses = {
  default:
    "bg-knowledge-brand text-knowledge-text-inverse hover:bg-knowledge-brand-hover disabled:hover:bg-knowledge-brand",
  destructive:
    "bg-knowledge-danger text-knowledge-text-inverse hover:bg-knowledge-danger-hover disabled:hover:bg-knowledge-danger",
  ghost:
    "bg-transparent text-knowledge-text-muted hover:bg-knowledge-surface-hover hover:text-knowledge-text-default disabled:hover:bg-transparent",
  secondary:
    "border border-knowledge-border-control bg-knowledge-surface-control text-knowledge-text-default hover:border-docs-border-accent hover:bg-knowledge-surface-hover disabled:border-knowledge-border-subtle disabled:text-knowledge-text-muted disabled:hover:border-knowledge-border-subtle disabled:hover:bg-knowledge-surface-control",
} as const;

const buttonSizeClasses = {
  default:
    "h-knowledge-control min-w-[92px] rounded-knowledge-control px-knowledge-action-button-x text-knowledge-button whitespace-nowrap",
  icon: "h-knowledge-icon-action w-knowledge-icon-action rounded-knowledge-control",
} as const;

type ButtonVariant = keyof typeof buttonVariantClasses;
type ButtonSize = keyof typeof buttonSizeClasses;

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly size?: ButtonSize;
  readonly variant?: ButtonVariant;
}

export function Button({
  className,
  size = "default",
  type = "button",
  variant = "default",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-knowledge-action-button-content-gap font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand disabled:cursor-not-allowed disabled:opacity-100",
        buttonVariantClasses[variant],
        buttonSizeClasses[size],
        className,
      )}
      type={type}
      {...props}
    />
  );
}
