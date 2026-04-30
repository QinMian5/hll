// abstract: DOM disclosure overlay for hovered or selected taxonomy leaf points.
// out_of_scope: deck.gl picking, title/detail data fetching, and graph focus semantics.

import { SquarePen } from "lucide-react";
import {
  forwardRef,
  type SyntheticEvent,
  useCallback,
  useImperativeHandle,
  useLayoutEffect,
  useRef,
} from "react";

import { KnowledgeRichText, ScrollArea } from "../../../../shared/ui";
import type { SearchResultCardEditPayload } from "../../../search/components/SearchResultCard";
import type { LayoutViewport } from "../layout/taxonomyLayoutTypes";
import { projectLeafWorldPoint } from "./LeafTitleLabelsOverlay";
import type {
  LeafDisclosureState,
  LeafOrthographicViewport,
} from "./leafSceneTypes";

interface LeafDisclosureOverlayProps {
  readonly canvas: LayoutViewport;
  readonly disclosure: LeafDisclosureState | null;
  readonly onSuggestEdit?: (card: SearchResultCardEditPayload) => void;
  readonly viewport: LeafOrthographicViewport;
}

export interface LeafDisclosureOverlayHandle {
  syncViewport: (viewport: LeafOrthographicViewport) => void;
}

const DISCLOSURE_GAP_PX = 16;
const DISCLOSURE_CARD_SIZE_CLASS =
  "[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-md)] [--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-md)] [--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-md)] lg:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-lg)] lg:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-lg)] lg:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-lg)] xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-xl)] xl:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-xl)] xl:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-xl)] 2xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-2xl)] 2xl:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-2xl)] 2xl:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-2xl)]";
const DISCLOSURE_CARD_CLASS = `absolute top-0 left-0 z-[22] m-0 pointer-events-auto flex h-[var(--leaf-disclosure-card-height)] w-[min(var(--leaf-disclosure-card-width),calc(100%_-_24px))] flex-col items-start gap-2 overflow-hidden rounded-knowledge-leaf-disclosure border border-[rgba(133,163,214,0.34)] bg-white px-4 py-4 text-left shadow-[0_8px_18px_rgba(59,82,125,0.1)] ${DISCLOSURE_CARD_SIZE_CLASS}`;
const DISCLOSURE_CONTENT_SCROLL_CLASS =
  "[--scroll-area-padding-right:var(--spacing-knowledge-leaf-disclosure-scrollbar-width)] [--scroll-area-scrollbar-width:var(--spacing-knowledge-leaf-disclosure-scrollbar-width)] h-[var(--leaf-disclosure-card-content-height)] w-full flex-none";
const DISCLOSURE_CONTENT_VIEWPORT_CLASS =
  "overflow-x-hidden overflow-y-auto [&_[data-testid=knowledge-rich-text-content]]:text-[12px] [&_[data-testid=knowledge-rich-text-content]]:leading-[17px] [&_[data-testid=knowledge-rich-text-content]]:text-knowledge-text-muted";

interface OverlayPosition {
  readonly left: number;
  readonly top: number;
}

function resolvePosition(options: {
  readonly canvas: LayoutViewport;
  readonly disclosure: LeafDisclosureState;
  readonly viewport: LeafOrthographicViewport;
}): OverlayPosition {
  const projected = projectLeafWorldPoint(
    options.canvas,
    options.viewport,
    options.disclosure.node.position,
  );

  return {
    left: projected.x,
    top: projected.y + DISCLOSURE_GAP_PX,
  };
}

function disclosureTransform(position: OverlayPosition) {
  return `translate3d(${position.left}px, ${position.top}px, 0px) translate(-50%, 0%)`;
}

function stopCanvasPropagation(event: SyntheticEvent) {
  event.stopPropagation();
}

function LeafDisclosureHeader({
  node,
  onSuggestEdit,
  title,
}: {
  readonly node: LeafDisclosureState["node"];
  readonly onSuggestEdit?: (card: SearchResultCardEditPayload) => void;
  readonly title: string;
}) {
  return (
    <div className="flex h-6 w-full shrink-0 items-center justify-between gap-2 overflow-hidden">
      <div className="min-w-0 flex-1 [&_[data-testid=knowledge-rich-text-title]]:text-[13px] [&_[data-testid=knowledge-rich-text-title]]:leading-[18px] [&_[data-testid=knowledge-rich-text-title]]:font-medium [&_[data-testid=knowledge-rich-text-title]]:text-knowledge-text-default">
        <KnowledgeRichText text={title} variant="title" />
      </div>
      {onSuggestEdit ? (
        <button
          aria-label={`Suggest edit for ${title}`}
          className="flex size-6 shrink-0 items-center justify-center rounded-[4px] bg-white/0 p-1 text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
          data-testid="taxonomy-leaf-disclosure-edit-button"
          onClick={(event) => {
            stopCanvasPropagation(event);
            onSuggestEdit({
              content: node.content,
              currentVersion: node.currentVersion,
              nodeId: node.graphNodeId,
              title: node.title,
            });
          }}
          onDoubleClick={stopCanvasPropagation}
          onPointerDown={stopCanvasPropagation}
          onPointerUp={stopCanvasPropagation}
          title="Suggest edit"
          type="button"
        >
          <SquarePen aria-hidden="true" className="size-4" strokeWidth={1.7} />
        </button>
      ) : null}
    </div>
  );
}

function LeafDisclosureContent({ content }: { readonly content: string }) {
  return (
    <ScrollArea
      className={DISCLOSURE_CONTENT_SCROLL_CLASS}
      data-testid="taxonomy-leaf-disclosure-content-scroll-area"
      viewportClassName={DISCLOSURE_CONTENT_VIEWPORT_CLASS}
    >
      <KnowledgeRichText text={content} variant="content" />
    </ScrollArea>
  );
}

export const LeafDisclosureOverlay = forwardRef<
  LeafDisclosureOverlayHandle,
  LeafDisclosureOverlayProps
>(function LeafDisclosureOverlay(
  { canvas, disclosure, onSuggestEdit, viewport },
  ref,
) {
  const elementRef = useRef<HTMLElement | null>(null);
  const canvasRef = useRef(canvas);
  const disclosureRef = useRef(disclosure);
  const viewportRef = useRef(viewport);

  const syncViewport = useCallback((nextViewport: LeafOrthographicViewport) => {
    viewportRef.current = nextViewport;

    const currentDisclosure = disclosureRef.current;
    if (!currentDisclosure || !elementRef.current) {
      return;
    }

    const nextPosition = resolvePosition({
      canvas: canvasRef.current,
      disclosure: currentDisclosure,
      viewport: nextViewport,
    });

    elementRef.current.style.transform = disclosureTransform(nextPosition);
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      syncViewport,
    }),
    [syncViewport],
  );

  useLayoutEffect(() => {
    canvasRef.current = canvas;
    syncViewport(viewportRef.current);
  }, [canvas, syncViewport]);

  useLayoutEffect(() => {
    disclosureRef.current = disclosure;
    syncViewport(viewportRef.current);
  }, [disclosure, syncViewport]);

  useLayoutEffect(() => {
    viewportRef.current = viewport;
    syncViewport(viewport);
  }, [syncViewport, viewport]);

  if (!disclosure) {
    return null;
  }

  const currentPosition = resolvePosition({
    canvas,
    disclosure,
    viewport,
  });
  const sharedProps = {
    className: DISCLOSURE_CARD_CLASS,
    "data-disclosure-mode": disclosure.mode,
    "data-testid": "taxonomy-leaf-disclosure-overlay",
    onClick: stopCanvasPropagation,
    onDoubleClick: stopCanvasPropagation,
    onKeyDown: stopCanvasPropagation,
    onPointerDown: stopCanvasPropagation,
    onPointerUp: stopCanvasPropagation,
    onWheel: stopCanvasPropagation,
    style: {
      transform: disclosureTransform(currentPosition),
    },
  } as const;

  if (disclosure.mode === "selected") {
    return (
      <dialog
        {...sharedProps}
        aria-label="Selected knowledge card"
        open
        ref={(element) => {
          elementRef.current = element;
        }}
      >
        <LeafDisclosureHeader
          node={disclosure.node}
          onSuggestEdit={onSuggestEdit}
          title={disclosure.node.title}
        />
        <LeafDisclosureContent content={disclosure.node.content} />
      </dialog>
    );
  }

  return (
    <div
      {...sharedProps}
      ref={(element) => {
        elementRef.current = element;
      }}
    >
      <LeafDisclosureHeader
        node={disclosure.node}
        onSuggestEdit={onSuggestEdit}
        title={disclosure.node.title}
      />
      <LeafDisclosureContent content={disclosure.node.content} />
    </div>
  );
});
