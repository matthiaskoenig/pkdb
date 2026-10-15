import { defineComponent, h } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Fetched } from "../../src/curation-app/api/client";
import { ServerStopped } from "../../src/study-views/errors";
import { keepUnchanged, usePolling, type Polling } from "../../src/curation-app/composables/usePolling";

type Load = (etag: string | null, signal: AbortSignal) => Promise<Fetched<string>>;

/** Mounts a tiny component that polls with `load`. */
function mountPolling<T = string>(load: (etag: string | null, signal: AbortSignal) => Promise<Fetched<T>>) {
  let polling: Polling<T> | undefined;
  const wrapper = mount(
    defineComponent({
      setup() {
        polling = usePolling(load);
        return () => h("div");
      },
    }),
  );
  if (!polling) throw new Error("The component did not set up polling");
  return { wrapper, polling };
}

let visibility: DocumentVisibilityState = "visible";

function setVisibility(state: DocumentVisibilityState) {
  visibility = state;
  document.dispatchEvent(new Event("visibilitychange"));
}

beforeEach(() => {
  vi.useFakeTimers();
  visibility = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("usePolling", () => {
  it("polls every 1500 ms with the previous ETag and keeps the data on 304", async () => {
    const load = vi
      .fn<Load>()
      .mockResolvedValueOnce({ status: 200, etag: '"v1"', data: "first" })
      .mockResolvedValueOnce({ status: 304, etag: '"v1"' })
      .mockResolvedValueOnce({ status: 200, etag: '"v2"', data: "second" })
      .mockResolvedValue({ status: 304, etag: '"v2"' });
    const { wrapper, polling } = mountPolling(load);
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(1);
    expect(polling.data.value).toBe("first");

    await vi.advanceTimersByTimeAsync(1499);
    expect(load).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(load).toHaveBeenCalledTimes(2);
    expect(polling.data.value).toBe("first");

    await vi.advanceTimersByTimeAsync(1500);
    expect(polling.data.value).toBe("second");
    await vi.advanceTimersByTimeAsync(1500);
    expect(load.mock.calls.map(([etag]) => etag)).toEqual([null, '"v1"', '"v1"', '"v2"']);
    expect(polling.data.value).toBe("second");
    wrapper.unmount();
  });

  it("pauses while the document is hidden and refreshes when it is visible again", async () => {
    const load = vi.fn<Load>().mockResolvedValue({ status: 304, etag: '"v1"' });
    const { wrapper } = mountPolling(load);
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(1);

    setVisibility("hidden");
    await vi.advanceTimersByTimeAsync(6000);
    expect(load).toHaveBeenCalledTimes(1);

    setVisibility("visible");
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1500);
    expect(load).toHaveBeenCalledTimes(3);
    wrapper.unmount();
  });

  it("stops after unmount and aborts the request in flight", async () => {
    let signal: AbortSignal | undefined;
    const load = vi.fn<Load>().mockImplementation((_etag, abort) => {
      signal = abort;
      return new Promise(() => {});
    });
    const { wrapper } = mountPolling(load);
    await vi.advanceTimersByTimeAsync(0);
    expect(load).toHaveBeenCalledTimes(1);
    wrapper.unmount();
    expect(signal?.aborted).toBe(true);

    setVisibility("hidden");
    setVisibility("visible");
    await vi.advanceTimersByTimeAsync(6000);
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("shows a stopped server, keeps the data and recovers when the server answers again", async () => {
    const load = vi
      .fn<Load>()
      .mockResolvedValueOnce({ status: 200, etag: '"v1"', data: "before" })
      .mockRejectedValueOnce(new ServerStopped("GET /local/state"))
      .mockResolvedValue({ status: 200, etag: '"v2"', data: "after restart" });
    const { wrapper, polling } = mountPolling(load);
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(1500);
    expect(polling.error.value).toBeInstanceOf(ServerStopped);
    expect(polling.data.value).toBe("before");

    await vi.advanceTimersByTimeAsync(1500);
    expect(polling.error.value).toBeNull();
    expect(polling.data.value).toBe("after restart");
    wrapper.unmount();
  });

  it("ignores a poll in flight that a refresh superseded", async () => {
    let answerPoll: (value: Fetched<string>) => void = () => {};
    const load = vi
      .fn<Load>()
      .mockResolvedValueOnce({ status: 200, etag: '"v1"', data: "first" })
      .mockImplementationOnce(() => new Promise((resolve) => (answerPoll = resolve)))
      .mockResolvedValue({ status: 200, etag: '"v3"', data: "after the write" });
    const { wrapper, polling } = mountPolling(load);
    await vi.advanceTimersByTimeAsync(1500);
    expect(load).toHaveBeenCalledTimes(2);

    await polling.refresh();
    expect(polling.data.value).toBe("after the write");
    answerPoll({ status: 200, etag: '"v2"', data: "before the write" });
    await vi.advanceTimersByTimeAsync(0);
    expect(polling.data.value).toBe("after the write");
    await vi.advanceTimersByTimeAsync(1500);
    expect(load.mock.calls.at(-1)?.[0]).toBe('"v3"');
    wrapper.unmount();
  });
});

describe("keepUnchanged", () => {
  /** A state of JSON as a poll answers it, parsed anew each time. */
  function state(statuses: string[], extra: Record<string, unknown> = {}) {
    return JSON.parse(
      JSON.stringify({
        studies: statuses.map((status, index) => ({ id: `s${index}`, status, files: [{ id: "a.tsv" }], summary: null })),
        paused: false,
        ...extra,
      }),
    ) as { studies: { id: string; status: string; files: unknown[] }[]; paused: boolean };
  }

  it("keeps the objects that did not change and takes those that did", () => {
    const previous = state(["valid", "queued", "valid"]);
    const next = state(["valid", "running", "valid"]);
    const kept = keepUnchanged(previous, next);
    expect(kept).toBe(next);
    expect(kept).toEqual(state(["valid", "running", "valid"]));
    expect(kept.studies).not.toBe(previous.studies);
    expect(kept.studies[0]).toBe(previous.studies[0]);
    expect(kept.studies[2]).toBe(previous.studies[2]);
    expect(kept.studies[1]).not.toBe(previous.studies[1]);
    // The parts of a changed object that did not change are kept too.
    expect(kept.studies[1]!.files).toBe(previous.studies[1]!.files);
  });

  it("answers the previous state when nothing changed", () => {
    const previous = state(["valid", "queued"]);
    expect(keepUnchanged(previous, state(["valid", "queued"]))).toBe(previous);
    expect(keepUnchanged(null, previous)).toBe(previous);
    expect(keepUnchanged("text", "text")).toBe("text");
  });

  it("sees added and removed items and keys, and changed kinds of values", () => {
    const previous = state(["valid", "queued"]);
    expect(keepUnchanged(previous, state(["valid", "queued", "valid"]))).not.toBe(previous);
    expect(keepUnchanged(previous, state(["valid"]))).not.toBe(previous);
    expect(keepUnchanged(previous, state(["valid", "queued"], { error: null }))).not.toBe(previous);
    const fewer = state(["valid", "queued"]) as Record<string, unknown>;
    delete fewer.paused;
    expect(keepUnchanged(previous, fewer)).toBe(fewer);
    expect(keepUnchanged({ value: [] }, { value: {} })).toEqual({ value: {} });
    expect(keepUnchanged({ value: {} }, { value: [] })).toEqual({ value: [] });
    expect(keepUnchanged({ value: null }, { value: {} })).toEqual({ value: {} });
    expect(keepUnchanged({ value: 1 }, { value: "1" })).toEqual({ value: "1" });
  });

  it("gives the polled data the objects of the data before that did not change", async () => {
    const answers = [state(["valid", "queued"]), state(["valid", "running"]), state(["valid", "running"])];
    const { wrapper, polling } = mountPolling(async () => ({ status: 200, etag: null, data: answers.shift()! }));
    await vi.advanceTimersByTimeAsync(0);
    const first = polling.data.value!;
    await vi.advanceTimersByTimeAsync(1500);
    const second = polling.data.value!;
    expect(second).not.toBe(first);
    expect(second.studies[0]).toBe(first.studies[0]);
    await vi.advanceTimersByTimeAsync(1500);
    expect(polling.data.value).toBe(second);
    wrapper.unmount();
  });
});
