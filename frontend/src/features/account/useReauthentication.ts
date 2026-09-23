import { onScopeDispose, ref, watch } from "vue";
import { sessionApi } from "../../api/session";
import { errorMessage } from "../../api/client";
import { useSessionStore } from "../../stores/session";
export function useReauthentication() {
  const session = useSessionStore();
  const recentlyConfirmed = ref(false),
    reauthDialog = ref(false),
    reauthPassword = ref(""),
    reauthError = ref(""),
    reauthBusy = ref(false);
  let pending: (() => void | Promise<void>) | null = null,
    generation = 0;
  function clearPending(open: boolean) {
    if (!open) {
      pending = null;
      reauthPassword.value = "";
    }
  }
  function reset() {
    generation++;
    recentlyConfirmed.value = false;
    reauthDialog.value = false;
    reauthBusy.value = false;
    reauthError.value = "";
    clearPending(false);
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  watch(reauthDialog, clearPending);
  function secure(action: () => void | Promise<void>) {
    if (recentlyConfirmed.value) return action();
    pending = action;
    reauthError.value = "";
    reauthDialog.value = true;
  }
  async function reauthenticate() {
    if (reauthBusy.value) return;
    const id = generation;
    reauthBusy.value = true;
    reauthError.value = "";
    try {
      await sessionApi.reauthenticate(reauthPassword.value);
      if (id !== generation) return;
      recentlyConfirmed.value = true;
      const action = pending;
      reauthDialog.value = false;
      clearPending(false);
      await action?.();
    } catch (cause) {
      if (id === generation) reauthError.value = errorMessage(cause);
    } finally {
      reauthPassword.value = "";
      if (id === generation) reauthBusy.value = false;
    }
  }
  return {
    recentlyConfirmed,
    reauthDialog,
    reauthPassword,
    reauthError,
    reauthBusy,
    clearPending,
    secure,
    reauthenticate,
  };
}
