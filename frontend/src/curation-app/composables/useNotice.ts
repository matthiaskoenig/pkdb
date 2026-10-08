import { onBeforeUnmount, readonly, ref, type Ref } from "vue";
import { NOTICE_MS } from "../study";

/**
 * The notice of the last action that succeeded, for a polite live region: `announce` shows a
 * text, which disappears after `NOTICE_MS`; an empty text clears it at once.
 */
export function useNotice(): { notice: Readonly<Ref<string>>; announce: (text: string) => void } {
  const notice = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  function announce(text: string): void {
    clearTimeout(timer);
    notice.value = text;
    timer = text ? setTimeout(() => (notice.value = ""), NOTICE_MS) : undefined;
  }

  onBeforeUnmount(() => clearTimeout(timer));
  return { notice: readonly(notice), announce };
}
