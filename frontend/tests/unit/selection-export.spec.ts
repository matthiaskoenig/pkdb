import { AxiosError, AxiosHeaders } from "axios";
import { effectScope } from "vue";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, it, vi } from "vitest";
import {
  exportFailure,
  exportFilename,
  useSelectionExport,
} from "../../src/features/exports/useSelectionExport";
import { useSearchStore } from "../../src/stores/search";
import { useSessionStore } from "../../src/stores/session";
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", async () => ({
  api: { get: mocks.get },
  apiBase: "",
  errorMessage: (await import("../../src/api/errors")).errorMessage,
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));
function failure(
  status: number,
  body: Blob,
  headers: Record<string, string> = {},
) {
  return new AxiosError(
    "Request failed",
    "ERR_BAD_RESPONSE",
    undefined,
    undefined,
    {
      status,
      statusText: "Failure",
      data: body,
      headers,
      config: { headers: new AxiosHeaders() },
    },
  );
}
function jsonBlob(body: unknown) {
  const blob = new Blob([JSON.stringify(body)], { type: "application/json" });
  Object.defineProperty(blob, "text", {
    value: () => Promise.resolve(JSON.stringify(body)),
  });
  return blob;
}
function selection() {
  const search = useSearchStore();
  search.selection = {
    status: "ready",
    data: {
      uuid: "test-selection",
      counts: {
        studies: 1,
        groups: 1,
        individuals: 0,
        interventions: 1,
        measurements: 1,
        timecourses: 0,
        scatters: 0,
      },
    },
  };
  return search;
}
beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
  URL.createObjectURL = vi.fn(() => "blob:export");
  URL.revokeObjectURL = vi.fn();
});

it("decodes binary API errors while preserving authentication and limit statuses", async () => {
  expect(
    await exportFailure(
      failure(413, jsonBlob({ detail: "Export exceeds configured row limit" })),
    ),
  ).toBe("Export exceeds configured row limit");
  expect(await exportFailure(failure(401, jsonBlob({})))).toBe(
    "Sign in to continue.",
  );
  expect(await exportFailure(failure(403, jsonBlob({})))).toContain(
    "permission",
  );
  expect(
    await exportFailure(failure(503, jsonBlob({}), { "retry-after": "3" })),
  ).toContain("Retry in 3 seconds");
});
it("keeps HTTP classification if the binary error is not valid JSON", async () => {
  const body = new Blob(["bad gateway"]);
  Object.defineProperty(body, "text", {
    value: () => Promise.resolve("bad gateway"),
  });
  expect(await exportFailure(failure(413, body))).toContain(
    "export size or row limit",
  );
  expect(await exportFailure(failure(503, body))).toContain("Retry shortly");
});
it("uses the immutable applied dataset and server filename despite draft edits", async () => {
  const search = selection();
  search.applied.filters = { outputs__substance_sid__in: ["drug"] };
  search.draft.filters = { outputs__substance_sid__in: ["unapplied"] };
  mocks.get.mockResolvedValue({
    data: new Blob(["zip"]),
    headers: {
      "content-type": "application/x-zip-compressed",
      "content-disposition": 'attachment; filename="dataset.zip"',
    },
  });
  let filename = "";
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    filename = this.download;
  });
  const scope = effectScope();
  const exports = scope.run(useSelectionExport);
  await exports?.download();
  const request: unknown = mocks.get.mock.calls[0]?.[0];
  expect(request).toContain("outputs__substance_sid__in=drug");
  expect(request).not.toContain("unapplied");
  expect(request).toContain("download=true");
  expect(filename).toBe("dataset.zip");
  expect(exports?.error.value).toBe("");
  scope.stop();
});
it("ignores an error decoded after cancellation or identity change", async () => {
  selection();
  let finish: ((text: string) => void) | undefined;
  const body = new Blob();
  Object.defineProperty(body, "text", {
    value: () =>
      new Promise<string>((resolve) => {
        finish = resolve;
      }),
  });
  mocks.get.mockRejectedValue(failure(413, body));
  const scope = effectScope();
  const exports = scope.run(useSelectionExport);
  const pending = exports?.download();
  await Promise.resolve();
  await Promise.resolve();
  useSessionStore().invalidate();
  finish?.('{"detail":"old private error"}');
  await pending;
  expect(exports?.error.value).toBe("");
  expect(exports?.busy.value).toBe(false);
  scope.stop();
});
it("rejects a successful HTML response rather than downloading it as a ZIP", async () => {
  selection();
  mocks.get.mockResolvedValue({
    data: new Blob(["html"]),
    headers: { "content-type": "text/html" },
  });
  const scope = effectScope();
  const exports = scope.run(useSelectionExport);
  await exports?.download();
  expect(exports?.error.value).toContain("did not return a ZIP");
  expect(URL.createObjectURL).not.toHaveBeenCalled();
  scope.stop();
});
it("sanitizes download filenames and decodes RFC5987 names", () => {
  expect(exportFilename("attachment; filename*=UTF-8''data%20set.zip")).toBe(
    "data set.zip",
  );
  expect(exportFilename('attachment; filename="../../dataset.zip"')).toBe(
    "dataset.zip",
  );
});
