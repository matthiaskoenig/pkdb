import { describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { nextTick, ref, watch, type Ref } from "vue";
import { ApiError } from "../../src/study-views/errors";
import { usePreview } from "../../src/curation-app/composables/usePreview";

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

  it("keeps what the local server said about a failure, after the lead only for a refusal without detail", async () => {
    const input = ref<string | null>("Tab3");
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load, "The table could not be previewed.");
    const body = {
      error: "Could not preview the new table of caffeine/Example.",
      code: "file_error",
      detail: "PermissionError: [Errno 13] Permission denied",
      action: "Preview a table (POST /local/studies/tables/preview)",
      request_id: "3f9c2a71",
      time: "2026-10-12T14:03:11+02:00",
    };
    answers.get("Tab3")?.reject(new ApiError(400, body));
    await flushPromises();
    expect(preview.error.value?.text).toBe("Could not preview the new table of caffeine/Example.");
    expect(preview.error.value?.details?.detail).toBe("PermissionError: [Errno 13] Permission denied");
    expect(preview.error.value?.details?.requestId).toBe("3f9c2a71");

    input.value = "Tab4";
    await nextTick();
    answers.get("Tab4")?.reject(new ApiError(404, { ...body, error: "caffeine/Example is not a study", detail: null }));
    await flushPromises();
    expect(preview.error.value?.text).toBe("The table could not be previewed. caffeine/Example is not a study");
  });

  it("clears without input and keeps the message of a failure", async () => {
    const input = ref<string | null>("Tab3");
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    answers.get("Tab3")?.reject(new Error("The local server stopped."));
    await flushPromises();
    expect(preview.error.value?.text).toBe("The local server stopped.");
    input.value = null;
    await nextTick();
    expect([preview.data.value, preview.error.value, preview.loading.value]).toEqual([null, null, false]);
  });
});

describe("the shown preview", () => {
  /** A preview of `input`, with every answer that it showed. */
  function shown(input: Ref<string | null>) {
    const { answers, load } = recorder();
    const preview = usePreview(() => input.value, load);
    const seen: (string | null)[] = [];
    watch(preview.shown, (value) => seen.push(value), { flush: "sync" });
    return { answers, preview, seen };
  }

  it("keeps the last settled answer while the next one loads, and never shows a stale one", async () => {
    const input = ref<string | null>("Tab");
    const { answers, preview, seen } = shown(input);
    answers.get("Tab")?.resolve("refused");
    await flushPromises();
    expect([preview.shown.value, preview.loading.value]).toEqual(["refused", false]);

    input.value = "Tab3";
    await nextTick();
    // Actions use `data`, which waits for the answer about Tab3; the dialog shows the last answer as updating.
    expect([preview.data.value, preview.loading.value, preview.shown.value]).toEqual([null, true, "refused"]);
    input.value = "Tab31";
    await nextTick();
    answers.get("Tab3")?.resolve("outputs_Tab3");
    await flushPromises();
    // The answer about Tab3 came after Tab31 was typed: it never shows.
    expect([preview.shown.value, preview.loading.value]).toEqual(["refused", true]);
    answers.get("Tab31")?.resolve("outputs_Tab31");
    await flushPromises();
    expect([preview.data.value, preview.shown.value, preview.loading.value]).toEqual([
      "outputs_Tab31",
      "outputs_Tab31",
      false,
    ]);
    expect(seen).toEqual(["refused", "outputs_Tab31"]);
  });

  it("keeps the last failure while the next answer loads, and clears both at once without input", async () => {
    const input = ref<string | null>("Tab");
    const { answers, preview } = shown(input);
    answers.get("Tab")?.reject(new Error("The local server stopped."));
    await flushPromises();
    input.value = "Tab3";
    await nextTick();
    expect([preview.error.value, preview.shownError.value?.text]).toEqual([null, "The local server stopped."]);
    answers.get("Tab3")?.resolve("outputs_Tab3");
    await flushPromises();
    expect([preview.shown.value, preview.shownError.value]).toEqual(["outputs_Tab3", null]);

    input.value = "Tab4";
    await nextTick();
    input.value = null;
    await nextTick();
    expect([preview.shown.value, preview.shownError.value, preview.loading.value]).toEqual([null, null, false]);
  });
});
