import { onBeforeUnmount, onMounted, shallowRef, type Ref, type ShallowRef } from "vue";

export interface WindowPosition {
  /** The distance of the top of the element from the top of the window; negative once it scrolled above. */
  top: number;
  /** The height of the window. */
  height: number;
}

/**
 * Where `element` is in the window: measured when it mounts and once per animation frame while
 * anything in the page scrolls or the window resizes; `schedule` measures again in the next
 * frame, as after a change above the element.
 */
export function useWindowPosition(element: Readonly<Ref<HTMLElement | null>>): {
  position: Readonly<ShallowRef<WindowPosition>>;
  schedule(): void;
} {
  const position = shallowRef<WindowPosition>({ top: 0, height: window.innerHeight });
  let frame = 0;

  function measure(): void {
    frame = 0;
    const top = element.value?.getBoundingClientRect().top ?? 0;
    const height = window.innerHeight;
    if (top !== position.value.top || height !== position.value.height) position.value = { top, height };
  }

  function schedule(): void {
    if (frame === 0) frame = requestAnimationFrame(measure);
  }

  onMounted(() => {
    // Capture: scroll events do not bubble, and any scrolling ancestor moves the element.
    document.addEventListener("scroll", schedule, { capture: true, passive: true });
    window.addEventListener("resize", schedule, { passive: true });
    measure();
  });
  onBeforeUnmount(() => {
    document.removeEventListener("scroll", schedule, { capture: true });
    window.removeEventListener("resize", schedule);
    cancelAnimationFrame(frame);
  });
  return { position, schedule };
}
