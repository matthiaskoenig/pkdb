import type { App } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { csrfToken, setCsrfToken } from "../../src/curation-app/api/client";
import { start } from "../../src/curation-app/start";

let app: App | undefined;
let target: HTMLElement;

beforeEach(() => {
  setCsrfToken("");
  target = document.createElement("div");
  document.body.append(target);
});

afterEach(() => {
  app?.unmount();
  app = undefined;
  target.remove();
  window.history.replaceState(null, "", "/");
});

describe("start", () => {
  it("hands the launch token to the session before the hash router rewrites the hash", async () => {
    window.history.replaceState(null, "", "/#token=launch-token");
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(
      async () =>
        new Response(JSON.stringify({ csrf_token: "csrf-from-session" }), {
          headers: { "Content-Type": "application/json" },
        }),
    );
    app = await start(target);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [input, init] = fetch.mock.calls[0] ?? [];
    expect(String(input)).toBe("/local/session");
    expect(JSON.parse(String(init?.body))).toEqual({ token: "launch-token" });
    expect(csrfToken()).toBe("csrf-from-session");
    expect(window.location.hash).toBe("#/");
    expect(target.textContent).toContain("Local curation");
  });

  it.each(["#token=pasted", "#/token=pasted"])(
    "takes a launch URL pasted into the open app (%s) and shows the overview",
    async (hash) => {
      window.history.replaceState(null, "", "/#/studies/caffeine/Example");
      // Each request with its body and the hash at the time it was sent.
      const calls: [string, string, string][] = [];
      vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        calls.push([`${init?.method ?? "GET"} ${String(input)}`, String(init?.body ?? ""), window.location.hash]);
        return new Response(JSON.stringify({ csrf_token: "pasted-csrf" }), {
          headers: { "Content-Type": "application/json" },
        });
      });
      app = await start(target);
      const router = app.config.globalProperties.$router;
      await router.isReady();
      expect(calls).toEqual([]);

      window.location.hash = hash;
      await vi.waitFor(() => expect(window.location.hash).toBe("#/"));
      await vi.waitFor(() => expect(calls).toHaveLength(2));
      expect(calls).toEqual([
        ["POST /local/session", '{"token":"pasted"}', ""],
        ["GET /local/state", "", ""],
      ]);
      expect(router.currentRoute.value.name).toBe("Overview");
      expect(csrfToken()).toBe("pasted-csrf");
    },
  );

  it("mounts the app when the session cannot be created", async () => {
    window.history.replaceState(null, "", "/#token=used");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    app = await start(target);
    expect(target.textContent).toContain("Local curation");
    expect(window.location.hash).toBe("#/");
  });
});
