// abstract: DeckGL child disclosure overlay for hovered or selected taxonomy leaf points.
// out_of_scope: deck.gl picking, title/detail data fetching, and graph focus semantics.

import { SquarePen } from "lucide-react";
import type { SyntheticEvent } from "react";
import { useCallback, useRef } from "react";

import { KnowledgeRichText, ScrollArea } from "../../../../shared/ui";
import type { SearchResultCardEditPayload } from "../../../search/components/SearchResultCard";
import type { LayoutViewport } from "../layout/taxonomyLayoutTypes";
import { projectLeafWorldPoint } from "./leafProjection";
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

const DISCLOSURE_GAP_PX = 8;
const DISCLOSURE_CARD_SIZE_CLASS =
  "[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-md)] [--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-md)] [--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-md)] lg:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-lg)] lg:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-lg)] lg:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-lg)] xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-xl)] xl:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-xl)] xl:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-xl)] 2xl:[--leaf-disclosure-card-width:var(--spacing-knowledge-leaf-disclosure-width-2xl)] 2xl:[--leaf-disclosure-card-height:var(--spacing-knowledge-leaf-disclosure-height-2xl)] 2xl:[--leaf-disclosure-card-content-height:var(--spacing-knowledge-leaf-disclosure-content-height-2xl)]";
const DISCLOSURE_CARD_CLASS = `absolute top-0 left-0 z-[22] m-0 pointer-events-auto flex max-h-[var(--leaf-disclosure-card-height)] w-[min(var(--leaf-disclosure-card-width),calc(100%_-_24px))] flex-col items-start gap-2 overflow-hidden rounded-knowledge-leaf-disclosure border border-knowledge-leaf-disclosure-border bg-knowledge-surface-card-solid px-4 py-4 text-left shadow-knowledge-leaf-disclosure ${DISCLOSURE_CARD_SIZE_CLASS}`;
const DISCLOSURE_TITLE_AREA_CLASS =
  "min-w-0 flex-1 whitespace-normal break-words";
const DISCLOSURE_TITLE_TRACK_CLASS =
  "min-w-0 whitespace-normal break-words [&_[data-testid=knowledge-rich-text-title]]:whitespace-normal [&_[data-testid=knowledge-rich-text-title]]:text-knowledge-leaf-disclosure-title [&_[data-testid=knowledge-rich-text-title]]:font-medium [&_[data-testid=knowledge-rich-text-title]]:text-knowledge-text-default";
const DISCLOSURE_CONTENT_SCROLL_CLASS =
  "[--scroll-area-padding-right:var(--spacing-knowledge-leaf-disclosure-scrollbar-width)] [--scroll-area-scrollbar-width:var(--spacing-knowledge-leaf-disclosure-scrollbar-width)] max-h-[var(--leaf-disclosure-card-content-height)] min-h-0 w-full flex-1";
const DISCLOSURE_CONTENT_VIEWPORT_CLASS =
  "max-h-[var(--leaf-disclosure-card-content-height)] overflow-x-hidden overflow-y-auto overscroll-contain [&_[data-testid=knowledge-rich-text-content]]:text-knowledge-leaf-disclosure-body [&_[data-testid=knowledge-rich-text-content]]:text-knowledge-text-muted";

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

function stopNativeCanvasPropagation(event: WheelEvent) {
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
    <div
      className="flex min-h-6 w-full shrink-0 items-start justify-between gap-2"
      data-testid="taxonomy-leaf-disclosure-header"
    >
      <div
        className={DISCLOSURE_TITLE_AREA_CLASS}
        data-testid="taxonomy-leaf-disclosure-title-area"
      >
        <div
          className={DISCLOSURE_TITLE_TRACK_CLASS}
          data-testid="taxonomy-leaf-disclosure-title-track"
        >
          <KnowledgeRichText text={title} variant="title" />
        </div>
      </div>
      {onSuggestEdit ? (
        <button
          aria-label={`Suggest edit for ${title}`}
          className="flex size-6 shrink-0 items-center justify-center rounded-knowledge-control-compact bg-transparent p-1 text-knowledge-text-muted transition-colors hover:bg-knowledge-surface-hover hover:text-knowledge-text-default focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-brand"
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
      viewportFillsContainer={false}
      viewportClassName={DISCLOSURE_CONTENT_VIEWPORT_CLASS}
    >
      <KnowledgeRichText text={content} variant="content" />
    </ScrollArea>
  );
}

export function LeafDisclosureOverlay({
  canvas,
  disclosure,
  onSuggestEdit,
  viewport,
}: LeafDisclosureOverlayProps) {
  const disclosureElementRef = useRef<HTMLElement | null>(null);
  const setDisclosureElementRef = useCallback((element: HTMLElement | null) => {
    const currentElement = disclosureElementRef.current;

    if (currentElement) {
      currentElement.removeEventListener("wheel", stopNativeCanvasPropagation, {
        capture: true,
      });
    }

    if (element) {
      element.addEventListener("wheel", stopNativeCanvasPropagation, {
        capture: true,
        passive: false,
      });
    }

    disclosureElementRef.current = element;
  }, []);

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
    onWheelCapture: stopCanvasPropagation,
    ref: setDisclosureElementRef,
    style: {
      transform: disclosureTransform(currentPosition),
    },
  } as const;

  if (disclosure.mode === "selected") {
    return (
      <dialog {...sharedProps} aria-label="Selected knowledge card" open>
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
    <div {...sharedProps}>
      <LeafDisclosureHeader
        node={disclosure.node}
        onSuggestEdit={onSuggestEdit}
        title={disclosure.node.title}
      />
      <LeafDisclosureContent content={disclosure.node.content} />
    </div>
  );
}
