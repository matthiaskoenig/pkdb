import { getCurrentScope, onScopeDispose, shallowRef, type ShallowRef } from "vue";
import type { Fetched } from "../api/client";

/** How often the app asks the local server for changes. */
export const POLL_INTERVAL_MS = 1500;

export interface Polling<T> {
  /**
   * The data of the last 200 response; a 304 keeps it. The objects and arrays of a 200 response
   * that equal those of the data before are those of the data before (`keepUnchanged`).
   */
  readonly data: Readonly<ShallowRef<T | null>>;
  /** The error of the last load, such as ServerStopped or SessionMissing; null after a success. */
  readonly error: Readonly<ShallowRef<Error | null>>;
  /** Load now; a load in flight is aborted and its answer ignored. */
  refresh(): Promise<void>;
  /** Load now and then every interval while the page is visible; nothing while it polls already. */
  start(): Promise<void>;
  /** Stop polling and abort the load in flight. */
  stop(): void;
  /** Stop and forget the data, the error and the ETag, before polling another resource. */
  reset(): void;
}

/** Whether `value` is an object or an array. */
function isComposite(value: unknown): value is object {
  return typeof value === "object" && value !== null;
}

/**
 * `next` with the objects and arrays of `previous` that it equals at the same places, or
 * `previous` itself when all of `next` equals it. `next` is data of JSON that nothing else holds
 * yet, and changes in place: no object is made.
 *
 * A poll answers the whole state when a part of it changed, such as the status of a few studies
 * among a thousand. With the objects that did not change, what depends on them, such as the
 * rendered rows of those studies, stays as it is.
 *
 * It runs on every value of every poll, some 90,000 for a workspace of 1,000 studies, so it makes
 * no array of keys and goes through arrays by index. A value of JSON is never undefined, so a key
 * whose value equals that of `previous` is a key of `previous`.
 */
export function keepUnchanged<T>(previous: unknown, next: T): T {
  if (previous === next || !isComposite(next) || !isComposite(previous)) return next;
  if (Array.isArray(next)) return Array.isArray(previous) && keptItems(previous, next) ? (previous as T) : next;
  if (Array.isArray(previous)) return next;
  return keptFields(previous as Record<string, unknown>, next as Record<string, unknown>) ? (previous as T) : next;
}

/**
 * Whether `next` equals `previous`, after `next` took the objects of `previous` that equal its
 * own; `keepUnchanged` of arrays.
 */
function keptItems(previous: unknown[], next: unknown[]): boolean {
  let same = previous.length === next.length;
  for (let index = 0; index < next.length; index++) {
    const value = next[index];
    const old = previous[index];
    if (value === old) continue;
    if (isComposite(value) && keepUnchanged(old, value) === old) next[index] = old;
    else same = false;
  }
  return same;
}

/** `keptItems` of objects. */
function keptFields(previous: Record<string, unknown>, next: Record<string, unknown>): boolean {
  let same = true;
  for (const key in next) {
    const value = next[key];
    const old = previous[key];
    if (value === old) continue;
    if (isComposite(value) && keepUnchanged(old, value) === old) next[key] = old;
    else same = false;
  }
  if (!same) return false;
  // Every key of `next` is one of `previous`: they are the same keys when `previous` has no other.
  for (const key in previous) if (!Object.hasOwn(next, key)) return false;
  return true;
}

/**
 * Poll `load` every `intervalMs` while the page is visible, with the ETag of the last response.
 *
 * The next load is scheduled when the previous one ends, so loads never overlap. Polling goes
 * on after an error, so that the page recovers when the local server answers again. Polling
 * starts at once unless `immediate` is false, and stops when the component that set it up
 * unmounts or the store that set it up is disposed.
 */
export function usePolling<T>(
  load: (etag: string | null, signal: AbortSignal) => Promise<Fetched<T>>,
  intervalMs = POLL_INTERVAL_MS,
  { immediate = true }: { immediate?: boolean } = {},
): Polling<T> {
  const data = shallowRef<T | null>(null);
  const error = shallowRef<Error | null>(null);
  let etag: string | null = null;
  let running = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let controller: AbortController | undefined;
  // Only the answer of the latest load counts.
  let sequence = 0;

  function hidden(): boolean {
    return document.visibilityState === "hidden";
  }

  function cancel(): void {
    clearTimeout(timer);
    timer = undefined;
    controller?.abort();
    controller = undefined;
    sequence++;
  }

  function schedule(): void {
    clearTimeout(timer);
    timer = running && !hidden() ? setTimeout(() => void refresh(), intervalMs) : undefined;
  }

  async function refresh(): Promise<void> {
    cancel();
    const current = sequence;
    const abort = (controller = new AbortController());
    try {
      const result = await load(etag, abort.signal);
      if (current !== sequence) return;
      etag = result.etag;
      if (result.status === 200) data.value = keepUnchanged(data.value, result.data);
      error.value = null;
    } catch (caught) {
      if (current !== sequence) return;
      error.value = caught instanceof Error ? caught : new Error(String(caught));
    }
    controller = undefined;
    schedule();
  }

  function visibilityChanged(): void {
    if (!running) return;
    if (hidden()) clearTimeout(timer);
    else void refresh();
  }

  function start(): Promise<void> {
    if (running) return Promise.resolve();
    running = true;
    document.addEventListener("visibilitychange", visibilityChanged);
    return refresh();
  }

  function stop(): void {
    running = false;
    document.removeEventListener("visibilitychange", visibilityChanged);
    cancel();
  }

  function reset(): void {
    stop();
    etag = null;
    data.value = null;
    error.value = null;
  }

  if (getCurrentScope()) onScopeDispose(stop);
  if (immediate) void start();
  return { data, error, refresh, start, stop, reset };
}
