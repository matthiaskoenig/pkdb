import axios, { CanceledError, type InternalAxiosRequestConfig } from "axios";
import { isRecord } from "./errors";
export { errorMessage } from "./errors";
export const apiBase = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
export const api = axios.create({ baseURL: apiBase || "/", timeout: 30000 });
let csrfToken: string | null = null;
let csrfRequest: Promise<string> | null = null;
let generation = 0;
const requestEpochs = new WeakMap<InternalAxiosRequestConfig, number>();
const unauthorizedListeners = new Set<() => void>();
export function onUnauthorized(listener: () => void) {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}
export function clearCsrf() {
  generation++;
  csrfToken = null;
  csrfRequest = null;
}
export function cleanLegacyCredentials() {
  try {
    for (const key of ["token", "username", "vuex"])
      window.localStorage.removeItem(key);
  } catch {
    // Storage may be disabled by browser privacy policy. Sessions use cookies.
  }
}
api.interceptors.request.use(async (config) => {
  const base = new URL(apiBase || "/", window.location.href);
  const target = new URL(api.getUri(config), window.location.href);
  if (
    target.origin !== base.origin ||
    !["http:", "https:"].includes(target.protocol)
  ) {
    throw new Error("The API client only accepts the configured API origin.");
  }
  const epoch = generation;
  requestEpochs.set(config, epoch);
  config.withCredentials = true;
  if (
    !["get", "head", "options"].includes((config.method || "get").toLowerCase())
  ) {
    if (!csrfToken) {
      if (!csrfRequest) {
        const pending = api
          .get<unknown>("/api/v1/auth/csrf")
          .then((response) => {
            if (epoch !== generation)
              throw new CanceledError("Session changed");
            if (
              !isRecord(response.data) ||
              typeof response.data.csrf_token !== "string" ||
              !response.data.csrf_token
            )
              throw new Error("Invalid CSRF response");
            csrfToken = response.data.csrf_token;
            return csrfToken;
          });
        csrfRequest = pending;
        void pending
          .finally(() => {
            if (csrfRequest === pending) csrfRequest = null;
          })
          .catch(() => {});
      }
      await csrfRequest;
    }
    if (epoch !== generation || config.signal?.aborted)
      throw new CanceledError("Session changed");
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.config &&
      requestEpochs.get(error.config) === generation
    ) {
      if (error.response?.status === 401)
        for (const listener of unauthorizedListeners) listener();
      const data: unknown = error.response?.data;
      if (isRecord(data) && data.code === "csrf_failed") clearCsrf();
    }
    return Promise.reject(error);
  },
);
