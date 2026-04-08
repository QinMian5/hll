// abstract: Custom React Flow node renderer for taxonomy branch and leaf nodes.
// out_of_scope: Page-level query orchestration and layout solving.

import type { Node, NodeProps } from "@xyflow/react";
import { useId, useState } from "react";

import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

export function TaxonomyFlowNode({ data }: NodeProps<BubbleFlowNode>) {
  const isBranch = data.scope === "branch";
  const [isDisclosureOpen, setIsDisclosureOpen] = useState(false);
  const tooltipId = useId();
  const hoverCopy = data.content ?? data.tooltip;
  const canRevealContent = !isBranch && Boolean(data.content);
  const shouldShowTooltip = canRevealContent && isDisclosureOpen;

  return (
    /* biome-ignore lint/a11y/noStaticElementInteractions: React Flow owns click semantics; this container only controls hover disclosure. */
    <div
      aria-describedby={shouldShowTooltip ? tooltipId : undefined}
      className={`taxonomy-bubble taxonomy-bubble--${data.scope}`}
      data-depth={data.depth}
      data-node-scope={data.scope}
      onMouseEnter={() => {
        if (canRevealContent) {
          setIsDisclosureOpen(true);
        }
      }}
      onMouseLeave={() => {
        setIsDisclosureOpen(false);
      }}
      title={hoverCopy}
    >
      <span className="taxonomy-bubble__label">{data.label}</span>
      {isBranch ? <span className="taxonomy-bubble__hint">Open</span> : null}
      {shouldShowTooltip ? (
        <div className="taxonomy-bubble__tooltip" id={tooltipId} role="tooltip">
          {data.content}
        </div>
      ) : null}
    </div>
  );
}
