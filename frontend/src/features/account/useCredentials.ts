import { computed, onScopeDispose, ref, watch } from "vue";
import {
  accountApi,
  type ApiKey,
  type BrowserSession,
} from "../../api/account";
import { useSessionStore } from "../../stores/session";
export function useCredentials() {
  const session = useSessionStore();
  const keys = ref<ApiKey[]>([]),
    sessions = ref<BrowserSession[]>([]);
  const secret = ref(""),
    secretDialog = ref(false),
    rotated = ref(false),
    keyName = ref(""),
    keyDays = ref(90),
    keyWrite = ref(true);
  let controller = new AbortController(),
    generation = 0;
  function reset() {
    generation++;
    controller.abort();
    controller = new AbortController();
    keys.value = [];
    sessions.value = [];
    secret.value = "";
    secretDialog.value = false;
    keyName.value = "";
    keyWrite.value = true;
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  async function loadCredentials() {
    if (!session.profile) return;
    const id = ++generation;
    const values = await Promise.all([
      accountApi.keys(controller.signal),
      accountApi.sessions(controller.signal),
    ]);
    if (id !== generation) return;
    [keys.value, sessions.value] = values;
  }
  const canWrite = computed(
    () =>
      !!session.profile &&
      ["curator", "reviewer", "admin"].includes(session.profile.role),
  );
  async function createKey() {
    const id = generation;
    const value = await accountApi.createKey(
      keyName.value.trim(),
      Number(keyDays.value),
      keyWrite.value && canWrite.value,
    );
    if (id !== generation) return;
    secret.value = value;
    secretDialog.value = true;
    rotated.value = false;
    keyName.value = "";
    await loadCredentials();
  }
  async function rotateKey(key: ApiKey) {
    const id = generation;
    const value = await accountApi.rotateKey(key.id);
    if (id !== generation) return;
    secret.value = value;
    secretDialog.value = true;
    rotated.value = true;
    await loadCredentials();
  }
  async function revokeKey(key: ApiKey) {
    await accountApi.revokeKey(key.id);
    await loadCredentials();
  }
  async function revokeSession(value: BrowserSession) {
    await accountApi.revokeSession(value.id);
    if (value.current) session.invalidate();
    else await loadCredentials();
  }
  return {
    keys,
    sessions,
    secret,
    secretDialog,
    rotated,
    keyName,
    keyDays,
    keyWrite,
    canWrite,
    loadCredentials,
    createKey,
    rotateKey,
    revokeKey,
    revokeSession,
  };
}
