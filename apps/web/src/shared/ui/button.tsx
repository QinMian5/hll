// abstract: Minimal shadcn-style button primitive for shared interactive controls.
// out_of_scope: Feature-specific button behavior or async state orchestration.

import type { ButtonHTMLAttributes } from "react";

import { cn } from "../utils";

const buttonVariantClasses = {
  default:
    "bg-[#171717] text-[#FAFAFA] hover:bg-[#101010] disabled:hover:bg-[#171717]",
  ghost:
    "bg-transparent text-[rgba(99,114,143,0.9)] hover:bg-[rgba(226,234,246,0.48)] hover:text-[rgba(45,57,84,0.96)] disabled:hover:bg-transparent",
} as const;

const buttonSizeClasses = {
  default: "h-10 min-w-[92px] rounded-lg px-6 text-[12px] leading-4",
  icon: "h-11 w-11 rounded-[16px]",
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
        "inline-flex items-center justify-center font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-100",
        buttonVariantClasses[variant],
        buttonSizeClasses[size],
        className,
      )}
      type={type}
      {...props}
    />
  );
}
