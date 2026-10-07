import { ref, shallowRef, watch, type Ref, type ShallowRef, type WatchSource } from "vue";
import { isAbort } from "../api/client";
import { messageOf } from "../study";

export interface Loaded<T> {
  /** The last answer with its key; it stays while the same key loads again. */
  data: ShallowRef<{ key: string; content: T } | null>;
  /** Why the last load failed. */
  error: Ref<string | null>;
  /** Whether the key loads without an answer to show meanwhile. */
  loading: Ref<boolean>;
  /** Load the current key again, such as after a failure. */
  reload: () => Promise<void>;
}

/**
 * Loads `read(key)` when `key` changes and when `changed` does, such as the detail of the open
 * study, whose ETag-revalidated resources may have changed with it. Answers that arrive after a
 * newer load started are dropped, and so are loads aborted because the study closed.
 */
export function useLoaded<T>(
  key: () => string | null,
  read: (key: string) => Promise<T>,
  changed: WatchSource<unknown>,
): Loaded<T> {
  // Shallow: a table of thousands of rows needs no deep reactivity.
  const data = shallowRef<{ key: string; content: T } | null>(null);
  const error = ref<string | null>(null);
  const loading = ref(false);
  let request = 0;

  async function load(name: string | null): Promise<void> {
    const current = ++request;
    error.value = null;
    if (data.value?.key !== name) data.value = null;
    if (name === null) {
      loading.value = false;
      return;
    }
    loading.value = data.value === null;
    try {
      const content = await read(name);
      if (current === request) data.value = { key: name, content };
    } catch (caught) {
      if (current === request && !isAbort(caught)) error.value = messageOf(caught);
    } finally {
      if (current === request) loading.value = false;
    }
  }

  watch([key, changed], ([name]) => void load(name), { immediate: true });
  return { data, error, loading, reload: () => load(key()) };
}
