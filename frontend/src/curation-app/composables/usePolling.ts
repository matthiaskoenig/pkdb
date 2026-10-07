import { getCurrentScope, onScopeDispose, shallowRef, type ShallowRef } from "vue";
import type { Fetched } from "../api/client";

/** How often the app asks the local server for changes. */
export const POLL_INTERVAL_MS = 1500;

export interface Polling<T> {
  /** The data of the last 200 response; a 304 keeps it. */
  readonly data: ShallowRef<T | null>;
  /** The error of the last load, such as ServerStopped or SessionMissing; null after a success. */
  readonly error: ShallowRef<Error | null>;
  /** Load now; a load in flight is aborted and its answer ignored. */
  refresh(): Promise<void>;
  /** Load now and then every interval while the page is visible; nothing while it polls already. */
  start(): Promise<void>;
  /** Stop polling and abort the load in flight. */
  stop(): void;
  /** Stop and forget the data, the error and the ETag, before polling another resource. */
  reset(): void;
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
      if (result.status === 200) data.value = result.data;
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
