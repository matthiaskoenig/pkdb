import { onBeforeUnmount, readonly, ref, type Ref } from "vue";
import { NOTICE_MS } from "../local";

/**
 * The notice of the last action that succeeded, for a polite live region: `announce` shows a
 * text, which disappears after `NOTICE_MS`; an empty text clears it at once.
 */
export interface Notice {
  notice: Readonly<Ref<string>>;
  announce: (text: string) => void;
}

/** A notice that is not bound to a component, such as the one of the draft in the study store. */
export function createNotice(): Notice {
  const notice = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;

  function announce(text: string): void {
    clearTimeout(timer);
    notice.value = text;
    timer = text ? setTimeout(() => (notice.value = ""), NOTICE_MS) : undefined;
  }

  return { notice: readonly(notice), announce };
}

/** The notice of a component; its timer stops when the component unmounts. */
export function useNotice(): Notice {
  const { notice, announce } = createNotice();
  onBeforeUnmount(() => announce(""));
  return { notice, announce };
}
