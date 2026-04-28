// abstract: Shared rich-text renderer for knowledge-card title and content fields.
// out_of_scope: Feature-specific card layout, backend payload validation, and route-level data orchestration.

import "katex/dist/katex.min.css";

import {
  Component,
  type ErrorInfo,
  memo,
  type ReactNode,
  useMemo,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";

export interface KnowledgeRichTextProps {
  readonly text: string;
  readonly variant: "content" | "title";
}

interface KnowledgeRichTextBoundaryProps extends KnowledgeRichTextProps {
  readonly children: ReactNode;
}

interface KnowledgeRichTextBoundaryState {
  readonly hasError: boolean;
}

const contentContainerClasses =
  "min-w-0 text-[14px] leading-[22px] font-normal text-[rgba(61,75,103,0.82)] [&_.katex-display]:my-3 [&_.katex-display]:overflow-x-auto [&_.katex-display]:overflow-y-hidden [&_code]:rounded-[8px] [&_code]:bg-[rgba(222,230,244,0.75)] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-medium [&_code]:text-[rgba(28,42,68,0.92)] [&_ol]:my-0 [&_ol]:pl-5 [&_ol]:marker:text-[rgba(98,118,153,0.9)] [&_p]:m-0 [&_p+p]:mt-3 [&_pre]:m-0 [&_pre]:overflow-x-auto [&_pre]:rounded-[14px] [&_pre]:bg-[rgba(232,238,247,0.92)] [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_ul]:my-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:marker:text-[rgba(98,118,153,0.9)] [&_ul+p]:mt-3 [&_p+ul]:mt-3 [&_p+ol]:mt-3 [&_ol+p]:mt-3";
const fallbackClasses = {
  content: `${contentContainerClasses} whitespace-pre-wrap`,
  title:
    "min-w-0 text-[16px] leading-[22px] font-medium text-[rgba(18,23,41,0.96)] whitespace-pre-wrap",
} as const;
const titleContainerClasses =
  "min-w-0 text-[16px] leading-[22px] font-medium text-[rgba(18,23,41,0.96)] [&_.katex]:text-[rgba(18,23,41,0.96)] [&_.katex-display]:my-2 [&_.katex-display]:overflow-x-auto [&_.katex-display]:overflow-y-hidden [&_code]:rounded-[8px] [&_code]:bg-[rgba(222,230,244,0.75)] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.95em] [&_ol]:m-0 [&_ol]:pl-5 [&_p]:m-0 [&_pre]:m-0 [&_pre]:overflow-x-auto [&_pre]:rounded-[14px] [&_pre]:bg-[rgba(232,238,247,0.92)] [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_ul]:m-0 [&_ul]:list-disc [&_ul]:pl-5";

function normalizeMathDelimiters(text: string) {
  const withDisplayMath = text.replace(
    /\\\[([\s\S]+?)\\\]/g,
    (_match, expression: string) => {
      return `\n\n$$\n${expression}\n$$\n\n`;
    },
  );

  return withDisplayMath.replace(
    /\\\(([\s\S]+?)\\\)/g,
    (_match, expression: string) => {
      return `$${expression}$`;
    },
  );
}

class KnowledgeRichTextBoundary extends Component<
  KnowledgeRichTextBoundaryProps,
  KnowledgeRichTextBoundaryState
> {
  public state: KnowledgeRichTextBoundaryState = {
    hasError: false,
  };

  public static getDerivedStateFromError(): KnowledgeRichTextBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(_error: Error, _errorInfo: ErrorInfo) {}

  public render() {
    const { children, text, variant } = this.props;

    if (this.state.hasError) {
      return (
        <div
          className={fallbackClasses[variant]}
          data-testid={`knowledge-rich-text-${variant}`}
        >
          {text}
        </div>
      );
    }

    return children;
  }
}

export const KnowledgeRichText = memo(function KnowledgeRichText({
  text,
  variant,
}: KnowledgeRichTextProps) {
  const normalizedText = useMemo(() => normalizeMathDelimiters(text), [text]);
  const className =
    variant === "title" ? titleContainerClasses : contentContainerClasses;
  const markdownComponents = useMemo(
    () => ({
      p: ({ children }: { readonly children?: ReactNode }) =>
        variant === "title" ? <span>{children}</span> : <p>{children}</p>,
    }),
    [variant],
  );

  return (
    <KnowledgeRichTextBoundary text={text} variant={variant}>
      <div className={className} data-testid={`knowledge-rich-text-${variant}`}>
        <ReactMarkdown
          components={markdownComponents}
          rehypePlugins={[rehypeKatex]}
          remarkPlugins={[remarkMath]}
          skipHtml
        >
          {normalizedText}
        </ReactMarkdown>
      </div>
    </KnowledgeRichTextBoundary>
  );
});
