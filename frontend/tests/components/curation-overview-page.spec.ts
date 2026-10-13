import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { VSelect } from "vuetify/components";
import { ApiError } from "../../src/curation-app/api/client";
import type { Job, Profile, Snapshot, SyncStatus } from "../../src/curation-app/api/types";
import type { Router } from "vue-router";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { SEARCH_DELAY_MS } from "../../src/curation-app/overview";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useOverviewFilters } from "../../src/curation-app/stores/overviewFilters";
import { OVERSCAN, ROW_HEIGHT, rowItem } from "../../src/curation-app/studyTable";
import { NOTICE_MS } from "../../src/curation-app/study";
import OverviewPage from "../../src/curation-app/views/OverviewPage.vue";
import { snapshot, studyRow } from "../unit/curation-fixtures";
import { button, click, field, focusDialog, page, serve, setViewport } from "./curation-dom";

vi.mock("../../src/curation-app/studyTable", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/curation-app/studyTable")>();
  return { ...actual, rowItem: vi.fn(actual.rowItem) };
});

const FAILED = { request_id: "3f9c2a71", time: "2026-10-12T14:03:11+02:00" };

enableAutoUnmount(afterEach);

let pinia: Pinia;
/** The router of the last mounted page. */
let router: Router;

const ISSUE_URL = "https://github.com/matthiaskoenig/pkdb_data/issues/2158";
const UPLOAD_URL = "https://beta.pk-db.com/studies/caffeine/Harder1988";

const example = studyRow();
const harder = studyRow({
  id: "caffeine/Harder1988",
  name: "Harder1988",
  path: "studies/caffeine/Harder1988",
  mode: "upload",
  status: "invalid",
  summary: {
    title: "Effect of smoking on caffeine",
    review_status: "in_review",
    open_items: 2,
    curators: ["mkoenig", "janekg", "curator"],
    creator: "mkoenig",
    release: { pkdb_id: "PKDB00198", date: "2026-09-28" },
    issue: 2158,
    provenance: { kind: "automatic_curation", method: "claude-opus-5-5" },
    ai: true,
  },
  counts: { errors: 2, warnings: 0 },
  sync: { status: "workbook_open", changes: 0, conflicts: 0 },
  issue: { number: 2158, state: "open", labels: ["check"], assignees: [], url: ISSUE_URL },
  last_upload: {
    persistence: "replaced",
    at: "2026-10-01T12:00:00Z",
    endpoint: "https://beta.pk-db.com",
    url: UPLOAD_URL,
  },
});
const approved = studyRow({
  id: "codeine/Kirchheiner2007",
  name: "Kirchheiner2007",
  substance: "codeine",
  path: "studies/codeine/Kirchheiner2007",
  summary: { ...example.summary, title: "Codeine in CYP2D6 ultrarapid metabolizers", review_status: "approved" },
  counts: { errors: 0, warnings: 1 },
});

const profiles: Profile[] = [
  {
    username: "mkoenig",
    display_name: "Matthias König",
    title: null,
    affiliation: null,
    avatar_url: "/avatars/matthias_koenig.webp",
  },
  { username: "janekg", display_name: "Jan Grzegorzewski", title: null, affiliation: null, avatar_url: null },
];

/** The overview of `state` with the curator roster `curators`, on the route `#/`. */
async function mountPage(state: Snapshot, curators: Profile[] = profiles) {
  serve({ "/local/state": state, "/local/curators": { curators } });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

/** The rows of the study table. */
function rows(): DOMWrapper<HTMLTableRowElement>[] {
  return page().findAll<HTMLTableRowElement>(".study-table tbody tr.study-row");
}

/** The identities of the rows, in their order. */
function identities(): string[] {
  return rows().map((row) => row.get(".study-identity").text());
}

/** The row of the study `id`. */
function rowOf(id: string): DOMWrapper<HTMLTableRowElement> {
  const found = rows().filter((row) => row.get(".study-identity").text() === id);
  if (found.length !== 1) throw new Error(`Expected one row ${id}, found ${found.length}`);
  return found[0]!;
}

/** The checkbox with the accessible name `name`. */
function checkbox(name: string) {
  return page().get<HTMLInputElement>(`input[type="checkbox"][aria-label="${name}"]`);
}

/** Type `text` into the search and wait until the table follows it. */
async function search(text: string): Promise<void> {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  try {
    await field("Search studies").setValue(text);
    vi.advanceTimersByTime(SEARCH_DELAY_MS);
    await flushPromises();
  } finally {
    vi.useRealTimers();
  }
}

async function check(name: string): Promise<void> {
  await checkbox(name).trigger("click");
  await flushPromises();
}

/** Chooses `value` in the select with the label `label`. */
async function choose(wrapper: ReturnType<typeof mount>, label: string, value: string): Promise<void> {
  const select = wrapper.findAllComponents(VSelect).find((candidate) => candidate.props("label") === label);
  if (!select) throw new Error(`No select "${label}"`);
  await select.setValue(value);
  await flushPromises();
}

function dialog() {
  return page().get('.v-overlay--active[role="dialog"]');
}

/** Whether a dialog is open; a closed one may stay in the page during its transition. */
function dialogOpen(): boolean {
  return page().find('.v-overlay--active[role="dialog"]').exists();
}

function unknownJob(changes: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    study_id: "caffeine/Example",
    study_name: "Example",
    action: "upload",
    status: "unknown",
    created_at: "2026-10-01T12:00:00Z",
    message: "The connection closed during the upload",
    automatic: false,
    endpoint: "https://beta.pk-db.com",
    report_id: null,
    sid: "caffeine/Example",
    ...changes,
  };
}

/** The calls of `rowItem` for studies; the rows that size the columns (StudyTable.vue) have no identity. */
function studyItemCalls() {
  return vi.mocked(rowItem).mock.calls.filter(([row]) => row.id !== "");
}

/** `count` studies of three substances with titles of their own. */
function manyStudies(count = 1000) {
  return Array.from({ length: count }, (_, index) => {
    const substance = ["caffeine", "codeine", "midazolam"][index % 3]!;
    const name = `Study${index}`;
    return studyRow({
      id: `${substance}/${name}`,
      name,
      substance,
      path: `studies/${substance}/${name}`,
      summary: { ...example.summary, title: `Title ${index}` },
    });
  });
}

/** The rows that a window of `height` px renders at the top of the table, beyond the overscan. */
function windowRows(height: number): number {
  return Math.ceil(height / ROW_HEIGHT) + OVERSCAN;
}

/** The positions of the rendered study rows (`aria-rowindex`, 2 for the first study). */
function rowIndices(): number[] {
  return rows().map((row) => Number(row.attributes("aria-rowindex")));
}

/** Waits for the next task, after the updates and promises before it. */
async function afterTask(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve));
  await flushPromises();
}

/**
 * Moves the body of the study table to `top` px from the top of the window, as scrolling the page
 * would, and waits for the frame that measures it; jsdom has no layout.
 */
async function scrollBody(top: number): Promise<void> {
  const body = page().get(".study-table tbody").element;
  vi.spyOn(body, "getBoundingClientRect").mockReturnValue({ top } as DOMRect);
  document.dispatchEvent(new Event("scroll"));
  await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  await flushPromises();
}

beforeEach(() => {
  setViewport(1280);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("OverviewPage", () => {
  it("shows one row per study with its identity, title, review, problems and upload", async () => {
    await mountPage(snapshot({ studies: [harder, approved, example] }));
    expect(identities()).toEqual(["caffeine/Example", "caffeine/Harder1988", "codeine/Kirchheiner2007"]);

    const row = rowOf("caffeine/Harder1988");
    expect(row.get(".study-row-title").text()).toBe("Effect of smoking on caffeine");
    expect(row.get(".cell-review .status-chip").text()).toBe("In review");
    expect(row.get(".ai-marker").text()).toBe("AI");
    expect(row.get(".cell-open").text()).toBe("2");
    expect(row.get(".cell-problems").text()).toContain("2 errors");
    expect(row.get(".cell-sync").text()).toBe("Workbook open");
    expect(row.get(".cell-release").text()).toBe("PKDB00198");
    const issue = row.get(".cell-issue a");
    expect(issue.text()).toBe("#2158");
    expect(issue.attributes("href")).toBe(ISSUE_URL);
    expect(row.get(".cell-mode").text()).toBe("Upload");
    const upload = row.get(".cell-upload a");
    expect(upload.text()).toMatch(/^2026-10-01 \d\d:\d\d$/);
    expect(upload.attributes("href")).toBe(UPLOAD_URL);

    const draft = rowOf("caffeine/Example");
    expect(draft.get(".cell-review").text()).toBe("Draft");
    expect(draft.find(".ai-marker").exists()).toBe(false);
    expect(draft.get(".cell-open").text()).toBe("0");
    expect(draft.get(".cell-problems").text()).toBe("valid");
    expect(draft.get(".cell-release").text()).toBe("-");
    expect(draft.get(".cell-issue").text()).toBe("-");
    expect(draft.get(".cell-mode").text()).toBe("Validate");
    expect(draft.get(".cell-upload").text()).toBe("-");

    const other = rowOf("codeine/Kirchheiner2007");
    expect(other.get(".cell-review").text()).toBe("Approved");
    expect(other.get(".cell-problems").text()).toBe("1 warning");
  });

  it("links the last upload only to a web page", async () => {
    const last_upload = { ...harder.last_upload!, url: "javascript:alert(1)" };
    await mountPage(snapshot({ studies: [{ ...harder, last_upload }] }));
    const cell = rowOf("caffeine/Harder1988").get(".cell-upload");
    expect(cell.find("a").exists()).toBe(false);
    expect(cell.text()).toMatch(/^2026-10-01 \d\d:\d\d$/);
  });

  it("names every sync status", async () => {
    const labels: [SyncStatus, string][] = [
      ["in_sync", "In sync"],
      ["workbook_open", "Workbook open"],
      ["changed", "Changed"],
      ["conflict", "Conflict"],
      ["syncing", "Syncing"],
      ["no_workbook", "No workbook"],
      ["unknown", "Unknown"],
      ["not_checked", "Not checked yet"],
    ];
    const studies = labels.map(([status], index) =>
      studyRow({
        id: `caffeine/Study${index}`,
        name: `Study${index}`,
        path: `studies/caffeine/Study${index}`,
        sync: { status, changes: 0, conflicts: 0 },
      }),
    );
    await mountPage(snapshot({ studies }));
    expect(labels.map((_, index) => rowOf(`caffeine/Study${index}`).get(".cell-sync").text())).toEqual(
      labels.map(([, label]) => label),
    );
  });

  it("shows the curators as avatars named by their profiles", async () => {
    await mountPage(snapshot({ studies: [harder] }));
    const curators = rowOf("caffeine/Harder1988").get(".cell-curators");
    const photo = curators.get('img[alt="Matthias König"]');
    expect(photo.attributes("src")).toBe("/avatars/matthias_koenig.webp");
    expect(curators.get('[role="img"][aria-label="Jan Grzegorzewski"]').text()).toBe("JG");
    expect(curators.get('[role="img"][aria-label="curator"]').text()).toBe("C");
  });

  it("loads the curator profiles once the page has a session, as after a pasted launch URL", async () => {
    // Without a session the local server answers 401; a launch URL pasted into the open overview
    // creates the session and loads the state, but does not mount the page again.
    let session = false;
    const state = snapshot({ studies: [harder], author: { user: "mkoenig", reason: null } });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(input instanceof Request ? input.url : String(input), "http://127.0.0.1").pathname;
      const [status, body] = !session
        ? [401, { error: "No session" }]
        : path === "/local/state"
          ? [200, state]
          : [200, { curators: profiles }];
      return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
    });
    await useOverviewStore().refresh();
    router = makeRouter();
    await router.push("/");
    await router.isReady();
    const wrapper = mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
    await flushPromises();
    expect(page().find(".study-table").exists()).toBe(false);

    session = true;
    await useOverviewStore().refresh();
    await flushPromises();
    const curators = rowOf("caffeine/Harder1988").get(".cell-curators");
    expect(curators.get('img[alt="Matthias König"]').attributes("src")).toBe("/avatars/matthias_koenig.webp");
    const select = wrapper.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "Curator")!;
    expect((select.props("items") as { title: string }[]).map((item) => item.title)).toContain(
      "Me: Matthias König (1)",
    );
  });

  it("shows at most three circles of curators, the last one counting the others", async () => {
    const many = studyRow({ summary: { ...example.summary, curators: ["a", "b", "curator", "mkoenig", "janekg"] } });
    await mountPage(snapshot({ studies: [many, harder] }));
    const curators = rowOf("caffeine/Example").get(".cell-curators");
    expect(curators.findAll(".curator")).toHaveLength(2);
    const more = curators.get(".curator-more");
    expect(more.text()).toBe("+3");
    expect(more.attributes("aria-label")).toBe("And curator, Matthias König, Jan Grzegorzewski");
    // Three curators fit in three circles.
    expect(rowOf("caffeine/Harder1988").findAll(".cell-curators .curator")).toHaveLength(3);
    expect(rowOf("caffeine/Harder1988").find(".curator-more").exists()).toBe(false);
  });

  it("shows initials when the curator roster cannot be loaded", async () => {
    serve({ "/local/state": snapshot({ studies: [harder] }) });
    await useOverviewStore().refresh();
    router = makeRouter();
    await router.push("/");
    mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
    await flushPromises();
    const curators = rowOf("caffeine/Harder1988").get(".cell-curators");
    expect(curators.get('[role="img"][aria-label="mkoenig"]').text()).toBe("M");
  });

  it("shows each study on one line with its title truncated and complete in a tooltip", async () => {
    await mountPage(snapshot());
    const row = rows()[0]!;
    const title = row.get(".study-row-title");
    expect(title.attributes("title")).toBe(studyRow().summary.title);
    expect(row.findAll(".study-row-line")).toHaveLength(1);
  });

  it("names the whole identity of a study in its link and its tooltip, as a narrow cell cuts it", async () => {
    await mountPage(snapshot({ studies: [harder, studyRow({ duplicate: true, path: "archive/caffeine/Example" })] }));
    const link = rowOf("caffeine/Harder1988").get("a.study-identity");
    expect(link.text()).toBe("caffeine/Harder1988");
    expect(link.attributes("title")).toBe("caffeine/Harder1988");
    expect(rowOf("caffeine/Example").get("span.study-identity").attributes("title")).toBe("caffeine/Example");
  });

  it("opens the study page when a row is clicked", async () => {
    await mountPage(snapshot());
    const identity = rowOf("caffeine/Example").get(".study-identity");
    expect(identity.attributes("href")).toBe("#/studies/caffeine/Example");
    await rowOf("caffeine/Example").get(".cell-sync").trigger("click");
    await vi.waitFor(() => expect(window.location.hash).toBe("#/studies/caffeine/Example"));
  });

  it("does not open the study for a click beside the checkbox or after selecting text", async () => {
    await mountPage(snapshot());
    const push = vi.spyOn(router, "push");
    await rowOf("caffeine/Example").get("td.cell-select").trigger("click");
    expect(push).not.toHaveBeenCalled();

    // Dragging over the title selects its text; the click that ends the drag keeps the page.
    const title = rowOf("caffeine/Example").get(".study-row-title").element;
    const range = document.createRange();
    range.selectNodeContents(title);
    window.getSelection()?.addRange(range);
    expect(window.getSelection()?.toString()).toBe("Caffeine pharmacokinetics");
    await rowOf("caffeine/Example").get(".study-row-title").trigger("click");
    expect(push).not.toHaveBeenCalled();

    window.getSelection()?.removeAllRanges();
    await rowOf("caffeine/Example").get(".study-row-title").trigger("click");
    expect(push).toHaveBeenCalledOnce();
  });

  it("shows a duplicate identity that cannot be selected or opened", async () => {
    // The server never validates a duplicate, nor retries its uploads.
    const duplicates = [
      studyRow({ duplicate: true, status: "discovered" }),
      studyRow({ duplicate: true, status: "unknown", path: "archive/caffeine/Example" }),
    ];
    await mountPage(snapshot({ studies: duplicates }));
    expect(rows()).toHaveLength(2);
    for (const row of rows()) {
      expect(row.text()).toContain("Duplicate identity");
      expect(row.find("a.study-identity").exists()).toBe(false);
      expect(row.get('input[type="checkbox"]').attributes("disabled")).toBeDefined();
      expect(row.get(".cell-problems").text()).toBe("-");
      expect(row.find(".retry-button").exists()).toBe(false);
    }
    expect(rows().map((row) => row.get(".study-path").text())).toEqual([
      "archive/caffeine/Example",
      "studies/caffeine/Example",
    ]);
    const push = vi.spyOn(router, "push");
    await rows()[0]!.get(".cell-sync").trigger("click");
    expect(push).not.toHaveBeenCalled();
  });

  it("validates the selected studies", async () => {
    const enqueue = vi.spyOn(useOverviewStore(), "enqueue").mockResolvedValue();
    await mountPage(snapshot({ studies: [example, harder] }));
    expect(button("Validate").attributes("disabled")).toBeDefined();
    expect(page().get(".batch-count").text()).toBe("No studies selected");

    await check("Select caffeine/Example");
    expect(page().get(".batch-count").text()).toBe("1 study selected");
    await click("Validate");
    expect(enqueue).toHaveBeenCalledWith(["caffeine/Example"], "validate");
    expect(page().get('[role="status"]').text()).toBe("Validation queued for 1 study.");
    await check("Select caffeine/Harder1988");
    expect(page().get('[role="status"]').text()).toBe("");
  });

  it("clears the notice after a few seconds, as the notices of the study page", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      vi.spyOn(useOverviewStore(), "enqueue").mockResolvedValue();
      await mountPage(snapshot({ studies: [example, harder] }));
      await check("Select caffeine/Example");
      await click("Validate");
      expect(page().get('[role="status"]').text()).toBe("Validation queued for 1 study.");
      vi.advanceTimersByTime(NOTICE_MS);
      await flushPromises();
      expect(page().get('[role="status"]').text()).toBe("");
    } finally {
      vi.useRealTimers();
    }
  });

  it("drops the notice of a request when the selection changed while it ran", async () => {
    let finish = () => {};
    vi.spyOn(useOverviewStore(), "enqueue").mockImplementation(
      () => new Promise<void>((resolve) => (finish = resolve)),
    );
    await mountPage(snapshot({ studies: [example, harder] }));
    await check("Select caffeine/Example");
    await button("Validate").trigger("click");
    await check("Select caffeine/Harder1988");
    finish();
    await flushPromises();
    expect(page().get('[role="status"]').text()).toBe("");
  });

  it("selects all shown studies", async () => {
    const enqueue = vi.spyOn(useOverviewStore(), "enqueue").mockResolvedValue();
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    await search("caffeine");
    await check("Select all shown studies");
    expect(page().get(".batch-count").text()).toBe("2 studies selected");
    await click("Validate");
    expect(enqueue).toHaveBeenCalledWith(["caffeine/Example", "caffeine/Harder1988"], "validate");

    // A study that a filter hides leaves the selection.
    await search("harder");
    expect(page().get(".batch-count").text()).toBe("1 study selected");
  });

  it("marks a partial selection on the select-all checkbox natively too", async () => {
    await mountPage(snapshot({ studies: [example, harder] }));
    await check("Select caffeine/Example");
    const all = checkbox("Select all shown studies");
    expect(all.attributes("aria-checked")).toBe("mixed");
    expect(all.element.indeterminate).toBe(true);
    await check("Select caffeine/Harder1988");
    expect(checkbox("Select all shown studies").element.indeterminate).toBe(false);
  });

  it("reviews an upload of the selected studies before it starts", async () => {
    const enqueue = vi.spyOn(useOverviewStore(), "enqueue").mockResolvedValue();
    await mountPage(
      snapshot({
        studies: [example, harder],
        can_upload: true,
        offline: false,
        authenticated: true,
        account: "mkoenig",
        connection: "connected",
        endpoint: "https://beta.pk-db.com",
      }),
    );
    await check("Select all shown studies");
    await click("Upload");
    expect(dialog().get("h2").text()).toBe("Review upload");
    expect(dialog().text()).toContain("https://beta.pk-db.com");
    expect(dialog().findAll(".upload-study-identity").map((item) => item.text())).toEqual([
      "caffeine/Example",
      "caffeine/Harder1988",
    ]);
    expect(enqueue).not.toHaveBeenCalled();

    await click("Validate and upload");
    expect(enqueue).toHaveBeenCalledWith(["caffeine/Example", "caffeine/Harder1988"], "upload");
    expect(dialogOpen()).toBe(false);
    expect(page().get('[role="status"]').text()).toBe("Upload queued for 2 studies.");
  });

  it("keeps the upload dialog open with the refusal of the server", async () => {
    vi.spyOn(useOverviewStore(), "enqueue").mockRejectedValue(
      new ApiError(400, { error: "Remote actions require a connected endpoint and API key" }),
    );
    await mountPage(snapshot({ can_upload: true }));
    await check("Select caffeine/Example");
    await click("Upload");
    await click("Validate and upload");
    expect(dialog().get(".v-alert").text()).toContain("Remote actions require a connected endpoint and API key");
  });

  it("offers no upload without upload permission and tells why", async () => {
    await mountPage(snapshot({ can_upload: false, offline: true }));
    await check("Select caffeine/Example");
    const upload = button("Upload");
    expect(upload.attributes("disabled")).toBeDefined();
    const reason = document.getElementById(upload.attributes("aria-describedby") ?? "");
    expect(reason?.textContent?.trim()).toBe("Work offline is on. Turn it off in the settings to upload.");

    await page().get(".upload-action").trigger("mouseenter");
    await vi.waitFor(() =>
      expect(page().find(".v-tooltip").text()).toBe("Work offline is on. Turn it off in the settings to upload."),
    );
  });

  it("applies an On save action to the selected studies", async () => {
    const setMode = vi.spyOn(useOverviewStore(), "setMode").mockResolvedValue(snapshot());
    const wrapper = await mountPage(snapshot({ studies: [example, harder] }));
    expect(button("Apply").attributes("disabled")).toBeDefined();
    await check("Select caffeine/Harder1988");
    await choose(wrapper, "On save", "off");
    await click("Apply");
    expect(setMode).toHaveBeenCalledWith(["caffeine/Harder1988"], "off");
    expect(page().get('[role="status"]').text()).toBe("On save is Off for 1 study.");
  });

  it("asks before it turns on upload on save", async () => {
    const setMode = vi.spyOn(useOverviewStore(), "setMode").mockResolvedValue(snapshot());
    const wrapper = await mountPage(snapshot({ can_upload: true, endpoint: "https://beta.pk-db.com" }));
    await check("Select caffeine/Example");
    await choose(wrapper, "On save", "upload");
    await click("Apply");
    expect(setMode).not.toHaveBeenCalled();
    expect(dialog().get("h2").text()).toBe("Turn on upload on save");
    await click("Turn on upload on save");
    expect(setMode).toHaveBeenCalledWith(["caffeine/Example"], "upload");
  });

  it("falls back to Validate on save when the upload permission ends", async () => {
    const wrapper = await mountPage(snapshot({ can_upload: true }));
    await choose(wrapper, "On save", "upload");
    serve({ "/local/state": snapshot({ can_upload: false }), "/local/curators": { curators: profiles } });
    await useOverviewStore().refresh();
    await flushPromises();
    const select = wrapper.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "On save");
    expect(select?.props("modelValue")).toBe("validate");
  });

  it("shows the refusal of a batch action", async () => {
    vi.spyOn(useOverviewStore(), "enqueue").mockRejectedValue(
      new ApiError(400, { error: "Reconcile unknown uploads first" }),
    );
    await mountPage(snapshot());
    await check("Select caffeine/Example");
    await click("Validate");
    expect(page().get(".overview-error").text()).toContain("Reconcile unknown uploads first");
  });

  it("counts the study format 1 folders that it does not list", async () => {
    await mountPage(snapshot({ format1_folders: 1412 }));
    expect(page().get(".overview-footer").text()).toBe(
      "1,412 study format 1 folders are not listed. They stay on the released app version until they are converted.",
    );
  });

  it("names a single study format 1 folder", async () => {
    await mountPage(snapshot({ format1_folders: 1 }));
    expect(page().get(".overview-footer").text()).toBe(
      "1 study format 1 folder is not listed. It stays on the released app version until it is converted.",
    );
  });

  it("has no footer without study format 1 folders", async () => {
    await mountPage(snapshot({ format1_folders: 0 }));
    expect(page().find(".overview-footer").exists()).toBe(false);
  });

  it("keeps the review button and one line for an uncertain upload with chips, note and message", async () => {
    const busy = studyRow({
      status: "unknown",
      message: "The connection closed during the upload and the server did not answer again",
      counts: { ...example.counts, errors: 2, warnings: 3 },
    });
    await mountPage(snapshot({ studies: [busy] }));
    const row = rowOf("caffeine/Example");
    expect(row.findAll(".study-row-line")).toHaveLength(1);
    expect(row.get(".cell-problems").findAll(".status-chip").length).toBeGreaterThanOrEqual(2);
    expect(row.get(".cell-note").attributes("title")).toBe(row.get(".cell-note").text());
    expect(button("Review uncertain upload of caffeine/Example").text()).toBe("Review");
  });

  it("retries an uncertain upload only after the curator confirms the check of the server", async () => {
    const retry = vi.spyOn(useOverviewStore(), "retry").mockResolvedValue(snapshot());
    await mountPage(
      snapshot({
        studies: [studyRow({ status: "unknown", message: "The connection closed during the upload" })],
        jobs: [unknownJob()],
        can_upload: true,
        offline: false,
        authenticated: true,
        connection: "connected",
        endpoint: "https://beta.pk-db.com",
      }),
    );
    const row = rowOf("caffeine/Example");
    expect(row.get(".cell-problems").text()).toContain("Upload outcome unknown");
    const action = button("Review uncertain upload of caffeine/Example");
    expect(action.text()).toBe("Review");
    await click("Review uncertain upload of caffeine/Example");
    expect(dialog().get("h2").text()).toBe("Review uncertain upload");
    expect(dialog().text()).toContain("https://beta.pk-db.com");
    const inspect = dialog().get(".retry-inspect");
    expect(inspect.attributes("href")).toBe("https://beta.pk-db.com/api/v2/studies/caffeine/Example/publication");

    const confirm = button("Validate and upload again");
    expect(confirm.attributes("disabled")).toBeDefined();
    await click("Validate and upload again");
    expect(retry).not.toHaveBeenCalled();

    await dialog().get('input[type="checkbox"]').trigger("click");
    await flushPromises();
    expect(button("Validate and upload again").attributes("disabled")).toBeUndefined();
    await click("Validate and upload again");
    expect(retry).toHaveBeenCalledWith("caffeine/Example", { acknowledgeUnknown: true });
    expect(dialogOpen()).toBe(false);
    expect(page().get('[role="status"]').text()).toBe("Upload queued again for caffeine/Example.");
  });

  it("focuses the link of the study when the retry removed its Review", async () => {
    const connected = {
      can_upload: true,
      offline: false,
      authenticated: true,
      connection: "connected" as const,
      endpoint: "https://beta.pk-db.com",
    };
    const queued = snapshot({ studies: [studyRow({ status: "validating" })], ...connected });
    vi.spyOn(useOverviewStore(), "retry").mockImplementation(async () => {
      serve({ "/local/state": queued, "/local/curators": { curators: profiles } });
      await useOverviewStore().refresh();
      return queued;
    });
    await mountPage(snapshot({ studies: [studyRow({ status: "unknown" })], jobs: [unknownJob()], ...connected }));
    button("Review uncertain upload of caffeine/Example").element.focus();
    await click("Review uncertain upload of caffeine/Example");
    focusDialog();
    await dialog().get('input[type="checkbox"]').trigger("click");
    await flushPromises();
    await click("Validate and upload again");
    expect(page().find(".retry-button").exists()).toBe(false);
    expect(document.activeElement).toBe(rowOf("caffeine/Example").get("a.study-identity").element);
  });

  it("offers no retry once the outcome of the upload is known", async () => {
    const state = snapshot({
      studies: [studyRow({ status: "unknown" })],
      jobs: [unknownJob()],
      can_upload: true,
      endpoint: "https://beta.pk-db.com",
    });
    await mountPage(state);
    await click("Review uncertain upload of caffeine/Example");
    // Resume reconciled the upload with the server while the dialog was open.
    serve({
      "/local/state": { ...state, jobs: [unknownJob({ status: "succeeded" })] },
      "/local/curators": { curators: profiles },
    });
    await useOverviewStore().refresh();
    await flushPromises();
    await dialog().get('input[type="checkbox"]').trigger("click");
    await flushPromises();
    expect(dialog().text()).toContain("The outcome of this upload is known now.");
    expect(button("Validate and upload again").attributes("disabled")).toBeDefined();
  });

  it("filters the table 150 ms after the last keystroke", async () => {
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await field("Search studies").setValue("smok");
      vi.advanceTimersByTime(SEARCH_DELAY_MS - 1);
      await flushPromises();
      expect(identities()).toHaveLength(3);
      await field("Search studies").setValue("smoking");
      vi.advanceTimersByTime(SEARCH_DELAY_MS - 1);
      await flushPromises();
      expect(identities()).toHaveLength(3);
      vi.advanceTimersByTime(1);
      await flushPromises();
      expect(identities()).toEqual(["caffeine/Harder1988"]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("builds the item of each row once per snapshot, not per filter or sort change", async () => {
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    vi.mocked(rowItem).mockClear();
    await search("smoking");
    await search("");
    await click("Open items");
    expect(studyItemCalls()).toHaveLength(0);
    serve({ "/local/state": snapshot({ studies: [example, harder, approved] }), "/local/curators": { curators: profiles } });
    await useOverviewStore().refresh();
    await flushPromises();
    expect(studyItemCalls()).toHaveLength(3);
  });

  it("renders the rows of 1,000 studies that the window shows and selects all of them", async () => {
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    expect(page().get(".study-table table").attributes("aria-rowcount")).toBe("1001");
    expect(rows()).toHaveLength(windowRows(400));
    expect(rows()[0]!.attributes("aria-rowindex")).toBe("2");
    expect(page().findAll("tr.study-space")).toHaveLength(1);
    expect(page().findAll("tr.study-sizer").length).toBeGreaterThan(0);
    await check("Select all shown studies");
    expect(page().get(".batch-count").text()).toBe("1,000 studies selected");
  });

  it("renders only the rows in the window while the search filters 1,000 studies", async () => {
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    for (const [text, shown] of [
      ["study1", 111],
      ["title 9", 111],
      ["codeine", 333],
      ["study999", 1],
      ["", 1000],
    ] as const) {
      await search(text);
      expect(page().get(".study-table table").attributes("aria-rowcount"), text).toBe(String(shown + 1));
      expect(rowIndices(), text).toEqual(Array.from({ length: Math.min(shown, windowRows(400)) }, (_, index) => index + 2));
    }
  });

  it("builds the items of the rendered rows only when a poll brings 1,000 new rows", async () => {
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    vi.mocked(rowItem).mockClear();
    // While jobs run, every poll brings new rows; here one study validates.
    const studies = manyStudies().map((row, index) => (index === 0 ? { ...row, status: "validating" as const } : row));
    serve({ "/local/state": snapshot({ studies }), "/local/curators": { curators: profiles } });
    await useOverviewStore().refresh();
    await flushPromises();
    expect(rows()[0]!.get(".cell-problems").text()).toBe("Validating");
    expect(studyItemCalls()).toHaveLength(windowRows(400));
  });

  it("follows the scrolled page and keeps the row with the keyboard focus until the focus leaves the table", async () => {
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    const input = rows()[0]!.get("input").element;
    input.focus();
    // The body scrolled 2,400 px above the window: rows 100 to 116 are in view.
    await scrollBody(-2400);
    const inView = Array.from({ length: 127 - 90 }, (_, index) => 90 + index + 2);
    expect(rowIndices()).toEqual([2, ...inView]);
    // A space between the focused row and the window, and one below the window.
    expect(page().findAll("tr.study-space")).toHaveLength(2);
    expect(document.activeElement).toBe(input);

    // The focus moves within the row: it stays.
    const link = rows()[0]!.get<HTMLAnchorElement>("a.study-identity").element;
    link.focus();
    await afterTask();
    expect(rowIndices()).toEqual([2, ...inView]);

    // The window loses the focus, as to another application: the event names no new target, and
    // the row keeps the focus of the page.
    link.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
    await afterTask();
    expect(document.activeElement).toBe(link);
    expect(rowIndices()).toEqual([2, ...inView]);

    // The focus leaves the table: the row goes.
    link.blur();
    await afterTask();
    expect(rowIndices()).toEqual(inView);
  });

  it("does not pin a row again that a filter removed while it had the focus", async () => {
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    rows()[0]!.get("input").element.focus();
    await scrollBody(-2400);
    expect(rowIndices()[0]).toBe(2);
    await search("study999");
    await search("");
    expect(rowIndices()).toEqual(Array.from({ length: 127 - 90 }, (_, index) => 90 + index + 2));
  });

  it("measures the window again when the page changes its size, as after a change above the table", async () => {
    const observed: unknown[] = [];
    let resized: () => void = () => {};
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: () => void) {
          resized = callback;
        }
        observe(target: unknown) {
          observed.push(target);
        }
        unobserve() {}
        disconnect() {}
      },
    );
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    expect(observed).toContain(document.documentElement);
    // The body moved without a scroll event, as when an alert above the table wrapped.
    const body = page().get(".study-table tbody").element;
    vi.spyOn(body, "getBoundingClientRect").mockReturnValue({ top: -2400 } as DOMRect);
    resized();
    await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    await flushPromises();
    expect(rowIndices()[0]).toBe(90 + 2);
  });

  it("sizes the window and the spaces by the height of a rendered row, which a larger font raises", async () => {
    // jsdom has no layout: every row is 30 px high, as with a larger font than the default one.
    vi.spyOn(HTMLTableRowElement.prototype, "getBoundingClientRect").mockReturnValue({ top: 0, height: 30 } as DOMRect);
    setViewport(1280, 400);
    await mountPage(snapshot({ studies: manyStudies() }));
    const shown = Math.ceil(400 / 30) + OVERSCAN;
    expect(rowIndices()).toEqual(Array.from({ length: shown }, (_, index) => index + 2));
    expect(page().get<HTMLTableCellElement>("tr.study-space td").element.style.height).toBe(`${(1000 - shown) * 30}px`);
  });

  it("shows the profiles of the curators in the rows that were shown before the roster arrived", async () => {
    let release: () => void = () => {};
    const roster = new Promise<void>((resolve) => (release = resolve));
    const state = snapshot({ studies: [harder] });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = new URL(input instanceof Request ? input.url : String(input), "http://127.0.0.1").pathname;
      if (path === "/local/curators") await roster;
      return new Response(JSON.stringify(path === "/local/state" ? state : { curators: profiles }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    await useOverviewStore().refresh();
    router = makeRouter();
    await router.push("/");
    await router.isReady();
    mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
    await flushPromises();
    const before = rowOf("caffeine/Harder1988").get(".cell-curators");
    expect(before.get('[role="img"][aria-label="mkoenig"]').text()).toBe("M");
    expect(before.find("img").exists()).toBe(false);
    vi.mocked(rowItem).mockClear();

    release();
    await flushPromises();
    const after = rowOf("caffeine/Harder1988").get(".cell-curators");
    expect(after.get('img[alt="Matthias König"]').attributes("src")).toBe("/avatars/matthias_koenig.webp");
    expect(after.get('[role="img"][aria-label="Jan Grzegorzewski"]').text()).toBe("JG");
    expect(studyItemCalls()).toHaveLength(1);
  });

  it("applies the search at once when the keyboard empties the field", async () => {
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    await search("smoking");
    expect(identities()).toHaveLength(1);
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await field("Search studies").setValue("");
      await flushPromises();
      expect(identities()).toHaveLength(3);
      expect(useOverviewFilters().search).toBe("");
    } finally {
      vi.useRealTimers();
    }
  });

  it("clears the search at once with its clear icon", async () => {
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    await search("smoking");
    expect(identities()).toHaveLength(1);
    await page().get('[aria-label="Clear Search studies"]').trigger("click");
    await flushPromises();
    expect(identities()).toHaveLength(3);
    expect(field("Search studies").element.value).toBe("");
  });

  it("keeps a search typed just before the overview is left", async () => {
    const wrapper = await mountPage(snapshot({ studies: [example, harder, approved] }));
    await field("Search studies").setValue("smoking");
    wrapper.unmount();
    expect(useOverviewFilters().search).toBe("smoking");
  });

  it("filters by search, substance and status chip", async () => {
    const wrapper = await mountPage(snapshot({ studies: [example, harder, approved] }));
    expect(page().get(".overview-count").text()).toBe("3 studies");

    await search("smoking");
    expect(identities()).toEqual(["caffeine/Harder1988"]);
    expect(page().get(".overview-count").text()).toBe("1 of 3 studies");
    await search("");

    await choose(wrapper, "Substance", "codeine");
    expect(identities()).toEqual(["codeine/Kirchheiner2007"]);
    await choose(wrapper, "Substance", "");

    const attention = button(/^Needs attention/);
    expect(attention.text()).toMatch(/Needs attention\s*1/);
    await attention.trigger("click");
    await flushPromises();
    expect(identities()).toEqual(["caffeine/Harder1988"]);
    expect(button(/^Needs attention/).attributes("aria-pressed")).toBe("true");
    expect(button(/^All/).attributes("aria-pressed")).toBe("false");

    await click(/^Approved/);
    expect(identities()).toEqual(["codeine/Kirchheiner2007"]);

    await search("smoking");
    expect(rows()).toHaveLength(0);
    expect(page().text()).toContain("No studies match these filters.");
    await click("Clear filters");
    expect(identities()).toHaveLength(3);
    expect(field("Search studies").element.value).toBe("");
  });

  it("filters by curator, with the user of the app first", async () => {
    const state = snapshot({ studies: [example, harder, approved], author: { user: "mkoenig", reason: null } });
    const wrapper = await mountPage(state);
    const select = wrapper.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "Curator")!;
    expect((select.props("items") as { title: string }[]).map((item) => item.title)).toEqual([
      "All curators",
      "Me: Matthias König (1)",
      "curator (3)",
      "Jan Grzegorzewski (1)",
    ]);

    await choose(wrapper, "Curator", "mkoenig");
    expect(identities()).toEqual(["caffeine/Harder1988"]);
    expect(page().get(".overview-count").text()).toBe("1 of 3 studies");
    expect(button(/^All/).text()).toMatch(/All\s*1/);
    await choose(wrapper, "Curator", "curator");
    expect(identities()).toHaveLength(3);

    await choose(wrapper, "Curator", "janekg");
    await click(/^Approved/);
    expect(rows()).toHaveLength(0);
    await click("Clear filters");
    expect(identities()).toHaveLength(3);
    expect(select.props("modelValue")).toBe("");
  });

  it("offers Me without studies of the user, and no Me without a user", async () => {
    const wrapper = await mountPage(
      snapshot({ studies: [example, approved], author: { user: "mkoenig", reason: null } }),
    );
    const titles = () =>
      (
        wrapper.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "Curator")!.props(
          "items",
        ) as { title: string }[]
      ).map((item) => item.title);
    expect(titles()).toEqual(["All curators", "Me: Matthias König (0)", "curator (2)"]);
    wrapper.unmount();

    const anonymous = await mountPage(snapshot({ studies: [example], author: { user: null, reason: "no_user" } }));
    expect(
      (
        anonymous.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "Curator")!.props(
          "items",
        ) as { title: string }[]
      ).map((item) => item.title),
    ).toEqual(["All curators", "curator (1)"]);
  });

  it("keeps the filters and the sort order when the overview is shown again", async () => {
    const state = snapshot({ studies: [example, harder, approved], author: { user: "mkoenig", reason: null } });
    const first = await mountPage(state);
    await choose(first, "Curator", "curator");
    await choose(first, "Substance", "caffeine");
    await click("Open items");
    first.unmount();

    const again = await mountPage(state);
    expect(identities()).toEqual(["caffeine/Example", "caffeine/Harder1988"]);
    expect(page().get(".overview-count").text()).toBe("2 of 3 studies");
    const header = page().findAll("th").find((cell) => cell.text().startsWith("Open items"))!;
    expect(header.attributes("aria-sort")).toBe("ascending");
    expect(
      again.findAllComponents(VSelect).find((candidate) => candidate.props("label") === "Curator")!.props("modelValue"),
    ).toBe("curator");
  });

  it("starts with the default filters in another workspace", async () => {
    const state = snapshot({ studies: [example, harder, approved] });
    const wrapper = await mountPage(state);
    await choose(wrapper, "Curator", "janekg");
    await click("Open items");
    expect(identities()).toEqual(["caffeine/Harder1988"]);

    serve({ "/local/state": { ...state, workspace: "/elsewhere/pkdb_data" }, "/local/curators": { curators: profiles } });
    await useOverviewStore().refresh();
    await flushPromises();
    expect(identities()).toEqual(["caffeine/Example", "caffeine/Harder1988", "codeine/Kirchheiner2007"]);
    expect(page().findAll("th").find((cell) => cell.text().startsWith("Study"))!.attributes("aria-sort")).toBe(
      "ascending",
    );
  });

  it("sorts by a column header", async () => {
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    const header = () => page().findAll("th").find((cell) => cell.text().startsWith("Open items"))!;
    expect(page().findAll("th").find((cell) => cell.text().startsWith("Study"))!.attributes("aria-sort")).toBe(
      "ascending",
    );
    await click("Open items");
    expect(header().attributes("aria-sort")).toBe("ascending");
    expect(identities()).toEqual(["caffeine/Example", "codeine/Kirchheiner2007", "caffeine/Harder1988"]);
    await click("Open items");
    expect(header().attributes("aria-sort")).toBe("descending");
    expect(identities()[0]).toBe("caffeine/Harder1988");
  });

  it("offers to choose a workspace without studies", async () => {
    await mountPage(snapshot({ studies: [] }));
    expect(page().text()).toContain("This workspace has no study format 2 studies.");
    expect(page().find(".study-table").exists()).toBe(false);
    await click("Choose workspace");
    expect(useDialogStore().workspace).toBe(true);
  });

  it("does not poll the state itself", async () => {
    const start = vi.spyOn(useOverviewStore(), "start");
    await mountPage(snapshot());
    expect(start).not.toHaveBeenCalled();
  });

  it("keeps the upload dialog open with what failed on the server", async () => {
    vi.spyOn(useOverviewStore(), "enqueue").mockRejectedValue(
      new ApiError(400, {
        error: "Could not start the upload.",
        code: "invalid_request",
        detail: "ValueError: Upload requires a connected endpoint and API key",
        action: "Upload (POST /local/jobs)",
        ...FAILED,
      }),
    );
    await mountPage(snapshot({ can_upload: true }));
    await check("Select caffeine/Example");
    await click("Upload");
    await click("Validate and upload");
    const alert = dialog().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe("Could not start the upload.");
    expect(alert.get(".action-failure-detail").text()).toBe("ValueError: Upload requires a connected endpoint and API key");
    expect(alert.get("summary").text()).toBe("Details");
    // It goes with the next attempt and when the dialog opens again: no close button, which would drop the focus.
    expect(alert.find(".v-alert__close").exists()).toBe(false);
  });

  it("shows what failed in a batch action until it is closed", async () => {
    vi.spyOn(useOverviewStore(), "enqueue").mockRejectedValue(
      new ApiError(400, {
        error: "Could not start the validation.",
        code: "invalid_request",
        detail: "ValueError: Reconcile unknown uploads first",
        action: "Validate (POST /local/jobs)",
        ...FAILED,
      }),
    );
    await mountPage(snapshot());
    await check("Select caffeine/Example");
    await click("Validate");
    const alert = page().get(".overview-error");
    expect(alert.get(".action-failure-text").text()).toBe("Could not start the validation.");
    expect(alert.get(".action-failure-detail").text()).toBe("ValueError: Reconcile unknown uploads first");
    await alert.get('button[aria-label="Close"]').trigger("click");
    await flushPromises();
    expect(page().find(".overview-error").exists()).toBe(false);
  });

  it("keeps the retry dialog open with what failed", async () => {
    vi.spyOn(useOverviewStore(), "retry").mockRejectedValue(
      new ApiError(400, {
        error: "Could not upload the study again.",
        code: "invalid_request",
        detail: "ValueError: Acknowledge the unknown outcome first",
        action: "Upload again (POST /local/retry)",
        ...FAILED,
      }),
    );
    await mountPage(
      snapshot({
        studies: [studyRow({ status: "unknown" })],
        jobs: [unknownJob()],
        can_upload: true,
        offline: false,
        authenticated: true,
        connection: "connected",
        endpoint: "https://beta.pk-db.com",
      }),
    );
    await click("Review uncertain upload of caffeine/Example");
    await dialog().get('input[type="checkbox"]').trigger("click");
    await flushPromises();
    await click("Validate and upload again");
    const alert = dialog().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe("Could not upload the study again.");
    expect(alert.get(".action-failure-detail").text()).toBe("ValueError: Acknowledge the unknown outcome first");
    // It goes with the next attempt and when the dialog opens again: no close button, which would drop the focus.
    expect(alert.find(".v-alert__close").exists()).toBe(false);
  });
});
