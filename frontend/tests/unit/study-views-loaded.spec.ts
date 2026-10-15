import { describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { effectScope, ref } from "vue";
import { useLoaded } from "../../src/study-views/composables/useLoaded";

/** A read that answers when the test says so, with the signals that it was given. */
function pendingReads() {
  const reads: { key: string; signal: AbortSignal; answer: (text: string) => void; fail: (error: unknown) => void }[] = [];
  const read = (key: string, signal: AbortSignal) =>
    new Promise<string>((answer, fail) => {
      reads.push({ key, signal, answer, fail });
    });
  return { reads, read };
}

const lead = (key: string) => `${key} could not be loaded.`;

describe("useLoaded", () => {
  it("aborts the read of a load that a newer load replaces and drops what it answers", async () => {
    const { reads, read } = pendingReads();
    const key = ref("a.tsv");
    const scope = effectScope();
    const loaded = scope.run(() => useLoaded(() => key.value, read, () => 0, lead))!;
    key.value = "b.tsv";
    await flushPromises();
    expect(reads.map(({ key, signal }) => [key, signal.aborted])).toEqual([
      ["a.tsv", true],
      ["b.tsv", false],
    ]);
    // A page that answers an aborted read with another error than an AbortError.
    reads[0]!.fail(new TypeError("Failed to fetch"));
    reads[1]!.answer("rows of b");
    await flushPromises();
    expect(loaded.error.value).toBeNull();
    expect(loaded.data.value).toEqual({ key: "b.tsv", content: "rows of b", version: 0 });
    scope.stop();
  });

  it("aborts the read when the component unmounts, without a failure", async () => {
    const { reads, read } = pendingReads();
    const scope = effectScope();
    const loaded = scope.run(() => useLoaded(() => "a.tsv", read, () => 0, lead))!;
    expect(reads[0]!.signal.aborted).toBe(false);
    scope.stop();
    expect(reads[0]!.signal.aborted).toBe(true);
    reads[0]!.fail(new TypeError("Failed to fetch"));
    await flushPromises();
    expect(loaded.error.value).toBeNull();
    expect(loaded.data.value).toBeNull();
  });

  it("shows the failure of a read that was not aborted", async () => {
    const { reads, read } = pendingReads();
    const scope = effectScope();
    const loaded = scope.run(() => useLoaded(() => "a.tsv", read, () => 0, lead))!;
    reads[0]!.fail(new Error("The server answered 500."));
    await flushPromises();
    expect(loaded.error.value?.text).toContain("a.tsv could not be loaded.");
    scope.stop();
  });
});
