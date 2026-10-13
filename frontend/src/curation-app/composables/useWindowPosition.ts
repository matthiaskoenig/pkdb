import { onBeforeUnmount, onMounted, shallowRef, type Ref, type ShallowRef } from "vue";

export interface WindowPosition {
  /** The distance of the top of the element from the top of the window; negative once it scrolled above. */
  top: number;
  /** The height of the window. */
  height: number;
  /** The height of the first row of the element, or null while it has none. */
  rowHeight: number | null;
}

/**
 * Where `element` is in the window, and the height of its first row, which `row` selects: measured
 * when it mounts and once per animation frame while anything in the page scrolls, the window
 * resizes or the element changes its size, as when a larger font makes its rows taller; `schedule`
 * measures again in the next frame, as after a change above the element.
 */
export function useWindowPosition(
  element: Readonly<Ref<HTMLElement | null>>,
  row: string,
): {
  position: Readonly<ShallowRef<WindowPosition>>;
  schedule(): void;
} {
  const position = shallowRef<WindowPosition>({ top: 0, height: window.innerHeight, rowHeight: null });
  let frame = 0;
  let observer: ResizeObserver | undefined;

  function measure(): void {
    frame = 0;
    const top = element.value?.getBoundingClientRect().top ?? 0;
    const height = window.innerHeight;
    // A row without a layout, as in a hidden page, keeps the last height.
    const rowHeight = element.value?.querySelector(row)?.getBoundingClientRect().height || position.value.rowHeight;
    const last = position.value;
    if (top !== last.top || height !== last.height || rowHeight !== last.rowHeight) {
      position.value = { top, height, rowHeight };
    }
  }

  function schedule(): void {
    if (frame === 0) frame = requestAnimationFrame(measure);
  }

  onMounted(() => {
    // Capture: scroll events do not bubble, and any scrolling ancestor moves the element.
    document.addEventListener("scroll", schedule, { capture: true, passive: true });
    window.addEventListener("resize", schedule, { passive: true });
    // In the next frame, not in the callback: the new position changes the size of the element,
    // which the browser would report as a loop of the observer.
    observer = new ResizeObserver(schedule);
    if (element.value) observer.observe(element.value);
    measure();
  });
  onBeforeUnmount(() => {
    document.removeEventListener("scroll", schedule, { capture: true });
    window.removeEventListener("resize", schedule);
    observer?.disconnect();
    cancelAnimationFrame(frame);
  });
  return { position, schedule };
}
