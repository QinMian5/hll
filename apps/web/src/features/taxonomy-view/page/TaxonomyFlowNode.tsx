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
      "border-[#c8d7f0]/70 bg-[radial-gradient(circle_at_30%_26%,rgba(255,255,255,0.98)_0%,rgba(237,244,255,0.94)_44%,rgba(221,232,251,0.9)_72%,rgba(206,220,246,0.86)_100%)] shadow-[0_18px_40px_rgba(160,184,221,0.2),inset_0_1px_0_rgba(255,255,255,0.92)]",
    halo: "bg-[radial-gradient(circle,rgba(214,228,255,0.58)_0%,rgba(214,228,255,0.22)_52%,transparent_76%)] blur-[10px]",
    glow: "bg-[radial-gradient(circle_at_40%_35%,rgba(255,255,255,0.92)_0%,rgba(240,246,255,0.62)_34%,transparent_66%)] opacity-95",
    sheen:
      "bg-[linear-gradient(180deg,rgba(255,255,255,0.88)_0%,rgba(255,255,255,0.18)_45%,transparent_78%)] opacity-90",
    label:
      "max-w-[72%] text-[clamp(15px,1.05vw,18px)] font-medium leading-[1.05] tracking-[-0.03em] text-[#183153]",
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
      style={{ transform: `rotate(${rotationDegrees})` }}
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
      >
        {data.label}
      </span>
    </div>
  );
}
