import { computed, onScopeDispose, ref, watch } from "vue";
import {
  accountApi,
  type ApiKey,
  type BrowserSession,
  type Identity,
} from "../../api/account";
import type { Provider } from "../../api/session";
import { useSessionStore } from "../../stores/session";
export function useCredentials() {
  const session = useSessionStore();
  const keys = ref<ApiKey[]>([]),
    sessions = ref<BrowserSession[]>([]),
    identities = ref<Identity[]>([]),
    providers = ref<Provider[]>([]);
  const secret = ref(""),
    secretDialog = ref(false),
    rotated = ref(false),
    keyName = ref(""),
    keyDays = ref(90),
    keyWrite = ref(false);
  let controller = new AbortController(),
    generation = 0;
  function reset() {
    generation++;
    controller.abort();
    controller = new AbortController();
    keys.value = [];
    sessions.value = [];
    identities.value = [];
    providers.value = [];
    secret.value = "";
    secretDialog.value = false;
    keyName.value = "";
    keyWrite.value = false;
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  async function loadCredentials() {
    if (!session.profile || session.profile.mfa_required) return;
    const id = ++generation;
    const values = await Promise.all([
      accountApi.keys(controller.signal),
      accountApi.sessions(controller.signal),
      accountApi.identities(controller.signal),
      accountApi.providers(controller.signal),
    ]);
    if (id !== generation) return;
    [keys.value, sessions.value, identities.value, providers.value] = values;
  }
  const canWrite = computed(
    () =>
      !!session.profile &&
      ["curator", "reviewer", "admin"].includes(session.profile.role),
  );
  const availableProviders = computed(() =>
    providers.value.filter(
      (value) => !identities.value.some((item) => item.provider === value),
    ),
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
  async function link(value: Provider) {
    const id = generation;
    const url = await accountApi.providerAction(value, "link");
    if (id === generation) window.location.assign(url);
  }
  async function providerReauth(value: Provider) {
    const id = generation;
    const url = await accountApi.providerAction(value, "reauthenticate");
    if (id === generation) window.location.assign(url);
  }
  async function unlink(value: Identity) {
    await accountApi.unlink(value.id);
    await session.refreshProfile();
    await loadCredentials();
  }
  return {
    keys,
    sessions,
    identities,
    providers,
    secret,
    secretDialog,
    rotated,
    keyName,
    keyDays,
    keyWrite,
    canWrite,
    availableProviders,
    loadCredentials,
    createKey,
    rotateKey,
    revokeKey,
    revokeSession,
    link,
    providerReauth,
    unlink,
  };
}
