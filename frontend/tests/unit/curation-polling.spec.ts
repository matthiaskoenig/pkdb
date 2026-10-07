import { defineComponent, h } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ServerStopped, type Fetched } from "../../src/curation-app/api/client";
import { usePolling, type Polling } from "../../src/curation-app/composables/usePolling";

type Load = (etag: string | null, signal: AbortSignal) => Promise<Fetched<string>>;

/** Mounts a tiny component that polls with `load`. */
function mountPolling(load: Load) {
  let polling: Polling<string> | undefined;
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
      .mockRejectedValueOnce(new ServerStopped("The local server stopped. Start pkdb curate again."))
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
