import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h } from "vue";
import { RouterView, type Router } from "vue-router";
import { VSelect } from "vuetify/components";
import type {
  ReviewItem,
  Snapshot,
  StudyDetail,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import OverviewPage from "../../src/curation-app/views/OverviewPage.vue";
import { NOTICE_MS } from "../../src/curation-app/study";
import StudyPage from "../../src/curation-app/views/StudyPage.vue";
import { json, snapshot, sourceSummary, studyDetail, studyMetadata, studyRow } from "../unit/curation-fixtures";
import {
  button,
  buttons,
  click,
  field,
  focusDialog,
  labeled,
  page,
  radio,
  serveApi,
  setViewport,
  type ServedRequest,
} from "./curation-dom";

enableAutoUnmount(afterEach);

const ISSUE_URL = "https://github.com/matthiaskoenig/pkdb_data/issues/2158";
const HARDER = "/local/studies/caffeine/Harder1988";
const EXAMPLE = "/local/studies/caffeine/Example";

const release = { pkdb_id: "PKDB00198", date: "2026-09-28" };
const provenance = {
  kind: "automatic_curation" as const,
  source_key: "pkdb.ai",
  method: "claude-opus-5-5",
  version: "1",
  assets: [],
  run_id: "run-1",
};
const question: ReviewItem = {
  id: "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
  kind: "question",
  state: "open",
  target: { file: "outputs_Tab2.tsv", column: "mean" },
  text: "Is the mean read from the table?",
  author: "curator",
  created: "2026-10-05T10:12:00Z",
  thread: [],
};

/** Released, in review with one open item, AI curated, with an issue labeled `check` and two errors. */
const harder: StudyDetail = studyDetail({
  id: "caffeine/Harder1988",
  path: "caffeine/Harder1988",
  status: "invalid",
  mode: "upload",
  sync: { status: "workbook_open", changes: 0, conflicts: 0 },
  counts: { errors: 2, warnings: 1 },
  summary: {
    title: "Effect of smoking on caffeine clearance and plasma levels in healthy volunteers",
    review_status: "in_review",
    open_items: 1,
    curators: ["mkoenig"],
    creator: "curator",
    release,
    issue: 2158,
    provenance: { kind: "automatic_curation", method: "claude-opus-5-5" },
    ai: true,
  },
  issue: { number: 2158, state: "open", labels: ["check"], assignees: [], url: ISSUE_URL },
  metadata: {
    revision: "study-3",
    value: studyMetadata({ reference: { pmid: "2895442" }, issue: 2158, release, provenance }),
    issues: [],
  },
  review: {
    revision: "review-7",
    value: { status: "in_review", reviewers: ["curator"], items: [question] },
    issues: [],
  },
  sources: [
    sourceSummary({ source: "Fig1", kind: "figure", image: "Harder1988_Fig1.png", tables: ["timecourses_Fig1.tsv"] }),
    sourceSummary({ source: "Tab2", image: "Harder1988_Tab2.png", tables: ["outputs_Tab2.tsv"] }),
  ],
  files: [
    "characteristica.tsv",
    "Harder1988.pdf",
    "Harder1988_Fig1.png",
    "Harder1988_Tab2.png",
    "Harder1988_Tab3.png",
    "interventions.tsv",
    "outputs_Tab2.tsv",
    "reference.json",
    "review.json",
    "study.json",
    "subjects.tsv",
    "timecourses_Fig1.tsv",
  ],
  tables: [
    { file: "subjects.tsv", kind: "subjects" },
    { file: "interventions.tsv", kind: "interventions" },
    { file: "characteristica.tsv", kind: "characteristica" },
    { file: "outputs_Tab2.tsv", kind: "outputs" },
    { file: "timecourses_Fig1.tsv", kind: "timecourses" },
  ],
});

/** The last upload of a study, without its URL. */
const UPLOAD = { persistence: "replaced" as const, at: "2026-10-01T12:00:00Z", endpoint: "https://beta.pk-db.com" };

const harderRow = studyRow({
  id: "caffeine/Harder1988",
  name: "Harder1988",
  path: "caffeine/Harder1988",
  mode: "upload",
  status: "invalid",
  summary: harder.summary,
  counts: harder.counts,
});

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];

/** The study page at `path` of the hash router, with `routes` of the local API besides the defaults. */
async function mountPage(path: string, routes: Record<string, unknown> = {}, state: Snapshot = snapshot()) {
  requests = serveApi({
    "GET /local/state": state,
    [`GET ${HARDER}`]: harder,
    [`GET ${EXAMPLE}`]: studyDetail(),
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(path);
  await router.isReady();
  const wrapper = mount(StudyPage, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

/** The POST requests to `path`, by their bodies. */
function posted(path: string): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === path).map(({ body }) => body);
}

function select(wrapper: ReturnType<typeof mount>, label: string) {
  return labeled(wrapper, VSelect, label);
}

function dialog() {
  return page().get('.v-overlay--active[role="dialog"]');
}

function alertText(): string {
  return page().get(".study-alert").text();
}

function issue(message: string, changes: Partial<ValidationIssue> = {}): ValidationIssue {
  return { code: "workbook_invalid", severity: "error", message, ...changes };
}

function tablesResult(changes: Partial<TablesResult> = {}): TablesResult {
  return { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [], ...changes };
}

/** A clipboard with `writeText`, removed again after the test; jsdom has none. */
function stubClipboard(writeText: (text: string) => Promise<void>) {
  const spy = vi.fn(writeText);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: spy } });
  onTestFinished(() => {
    Reflect.deleteProperty(navigator, "clipboard");
  });
  return spy;
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("routes", () => {
  it("imports the route views eagerly, so that navigation works after the server stopped", () => {
    const routes = makeRouter();
    expect(routes.resolve("/").matched[0]?.components?.default).toBe(OverviewPage);
    expect(routes.resolve("/studies/caffeine/Example/review").matched[0]?.components?.default).toBe(StudyPage);
  });
});

describe("StudyPage", () => {
  it("stays on the overview when the study page is left", async () => {
    requests = serveApi({ "GET /local/state": snapshot({ studies: [harderRow] }), [`GET ${HARDER}`]: harder });
    router = makeRouter();
    await router.push("/studies/caffeine/Harder1988/review");
    mount(defineComponent({ render: () => h(RouterView) }), {
      attachTo: document.body,
      global: { plugins: [pinia, router] },
    });
    await flushPromises();
    expect(page().find(".study-header").exists()).toBe(true);
    const studyRequests = () => requests.filter(({ path }) => path.startsWith("/local/studies/"));
    // The detail, and the table that the selected review item targets.
    const opened = studyRequests().length;
    expect(studyRequests().filter(({ path }) => path === HARDER)).toHaveLength(1);

    await router.push("/");
    await flushPromises();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(router.currentRoute.value.name).toBe("Overview");
    expect(studyRequests().slice(opened)).toEqual([]);
  });

  it("redirects a study without a section to its default section", async () => {
    await mountPage("/studies/caffeine/Example");
    // The page replaces the route once the detail is loaded.
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("metadata"));
    expect(window.location.hash).toBe("#/studies/caffeine/Example/metadata");
  });

  it("opens a study with open items on Review, and an unknown section on the default", async () => {
    await mountPage("/studies/caffeine/Harder1988/figures");
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("review"));
  });

  it("lists the six sections with counts in the rail and marks the active one", async () => {
    await mountPage("/studies/caffeine/Harder1988/problems");
    const nav = page().get('nav[aria-label="Study sections"]');
    const links = nav.findAll("a");
    expect(links.map((link) => link.get(".rail-label").element.firstChild?.textContent)).toEqual([
      "Metadata",
      "Review",
      "Problems",
      "Sources",
      "Tables",
      "Activity",
    ]);
    expect(links.map((link) => link.find(".rail-count").exists() && link.get(".rail-count").text())).toEqual([
      false,
      "1",
      "3",
      "2",
      "5",
      false,
    ]);
    // The counts have their meaning for screen readers.
    expect(links[1]!.get(".rail-label").text()).toBe("Review, 1 open item");
    expect(links[2]!.get(".rail-label").text()).toBe("Problems, 3 problems");
    expect(links[0]!.get(".rail-label").text()).toBe("Metadata");
    expect(links[1]!.attributes("href")).toBe("#/studies/caffeine/Harder1988/review");
    expect(links.map((link) => link.attributes("aria-current") ?? null)).toEqual([
      null,
      null,
      "page",
      null,
      null,
      null,
    ]);
    expect(page().get(".study-section h2").text()).toBe("Problems");

    await links[4]!.trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("tables"));
    await flushPromises();
    expect(page().get(".study-section h2").text()).toBe("Tables");
  });

  it("shows the rail as a select below 600 px", async () => {
    setViewport(375, 800);
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review");
    expect(page().find('nav[aria-label="Study sections"] a').exists()).toBe(false);
    const sections = select(wrapper, "Section");
    expect(sections.props("modelValue")).toBe("review");
    expect(sections.props("items")).toContainEqual({ title: "Problems (3)", value: "problems" });
    await sections.setValue("sources");
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("sources"));
  });

  it("shows the identity, the review status, the release, the issue and the provenance", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review");
    const header = page().get(".study-header");
    expect(header.get("h1").text()).toBe("caffeine/Harder1988");
    expect(select(wrapper, "Review status").props("modelValue")).toBe("in_review");
    expect(header.get(".release-chip").text()).toBe("PKDB00198 · released 2026-09-28");
    const issueChip = header.get(".issue-chip");
    expect(issueChip.text()).toBe("#2158 · check");
    expect(issueChip.attributes("href")).toBe(ISSUE_URL);
    expect(header.get(".provenance-chip").text()).toBe("AI curated · claude-opus-5-5");
  });

  it("shows a summary line with the title, the PMID, On save, the sync status and the problems", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    const header = page().get(".study-header");
    expect(header.get(".study-title").text()).toBe(
      "Effect of smoking on caffeine clearance and plasma levels in healthy volunteers",
    );
    const facts = header.get(".study-facts");
    expect(facts.get(".fact-pmid a").text()).toBe("2895442");
    expect(facts.get(".fact-pmid a").attributes("href")).toBe("https://pubmed.ncbi.nlm.nih.gov/2895442/");
    expect(facts.get(".fact-mode").text()).toBe("On save Upload");
    expect(facts.get(".fact-sync").text()).toBe("Workbook open");
    expect(facts.findAll(".fact-problems .v-chip").map((chip) => chip.text())).toEqual(["2 errors", "1 warning"]);
  });

  it("links the last upload to its page on PK-DB", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, last_upload: { ...UPLOAD, url: "https://beta.pk-db.com/data/Harder1988" } },
    });
    expect(page().get(".fact-upload a").attributes("href")).toBe("https://beta.pk-db.com/data/Harder1988");
  });

  it("links the last upload only to a web page", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, last_upload: { ...UPLOAD, url: "javascript:alert(1)" } },
    });
    const fact = page().get(".fact-upload");
    expect(fact.find("a").exists()).toBe(false);
    expect(fact.get("span:not(.fact-name)").text()).toMatch(/^2026-10-01 \d\d:\d\d$/);
  });

  it("names a study before its first check and without release, issue and AI", async () => {
    const fresh = studyDetail({
      status: "discovered",
      sync: { status: "not_checked", changes: 0, conflicts: 0 },
      summary: { ...studyDetail().summary, title: null },
      metadata: { revision: "study-1", value: studyMetadata({ reference: {} }), issues: [] },
    });
    await mountPage("/studies/caffeine/Example/metadata", { [`GET ${EXAMPLE}`]: fresh });
    const header = page().get(".study-header");
    expect(header.find(".release-chip").exists()).toBe(false);
    expect(header.find(".issue-chip").exists()).toBe(false);
    expect(header.find(".provenance-chip").exists()).toBe(false);
    expect(header.get(".study-title").text()).toBe("No reference title yet");
    expect(header.find(".fact-pmid").exists()).toBe(false);
    expect(header.get(".fact-sync").text()).toBe("Not checked yet");
    expect(header.get(".fact-problems").text()).toBe("Not validated yet");
  });

  it("sets the review status over the revision of review.json", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": { revision: "review-8" },
    });
    await select(wrapper, "Review status").setValue("approved");
    await flushPromises();
    expect(posted("/local/studies/review")).toEqual([
      { study: "caffeine/Harder1988", revision: "review-7", action: "status", status: "approved" },
    ]);
  });

  it("explains a refused approval and resets the review status", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": () =>
        json({ error: "1 review item is open", issues: [], code: "approval_refused" }, { status: 422 }),
    });
    const status = select(wrapper, "Review status");
    await status.setValue("approved");
    await flushPromises();
    expect(page().get(".study-alert .action-failure-text").text()).toBe(
      "Approved needs zero open review items and zero validation errors. 1 review item is open.",
    );
    const link = page().get(".study-alert a");
    expect(link.text()).toBe("Show the open items");
    expect(link.attributes("href")).toBe("#/studies/caffeine/Harder1988/review");
    expect(status.props("modelValue")).toBe("in_review");
  });

  it("lists the errors that block an approval, a few of them, with a link to Problems", async () => {
    const errors = ["Fig1", "Fig2", "Tab1", "Tab2"].map((source) =>
      issue(`Harder1988_${source}.png is missing`, { code: "missing_image" }),
    );
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": () =>
        json({ error: "Validation has 4 errors", issues: errors, code: "approval_refused" }, { status: 422 }),
    });
    await select(wrapper, "Review status").setValue("approved");
    await flushPromises();
    const alert = page().get(".study-alert");
    expect(alert.get(".action-failure-text").text()).toBe(
      "Approved needs zero open review items and zero validation errors. Validation has 4 errors.",
    );
    expect(alert.findAll("li").map((item) => item.text())).toEqual([
      "Harder1988_Fig1.png is missing",
      "Harder1988_Fig2.png is missing",
      "Harder1988_Tab1.png is missing",
      "and 1 more",
    ]);
    const link = alert.get("a");
    expect(link.text()).toBe("Show the problems");
    expect(link.attributes("href")).toBe("#/studies/caffeine/Harder1988/problems");
  });

  it("allows no other action while the review status is being set", async () => {
    let answer: (response: Response) => void = () => undefined;
    const slow = new Promise<Response>((resolve) => (answer = resolve));
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": () => slow,
      "POST /local/jobs": { ok: true },
    });
    const status = select(wrapper, "Review status");
    await status.setValue("approved");
    await flushPromises();
    expect(status.props("modelValue")).toBe("approved");
    expect(status.props("disabled")).toBe(true);
    expect(status.get('[role="progressbar"]').attributes("aria-label")).toBe("Setting the review status");
    for (const name of ["Open tables", "Validate", "More actions"])
      expect(button(name).attributes("disabled")).toBeDefined();

    // A second choice while the first one is written changes nothing.
    await status.setValue("draft");
    await button("Validate").trigger("click");
    await flushPromises();
    expect(posted("/local/studies/review")).toHaveLength(1);
    expect(posted("/local/jobs")).toHaveLength(0);

    answer(json({ revision: "review-8" }));
    await flushPromises();
    expect(status.props("disabled")).toBe(false);
    expect(button("Validate").attributes("disabled")).toBeUndefined();
    expect(page().get(".study-notice").text()).toBe("Review status set to Approved.");
  });

  it("explains a review.json that changed on disk before the status was set", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": () =>
        json(
          { error: "review.json changed", file: "review.json", revision: "review-9", content: "{}" },
          { status: 409 },
        ),
    });
    await select(wrapper, "Review status").setValue("approved");
    await flushPromises();
    expect(alertText()).toBe(
      "review.json changed on disk, so the status was not set. Check the review and set it again.",
    );
  });

  it("asks to set the user when a write needs one, as every section does", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/review": () =>
        json({ error: "no_user", message: "Set your PK-DB username in the settings." }, { status: 403 }),
    });
    await select(wrapper, "Review status").setValue("draft");
    await flushPromises();
    // The settings do not open by themselves.
    expect(useDialogStore().settings).toBe(false);
    expect(page().get(".study-header .user-hint").text()).toContain("Set your PK-DB user in Connection settings.");
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });

  it("opens the workbook and shows the issues of the sync", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": tablesResult({
        ok: false,
        opened: false,
        issues: [issue("Harder1988.xlsx could not be created: the folder is read-only")],
      }),
    });
    await click("Open tables");
    expect(posted("/local/studies/tables")).toEqual([{ study: "caffeine/Harder1988", action: "open" }]);
    expect(alertText()).toContain("The workbook could not be opened.");
    expect(alertText()).toContain("Harder1988.xlsx could not be created: the folder is read-only");
  });

  it("opens the workbook quietly when the sync is clean", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": tablesResult({ opened: true }),
    });
    await click("Open tables");
    expect(page().find(".study-alert").exists()).toBe(false);
    expect(page().get(".study-notice").text()).toBe("The workbook opened.");
  });

  it("queues a validation of the study", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", { "POST /local/jobs": { ok: true } });
    await click("Validate");
    expect(posted("/local/jobs")).toEqual([{ ids: ["caffeine/Harder1988"], action: "validate" }]);
    const notice = page().get(".study-notice");
    expect(notice.text()).toBe("Validation queued.");
    expect(notice.attributes()).toMatchObject({ role: "status", "aria-live": "polite" });
  });

  it("clears a notice after a few seconds and keeps an error until it is dismissed", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await mountPage("/studies/caffeine/Harder1988/review", {
        "POST /local/jobs": { ok: true },
        "POST /local/studies/tables": () => json({ error: "Unable to open the workbook" }, { status: 500 }),
      });
      await click("Validate");
      expect(page().get(".study-notice").text()).toBe("Validation queued.");
      vi.advanceTimersByTime(NOTICE_MS);
      await flushPromises();
      expect(page().get(".study-notice").text()).toBe("");

      await click("Open tables");
      vi.advanceTimersByTime(NOTICE_MS * 4);
      await flushPromises();
      expect(alertText()).toBe("Unable to open the workbook");
      await page().get(".study-alert").get('button[aria-label="Close"]').trigger("click");
      await flushPromises();
      expect(page().find(".study-alert").exists()).toBe(false);
    } finally {
      vi.useRealTimers();
    }
  });

  it("uploads only with an upload permission, and says why it cannot", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {}, snapshot({ studies: [harderRow] }));
    const upload = button("Upload");
    expect(upload.attributes("disabled")).toBeDefined();
    // A caption, also shown where no pointer can hover over the tooltip.
    const reason = page().get(".upload-reason");
    expect(reason.text()).toBe("Work offline is on. Turn it off in the settings to upload.");
    expect(upload.attributes("aria-describedby")).toBe(reason.attributes("id"));
  });

  it("says why it cannot upload a study that the overview does not list yet", async () => {
    const connected = snapshot({ can_upload: true, offline: false, authenticated: true, connection: "connected" });
    await mountPage("/studies/caffeine/Harder1988/review", {}, connected);
    expect(button("Upload").attributes("disabled")).toBeDefined();
    expect(page().get(".upload-reason").text()).toBe(
      "The workspace scan has not listed this study yet. Upload waits for the next scan.",
    );
  });

  it("reviews an upload in the upload dialog", async () => {
    const connected = snapshot({
      studies: [harderRow],
      can_upload: true,
      offline: false,
      authenticated: true,
      connection: "connected",
      endpoint: "https://beta.pk-db.com",
    });
    await mountPage("/studies/caffeine/Harder1988/review", { "POST /local/jobs": { ok: true } }, connected);
    await click("Upload");
    expect(dialog().text()).toContain("Review upload");
    expect(dialog().text()).toContain("caffeine/Harder1988");
    await click("Validate and upload");
    expect(posted("/local/jobs")).toEqual([{ ids: ["caffeine/Harder1988"], action: "upload" }]);
  });

  it("opens the folder and the PDF of the study and copies its path", async () => {
    const writeText = stubClipboard(async () => undefined);
    await mountPage("/studies/caffeine/Harder1988/review", { "POST /local/files/open": { ok: true } });

    await click("More actions");
    await click("Open folder");
    await click("More actions");
    await click("Open PDF");
    expect(posted("/local/files/open")).toEqual([
      { study_id: "caffeine/Harder1988" },
      { study_id: "caffeine/Harder1988", file: "Harder1988.pdf" },
    ]);

    await click("More actions");
    await click("Copy path");
    expect(writeText).toHaveBeenCalledWith("/work/pkdb_data/caffeine/Harder1988");
    expect(page().get(".study-notice").text()).toBe("Path copied.");
  });

  it("shows the path when it cannot be copied", async () => {
    stubClipboard(async () => {
      throw new DOMException("Write permission denied", "NotAllowedError");
    });
    await mountPage("/studies/caffeine/Harder1988/review");
    await click("More actions");
    await click("Copy path");
    expect(alertText()).toBe("The path could not be copied: /work/pkdb_data/caffeine/Harder1988");
    expect(page().get(".study-notice").text()).toBe("");
  });

  it("offers Open PDF only when the folder has the PDF", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, files: harder.files.filter((file) => !file.endsWith(".pdf")) },
    });
    await click("More actions");
    expect(button("Open PDF").attributes("disabled")).toBeDefined();
  });

  it("adds a data table from the add table dialog", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": tablesResult({ table: "outputs_Tab3", workbook_action: "regenerated" }),
    });
    await click("More actions");
    await click("Add table");
    expect(dialog().get("h2").text()).toBe("Add table");
    expect(radio("Outputs").checked).toBe(true);
    expect(button("Add").attributes("disabled")).toBeDefined();

    await field("Source").setValue("Tab3");
    await flushPromises();
    const preview = dialog().get(".table-preview");
    expect(preview.text()).toContain("outputs_Tab3");
    expect(preview.text()).toContain("outputs_Tab3.tsv");
    expect(preview.text()).toContain("Harder1988_Tab3.png");
    expect(preview.get(".image-state").text()).toBe("In the folder");

    await click("Add");
    expect(posted("/local/studies/tables")).toEqual([
      { study: "caffeine/Harder1988", action: "add", table: "outputs_Tab3" },
    ]);
    expect(page().find('.v-overlay--active[role="dialog"]').exists()).toBe(false);
    expect(page().get(".study-notice").text()).toBe("Added the sheet outputs_Tab3 to the workbook.");
  });

  it("returns the focus to More actions when Add table, an item of its menu, closes", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    button("More actions").element.focus();
    await click("More actions");
    button("Add table").element.focus();
    await click("Add table");
    focusDialog();
    await click("Cancel");
    expect(document.activeElement).toBe(button("More actions").element);
  });

  it("adds a raw table and shows the issues of the API", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": tablesResult({
        ok: false,
        issues: [
          issue(
            "Harder1988.xlsx is open in a spreadsheet application. Close the workbook first, or copy a sheet " +
              "in the spreadsheet application and rename it to Harder1988_Tab4",
            { code: "workbook_open" },
          ),
        ],
      }),
    });
    await click("More actions");
    await click("Add table");
    radio("Raw table").click();
    await flushPromises();
    await field("Source").setValue("Tab4");
    await flushPromises();
    const preview = dialog().get(".table-preview");
    expect(preview.text()).toContain("Harder1988_Tab4.tsv");
    expect(preview.get(".image-state").text()).toBe("Missing");
    expect(preview.text()).toContain("Add Harder1988_Tab4.png to the folder");

    await click("Add");
    expect(posted("/local/studies/tables")).toEqual([{ study: "caffeine/Harder1988", action: "add", raw: "Tab4" }]);
    expect(dialog().get(".v-alert").text()).toContain("Close the workbook first");
  });

  it("asks in Add table to set the user when the write needs one", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    await click("Add");
    // No second dialog opens on top of Add table by itself.
    expect(useDialogStore().settings).toBe(false);
    expect(dialog().get(".user-hint").text()).toContain("Set your PK-DB user in Connection settings.");
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });

  it("refuses a source that is not a paper table or figure, and an existing table", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab 3");
    await flushPromises();
    expect(dialog().text()).toContain("Use a source such as Tab3, Fig2A or Text.");
    expect(button("Add").attributes("disabled")).toBeDefined();
    await field("Source").setValue("Tab2");
    await flushPromises();
    expect(dialog().text()).toContain("outputs_Tab2.tsv already exists.");
    expect(button("Add").attributes("disabled")).toBeDefined();
  });

  it("explains a duplicate identity with both folders", async () => {
    const paths = ["caffeine/Example", "archive, 2020/caffeine/Example"];
    const message = `caffeine/Example is the identity of two folders: ${paths.join(", ")}; rename one`;
    await mountPage("/studies/caffeine/Example", {
      [`GET ${EXAMPLE}`]: () => json({ error: message, paths }, { status: 409 }),
    });
    const main = page().get(".study-failure");
    expect(main.get("h1").text()).toBe("This identity belongs to two folders");
    // A folder name with a comma stays one folder.
    expect(main.findAll("li").map((item) => item.text())).toEqual(paths);
    expect(main.get("a").attributes("href")).toBe("#/");
    expect(page().find(".study-header").exists()).toBe(false);
  });

  it("explains a study that is not in the workspace, with a link back", async () => {
    await mountPage("/studies/caffeine/Missing2000/review");
    const main = page().get(".study-failure");
    expect(main.get("h1").text()).toBe("This study is not in the workspace");
    const back = main.get("a");
    expect(back.text()).toBe("Back to the studies");
    expect(back.attributes("href")).toBe("#/");
    expect(buttons("Open tables")).toHaveLength(0);
  });
});
