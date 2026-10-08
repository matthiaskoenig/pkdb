import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { effectScope, nextTick, ref, watch, type Ref } from "vue";
import { PREVIEW_HOLD_MS, usePreview, useShownPreview } from "../../src/curation-app/composables/usePreview";

/** A request that the test answers when it wants. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (error: unknown) => void } {
  let resolve: (value: T) => void = () => undefined;
  let reject: (error: unknown) => void = () => undefined;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function recorder() {
  const asked: string[] = [];
  const answers = new Map<string, ReturnType<typeof deferred<string>>>();
  const load = (value: string) => {
    asked.push(value);
    const answer = deferred<string>();
    answers.set(value, answer);
    return answer.promise;
  };
  return { asked, answers, load };
}

describe("usePreview", () => {
  it("asks for one input at a time and keeps only the answer for the current input", async () => {
    const input = ref<string | null>("Tab");
    const { asked, answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    expect(asked).toEqual(["Tab"]);
    expect(preview.loading.value).toBe(true);
    input.value = "Tab3";
    await nextTick();
    input.value = "Tab31";
    await nextTick();
    expect(asked).toEqual(["Tab"]);
    answers.get("Tab")?.resolve("old");
    await flushPromises();
    // The answer of an older input never shows; the newest input is asked for next.
    expect(preview.data.value).toBeNull();
    expect(asked).toEqual(["Tab", "Tab31"]);
    answers.get("Tab31")?.resolve("new");
    await flushPromises();
    expect(preview.data.value).toBe("new");
    expect(preview.loading.value).toBe(false);
  });

  it("clears without input and keeps the message of a failure", async () => {
    const input = ref<string | null>("Tab3");
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    answers.get("Tab3")?.reject(new Error("The local server stopped."));
    await flushPromises();
    expect(preview.error.value).toBe("The local server stopped.");
    input.value = null;
    await nextTick();
    expect([preview.data.value, preview.error.value, preview.loading.value]).toEqual([null, null, false]);
  });
});

describe("useShownPreview", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  /** Fake timeouts only: flushPromises waits with setImmediate. */
  const fakeTimeouts = () => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });

  /** A shown preview of `input`, with every value that it showed. */
  function shown(input: Ref<string | null>) {
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    const view = useShownPreview(preview);
    const seen: (string | null)[] = [];
    watch(view.data, (value) => seen.push(value), { flush: "sync" });
    return { answers, preview, view, seen };
  }

  it("replaces the last answer by a fast one without showing nothing in between", async () => {
    const input = ref<string | null>("Tab");
    const { answers, preview, view, seen } = shown(input);
    answers.get("Tab")?.resolve("refused");
    await flushPromises();
    input.value = "Tab3";
    await nextTick();
    // The answer for Tab3 loads: no action can use the answer for Tab, which still shows.
    expect([preview.data.value, preview.loading.value, view.data.value]).toEqual([null, true, "refused"]);
    answers.get("Tab3")?.resolve("outputs_Tab3");
    await flushPromises();
    expect(view.data.value).toBe("outputs_Tab3");
    expect(seen).toEqual(["refused", "outputs_Tab3"]);
  });

  it("shows nothing when an answer takes longer than the hold, and clears at once without input", async () => {
    fakeTimeouts();
    const input = ref<string | null>("Tab");
    const { answers, view } = shown(input);
    answers.get("Tab")?.reject(new Error("The local server stopped."));
    await flushPromises();
    expect(view.error.value).toBe("The local server stopped.");
    input.value = "Tab3";
    await nextTick();
    vi.advanceTimersByTime(PREVIEW_HOLD_MS - 1);
    expect(view.error.value).toBe("The local server stopped.");
    vi.advanceTimersByTime(1);
    expect([view.data.value, view.error.value]).toEqual([null, null]);
    answers.get("Tab3")?.resolve("outputs_Tab3");
    await flushPromises();
    expect(view.data.value).toBe("outputs_Tab3");
    input.value = null;
    await nextTick();
    expect([view.data.value, view.error.value]).toEqual([null, null]);
  });

  it("stops its timer with its scope", async () => {
    fakeTimeouts();
    const input = ref<string | null>("Tab");
    const scope = effectScope();
    const { answers, view } = scope.run(() => shown(input))!;
    answers.get("Tab")?.resolve("refused");
    await flushPromises();
    input.value = "Tab3";
    await nextTick();
    scope.stop();
    vi.advanceTimersByTime(PREVIEW_HOLD_MS);
    expect(view.data.value).toBe("refused");
  });
});
