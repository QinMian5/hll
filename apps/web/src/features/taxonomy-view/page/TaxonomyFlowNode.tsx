// abstract: Custom React Flow node renderer for taxonomy branch and leaf nodes.
// out_of_scope: Page-level query orchestration and layout solving.

import type { Node, NodeProps } from "@xyflow/react";

import type { TaxonomyLayoutNodeData } from "./layout/taxonomyLayoutTypes";

type BubbleFlowNode = Node<TaxonomyLayoutNodeData, "bubble">;

export function TaxonomyFlowNode({ data }: NodeProps<BubbleFlowNode>) {
  const isBranch = data.scope === "branch";
  const hoverCopy = data.content ?? data.tooltip;

  return (
    <div
      className={`taxonomy-bubble taxonomy-bubble--${data.scope}`}
      data-depth={data.depth}
      title={hoverCopy}
    >
      <span className="taxonomy-bubble__label">{data.label}</span>
      {isBranch ? <span className="taxonomy-bubble__hint">Open</span> : null}
    </div>
  );
}
