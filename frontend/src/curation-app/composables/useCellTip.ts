/**
 * One tooltip for the cells of a grid, or for other elements of a large table, such as the study
 * identities of the overview. The cells that have one carry `data-tip`, whose value names what the
 * tooltip shows. The tooltip follows the pointer and the keyboard focus, as the tooltips of Vuetify
 * do, but one tooltip serves every cell, so that a large table renders none per cell.
 * A tooltip of the pointer moves to another cell only once the pointer rested there for
 * `TIP_LINGER`, so that the pointer can cross the cells below its cell on its way onto it. Escape
 * hides it; when the pointer is in its cell, it shows there again once the pointer left the cell.
 */
import { onScopeDispose, ref, shallowRef, type Ref } from "vue";

/** How long the pointer rests on a cell before its tooltip shows. */
export const TIP_DELAY = 300;

/**
 * How long a tooltip of the pointer stays after the pointer left its cell or the tooltip, so
 * that the pointer can move from the cell onto the tooltip, and how long the pointer rests on
 * another cell with a tooltip before the tooltip moves there.
 */
export const TIP_LINGER = 150;

export interface CellTip {
  /** The cell whose tooltip shows; null while none shows. */
  readonly cell: Readonly<Ref<HTMLElement | null>>;
  /** The `data-tip` of that cell. */
  readonly key: Readonly<Ref<string | null>>;
  /** For `mouseover` of the element around the cells. */
  over(event: MouseEvent): void;
  /** For `mouseout` of the element around the cells. */
  out(event: MouseEvent): void;
  /** For `focusin` of the element around the cells. */
  focusIn(event: FocusEvent): void;
  /** For `focusout` of the element around the cells. */
  focusOut(event: FocusEvent): void;
  /** For `mouseenter` of the tooltip, which the pointer may rest on. */
  enterTip(): void;
  /** For `mouseleave` of the tooltip. */
  leaveTip(): void;
  /** The cells scrolled in `view`: another cell is under the pointer now, and a focused cell may have left the view. */
  scrolled(view: HTMLElement | null): void;
  /** Hide the tooltip at once. */
  hide(): void;
}

/** The cell with a tooltip that holds `target`. */
function cellOf(target: EventTarget | null): HTMLElement | null {
  return target instanceof Element ? target.closest<HTMLElement>("[data-tip]") : null;
}

/** Whether the focus of `element` shows its ring, as after a key; without `:focus-visible`, every focus. */
function focusVisible(element: Element): boolean {
  try {
    return element.matches(":focus-visible");
  } catch {
    return true;
  }
}

/** Whether `rect` lies outside `view`; a view without a layout holds everything. */
function outside(rect: DOMRect, view: DOMRect): boolean {
  if (!view.width || !view.height) return false;
  return rect.bottom <= view.top || rect.top >= view.bottom || rect.right <= view.left || rect.left >= view.right;
}

export function useCellTip(): CellTip {
  const cell = shallowRef<HTMLElement | null>(null);
  const key = ref<string | null>(null);
  /** What showed the tooltip: a tooltip of the focus stays while its cell has the focus. */
  let opener: "pointer" | "focus" | null = null;
  /**
   * The cell that the pointer rests on while its tooltip waits: for `TIP_DELAY` to show, or for
   * `TIP_LINGER` to move there from the open tooltip of the pointer.
   */
  let waiting: HTMLElement | null = null;
  /** The cell with a tooltip that the pointer is in. */
  let hovered: HTMLElement | null = null;
  /**
   * The cell whose tooltip Escape hid, or that the tooltip was to move to, while the pointer was
   * in it: it shows again once the pointer left the cell.
   */
  let dismissed: HTMLElement | null = null;
  /** Whether the scope ended: then nothing shows any more. */
  let disposed = false;
  let showTimer: ReturnType<typeof setTimeout> | undefined;
  let hideTimer: ReturnType<typeof setTimeout> | undefined;

  function stopTimers(): void {
    clearTimeout(showTimer);
    clearTimeout(hideTimer);
    showTimer = undefined;
    hideTimer = undefined;
    waiting = null;
  }

  function escape(event: KeyboardEvent): void {
    if (event.key !== "Escape") return;
    if (hovered !== null && (hovered === cell.value || hovered === waiting)) dismissed = hovered;
    hide();
  }

  function show(target: HTMLElement, by: "pointer" | "focus"): void {
    if (disposed) return;
    stopTimers();
    if (cell.value === null) document.addEventListener("keydown", escape, true);
    cell.value = target;
    key.value = target.dataset.tip ?? null;
    opener = by;
  }

  function hide(): void {
    stopTimers();
    if (cell.value !== null) document.removeEventListener("keydown", escape, true);
    cell.value = null;
    key.value = null;
    opener = null;
  }

  function hideSoon(): void {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, TIP_LINGER);
  }

  function over(event: MouseEvent): void {
    const target = cellOf(event.target);
    if (target) hovered = target;
    if (disposed || !target || target === waiting || target === dismissed) return;
    // Back in the cell of the tooltip: it stays there.
    if (target === cell.value) {
      stopTimers();
      return;
    }
    // An open tooltip of the pointer moves to the next cell once the pointer rested there for
    // `TIP_LINGER`, rather than hides; the pointer may only cross the cell on its way onto the
    // tooltip, which `enterTip` keeps where it is.
    const delay = opener === "pointer" ? TIP_LINGER : TIP_DELAY;
    stopTimers();
    waiting = target;
    showTimer = setTimeout(() => show(target, "pointer"), delay);
  }

  function out(event: MouseEvent): void {
    const from = cellOf(event.target);
    if (!from || (event.relatedTarget instanceof Node && from.contains(event.relatedTarget))) return;
    if (from === hovered) hovered = null;
    if (from === dismissed) dismissed = null;
    if (from === waiting) {
      clearTimeout(showTimer);
      waiting = null;
      // The tooltip of the pointer that was to move here hides, unless the pointer reaches it.
      if (opener === "pointer") hideSoon();
    }
    if (from === cell.value && opener === "pointer") hideSoon();
  }

  function focusIn(event: FocusEvent): void {
    if (disposed) return;
    const target = cellOf(event.target);
    if (target && event.target instanceof Element && focusVisible(event.target)) show(target, "focus");
  }

  function focusOut(event: FocusEvent): void {
    const current = cell.value;
    if (opener !== "focus" || !current) return;
    if (event.relatedTarget instanceof Node && current.contains(event.relatedTarget)) return;
    hide();
  }

  /** The pointer reached the tooltip: it neither hides nor moves to a cell that the pointer crossed. */
  function enterTip(): void {
    stopTimers();
  }

  function leaveTip(): void {
    if (opener === "pointer") hideSoon();
  }

  function scrolled(view: HTMLElement | null): void {
    const current = cell.value;
    if (!current) return;
    if (opener === "pointer") hide();
    else if (view && outside(current.getBoundingClientRect(), view.getBoundingClientRect())) hide();
  }

  onScopeDispose(() => {
    disposed = true;
    hide();
  });
  return { cell, key, over, out, focusIn, focusOut, enterTip, leaveTip, scrolled, hide };
}
