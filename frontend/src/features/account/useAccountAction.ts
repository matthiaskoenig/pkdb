import { onScopeDispose, ref, watch } from "vue";
import { useSessionStore } from "../../stores/session";
import { errorMessage } from "../../api/client";
export function useAccountAction() {
  const session = useSessionStore();
  const busy = ref(false),
    error = ref(""),
    notice = ref("");
  let generation = 0;
  function reset() {
    generation++;
    busy.value = false;
    error.value = "";
    notice.value = "";
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  async function run(
    action: (current: () => boolean) => Promise<void>,
    message = "",
  ) {
    if (busy.value) return;
    busy.value = true;
    error.value = "";
    notice.value = "";
    const id = generation;
    const current = () => id === generation;
    try {
      await action(current);
      if (current() && message) notice.value = message;
    } catch (cause) {
      if (current()) error.value = errorMessage(cause);
    } finally {
      if (current()) busy.value = false;
    }
  }
  return { busy, error, notice, run, reset };
}
