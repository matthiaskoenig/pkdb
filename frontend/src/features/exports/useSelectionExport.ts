import { AxiosError, isAxiosError } from "axios";
import { ref, onScopeDispose, watch } from "vue";
import { api, errorMessage } from "../../api/client";
import { serializeCriteria } from "../search/serialize";
import { useSearchStore } from "../../stores/search";
import { useSessionStore } from "../../stores/session";
import { criteriaKey } from "../search/codec";

export function exportFilename(disposition: unknown): string {
  if (typeof disposition !== "string") return "pkdata.zip";
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1];
  const plain = /filename="([^"]+)"|filename=([^;]+)/i.exec(disposition);
  let filename = plain?.[1] ?? plain?.[2] ?? "pkdata.zip";
  if (encoded) {
    try {
      filename = decodeURIComponent(encoded);
    } catch {
      /* Fall back to the ordinary filename. */
    }
  }
  const basename = filename.trim().split(/[\\/]/).pop() ?? "";
  return (
    Array.from(basename)
      .filter(
        (character) =>
          character.charCodeAt(0) >= 32 && character.charCodeAt(0) !== 127,
      )
      .join("") || "pkdata.zip"
  );
}

export async function exportFailure(cause: unknown): Promise<string> {
  if (cause instanceof RangeError) return cause.message;
  if (!isAxiosError<unknown>(cause) || !cause.response)
    return errorMessage(cause);
  let failure = cause;
  if (cause.response.data instanceof Blob) {
    try {
      const data: unknown = JSON.parse(await cause.response.data.text());
      // Preserve AxiosError identity/status; spreading an Error loses the
      // prototype marker used by the shared HTTP error classifier.
      failure = new AxiosError(
        cause.message,
        cause.code,
        cause.config,
        cause.request,
        { ...cause.response, data },
      );
    } catch {
      /* Non-JSON failures still retain their HTTP status. */
    }
  }
  if (cause.response.status === 413) {
    const message = errorMessage(failure);
    return message === "The request could not be completed. Please try again."
      ? "The selected dataset exceeds the export size or row limit. Narrow the applied search and retry."
      : message;
  }
  if (cause.response.status === 503) {
    const delay = Number(cause.response.headers["retry-after"]);
    const retry =
      Number.isFinite(delay) && delay > 0
        ? ` Retry in ${Math.ceil(delay)} second${delay === 1 ? "" : "s"}.`
        : " Retry shortly.";
    return `Export capacity is temporarily unavailable.${retry}`;
  }
  return errorMessage(failure);
}

export function useSelectionExport() {
  const search = useSearchStore(),
    session = useSessionStore(),
    busy = ref(false),
    error = ref("");
  let controller: AbortController | undefined,
    generation = 0,
    url: string | undefined;
  function cancel() {
    generation++;
    controller?.abort();
    busy.value = false;
    if (url) {
      URL.revokeObjectURL(url);
      url = undefined;
    }
  }
  watch(
    () => [criteriaKey(search.applied), session.epoch],
    () => {
      cancel();
      error.value = "";
    },
    { flush: "sync" },
  );
  onScopeDispose(cancel);
  async function download() {
    if (busy.value || search.selection.status !== "ready") return;
    cancel();
    const own = generation,
      epoch = session.epoch;
    const current = () => own === generation && epoch === session.epoch;
    controller = new AbortController();
    busy.value = true;
    error.value = "";
    try {
      const params = serializeCriteria(search.applied);
      params.set("download", "true");
      const response = await api.get<Blob>(`/api/v1/filter/?${params}`, {
        signal: controller.signal,
        responseType: "blob",
      });
      if (!current()) return;
      if (
        !(response.data instanceof Blob) ||
        !String(response.headers["content-type"]).includes("zip")
      )
        throw new RangeError(
          "The server did not return a ZIP dataset. Please retry.",
        );
      url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = exportFilename(response.headers["content-disposition"]);
      document.body.append(link);
      link.click();
      link.remove();
      const completedUrl = url;
      url = undefined;
      setTimeout(() => URL.revokeObjectURL(completedUrl), 0);
    } catch (cause) {
      if (current()) {
        const message = await exportFailure(cause);
        if (current()) error.value = message;
      }
    } finally {
      if (current()) busy.value = false;
    }
  }
  return { busy, error, download, cancel };
}
