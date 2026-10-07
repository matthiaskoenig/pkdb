import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { VSelect } from "vuetify/components";
import { ApiError } from "../../src/curation-app/api/client";
import type { Job, Profile, Snapshot, SyncStatus } from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import OverviewPage from "../../src/curation-app/views/OverviewPage.vue";
import { snapshot, studyRow } from "../unit/curation-fixtures";
import { button, click, field, page, serve, setViewport } from "./curation-dom";

enableAutoUnmount(afterEach);

let pinia: Pinia;

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
  const router = makeRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

/** The rows of the study table. */
function rows(): DOMWrapper<HTMLTableRowElement>[] {
  return page().findAll<HTMLTableRowElement>(".study-table tbody tr");
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
    expect(row.get(".study-title").text()).toBe("Effect of smoking on caffeine");
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

  it("counts the curators after the third avatar", async () => {
    const many = studyRow({ summary: { ...example.summary, curators: ["a", "b", "c", "mkoenig", "janekg"] } });
    await mountPage(snapshot({ studies: [many] }));
    const curators = rowOf("caffeine/Example").get(".cell-curators");
    expect(curators.findAll(".curator")).toHaveLength(3);
    const more = curators.get(".curator-more");
    expect(more.text()).toBe("+2");
    expect(more.attributes("aria-label")).toBe("And Matthias König, Jan Grzegorzewski");
  });

  it("shows initials when the curator roster cannot be loaded", async () => {
    serve({ "/local/state": snapshot({ studies: [harder] }) });
    await useOverviewStore().refresh();
    const router = makeRouter();
    await router.push("/");
    mount(OverviewPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
    await flushPromises();
    const curators = rowOf("caffeine/Harder1988").get(".cell-curators");
    expect(curators.get('[role="img"][aria-label="mkoenig"]').text()).toBe("M");
  });

  it("opens the study page when a row is clicked", async () => {
    await mountPage(snapshot());
    expect(rowOf("caffeine/Example").get(".study-identity").attributes("href")).toBe("#/studies/caffeine/Example");
    await rowOf("caffeine/Example").get(".cell-sync").trigger("click");
    await vi.waitFor(() => expect(window.location.hash).toBe("#/studies/caffeine/Example"));
  });

  it("shows a duplicate identity that cannot be selected or opened", async () => {
    const duplicates = [
      studyRow({ duplicate: true }),
      studyRow({ duplicate: true, path: "archive/caffeine/Example" }),
    ];
    await mountPage(snapshot({ studies: duplicates }));
    expect(rows()).toHaveLength(2);
    for (const row of rows()) {
      expect(row.text()).toContain("Duplicate identity");
      expect(row.find("a.study-identity").exists()).toBe(false);
      expect(row.get('input[type="checkbox"]').attributes("disabled")).toBeDefined();
    }
    expect(rows().map((row) => row.get(".study-path").text())).toEqual([
      "archive/caffeine/Example",
      "studies/caffeine/Example",
    ]);
    await rows()[0]!.get(".cell-sync").trigger("click");
    await flushPromises();
    expect(window.location.hash).toBe("#/");
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

  it("selects all shown studies", async () => {
    const enqueue = vi.spyOn(useOverviewStore(), "enqueue").mockResolvedValue();
    await mountPage(snapshot({ studies: [example, harder, approved] }));
    await field("Search studies").setValue("caffeine");
    await flushPromises();
    await check("Select all shown studies");
    expect(page().get(".batch-count").text()).toBe("2 studies selected");
    await click("Validate");
    expect(enqueue).toHaveBeenCalledWith(["caffeine/Example", "caffeine/Harder1988"], "validate");

    // A study that a filter hides leaves the selection.
    await field("Search studies").setValue("harder");
    await flushPromises();
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
    await new Promise((resolve) => setTimeout(resolve, 50));
    await flushPromises();
    expect(page().get(".v-tooltip").text()).toBe("Work offline is on. Turn it off in the settings to upload.");
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
      "1,412 study format 1 folders are not listed. Convert them with pkdb migrate; until then they stay on the released app version.",
    );
  });

  it("names a single study format 1 folder", async () => {
    await mountPage(snapshot({ format1_folders: 1 }));
    expect(page().get(".overview-footer").text()).toBe(
      "1 study format 1 folder is not listed. Convert it with pkdb migrate; until then it stays on the released app version.",
    );
  });

  it("has no footer without study format 1 folders", async () => {
    await mountPage(snapshot({ format1_folders: 0 }));
    expect(page().find(".overview-footer").exists()).toBe(false);
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

  it("filters by search, substance and status chip", async () => {
    const wrapper = await mountPage(snapshot({ studies: [example, harder, approved] }));
    expect(page().get(".overview-count").text()).toBe("3 studies");

    await field("Search studies").setValue("smoking");
    await flushPromises();
    expect(identities()).toEqual(["caffeine/Harder1988"]);
    expect(page().get(".overview-count").text()).toBe("1 of 3 studies");
    await field("Search studies").setValue("");
    await flushPromises();

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

    await field("Search studies").setValue("smoking");
    await flushPromises();
    expect(rows()).toHaveLength(0);
    expect(page().text()).toContain("No studies match these filters.");
    await click("Clear filters");
    expect(identities()).toHaveLength(3);
    expect(field("Search studies").element.value).toBe("");
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
});
