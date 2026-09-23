import { onScopeDispose, ref, watch } from "vue";
import { api, apiBase, errorMessage } from "../../api/client";
import { useSessionStore } from "../../stores/session";

export function fileUrl(path: string): string {
  const base = new URL(apiBase || "/", window.location.href);
  const target = new URL(path, base);
  if (target.origin !== base.origin || !target.pathname.startsWith("/media/"))
    throw new Error("This file is not an authorized API attachment URL.");
  return target.href;
}

export function useImagePreview() {
  const session = useSessionStore();
  const busy = ref(false);
  const failure = ref("");
  const preview = ref("");
  let controller: AbortController | undefined;
  let generation = 0;
  function clear() {
    generation++;
    controller?.abort();
    if (preview.value) URL.revokeObjectURL(preview.value);
    preview.value = "";
    busy.value = false;
    failure.value = "";
  }
  async function load(path: string) {
    clear();
    const current = generation;
    const epoch = session.epoch;
    controller = new AbortController();
    busy.value = true;
    try {
      const response = await api.get<Blob>(fileUrl(path), {
        responseType: "blob",
        signal: controller.signal,
      });
      if (current !== generation || epoch !== session.epoch) return;
      if (!(response.data instanceof Blob))
        throw new Error("The server returned an invalid file.");
      if (!/^image\/(png|jpeg|gif|webp|avif)$/.test(response.data.type))
        throw new Error("This attachment cannot be previewed as an image.");
      preview.value = URL.createObjectURL(response.data);
    } catch (error) {
      if (current === generation && epoch === session.epoch)
        failure.value = errorMessage(error);
    } finally {
      if (current === generation) busy.value = false;
    }
  }
  watch(() => session.epoch, clear);
  onScopeDispose(clear);
  return { busy, failure, preview, load, clear };
}
