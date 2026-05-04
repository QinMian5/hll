// abstract: Shared routed-page header primitive with tokenized title and subtitle typography.
// out_of_scope: Route-specific page actions and feature content layout.

import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../utils";

export interface PageHeaderProps
  extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  readonly actions?: ReactNode;
  readonly subtitle?: string;
  readonly subtitleClassName?: string;
  readonly title: string;
  readonly titleClassName?: string;
}

/** Shared header used by routed shell pages that bind to page-level Figma tokens. */
export function PageHeader({
  actions,
  className,
  subtitle,
  subtitleClassName,
  title,
  titleClassName,
  ...props
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex h-knowledge-page-header-height shrink-0 items-center overflow-hidden",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-knowledge-page-header-title-gap">
        <h1
          className={cn(
            "m-0 min-w-0 w-full text-knowledge-page-title font-semibold text-knowledge-text-default",
            titleClassName,
          )}
        >
          {title}
        </h1>
        {subtitle ? (
          <p
            className={cn(
              "m-0 min-w-0 text-knowledge-page-subtitle text-knowledge-text-muted",
              subtitleClassName,
            )}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="ml-4 flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
