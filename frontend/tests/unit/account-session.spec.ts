import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import {
  AxiosError,
  AxiosHeaders,
  type InternalAxiosRequestConfig,
} from "axios";
import { api, clearCsrf } from "../../src/api/client";
import { parseProfile, sessionApi } from "../../src/api/session";
import { useSessionStore } from "../../src/stores/session";
import { deferred, profileFixture } from "./account-fixtures";
let pinia = createPinia();
const originalAdapter = api.defaults.adapter;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  clearCsrf();
});
afterEach(() => {
  disposePinia(pinia);
  if (originalAdapter) api.defaults.adapter = originalAdapter;
  else delete api.defaults.adapter;
  vi.restoreAllMocks();
});
function response(config: InternalAxiosRequestConfig, data: unknown) {
  return {
    config,
    data,
    status: 200,
    statusText: "OK",
    headers: new AxiosHeaders(),
  };
}
describe("session and API ownership", () => {
  it("initializes cookie session state when browser storage is unavailable", () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("Storage blocked", "SecurityError");
    });
    expect(() => useSessionStore()).not.toThrow();
    expect(useSessionStore().ready).toBe(false);
  });
  it("deduplicates CSRF acquisition and attaches it only after acquisition", async () => {
    const token = deferred<string>();
    const calls: string[] = [];
    api.defaults.adapter = async (config) => {
      calls.push(config.url || "");
      if (config.url === "/api/v1/auth/csrf")
        return response(config, { csrf_token: await token.promise });
      expect(config.headers.get("X-CSRF-Token")).toBe("csrf");
      expect(config.withCredentials).toBe(true);
      return response(config, {});
    };
    const first = api.post("/api/v1/me/api-keys", {}),
      second = api.post("/api/v1/auth/logout");
    await vi.waitFor(() => expect(calls).toEqual(["/api/v1/auth/csrf"]));
    token.complete("csrf");
    await Promise.all([first, second]);
    expect(calls.filter((url) => url.endsWith("/csrf"))).toHaveLength(1);
  });
  it("rejects an external destination before invoking the adapter", async () => {
    const adapter = vi.fn();
    api.defaults.adapter = adapter;
    await expect(api.get("https://untrusted.invalid/api")).rejects.toThrow(
      "configured API origin",
    );
    expect(adapter).not.toHaveBeenCalled();
  });
  it("does not send a mutation with an obsolete CSRF acquisition", async () => {
    const token = deferred<string>();
    const calls: string[] = [];
    api.defaults.adapter = async (config) => {
      calls.push(config.url || "");
      return response(config, { csrf_token: await token.promise });
    };
    const pending = api.post("/api/v1/auth/logout");
    const rejected = expect(pending).rejects.toThrow("Session changed");
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    clearCsrf();
    token.complete("old");
    await rejected;
    expect(calls).toEqual(["/api/v1/auth/csrf"]);
  });
  it("does not install a private profile arriving after invalidation", async () => {
    const pending = deferred<ReturnType<typeof profileFixture>>();
    vi.spyOn(sessionApi, "profile").mockReturnValue(pending.promise);
    const store = useSessionStore();
    const result = store.refreshProfile();
    store.invalidate();
    pending.complete(profileFixture());
    await result;
    expect(store.profile).toBeNull();
    expect(store.ready).toBe(true);
  });
  it("retains a signed-in profile when logout fails", async () => {
    const store = useSessionStore();
    store.profile = profileFixture();
    vi.spyOn(sessionApi, "logout").mockRejectedValue(new Error("offline"));
    await expect(store.logout()).rejects.toThrow("offline");
    expect(store.profile?.username).toBe("researcher");
  });
  it("ignores an obsolete 401 after a newer identity was installed", async () => {
    const pending = deferred<void>();
    let started = false;
    api.defaults.adapter = async (config) => {
      started = true;
      await pending.promise;
      throw new AxiosError(
        "Unauthorized",
        "ERR_BAD_REQUEST",
        config,
        undefined,
        { ...response(config, {}), status: 401 },
      );
    };
    const store = useSessionStore();
    store.profile = profileFixture();
    const request = api.get("/api/v1/me");
    const rejected = expect(request).rejects.toThrow("Unauthorized");
    await vi.waitFor(() => expect(started).toBe(true));
    store.invalidate();
    store.profile = profileFixture({ id: 99, username: "new-account" });
    pending.complete();
    await rejected;
    expect(store.profile.username).toBe("new-account");
  });
  it("accepts nullable optional profile references but rejects an unknown privilege", () => {
    expect(
      parseProfile({
        ...profileFixture(),
        github: null,
        orcid: null,
      }).github,
    ).toBe("");
    expect(() => parseProfile({ ...profileFixture(), role: "root" })).toThrow(
      "Invalid role",
    );
  });
});
