import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, nextTick, ref } from "vue";
import { studyRows, studyView, type StudyViewAnswer } from "../../src/features/studies/api";
import { useWebsiteStudy, useWebsiteStudyRows } from "../../src/features/studies/useWebsiteStudy";
import { useSessionStore } from "../../src/stores/session";
import { ApiError } from "../../src/study-views/errors";
import rowsCurator from "../fixtures/website-views/study-rows-curator.json";
import studyCurator from "../fixtures/website-views/study-curator.json";
import studyPublic from "../fixtures/website-views/study-public.json";

const mocks = vi.hoisted(() => ({ study: vi.fn(), rows: vi.fn() }));
vi.mock("../../src/features/studies/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/features/studies/api")>();
  return { ...actual, studyViewsApi: { ...actual.studyViewsApi, study: mocks.study, rows: mocks.rows } };
});
vi.mock("../../src/api/client", () => ({
  api: { get: vi.fn() },
  apiBase: "",
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));

enableAutoUnmount(afterEach);
let pinia: Pinia;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  mocks.study.mockReset();
  mocks.rows.mockReset();
});

function answer(body: unknown, id = "drug/Format2Fixture"): StudyViewAnswer {
  const view = studyView(body, "GET view");
  return { ...view, detail: { ...view.detail, id } };
}

function harness<T>(use: () => T): T {
  let state: T | undefined;
  mount(
    defineComponent({
      setup() {
        state = use();
        return () => h("p");
      },
    }),
    { global: { plugins: [pinia] } },
  );
  return state!;
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => (resolve = done));
  return { promise, resolve };
}

describe("loading the view of a study", () => {
  it("shows the study of the id, and clears it while another study loads", async () => {
    mocks.study.mockResolvedValueOnce(answer(studyCurator, "drug/A"));
    const id = ref("drug/A");
    const state = harness(() => useWebsiteStudy(id));
    await flushPromises();
    expect(state.detail.value?.id).toBe("drug/A");
    expect(state.audience.value).toBe("curator");
    const next = deferred<StudyViewAnswer>();
    mocks.study.mockReturnValueOnce(next.promise);
    id.value = "drug/B";
    await nextTick();
    expect(state.detail.value).toBeNull();
    expect(state.audience.value).toBeNull();
    next.resolve(answer(studyCurator, "drug/B"));
    await flushPromises();
    expect(state.detail.value?.id).toBe("drug/B");
  });

  it("reads again when the session changes, showing the old view until the new one comes", async () => {
    mocks.study.mockResolvedValueOnce(answer(studyCurator));
    const state = harness(() => useWebsiteStudy("drug/Format2Fixture"));
    await flushPromises();
    const next = deferred<StudyViewAnswer>();
    mocks.study.mockReturnValueOnce(next.promise);
    useSessionStore().epoch += 1;
    await nextTick();
    expect(state.audience.value).toBe("curator");
    next.resolve(answer(studyPublic));
    await flushPromises();
    expect(state.audience.value).toBe("public");
  });

  it("tells a study without a view by its 404 and keeps telling it while it reads again", async () => {
    mocks.study.mockRejectedValue(new ApiError(404, { message: "Not found" }, "GET view"));
    const state = harness(() => useWebsiteStudy("drug/Format2Legacy"));
    await flushPromises();
    expect(state.missing.value).toBe(true);
    expect(state.detail.value).toBeNull();
    useSessionStore().epoch += 1;
    await nextTick();
    expect(state.missing.value).toBe(true);
    await flushPromises();
    expect(state.missing.value).toBe(true);
    expect(mocks.study).toHaveBeenCalledTimes(2);
  });

  it("aborts the read of a study that it no longer shows", async () => {
    const signals: AbortSignal[] = [];
    mocks.study.mockImplementation((id: string, signal: AbortSignal) => {
      signals.push(signal);
      return new Promise<StudyViewAnswer>(() => undefined);
    });
    const id = ref("drug/A");
    harness(() => useWebsiteStudy(id));
    id.value = "drug/B";
    await nextTick();
    expect(signals.map((signal) => signal.aborted)).toEqual([true, false]);
  });

  it("shows nothing of a view read in another session when the read for the new session fails", async () => {
    mocks.study.mockResolvedValueOnce(answer(studyCurator));
    const state = harness(() => useWebsiteStudy("drug/Format2Fixture"));
    await flushPromises();
    expect(state.audience.value).toBe("curator");
    mocks.study.mockRejectedValue(new ApiError(500, { message: "Database unavailable" }, "GET view"));
    useSessionStore().epoch += 1;
    await flushPromises();
    expect(state.detail.value).toBeNull();
    expect(state.audience.value).toBeNull();
    expect(state.error.value).toBeInstanceOf(ApiError);
    expect(state.missing.value).toBe(false);
  });

  it("keeps the view of the same session when a retry fails", async () => {
    mocks.study.mockResolvedValueOnce(answer(studyCurator));
    const state = harness(() => useWebsiteStudy("drug/Format2Fixture"));
    await flushPromises();
    mocks.study.mockRejectedValue(new ApiError(500, { message: "Database unavailable" }, "GET view"));
    await state.reload();
    expect(state.audience.value).toBe("curator");
    expect(state.detail.value?.id).toBe("drug/Format2Fixture");
    expect(state.error.value).toBeInstanceOf(ApiError);
  });

  it("shows another failure as an error, not as a study without a view", async () => {
    mocks.study.mockRejectedValue(new ApiError(500, { message: "Database unavailable" }, "GET view"));
    const state = harness(() => useWebsiteStudy("drug/Format2Fixture"));
    await flushPromises();
    expect(state.missing.value).toBe(false);
    expect(state.error.value).toBeInstanceOf(ApiError);
  });
});

describe("loading the rows of the Studies page", () => {
  it("is ready with the rows, reads again when the session changes and retries a failure", async () => {
    const rows = studyRows(rowsCurator, "GET rows");
    mocks.rows.mockRejectedValueOnce(new ApiError(500, { message: "Database unavailable" }, "GET rows"));
    const state = harness(() => useWebsiteStudyRows());
    expect(state.status.value).toBe("loading");
    await flushPromises();
    expect(state.status.value).toBe("failed");
    mocks.rows.mockResolvedValue(rows);
    const retry = state.reload();
    expect(state.status.value).toBe("loading");
    await retry;
    expect(state.status.value).toBe("ready");
    expect(state.error.value).toBeNull();
    expect(state.rows.value.map((row) => row.id)).toEqual(["drug/Format2Fixture"]);
    useSessionStore().epoch += 1;
    await flushPromises();
    expect(mocks.rows).toHaveBeenCalledTimes(3);
    expect(state.status.value).toBe("ready");
  });

  it("shows no rows of another session when the read for the new session fails", async () => {
    mocks.rows.mockResolvedValueOnce(studyRows(rowsCurator, "GET rows"));
    const state = harness(() => useWebsiteStudyRows());
    await flushPromises();
    expect(state.status.value).toBe("ready");
    mocks.rows.mockRejectedValue(new ApiError(500, { message: "Database unavailable" }, "GET rows"));
    useSessionStore().epoch += 1;
    await flushPromises();
    expect(state.status.value).toBe("failed");
    expect(state.rows.value).toEqual([]);
    expect(state.profiles.value).toEqual([]);
    expect(state.error.value).toBeInstanceOf(ApiError);
  });

  it("keeps the rows of the same session when a retry fails", async () => {
    mocks.rows.mockResolvedValueOnce(studyRows(rowsCurator, "GET rows"));
    const state = harness(() => useWebsiteStudyRows());
    await flushPromises();
    mocks.rows.mockRejectedValue(new ApiError(500, { message: "Database unavailable" }, "GET rows"));
    await state.reload();
    expect(state.status.value).toBe("ready");
    expect(state.rows.value.map((row) => row.id)).toEqual(["drug/Format2Fixture"]);
    expect(state.error.value).toBeInstanceOf(ApiError);
  });
});
