import { onScopeDispose, ref, watch, type Ref } from "vue";

/**
 * The model of a text field that writes `target` `delay` ms after its last change, so that typing
 * does not filter on every keystroke. A change of `target` from elsewhere, such as Clear filters,
 * shows at once and drops a pending write; `flush` writes at once, as clearing the field does. A
 * pending write happens when the scope ends, so that no typed text is lost. A cleared field of
 * Vuetify writes null, which counts as "".
 */
export function useDebounced(target: Ref<string>, delay: number): { text: Ref<string>; flush(value?: string): void } {
  const text = ref(target.value);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function cancel(): void {
    clearTimeout(timer);
    timer = undefined;
  }

  function flush(value: string = text.value ?? ""): void {
    cancel();
    text.value = value;
    target.value = value;
  }

  watch(text, (raw) => {
    const value = raw ?? "";
    cancel();
    if (value !== target.value) timer = setTimeout(() => flush(value), delay);
  });
  watch(target, (value) => {
    if (value === (text.value ?? "")) return;
    cancel();
    text.value = value;
  });
  onScopeDispose(() => {
    if (timer !== undefined) flush();
  });
  return { text, flush };
}
