// abstract: Custom React Flow node renderer for taxonomy branch and leaf nodes.
// out_of_scope: Page-level query orchestration and layout solving.

import { Handle, type Node, type NodeProps, Position } from "@xyflow/react";
import { useId, useState } from "react";

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

const leafCardFrameClasses = [
  "group/card",
  "isolate",
  "relative",
  "grid",
  "size-full",
  "place-items-center",
  "overflow-visible",
  "text-center",
  "text-slate-950",
].join(" ");

const bubbleVariantClasses: Record<
  TaxonomyLayoutNodeData["scope"],
  { frame: string; halo: string; glow: string; sheen: string; label: string }
> = {
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
  inner: {
    frame:
      "border-[#d5e1f3]/80 bg-[radial-gradient(circle_at_30%_26%,rgba(255,255,255,0.98)_0%,rgba(244,248,255,0.94)_48%,rgba(230,237,248,0.9)_100%)] shadow-[0_16px_34px_rgba(168,184,214,0.16),inset_0_1px_0_rgba(255,255,255,0.92)]",
    halo: "bg-[radial-gradient(circle,rgba(226,235,251,0.42)_0%,rgba(226,235,251,0.16)_54%,transparent_78%)] blur-[10px]",
    glow: "bg-[radial-gradient(circle_at_42%_34%,rgba(255,255,255,0.9)_0%,rgba(245,249,255,0.52)_38%,transparent_68%)] opacity-90",
    sheen:
      "bg-[linear-gradient(180deg,rgba(255,255,255,0.8)_0%,rgba(255,255,255,0.14)_46%,transparent_78%)] opacity-85",
    label:
      "max-w-[74%] text-[clamp(13px,0.92vw,16px)] font-medium leading-[1.08] tracking-[-0.025em] text-[#213b5f]",
  },
  outer: {
    frame:
      "border-[#dbe4f3]/80 bg-[radial-gradient(circle_at_30%_26%,rgba(255,255,255,0.96)_0%,rgba(247,250,255,0.93)_52%,rgba(235,241,249,0.88)_100%)] shadow-[0_14px_30px_rgba(175,189,214,0.14),inset_0_1px_0_rgba(255,255,255,0.88)]",
    halo: "bg-[radial-gradient(circle,rgba(230,237,250,0.34)_0%,rgba(230,237,250,0.12)_52%,transparent_78%)] blur-[10px]",
    glow: "bg-[radial-gradient(circle_at_42%_34%,rgba(255,255,255,0.84)_0%,rgba(246,249,255,0.42)_40%,transparent_68%)] opacity-80",
    sheen:
      "bg-[linear-gradient(180deg,rgba(255,255,255,0.72)_0%,rgba(255,255,255,0.1)_48%,transparent_80%)] opacity-80",
    label:
      "max-w-[74%] text-[clamp(13px,0.88vw,15px)] font-medium leading-[1.1] tracking-[-0.02em] text-[#38506f]",
  },
};

const leafCardVariantClasses: Record<
  Exclude<TaxonomyLayoutNodeData["scope"], "branch">,
  { frame: string; label: string }
> = {
  inner: {
    frame:
      "rounded-[18px] border border-[#d6e1f1]/90 bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(244,248,255,0.96)_100%)] shadow-[0_14px_32px_rgba(166,184,214,0.16)]",
    label:
      "text-[14px] font-medium leading-[1.2] tracking-[-0.02em] text-[#223b60]",
  },
  outer: {
    frame:
      "rounded-[18px] border border-[#dde5f2]/90 bg-[linear-gradient(180deg,rgba(255,255,255,0.97)_0%,rgba(247,250,255,0.95)_100%)] shadow-[0_12px_28px_rgba(176,189,214,0.14)]",
    label:
      "text-[14px] font-medium leading-[1.2] tracking-[-0.02em] text-[#3b526f]",
  },
};

const centerHandleClasses = [
  "!h-0",
  "!w-0",
  "!min-h-0",
  "!min-w-0",
  "!border-0",
  "!bg-transparent",
  "!opacity-0",
  "!shadow-none",
  "!pointer-events-none",
  "!left-1/2",
  "!top-1/2",
  "!-translate-x-1/2",
  "!-translate-y-1/2",
].join(" ");

export function TaxonomyFlowNode({ data }: NodeProps<BubbleFlowNode>) {
  const isBranch = data.scope === "branch";
  const isPointNode = data.renderMode === "point";
  const isLeafCard = !isBranch && data.renderMode === "card";
  const [isDisclosureOpen, setIsDisclosureOpen] = useState(false);
  const tooltipId = useId();
  const canRevealContent = !isBranch && !isPointNode && Boolean(data.content);
  const shouldShowTooltip = canRevealContent && isDisclosureOpen;
  const visualVariant = bubbleVariantClasses[data.scope];
  const rotationDegrees = isBranch
    ? `${(((data.targetNodeId ?? 0) % 5) - 2) * 0.9}deg`
    : "0deg";
  const labelLayoutClasses = isBranch
    ? "absolute inset-[18%] z-[1] flex items-center justify-center text-center"
    : "relative z-[1] px-[10%]";

  return (
    /* biome-ignore lint/a11y/noStaticElementInteractions: React Flow owns click semantics; this container only controls hover disclosure. */
    <div
      aria-describedby={shouldShowTooltip ? tooltipId : undefined}
      className={isLeafCard ? leafCardFrameClasses : bubbleFrameClasses}
      data-bubble-family="taxonomy"
      data-bubble-variant={isBranch ? data.scope : undefined}
      data-depth={data.depth}
      data-node-presentation={data.renderMode}
      data-node-scope={data.scope}
      onMouseEnter={() => {
        if (canRevealContent) {
          setIsDisclosureOpen(true);
        }
      }}
      onMouseLeave={() => {
        setIsDisclosureOpen(false);
      }}
      style={{ transform: `rotate(${rotationDegrees})` }}
    >
      {!isBranch ? (
        <>
          <Handle
            className={centerHandleClasses}
            data-handle-anchor="center"
            data-testid="taxonomy-handle-target"
            id="center-target"
            isConnectable={false}
            position={Position.Top}
            type="target"
          />
          <Handle
            className={centerHandleClasses}
            data-handle-anchor="center"
            data-testid="taxonomy-handle-source"
            id="center-source"
            isConnectable={false}
            position={Position.Top}
            type="source"
          />
        </>
      ) : null}
      {isPointNode ? (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(111,135,176,0.92)_0%,rgba(160,182,219,0.86)_42%,rgba(222,232,248,0.54)_100%)] shadow-[0_0_0_1px_rgba(245,249,255,0.96),0_6px_14px_rgba(148,169,204,0.24)]"
          data-testid="taxonomy-point-node"
        />
      ) : null}
      {isBranch ? (
        <>
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
            className={`${labelLayoutClasses} [text-wrap:balance] ${visualVariant.label}`}
            data-bubble-tone={isBranch ? "branch" : "leaf"}
            data-testid="taxonomy-bubble-label"
          >
            {data.label}
          </span>
        </>
      ) : null}
      {isLeafCard ? (
        <>
          <span
            aria-hidden="true"
            className={`pointer-events-none absolute inset-0 ${leafCardVariantClasses[data.scope].frame}`}
            data-node-shape="card"
            data-testid="taxonomy-leaf-card-surface"
          />
          <span
            className={`relative z-[1] flex h-full w-full items-center justify-center px-4 py-3 text-center whitespace-normal break-words [text-wrap:balance] ${leafCardVariantClasses[data.scope].label}`}
            data-bubble-tone="leaf"
            data-testid="taxonomy-card-label"
          >
            {data.label}
          </span>
        </>
      ) : null}
      {shouldShowTooltip ? (
        <div
          className="absolute bottom-[calc(100%+14px)] left-1/2 z-[5] w-max max-w-[min(18rem,42vw)] -translate-x-1/2 rounded-[18px] border border-[#d5e1f2]/85 bg-[linear-gradient(180deg,rgba(255,255,255,0.98)_0%,rgba(243,247,255,0.96)_100%)] px-4 py-3 text-left text-[12px] leading-[1.4] text-[#314967] shadow-[0_20px_50px_rgba(165,183,212,0.28)]"
          data-testid="taxonomy-bubble-disclosure"
          id={tooltipId}
          role="tooltip"
        >
          {data.content}
        </div>
      ) : null}
    </div>
  );
}
