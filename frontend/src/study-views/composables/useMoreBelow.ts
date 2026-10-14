import { ref, watch, type Ref } from "vue";

export interface MoreBelow {
  /** Whether more of the region follows below its view. */
  readonly more: Readonly<Ref<boolean>>;
  /** The width of the vertical scroll bar of the region, which a fade at its bottom leaves free. */
  readonly scrollbar: Readonly<Ref<number>>;
}

/**
 * Whether more of the region `region` that scrolls follows below its view, for the fade at its
 * bottom (`MoreBelow.vue`), and the width of its scroll bar. It follows the scrolling of the
 * region and the sizes of the region, which change with the window, and of its content
 * `content`, which changes with what it shows. Both may come and go with the template.
 */
export function useMoreBelow(region: Ref<HTMLElement | null>, content: Ref<HTMLElement | null>): MoreBelow {
  const more = ref(false);
  const scrollbar = ref(0);

  function update(): void {
    const element = region.value;
    if (!element) return;
    more.value = element.scrollTop + element.clientHeight < element.scrollHeight - 1;
    scrollbar.value = element.offsetWidth - element.clientWidth;
  }

  watch(
    [region, content],
    ([element, inner], _, onCleanup) => {
      if (!element) {
        more.value = false;
        return;
      }
      update();
      const observer = new ResizeObserver(update);
      observer.observe(element);
      if (inner) observer.observe(inner);
      element.addEventListener("scroll", update, { passive: true });
      onCleanup(() => {
        observer.disconnect();
        element.removeEventListener("scroll", update);
      });
    },
    { immediate: true, flush: "post" },
  );

  return { more, scrollbar };
}
