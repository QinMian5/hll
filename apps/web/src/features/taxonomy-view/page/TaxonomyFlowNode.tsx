// abstract: Branch-only React Flow bubble renderer for taxonomy drill-down navigation.
// out_of_scope: Leaf deck.gl rendering, hover disclosure, and page-level query orchestration.

import type { Node, NodeProps } from "@xyflow/react";

import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

const bubbleFrameClasses = [
  "group/bubble",
  "isolate",
  "relative",
  "grid",
  "size-full",
  "place-items-center",
  "overflow-visible",
  "rounded-full",
  "text-center",
  "text-slate-950",
  "[transform-origin:center]",
  "transition-transform",
  "duration-200",
].join(" ");

const bubbleVariantClasses = {
  branch: {
    frame:
      "border-knowledge-bubble-border/70 bg-[image:var(--background-image-knowledge-bubble-surface)] shadow-knowledge-bubble-frame",
    halo: "bg-[image:var(--background-image-knowledge-bubble-halo)] blur-knowledge-bubble-halo",
    glow: "bg-[image:var(--background-image-knowledge-bubble-glow)] opacity-95",
    sheen:
      "bg-[image:var(--background-image-knowledge-bubble-sheen)] opacity-90",
    label: "font-medium tracking-normal text-knowledge-graph-label",
  },
} as const;

export function TaxonomyFlowNode({ data }: NodeProps<BubbleFlowNode>) {
  if (data.scope !== "branch") {
    throw new Error("TaxonomyFlowNode only supports branch bubble nodes.");
  }

  const visualVariant = bubbleVariantClasses.branch;
  const rotationDegrees = `${(((data.targetNodeId ?? 0) % 5) - 2) * 0.9}deg`;

  return (
    <div
      className={bubbleFrameClasses}
      data-bubble-family="taxonomy"
      data-bubble-variant="branch"
      data-depth={data.depth}
      data-node-scope="branch"
      data-testid="taxonomy-bubble-frame"
      style={{ transform: `rotate(${rotationDegrees})` }}
      title={data.tooltip || data.label}
    >
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute -inset-[14%] rounded-full ${visualVariant.halo}`}
        data-testid="taxonomy-bubble-halo"
      />
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0 rounded-full ${visualVariant.frame}`}
        data-testid="taxonomy-bubble-surface"
      />
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute inset-[10%] rounded-full ${visualVariant.glow}`}
        data-testid="taxonomy-bubble-core-glow"
      />
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute inset-x-[18%] top-[10%] h-[34%] rounded-full blur-[1px] ${visualVariant.sheen}`}
        data-testid="taxonomy-bubble-sheen"
      />
      <span
        className={`absolute inset-[18%] z-[1] flex items-center justify-center text-center [text-wrap:balance] ${visualVariant.label}`}
        data-bubble-tone="branch"
        data-testid="taxonomy-bubble-label"
        style={{
          fontSize: "var(--taxonomy-bubble-label-font-size)",
          lineHeight: "var(--taxonomy-bubble-label-line-height)",
          maxWidth: "var(--taxonomy-bubble-label-width)",
        }}
      >
        <span
          className="block max-w-full overflow-hidden text-ellipsis break-words [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:3]"
          data-testid="taxonomy-bubble-label-text"
        >
          {data.label}
        </span>
      </span>
    </div>
  );
}
