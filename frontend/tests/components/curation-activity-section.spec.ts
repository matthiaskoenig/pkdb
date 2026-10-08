import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { RouterView } from "vue-router";
import type { Job, JobReport, ReviewItem, Snapshot, StudyDetail, Upload } from "../../src/curation-app/api/types";
import { formatTime } from "../../src/curation-app/overview";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import messagesFixture from "../fixtures/curation-contract/messages.json";
import { json, reviewItem, snapshot, studyDetail, studyRow } from "../unit/curation-fixtures";
import {
  button,
  buttons,
  focusDialog,
  page,
  serveApi,
  setViewport,
  type Handler,
  type ServedRequest,
} from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const SECTION = "/studies/caffeine/Example/activity";
const CANCEL = "/local/jobs/cancel";
const CLEAR = "/local/history/clear";

/** A time of the server, in its ISO format, at `minute` past noon UTC. */
function at(minute: number): string {
  return `2026-10-07T12:${String(minute).padStart(2, "0")}:00.123456+00:00`;
}

/** A finished validation of caffeine/Example unless `changes` say otherwise. */
function job(id: string, changes: Partial<Job> = {}): Job {
  return {
    id,
    study_id: "caffeine/Example",
    study_name: "Example",
    action: "validate",
    status: "succeeded",
    stage: "complete",
    created_at: at(0),
    message: "Validation passed",
    automatic: false,
    endpoint: "",
    persistence: "not_attempted",
    report_id: id,
    ...changes,
  };
}

function write(id: string, message: string, created: string, changes: Partial<Job> = {}): Job {
  return {
    id,
    study_id: "caffeine/Example",
    study_name: "Example",
    action: "write",
    status: "succeeded",
    created_at: created,
    message,
    automatic: false,
    report_id: null,
    ...changes,
  };
}

/**
 * The jobs of the messages contract fixture, newest first: a review item added in the app, one
 * that part C saved without its item, and a validation that part C saved as canceled with the
 * message "Queued" (python/tests/test_curation_contract.py).
 */
const [ADDED, PART_C_WRITE, PART_C_CANCELED] = messagesFixture.jobs.map((entry, place) =>
  job(`contract-${place}`, { ...(entry as Partial<Job>), report_id: null, created_at: at(30 - place) }),
);
/** The review items of the fixture, among them the items of the jobs. */
const ITEMS = messagesFixture.items.map((entry) => reviewItem(entry as Partial<ReviewItem>));

const UPLOADED: Upload = {
  persistence: "created",
  at: at(30),
  endpoint: "https://pk-db.com",
  url: "https://pk-db.com/data/PKDB00198",
};

/** The activity of caffeine/Example as the detail lists it, newest first. */
const HISTORY: Job[] = [
  write("write-2", "Added review item 01K6Y4ZJ6Q8D3W6B6V5N1S2T3X", at(40), {
    item: "01K6Y4ZJ6Q8D3W6B6V5N1S2T3X",
    parts: [{ text: "Added " }, { item: "01K6Y4ZJ6Q8D3W6B6V5N1S2T3X" }],
  }),
  job("upload-1", {
    action: "upload",
    created_at: at(30),
    message: "Uploaded",
    endpoint: "https://pk-db.com",
    persistence: "created",
    upload: UPLOADED,
  }),
  job("remote-1", { action: "validate_remote", status: "failed", created_at: at(20), message: "Validation found problems" }),
  write("write-1", "Saved study.json", at(10)),
  job("validate-1", { automatic: true, created_at: at(0) }),
];

const REPORT: JobReport = {
  job: HISTORY[1]!,
  persistence: "created",
  report: { issues: [], complete: true },
};

let pinia: Pinia;
let requests: ServedRequest[];
let served: StudyDetail;
let state: Snapshot;

/** Jobs that clearing the history keeps whatever their age. */
const ACTIVE: readonly Job["status"][] = ["queued", "running", "unknown"];

/**
 * The workspace state with the jobs of the history, oldest first, as the server lists them; by
 * default a clear would remove the jobs that have ended.
 */
function workspace(jobs: Job[], changes: Partial<Snapshot> = {}): Snapshot {
  return snapshot({
    studies: [studyRow()],
    jobs: [...jobs].reverse(),
    clearable_jobs: jobs.filter((entry) => !ACTIVE.includes(entry.status)).length,
    ...changes,
  });
}

async function mountSection(
  jobs: Job[] = HISTORY,
  routes: Record<string, unknown> = {},
  changes: Partial<Snapshot> = {},
  study: Partial<StudyDetail> = {},
) {
  served = studyDetail({ jobs, ...study });
  state = workspace(jobs, changes);
  requests = serveApi({
    "GET /local/state": (() => json(state)) satisfies Handler,
    [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
    "GET /local/curators": { curators: [] },
    "GET /local/reports/upload-1": REPORT,
    ...routes,
  });
  await useOverviewStore().refresh();
  const router = makeRouter();
  await router.push(SECTION);
  await router.isReady();
  const wrapper = mount(RouterView, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

/** Changes the jobs that the server lists for the study and the workspace. */
function serveJobs(jobs: Job[], clearable = jobs.filter((entry) => !ACTIVE.includes(entry.status)).length): void {
  served = { ...served, jobs };
  state = { ...state, jobs: [...jobs].reverse(), clearable_jobs: clearable };
}

function entries(): DOMWrapper<Element>[] {
  return page().findAll(".activity-entry");
}

function entry(text: string): DOMWrapper<Element> {
  const found = entries().filter((candidate) => candidate.get(".activity-text").text() === text);
  if (found.length !== 1) throw new Error(`Expected one entry "${text}", found ${found.length}`);
  return found[0]!;
}

function textOf(element: Pick<DOMWrapper<Element>, "text">): string {
  return element.text().replace(/\s+/g, " ").trim();
}

/** The names of the buttons and links of an entry. */
function actionsOf(element: DOMWrapper<Element>): string[] {
  return element.findAll(".activity-actions :is(a, button)").map((control) => textOf(control));
}

function posted(path: string): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === path).map(({ body }) => body);
}

function notice(): string {
  return page().get(".activity-notice").text();
}

function dialog() {
  return page().get('.v-overlay--active[role="dialog"]');
}

function dialogOpen(): boolean {
  return page().find('.v-overlay--active[role="dialog"]').exists();
}

async function press(control: Pick<DOMWrapper<Element>, "trigger">): Promise<void> {
  await control.trigger("click");
  await flushPromises();
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("the activity of a study", () => {
  it("lists the jobs newest first with the action, the text, the local time and the status", async () => {
    await mountSection();
    expect(entries().map((element) => element.get(".activity-text").text())).toEqual([
      // The review item is no longer in review.json.
      "Added a review item",
      "Uploaded",
      "Validation found problems",
      "Saved study.json",
      "Validation passed",
    ]);
    const upload = entry("Uploaded");
    expect(textOf(upload.get(".activity-meta"))).toBe(`Upload · created · ${formatTime(at(30))}`);
    expect(upload.get("time").attributes("datetime")).toBe("2026-10-07T12:30:00.123Z");
    expect(upload.get(".activity-status").text()).toBe("Succeeded");
    // A validation that the local server started, after a save or at the first scan, says so.
    expect(textOf(entry("Validation passed").get(".activity-meta"))).toBe(`Validation · automatic · ${formatTime(at(0))}`);
    expect(textOf(entry("Saved study.json").get(".activity-meta"))).toBe(`Change in the app · ${formatTime(at(10))}`);
    expect(page().get(".activity-caption").text()).toBe("Newest first. The app keeps the last 100 finished jobs.");
  });

  it.each([
    // Neutral: the status says whether it passed.
    ["validate", "Validation", "fa-clipboard-list"],
    ["validate_remote", "Server validation", "fa-server"],
    ["upload", "Upload", "fa-cloud-arrow-up"],
    ["write", "Change in the app", "fa-pen"],
  ] as const)("shows the icon and the name of a %s", async (action, label, icon) => {
    await mountSection([job("job-1", { action, message: "Done" })]);
    const shown = entry("Done");
    expect(shown.get(".activity-icon").classes()).toContain(icon);
    expect(shown.get(".activity-icon").attributes("aria-hidden")).toBe("true");
    expect(shown.get(".activity-action").text()).toBe(label);
  });

  it.each([
    ["queued", "Queued"],
    ["running", "Running"],
    ["succeeded", "Succeeded"],
    ["failed", "Failed"],
    ["invalid", "Problems found"],
    ["canceled", "Canceled"],
    ["conflict", "Conflict"],
    ["unknown", "Outcome unknown"],
    ["reviewed", "Reviewed"],
  ] as const)("labels the status %s", async (status, label) => {
    await mountSection([job("job-1", { status, report_id: null })]);
    const chip = entries()[0]!.get(".activity-status");
    expect(chip.text()).toBe(label);
    // Tinted chips keep the text in the surface color, as the status colors fail contrast as text.
    expect(chip.classes()).toContain("status-chip");
  });

  it("tells problems found from a job that failed, in the tone of the problem chips", async () => {
    await mountSection([
      job("failed-1", { status: "failed", message: "Could not read the source files; see the study", created_at: at(5) }),
      job("invalid-1", { status: "invalid", message: "Validation found problems" }),
    ]);
    const problems = entry("Validation found problems").get(".activity-status");
    expect(problems.text()).toBe("Problems found");
    expect(problems.classes()).toContain("text-error");
    expect(entry("Could not read the source files; see the study").get(".activity-status").text()).toBe("Failed");
  });

  it("says why a job was canceled, also for jobs that an earlier version canceled", async () => {
    await mountSection([
      job("replaced-1", { status: "canceled", message: "Replaced by a newer validation", report_id: null, created_at: at(40) }),
      PART_C_CANCELED!,
    ]);
    expect(entries().map((element) => element.get(".activity-text").text())).toEqual([
      "Replaced by a newer validation",
      "Canceled before it started",
    ]);
  });

  it("names review items by kind and text, linked to the item, also in a job saved by part C", async () => {
    const review = { revision: "review-2", value: { status: "draft" as const, reviewers: [], items: ITEMS }, issues: [] };
    await mountSection([ADDED!, PART_C_WRITE!], {}, {}, { review });
    const added = entries()[0]!.get(".activity-text");
    expect(textOf(added)).toBe("Added the question “Is the 4 h point read from the figure?”");
    const link = added.get("a");
    expect(link.text()).toBe("question “Is the 4 h point read from the figure?”");
    expect(link.attributes("href")).toBe(`#/studies/caffeine/Example/review?item=${ADDED!.item}`);
    const saved = entries()[1]!.get(".activity-text");
    expect(textOf(saved)).toBe("Added the question “The methods describe a 400 mg dose, but…”");
    expect(saved.get("a").attributes("href")).toBe("#/studies/caffeine/Example/review?item=01M2FC4AG038NKRKAYDXR834N3");
  });

  it("says a review item when the item is no longer in review.json", async () => {
    const review = { revision: "review-2", value: { status: "draft" as const, reviewers: [], items: [] }, issues: [] };
    await mountSection([ADDED!], {}, {}, { review });
    expect(textOf(entries()[0]!.get(".activity-text"))).toBe("Added a review item");
    expect(entries()[0]!.find(".activity-text a").exists()).toBe(false);
  });

  it("says what a queued or running job does instead of the message of the server", async () => {
    await mountSection([
      job("queued-1", { status: "queued", stage: "queued", message: "Queued", report_id: null, created_at: at(5) }),
      job("running-1", { action: "upload", status: "running", stage: "transfer", message: "Queued", report_id: null }),
    ]);
    expect(entries().map((element) => element.get(".activity-text").text())).toEqual([
      "Waiting to start",
      "Sending the study",
    ]);
  });

  it("names what an upload did on the server and links to the uploaded study", async () => {
    await mountSection([
      job("upload-3", {
        action: "upload",
        status: "reviewed",
        message: "User inspected the server and requested a new upload",
        persistence: "unknown",
        created_at: at(50),
      }),
      job("upload-2", { action: "upload", message: "Replaced", persistence: "replaced", created_at: at(40) }),
      job("upload-1", { action: "upload", message: "Uploaded", persistence: "created", upload: UPLOADED }),
    ]);
    expect(entry("User inspected the server and requested a new upload").get(".activity-persistence").text()).toBe(
      "unknown outcome",
    );
    expect(entry("Replaced").get(".activity-persistence").text()).toBe("replaced");
    const link = entry("Uploaded").get("a.activity-link");
    expect(textOf(link)).toBe("Open on PK-DB");
    expect(link.attributes("href")).toBe("https://pk-db.com/data/PKDB00198");
    expect(link.attributes("target")).toBe("_blank");
    expect(link.attributes("rel")).toBe("noopener noreferrer");
    expect(entry("Replaced").find("a.activity-link").exists()).toBe(false);
  });

  it("offers a report for jobs with one and Cancel for queued jobs only", async () => {
    await mountSection([
      job("queued-1", { status: "queued", stage: "queued", message: "Queued", report_id: null, created_at: at(5) }),
      ...HISTORY,
    ]);
    expect(actionsOf(entry("Waiting to start"))).toEqual(["Cancel"]);
    expect(actionsOf(entry("Uploaded"))).toEqual(["Open on PK-DB", "Download report"]);
    expect(actionsOf(entry("Validation found problems"))).toEqual(["Download report"]);
    expect(entry("Saved study.json").find(".activity-actions").exists()).toBe(false);
    expect(button("Cancel queued validation").text()).toBe("Cancel");
    // Each Download report and Open on PK-DB is described by the text and the time of its job.
    for (const control of [entry("Uploaded").get("button"), entry("Uploaded").get("a.activity-link")]) {
      const described = (control.attributes("aria-describedby") ?? "").split(" ");
      expect(described.map((id) => document.getElementById(id)?.textContent?.replace(/\s+/g, " ").trim())).toEqual([
        "Uploaded",
        `Upload · created · ${formatTime(at(30))}`,
      ]);
    }
  });

  it("says so when the study has no activity yet", async () => {
    await mountSection([]);
    expect(entries()).toHaveLength(0);
    expect(page().get(".activity-empty").text()).toBe(
      "No activity yet. Validations, uploads and changes in the app appear here.",
    );
    expect(button("Clear finished history").attributes("disabled")).toBeDefined();
  });
});

describe("report download", () => {
  function stubBlobs() {
    const created: Blob[] = [];
    const clicked: { href: string; download: string }[] = [];
    vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => {
      if (blob instanceof Blob) created.push(blob);
      return "blob:report";
    });
    vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
    // jsdom does not download.
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push({ href: this.getAttribute("href") ?? "", download: this.download });
    });
    return { created, clicked };
  }

  it("fetches the report and saves it as pkdb-report-<id>.json", async () => {
    const { created, clicked } = stubBlobs();
    await mountSection();
    await press(entry("Uploaded").get("button"));
    expect(requests.some((request) => request.method === "GET" && request.path === "/local/reports/upload-1")).toBe(
      true,
    );
    expect(clicked).toEqual([{ href: "blob:report", download: "pkdb-report-upload-1.json" }]);
    expect(created[0]!.type).toBe("application/json");
    expect(JSON.parse(await created[0]!.text())).toEqual(REPORT);
    expect(notice()).toBe("Downloaded pkdb-report-upload-1.json.");
  });

  it("explains a report that is no longer available and keeps it until it is dismissed", async () => {
    const { clicked } = stubBlobs();
    await mountSection(HISTORY, {
      "GET /local/reports/remote-1": () => json({ error: "Unknown resource or study" }, { status: 404 }),
    });
    await press(entry("Validation found problems").get("button"));
    expect(clicked).toEqual([]);
    const alert = page().get(".action-failure");
    expect(alert.text()).toContain("The report of this job is no longer available.");
    await press(alert.get("button"));
    expect(page().find(".action-failure").exists()).toBe(false);
  });
});

describe("cancel", () => {
  const queued = job("queued-1", {
    status: "queued",
    stage: "queued",
    message: "Queued",
    report_id: null,
    created_at: at(50),
  });

  it("cancels a queued job and shows it as canceled", async () => {
    const cancel: Handler = () => {
      serveJobs([{ ...queued, status: "canceled", message: "Canceled before starting" }, ...HISTORY]);
      return json(state);
    };
    await mountSection([queued, ...HISTORY], { [`POST ${CANCEL}`]: cancel });
    await press(button("Cancel queued validation"));
    expect(posted(CANCEL)).toEqual([{ ids: ["queued-1"] }]);
    expect(entries()[0]!.get(".activity-text").text()).toBe("Canceled before starting");
    expect(entries()[0]!.get(".activity-status").text()).toBe("Canceled");
    expect(notice()).toBe("Canceled the queued validation.");
    expect(buttons("Cancel queued validation")).toHaveLength(0);
    // The button is gone; the keyboard focus goes to the job instead of the page.
    expect(document.activeElement).toBe(entries()[0]!.element);
  });

  it("explains a job that started before it could be canceled", async () => {
    const cancel: Handler = () => {
      serveJobs([{ ...queued, status: "running", stage: "validate" }, ...HISTORY]);
      return json(state);
    };
    await mountSection([queued, ...HISTORY], { [`POST ${CANCEL}`]: cancel });
    await press(button("Cancel queued validation"));
    expect(page().get(".action-failure").text()).toContain("The validation started before it could be canceled.");
    expect(notice()).toBe("");
  });

  it("allows no other action while one runs", async () => {
    let answer: (() => void) | undefined;
    const cancel: Handler = () =>
      new Promise((resolve) => {
        answer = () => resolve(json(state));
      });
    await mountSection([queued, ...HISTORY], { [`POST ${CANCEL}`]: cancel });
    await button("Cancel queued validation").trigger("click");
    await flushPromises();
    expect(button("Clear finished history").attributes("disabled")).toBeDefined();
    for (const download of buttons("Download report")) expect(download.attributes("disabled")).toBeDefined();
    answer?.();
    await flushPromises();
    expect(button("Clear finished history").attributes("disabled")).toBeUndefined();
  });
});

describe("clear finished history", () => {
  const queued = job("queued-1", { status: "queued", stage: "queued", message: "Queued", report_id: null, created_at: at(50) });
  const unknown = job("upload-9", {
    action: "upload",
    status: "unknown",
    message: "The connection closed during the upload",
    persistence: "unknown",
    report_id: "upload-9",
    created_at: at(45),
  });

  it("says what it clears and asks first", async () => {
    await mountSection([queued, unknown, ...HISTORY], {}, { clearable_jobs: 42 });
    await press(button("Clear finished history"));
    expect(dialog().get("h2").text()).toBe("Clear finished history?");
    expect(textOf(dialog().get(".clear-text"))).toBe(
      "This removes 42 finished jobs of this workspace from the activity and deletes their reports. " +
        "Queued and running jobs, uploads with an unknown outcome, and the last upload and the current report " +
        "of each study stay.",
    );
    await press(button("Keep history"));
    expect(dialogOpen()).toBe(false);
    expect(posted(CLEAR)).toEqual([]);
  });

  it("clears the finished jobs and keeps the jobs that the server keeps", async () => {
    const clear: Handler = () => {
      // The last upload stays.
      serveJobs([queued, unknown, HISTORY[1]!], 0);
      return json(state);
    };
    await mountSection([queued, unknown, ...HISTORY], { [`POST ${CLEAR}`]: clear });
    await press(button("Clear finished history"));
    await press(button("Clear history"));
    expect(posted(CLEAR)).toEqual([{}]);
    expect(dialogOpen()).toBe(false);
    expect(entries().map((element) => element.get(".activity-text").text())).toEqual([
      "Waiting to start",
      "The connection closed during the upload",
      "Uploaded",
    ]);
    expect(notice()).toBe("Cleared the finished history.");
    // Only what clearing keeps is left, and the keyboard focus goes to the list.
    expect(button("Clear finished history").attributes("disabled")).toBeDefined();
    expect(document.activeElement).toBe(page().get(".activity-list").element);
  });

  it("names a single job, and moves the focus to the empty activity", async () => {
    const clear: Handler = () => {
      serveJobs([]);
      return json(state);
    };
    await mountSection([HISTORY[3]!], { [`POST ${CLEAR}`]: clear });
    await press(button("Clear finished history"));
    expect(textOf(dialog().get(".clear-text"))).toMatch(
      /^This removes 1 finished job of this workspace from the activity and deletes its report\. /,
    );
    await press(button("Clear history"));
    expect(document.activeElement).toBe(page().get(".activity-empty").element);
  });

  it("is available when the server says that a clear removes jobs", async () => {
    // Jobs of other studies of the workspace, which the server counts.
    await mountSection([queued], {}, { clearable_jobs: 3 });
    expect(button("Clear finished history").attributes("disabled")).toBeUndefined();
  });
});

describe("an upload with an unknown outcome", () => {
  const unknown = job("upload-9", {
    action: "upload",
    status: "unknown",
    message: "The connection closed during the upload",
    persistence: "unknown",
    endpoint: "https://beta.pk-db.com",
    report_id: "upload-9",
  });

  it("opens the review of the uncertain upload", async () => {
    await mountSection([unknown], {}, {
      studies: [studyRow({ status: "unknown" })],
      endpoint: "https://beta.pk-db.com",
    });
    const review = button("Review uncertain upload");
    expect(review.text()).toBe("Review");
    await press(review);
    expect(dialog().get("h2").text()).toBe("Review uncertain upload");
    expect(dialog().text()).toContain("The connection closed during the upload");
  });

  it("returns the focus to Review after Cancel, and to the job when the retry removed Review", async () => {
    const connected: Partial<Snapshot> = {
      studies: [studyRow({ status: "unknown" })],
      endpoint: "https://beta.pk-db.com",
      can_upload: true,
      offline: false,
      authenticated: true,
      connection: "connected",
    };
    const retry: Handler = () => {
      // The server keeps the earlier upload as failed and queues a new one.
      serveJobs([{ ...unknown, status: "failed" }]);
      return json(state);
    };
    await mountSection([unknown], { "POST /local/retry": retry }, connected);
    button("Review uncertain upload").element.focus();
    await press(button("Review uncertain upload"));
    focusDialog();
    await press(button("Cancel"));
    expect(document.activeElement).toBe(button("Review uncertain upload").element);

    await press(button("Review uncertain upload"));
    focusDialog();
    await press(dialog().get('input[type="checkbox"]'));
    await press(button("Validate and upload again"));
    expect(buttons("Review uncertain upload")).toHaveLength(0);
    expect(document.activeElement).toBe(page().get('[data-job="upload-9"]').element);
  });

  it("says so when the review queued the upload again", async () => {
    const retry = vi.spyOn(useOverviewStore(), "retry").mockImplementation(async () => state);
    await mountSection([unknown], {}, {
      studies: [studyRow({ status: "unknown" })],
      endpoint: "https://beta.pk-db.com",
      can_upload: true,
      offline: false,
      authenticated: true,
      connection: "connected",
    });
    await press(button("Review uncertain upload"));
    await press(dialog().get('input[type="checkbox"]'));
    await press(button("Validate and upload again"));
    expect(retry).toHaveBeenCalledWith("caffeine/Example", { acknowledgeUnknown: true });
    expect(dialogOpen()).toBe(false);
    expect(notice()).toBe("Upload queued again.");
  });
});
