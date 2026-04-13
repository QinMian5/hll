// abstract: Search-specific UI components for the routed search experience.
// out_of_scope: Search ranking, backend integration, and URL state ownership.

import { Search } from "lucide-react";
import type { FormEventHandler } from "react";

import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  ScrollArea,
} from "../../../shared/ui";

interface SearchFieldProps {
  readonly defaultValue: string;
  readonly onSubmit: FormEventHandler<HTMLFormElement>;
  readonly placeholder: string;
  readonly size: "compact" | "hero";
}

const fieldContainerClasses = {
  compact:
    "h-12 rounded-[24px] border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] pl-6 pr-[2px] shadow-[0_16px_36px_rgba(95,123,185,0.1)]",
  hero: "h-[72px] rounded-[28px] border border-[rgba(214,227,247,0.96)] bg-[rgba(255,255,255,0.82)] pl-6 pr-[10px] shadow-[0_16px_36px_rgba(95,123,185,0.1)]",
} as const;

const inputClasses = {
  compact:
    "h-full text-[16px] leading-6 font-medium text-[rgba(20,28,46,0.98)] placeholder:text-[rgba(99,114,143,0.72)]",
  hero: "h-full text-[18px] leading-6 font-normal text-[rgba(20,28,46,0.98)] placeholder:text-[rgba(99,114,143,0.72)]",
} as const;

export function SearchField({
  defaultValue,
  onSubmit,
  placeholder,
  size,
}: SearchFieldProps) {
  return (
    <form className="w-full max-w-[760px]" onSubmit={onSubmit}>
      <div
        className={`flex items-center justify-between ${fieldContainerClasses[size]}`}
      >
        <Input
          className={inputClasses[size]}
          data-testid="search-input"
          defaultValue={defaultValue}
          name="q"
          placeholder={placeholder}
          type="search"
        />
        <Button
          aria-label="Search"
          className="shrink-0"
          size="icon"
          type="submit"
          variant="ghost"
        >
          <Search className="h-[18px] w-[18px]" strokeWidth={2} />
        </Button>
      </div>
    </form>
  );
}

interface SearchResultCardProps {
  readonly content: string;
  readonly title: string;
}

export function SearchResultCard({ content, title }: SearchResultCardProps) {
  return (
    <Card className="flex h-full min-h-0 w-full flex-col p-5">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <div className="my-[14px] h-px shrink-0 bg-[#dee6f4]" />
      <CardContent>
        <ScrollArea viewportClassName="h-full pr-[10px]">
          <p className="m-0 text-[14px] leading-[22px] font-normal text-[rgba(61,75,103,0.82)]">
            {content}
          </p>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
