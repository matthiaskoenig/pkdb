import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { useDebounced } from "../../src/study-views/composables/useDebounced";

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
});

afterEach(() => {
  vi.useRealTimers();
});

function setup(initial = "") {
  const target = ref(initial);
  const scope = effectScope();
  const debounced = scope.run(() => useDebounced(target, 150))!;
  return { target, scope, ...debounced };
}

describe("useDebounced", () => {
  it("writes the target 150 ms after the last change", async () => {
    const { target, text } = setup();
    text.value = "smo";
    await nextTick();
    vi.advanceTimersByTime(100);
    text.value = "smoking";
    await nextTick();
    vi.advanceTimersByTime(149);
    expect(target.value).toBe("");
    vi.advanceTimersByTime(1);
    expect(target.value).toBe("smoking");
  });

  it("follows a change of the target at once and drops a pending write", async () => {
    const { target, text } = setup("old");
    text.value = "typed";
    await nextTick();
    target.value = "";
    await nextTick();
    expect(text.value).toBe("");
    vi.advanceTimersByTime(150);
    expect(target.value).toBe("");
  });

  it("writes at once on flush, and treats null of a cleared field as empty", async () => {
    const { target, text, flush } = setup("smoking");
    (text as { value: string | null }).value = null;
    await nextTick();
    flush("");
    expect(target.value).toBe("");
    expect(text.value).toBe("");
  });

  it("writes a pending text when its scope ends", async () => {
    const { target, text, scope } = setup();
    text.value = "smoking";
    await nextTick();
    scope.stop();
    expect(target.value).toBe("smoking");
  });
});
