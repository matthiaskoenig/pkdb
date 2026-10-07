import { beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";
import {
  ApiError,
  ServerStopped,
  SessionMissing,
  UnexpectedResponse,
  csrfToken,
  getJson,
  isAbort,
  isNoUser,
  isRevisionConflict,
  isValidationError,
  postJson,
  setCsrfToken,
  studyPath,
} from "../../src/curation-app/api/client";
import { bootstrap, launchToken } from "../../src/curation-app/api/session";
import { hasKeys, isRecord } from "../../src/curation-app/api/types";

function json(
  body: unknown,
  { status = 200, headers = {} }: { status?: number; headers?: Record<string, string> } = {},
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

/** The URL and init of the only fetch call. */
function request(fetch: MockInstance<typeof globalThis.fetch>) {
  expect(fetch).toHaveBeenCalledTimes(1);
  const [input, init] = fetch.mock.calls[0] ?? [];
  return { url: String(input), init: init ?? {}, headers: new Headers(init?.headers) };
}

/** The error that a promise rejects with. */
async function rejection(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("Expected the promise to reject");
}

beforeEach(() => {
  setCsrfToken("");
});

describe("getJson", () => {
  it("returns the data and the ETag without sending If-None-Match at first", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ ok: true }, { headers: { ETag: '"v1"' } }));
    await expect(getJson("/local/state", isRecord)).resolves.toEqual({ status: 200, etag: '"v1"', data: { ok: true } });
    const { url, init, headers } = request(fetch);
    expect(url).toBe("/local/state");
    expect(headers.has("If-None-Match")).toBe(false);
    expect(init.credentials).toBe("same-origin");
  });

  it("sends If-None-Match with the ETag and reports 304 with the ETag", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 304, headers: { ETag: '"v1"' } }));
    await expect(getJson("/local/state", isRecord, { etag: '"v1"' })).resolves.toEqual({ status: 304, etag: '"v1"' });
    expect(request(fetch).headers.get("If-None-Match")).toBe('"v1"');
  });

  it("refuses a response that is not an object", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(["not", "an", "object"]));
    const error = await rejection(getJson("/local/state", isRecord));
    expect(error).toBeInstanceOf(UnexpectedResponse);
    expect(error).not.toBeInstanceOf(ApiError);
  });

  it("refuses an object without one of the expected keys", async () => {
    const isPair = hasKeys<{ revision: string; content: string }>("revision", "content");
    expect(isPair({ revision: "r1", content: "" })).toBe(true);
    expect(isPair({ revision: "r1" })).toBe(false);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ revision: "r1" }));
    const error = await rejection(getJson("/local/studies/caffeine/Example", isPair));
    expect(error).toBeInstanceOf(UnexpectedResponse);
    expect(error instanceof UnexpectedResponse && error.status).toBe(200);
  });

  it("keeps the CSRF token of the state, so that POSTs work after a restart of the server", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(json({ csrf_token: "after-restart" }));
    await getJson("/local/state", isRecord);
    expect(csrfToken()).toBe("after-restart");
    fetch.mockResolvedValueOnce(json({ ok: true }));
    await postJson("/local/pause", { paused: true }, isRecord);
    expect(new Headers(fetch.mock.calls[1]?.[1]?.headers).get("X-CSRF-Token")).toBe("after-restart");
  });
});

describe("postJson", () => {
  it("sends the JSON body with the CSRF header and same-origin credentials", async () => {
    setCsrfToken("csrf-1");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ ok: true }));
    await expect(postJson("/local/jobs", { ids: ["caffeine/Example"], action: "validate" }, isRecord)).resolves.toEqual({
      ok: true,
    });
    const { url, init, headers } = request(fetch);
    expect(url).toBe("/local/jobs");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("same-origin");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-1");
    expect(JSON.parse(String(init.body))).toEqual({ ids: ["caffeine/Example"], action: "validate" });
  });

  it("takes a fresh CSRF token from the state and sends the action once more when the token is refused", async () => {
    setCsrfToken("");
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json({ error: "Missing or invalid action token" }, { status: 403 }))
      .mockResolvedValueOnce(json({ workspace: "/work", csrf_token: "fresh" }))
      .mockResolvedValueOnce(json({ revision: "r2" }));
    await expect(postJson("/local/studies/metadata", { study: "caffeine/Example" }, isRecord)).resolves.toEqual({
      revision: "r2",
    });
    const calls = fetch.mock.calls.map(([input, init]) => [
      init?.method ?? "GET",
      String(input),
      new Headers(init?.headers).get("X-CSRF-Token"),
    ]);
    expect(calls).toEqual([
      ["POST", "/local/studies/metadata", ""],
      ["GET", "/local/state", null],
      ["POST", "/local/studies/metadata", "fresh"],
    ]);
  });

  it("sends a refused action only once more", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) =>
        String(input) === "/local/state"
          ? json({ csrf_token: "fresh" })
          : json({ error: "Missing or invalid action token" }, { status: 403 }),
      );
    const error = await rejection(postJson("/local/jobs", {}, isRecord));
    expect(error).toBeInstanceOf(ApiError);
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("never sends an action again that a missing user refused", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(json({ error: "no_user", message: "Set a PK-DB user first" }, { status: 403 }));
    expect(isNoUser(await rejection(postJson("/local/studies/review", {}, isRecord)))).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("turns a stale revision into a revision conflict with the current document", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json(
        {
          error: "study.json changed on disk since it was read",
          file: "study.json",
          revision: "r2",
          content: '{"format": 2}',
        },
        { status: 409 },
      ),
    );
    const error = await rejection(postJson("/local/studies/metadata", { study: "caffeine/Example" }, isRecord));
    expect(error).toBeInstanceOf(ApiError);
    expect(isRevisionConflict(error)).toBe(true);
    if (!isRevisionConflict(error)) return;
    expect(error.status).toBe(409);
    expect(error.body.content).toBe('{"format": 2}');
    expect(error.body.revision).toBe("r2");
    expect(error.message).toBe("study.json changed on disk since it was read");
  });

  it("does not take an ambiguous identity for a revision conflict", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ error: "caffeine/Example is the identity of two folders: a, b; rename one" }, { status: 409 }),
    );
    const error = await rejection(postJson("/local/studies/review", { study: "caffeine/Example" }, isRecord));
    expect(error).toBeInstanceOf(ApiError);
    expect(isRevisionConflict(error)).toBe(false);
  });

  it("exposes the issues of a validation error", async () => {
    const issue = { code: "study_json", severity: "error", message: "Field required", source: null };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      json({ error: "Field required", issues: [issue], code: "approval_refused" }, { status: 422 }),
    );
    const error = await rejection(postJson("/local/studies/review", {}, isRecord));
    expect(isValidationError(error)).toBe(true);
    if (!isValidationError(error)) return;
    expect(error.body.issues).toEqual([issue]);
    expect(error.body.code).toBe("approval_refused");
    expect(isRevisionConflict(error)).toBe(false);
  });

  it("recognizes a missing or mismatched user, but not a refused origin", async () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    fetch.mockResolvedValueOnce(json({ error: "no_user", message: "Set a PK-DB user first" }, { status: 403 }));
    const missing = await rejection(postJson("/local/studies/metadata", {}, isRecord));
    expect(isNoUser(missing)).toBe(true);
    expect(missing).toBeInstanceOf(ApiError);
    expect(missing instanceof Error && missing.message).toBe("Set a PK-DB user first");

    fetch.mockResolvedValueOnce(json({ error: "user_mismatch", message: "The key belongs to another account" }, { status: 403 }));
    expect(isNoUser(await rejection(postJson("/local/studies/review", {}, isRecord)))).toBe(true);

    fetch.mockResolvedValueOnce(json({ error: "Cross-origin requests are not allowed" }, { status: 403 }));
    expect(isNoUser(await rejection(postJson("/local/studies/review", {}, isRecord)))).toBe(false);
  });

  it("reports a stopped server when fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const error = await rejection(postJson("/local/jobs", {}, isRecord));
    expect(error).toBeInstanceOf(ServerStopped);
    expect(error instanceof Error && error.message).toBe("The local server stopped. Start pkdb curate again.");
    await expect(getJson("/local/state", isRecord)).rejects.toBeInstanceOf(ServerStopped);
  });

  it("reports a missing session for 401", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      json({ error: "Open the launch URL printed in your terminal" }, { status: 401 }),
    );
    const error = await rejection(postJson("/local/jobs", {}, isRecord));
    expect(error).toBeInstanceOf(SessionMissing);
    expect(error instanceof Error && error.message).toBe("Open the launch URL printed in your terminal");
    await expect(getJson("/local/state", isRecord)).rejects.toBeInstanceOf(SessionMissing);
  });
});

describe("studyPath", () => {
  it("percent-encodes each segment of the identity and the route", () => {
    expect(studyPath("caffeine/Example")).toBe("/local/studies/caffeine/Example");
    expect(studyPath("caf feine/Ex%ample", "tables", "outputs Tab3.tsv")).toBe(
      "/local/studies/caf%20feine/Ex%25ample/tables/outputs%20Tab3.tsv",
    );
  });
});

describe("isAbort", () => {
  it("recognizes a canceled request", () => {
    expect(isAbort(new DOMException("The study was closed", "AbortError"))).toBe(true);
    expect(isAbort(new ServerStopped("The local server stopped. Start pkdb curate again."))).toBe(false);
    expect(isAbort(undefined)).toBe(false);
  });
});

describe("launchToken", () => {
  it("reads the token of the launch URL, also after the hash router rewrote it", () => {
    expect(launchToken("#token=abc")).toBe("abc");
    expect(launchToken("#/token=abc")).toBe("abc");
    expect(launchToken("#/studies/caffeine/Example")).toBeNull();
    expect(launchToken("#token=")).toBeNull();
    expect(launchToken("")).toBeNull();
  });
});

describe("bootstrap", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/");
  });

  it("clears the launch token from the address before posting it and keeps the CSRF token", async () => {
    window.history.replaceState(null, "", "/#token=launch-token");
    const calls: string[] = [];
    const replaceState = window.history.replaceState.bind(window.history);
    vi.spyOn(window.history, "replaceState").mockImplementation((data, unused, url) => {
      calls.push(`replaceState ${String(url)}`);
      replaceState(data, unused, url);
    });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      calls.push(`fetch ${String(input)} ${window.location.hash || "(no hash)"}`);
      return json({ csrf_token: "csrf-from-session" });
    });
    await bootstrap(window.location, window.history);
    expect(calls).toEqual(["replaceState /", "fetch /local/session (no hash)"]);
    const { init } = request(fetch);
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ token: "launch-token" });
    expect(csrfToken()).toBe("csrf-from-session");
    expect(window.location.href).toBe(`${window.location.origin}/`);
  });

  it("takes the launch token that the hash router rewrote", async () => {
    window.history.replaceState(null, "", "/#/token=rewritten");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ csrf_token: "csrf" }));
    await bootstrap(window.location, window.history);
    expect(JSON.parse(String(request(fetch).init.body))).toEqual({ token: "rewritten" });
    expect(window.location.hash).toBe("");
  });

  it("relies on the session cookie without a launch token", async () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    const replaceState = vi.spyOn(window.history, "replaceState");
    await bootstrap(window.location, window.history);
    expect(fetch).not.toHaveBeenCalled();
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("rejects when the launch token is refused", async () => {
    window.history.replaceState(null, "", "/#token=used");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ error: "Launch token expired or invalid" }, { status: 403 }));
    await expect(bootstrap(window.location, window.history)).rejects.toBeInstanceOf(ApiError);
    expect(window.location.hash).toBe("");
  });
});
