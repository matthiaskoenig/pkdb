import { onScopeDispose, ref, watch } from "vue";
import {
  accountApi,
  type AssignedStudy,
  type SecurityEvent,
} from "../../api/account";
import { errorMessage } from "../../api/client";
import { useSessionStore } from "../../stores/session";
export function useActivityPage<T>(
  load: (offset: number, signal: AbortSignal) => Promise<T[]>,
) {
  const session = useSessionStore();
  const rows = ref<T[]>([]),
    offset = ref(0),
    loading = ref(false),
    error = ref("");
  let generation = 0,
    controller = new AbortController();
  function reset() {
    generation++;
    controller.abort();
    controller = new AbortController();
    rows.value = [];
    offset.value = 0;
    loading.value = false;
    error.value = "";
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  async function refresh(next = 0) {
    if (!session.profile || loading.value)
      return;
    const id = generation;
    loading.value = true;
    error.value = "";
    try {
      const result = await load(next, controller.signal);
      if (id === generation) {
        rows.value = result;
        offset.value = next;
      }
    } catch (cause) {
      if (id === generation) error.value = errorMessage(cause);
    } finally {
      if (id === generation) loading.value = false;
    }
  }
  return { rows, offset, loading, error, refresh };
}
export function useAccountActivity() {
  return {
    studies: useActivityPage<AssignedStudy>(accountApi.studies),
    events: useActivityPage<SecurityEvent>(accountApi.events),
  };
}
