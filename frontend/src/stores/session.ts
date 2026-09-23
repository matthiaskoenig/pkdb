import { computed, onScopeDispose, ref } from "vue";
import { defineStore } from "pinia";
import {
  clearCsrf,
  cleanLegacyCredentials,
  onUnauthorized,
} from "../api/client";
import { errorMessage, errorStatus } from "../api/errors";
import { sessionApi, type Profile } from "../api/session";
export const useSessionStore = defineStore("session", () => {
  const profile = ref<Profile | null>(null);
  const ready = ref(false);
  const epoch = ref(0);
  const error = ref("");
  const loading = ref(false);
  let request = 0;
  cleanLegacyCredentials();
  function invalidate() {
    error.value = "";
    request++;
    epoch.value++;
    profile.value = null;
    ready.value = true;
    loading.value = false;
    clearCsrf();
  }
  onScopeDispose(onUnauthorized(invalidate));
  async function refreshProfile() {
    const identity = ++request;
    loading.value = true;
    error.value = "";
    try {
      const next = await sessionApi.profile();
      if (identity !== request) return;
      const before = profile.value;
      if (
        !before ||
        [
          before.id,
          before.role,
          before.mfa_required,
          before.mfa_recent,
        ].join() !==
          [next.id, next.role, next.mfa_required, next.mfa_recent].join()
      ) {
        epoch.value++;
        clearCsrf();
      }
      profile.value = next;
      return next;
    } catch (cause) {
      if (identity !== request) return;
      invalidate();
      if (errorStatus(cause) !== 401) {
        error.value = errorMessage(cause);
        throw cause;
      }
    } finally {
      if (identity === request) {
        loading.value = false;
        ready.value = true;
      }
    }
  }
  async function login(username: string, password: string) {
    await sessionApi.login(username, password);
    invalidate();
    return refreshProfile();
  }
  async function logout() {
    await sessionApi.logout();
    invalidate();
  }
  const status = computed(() =>
    loading.value
      ? "loading"
      : error.value
        ? "error"
        : !ready.value
          ? "unknown"
          : profile.value
            ? "authenticated"
            : "anonymous",
  );
  return {
    profile,
    ready,
    epoch,
    error,
    loading,
    status,
    authenticated: computed(() => profile.value !== null),
    refreshProfile,
    login,
    logout,
    invalidate,
  };
});
