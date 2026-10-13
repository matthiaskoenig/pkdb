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
  TablePreview,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { POLL_INTERVAL_MS } from "../../src/curation-app/composables/usePolling";
import { toForm } from "../../src/curation-app/metadata";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import OverviewPage from "../../src/curation-app/views/OverviewPage.vue";
import { NOTICE_MS } from "../../src/curation-app/study";
import { noteKinds } from "../../src/curation-app/tableKinds";
import StudyPage from "../../src/curation-app/views/StudyPage.vue";
import tablePreviewFixture from "../fixtures/curation-contract/table-preview.json";
import { json, snapshot, sourceSummary, studyDetail, studyMetadata, studyRow, tableEntry } from "../unit/curation-fixtures";
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
  type Handler,
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
  papers: [
    {
      file: "Harder1988.pdf",
      url: "/local/studies/caffeine/Harder1988/files/Harder1988.pdf",
      bytes: 1_204_331,
      version: "5f1d0e2a9c3b7e41",
    },
  ],
  tables: [
    tableEntry("subjects.tsv", "subjects"),
    tableEntry("interventions.tsv", "interventions"),
    tableEntry("characteristica.tsv", "characteristica"),
    tableEntry("outputs_Tab2.tsv", "outputs"),
    tableEntry("timecourses_Fig1.tsv", "timecourses"),
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

/** The view of the router, as the app renders it, so that the guards of the study page apply. */
const Routed = defineComponent({ render: () => h(RouterView) });

/**
 * The study page at `path` of the hash router, with `routes` of the local API besides the defaults. It
 * renders in the view of the router, as in the app, so that its guards of leaving the study apply.
 */
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
  const wrapper = mount(Routed, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  });
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

/** The previews of new tables of Harder1988 that the local server gives, by kind and source. */
const HARDER_PREVIEWS: Record<string, TablePreview> = {
  "outputs Tab3": {
    table: "outputs_Tab3",
    file: "outputs_Tab3.tsv",
    image: "Harder1988_Tab3.png",
    image_found: true,
    issues: [],
  },
  "raw Tab4": {
    table: "Harder1988_Tab4",
    file: "Harder1988_Tab4.tsv",
    image: "Harder1988_Tab4.png",
    image_found: false,
    issues: [],
  },
};

/** The preview of the contract fixture for a kind and a source, a real answer of the local server. */
function fixturePreview(kind: unknown, source: unknown): TablePreview | undefined {
  const entry = tablePreviewFixture.previews.find((preview) => preview.request.kind === kind && preview.request.source === source);
  return entry?.response as TablePreview | undefined;
}

/** Answers `POST /local/studies/tables/preview` for the posted kind and source from `preview`. */
function previewHandler(preview: (kind: unknown, source: unknown) => TablePreview | undefined): Handler {
  return (body) => {
    const answer = preview(body?.kind, body?.source);
    return answer ? json(answer) : json({ error: "Unknown resource" }, { status: 404 });
  };
}

const harderPreview = previewHandler((kind, source) => HARDER_PREVIEWS[`${String(kind)} ${String(source)}`]);

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

  it("shows the overview for an address that the app does not know, such as a pasted launch URL", async () => {
    const routes = makeRouter();
    for (const path of ["/token=pasted", "/studies", "/studies/caffeine/Example/data/more"]) {
      await routes.push(path);
      expect(routes.currentRoute.value.name).toBe("Overview");
    }
  });
});

describe("StudyPage", () => {
  it("stays on the overview when the study page is left", async () => {
    // The clock stands still until the study is left, so that no poll of the open study counts as one after it.
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      requests = serveApi({ "GET /local/state": snapshot({ studies: [harderRow] }), [`GET ${HARDER}`]: harder });
      router = makeRouter();
      await router.push("/studies/caffeine/Harder1988/review");
      mount(Routed, {
        attachTo: document.body,
        global: { plugins: [pinia, router] },
      });
      await flushPromises();
      expect(page().find(".study-header").exists()).toBe(true);
      const studyRequests = () => requests.filter(({ path }) => path.startsWith("/local/studies/"));
      // The detail, and the table that the selected review item targets.
      const opened = studyRequests().length;
      expect(studyRequests().filter(({ path }) => path === HARDER)).toHaveLength(1);

      const left = router.push("/");
      // An open study would be polled several times meanwhile.
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3);
      await left;
      await flushPromises();
      expect(router.currentRoute.value.name).toBe("Overview");
      expect(studyRequests().slice(opened)).toEqual([]);
    } finally {
      vi.useRealTimers();
    }
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

  it("lists the five sections with counts in the tabs and marks the active one", async () => {
    await mountPage("/studies/caffeine/Harder1988/problems");
    const nav = page().get('nav[aria-label="Study sections"]');
    const links = nav.findAll("a");
    expect(links.map((link) => link.get(".section-tab-label").element.firstChild?.textContent)).toEqual([
      "Metadata",
      "Review",
      "Problems",
      "Data",
      "Activity",
    ]);
    expect(links.map((link) => link.find(".section-tab-count").exists() && link.get(".section-tab-count").text())).toEqual([
      false,
      "1",
      "3",
      false,
      false,
    ]);
    // The counts have their meaning for screen readers.
    expect(links[1]!.get(".section-tab-label").text()).toBe("Review, 1 open item");
    expect(links[2]!.get(".section-tab-label").text()).toBe("Problems, 3 problems");
    expect(links[0]!.get(".section-tab-label").text()).toBe("Metadata");
    expect(links[1]!.attributes("href")).toBe("#/studies/caffeine/Harder1988/review");
    expect(links.map((link) => link.attributes("aria-current") ?? null)).toEqual([null, null, "page", null, null]);
    expect(page().get(".study-section h2").text()).toBe("Problems");
    expect(page().get(".study-section h2").classes()).toContain("d-sr-only");

    await links[3]!.trigger("click");
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("data"));
    await flushPromises();
    expect(page().get(".study-section h2").text()).toBe("Data");
  });

  it("shows the sections as one line of tabs with the facts of the study at its end", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    const nav = page().get('nav[aria-label="Study sections"]');
    expect(nav.classes()).toContain("section-tabs");
    expect(nav.findAll("a").map((link) => link.text().replace(/\s+/g, " ").trim())).toEqual([
      "Metadata",
      expect.stringMatching(/^Review/),
      expect.stringMatching(/^Problems/),
      "Data",
      "Activity",
    ]);
    expect(page().get(".section-tabs-facts").text()).toContain("On save");
  });

  it("links the last upload fact to its page on PK-DB, only when that is a web page", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, last_upload: { ...UPLOAD, url: "https://beta.pk-db.com/data/Harder1988" } },
    });
    const link = page().get(".section-tabs-facts a");
    expect(link.attributes("href")).toBe("https://beta.pk-db.com/data/Harder1988");
    expect(link.attributes("rel")).toBe("noopener noreferrer");
  });

  it("shows the tabs as a select below 600 px, with the facts of the study below it", async () => {
    setViewport(375, 800);
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, last_upload: { ...UPLOAD, url: "https://beta.pk-db.com/data/Harder1988" } },
    });
    expect(page().find('nav[aria-label="Study sections"] a').exists()).toBe(false);
    const facts = page().get(".section-tabs-facts");
    expect(facts.text()).toContain("On save: Upload");
    expect(facts.get("a").attributes("href")).toBe("https://beta.pk-db.com/data/Harder1988");
    const order = page().get(".section-tabs-select").element.compareDocumentPosition(facts.element);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const sections = select(wrapper, "Section");
    expect(sections.props("modelValue")).toBe("review");
    expect(sections.props("items")).toContainEqual({ title: "Problems (3)", value: "problems" });
    await sections.setValue("data");
    await vi.waitFor(() => expect(router.currentRoute.value.params.section).toBe("data"));
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

  it("shows a summary line with the title, the PMID, the sync status and the problems", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    const line = page().get(".study-header .study-header-line");
    const title = "Effect of smoking on caffeine clearance and plasma levels in healthy volunteers";
    expect(line.get(".study-title").text()).toBe(title);
    expect(line.get(".study-title").attributes("title")).toBe(title);
    expect(line.get(".fact-pmid a").text()).toBe("2895442");
    expect(line.get(".fact-pmid a").attributes("href")).toBe("https://pubmed.ncbi.nlm.nih.gov/2895442/");
    expect(line.get(".fact-sync").text()).toBe("Workbook open");
    expect(line.findAll(".fact-problems .v-chip").map((chip) => chip.text())).toEqual(["2 errors", "1 warning"]);
  });

  it("labels the review status beside its field, which keeps its name, so that the field fits into the line", async () => {
    const wrapper = await mountPage("/studies/caffeine/Harder1988/review");
    const status = select(wrapper, "Review status");
    expect(status.props("singleLine")).toBe(true);
    const input = status.get("input:not([type=hidden])");
    const label = page().get(".study-header-line label.fact-name");
    expect(label.text()).toBe("Review");
    expect(label.attributes("for")).toBe(input.attributes("id"));
    // The name of the field stays "Review status", from the label inside the field.
    expect(page().get(`#${input.attributes("aria-labelledby")}`).text()).toBe("Review status");
  });

  it("shows identity, chips, title and actions in one line", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    const line = page().get(".study-header-line");
    expect(line.find(".study-identity").exists()).toBe(true);
    expect(line.find(".study-title").exists()).toBe(true);
    expect(line.find(".study-buttons").exists()).toBe(true);
  });

  it("leaves On save and the last upload to the section tabs", async () => {
    await mountPage("/studies/caffeine/Harder1988/review");
    const header = page().get(".study-header");
    expect(header.text()).not.toContain("On save");
    expect(header.text()).not.toContain("Last upload");
    expect(page().get(".section-tabs-facts").text()).toContain("On save: Upload");
  });

  it("shows the last upload without a link unless it is a web page", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, last_upload: { ...UPLOAD, url: "javascript:alert(1)" } },
    });
    const facts = page().get(".section-tabs-facts");
    expect(facts.find("a").exists()).toBe(false);
    expect(facts.text()).toMatch(/Last upload 2026-10-01 \d\d:\d\d/);
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
      [`GET ${HARDER}`]: { ...harder, papers: [] },
    });
    await click("More actions");
    expect(button("Open PDF").attributes("disabled")).toBeDefined();
    expect(page().text()).toContain("No Harder1988.pdf in the folder");
  });

  it("offers Open PDF beyond the upload limits, where the study page lists the PDFs of the folder but no files", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, files: [], sources: [], tables: [] },
      "POST /local/files/open": { ok: true },
    });
    await click("More actions");
    expect(button("Open PDF").attributes("disabled")).toBeUndefined();
    await click("Open PDF");
    expect(posted("/local/files/open")).toEqual([{ study_id: "caffeine/Harder1988", file: "Harder1988.pdf" }]);
  });

  it("opens the PDF named after the study also with a suffix in capitals", async () => {
    const [paper] = harder.papers;
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: { ...harder, papers: [{ ...paper!, file: "Harder1988.PDF" }] },
      "POST /local/files/open": { ok: true },
    });
    await click("More actions");
    await click("Open PDF");
    expect(posted("/local/files/open")).toEqual([{ study_id: "caffeine/Harder1988", file: "Harder1988.PDF" }]);
  });

  it("adds a data table from the add table dialog", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": harderPreview,
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
    expect(posted("/local/studies/tables/preview")).toEqual([
      { study: "caffeine/Harder1988", kind: "outputs", source: "Tab3" },
    ]);
    expect(posted("/local/studies/tables")).toEqual([
      { study: "caffeine/Harder1988", action: "add", kind: "outputs", source: "Tab3" },
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
      "POST /local/studies/tables/preview": harderPreview,
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
    expect(posted("/local/studies/tables")).toEqual([
      { study: "caffeine/Harder1988", action: "add", kind: "raw", source: "Tab4" },
    ]);
    expect(dialog().get(".v-alert").text()).toContain("Close the workbook first");
    // It goes with the next attempt and when the dialog opens again: no close button, which would drop the focus.
    expect(dialog().find(".v-alert__close").exists()).toBe(false);
  });

  it("asks in Add table to set the user when the write needs one", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": harderPreview,
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
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": previewHandler(fixturePreview),
    });
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab 3");
    await flushPromises();
    expect(dialog().text()).toContain(fixturePreview("outputs", "Tab 3")?.issues[0]?.message);
    expect(dialog().find(".table-preview").exists()).toBe(false);
    expect(button("Add").attributes("disabled")).toBeDefined();
    await field("Source").setValue("Tab2");
    await flushPromises();
    expect(dialog().text()).toContain(fixturePreview("outputs", "Tab2")?.issues[0]?.message);
    expect(button("Add").attributes("disabled")).toBeDefined();
  });

  it("shows only the preview of the current source when the answers come late, and Add waits for it", async () => {
    const answers = new Map<unknown, (answer: Response) => void>();
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": (body: Record<string, unknown> | null) =>
        new Promise<Response>((resolve) => answers.set(body?.source, resolve)),
    });
    const sources = () => posted("/local/studies/tables/preview").map((body) => body?.source);
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab2");
    await flushPromises();
    await field("Source").setValue("Tab3");
    await flushPromises();
    // One request at a time: Tab3 is asked for when the answer about Tab2 arrives.
    expect(sources()).toEqual(["Tab2"]);
    expect(button("Add").attributes("disabled")).toBeDefined();

    answers.get("Tab2")?.(json(fixturePreview("outputs", "Tab2")));
    await flushPromises();
    // The answer about Tab2 is stale and never shows.
    expect(dialog().text()).not.toContain(fixturePreview("outputs", "Tab2")?.issues[0]?.message);
    expect(dialog().find(".table-preview").exists()).toBe(false);
    expect(sources()).toEqual(["Tab2", "Tab3"]);
    // Pressing Enter before the answer about Tab3 adds nothing.
    await dialog().get("form").trigger("submit");
    await flushPromises();
    expect(posted("/local/studies/tables")).toEqual([]);
    expect(button("Add").attributes("disabled")).toBeDefined();

    answers.get("Tab3")?.(json(HARDER_PREVIEWS["outputs Tab3"]));
    await flushPromises();
    expect(dialog().get(".table-preview").text()).toContain("outputs_Tab3.tsv");
    expect(button("Add").attributes("disabled")).toBeUndefined();

    /** The marks of the last preview while the next one loads: on the output, never on the field typed in. */
    const updating = () => {
      const source = dialog().get(".v-text-field");
      const facts = dialog().get(".table-preview");
      return {
        messages: source.classes().includes("is-updating"),
        facts: facts.classes().includes("is-updating"),
        factsBusy: facts.attributes("aria-busy"),
        statusBusy: dialog().get('[role="status"]').attributes("aria-busy"),
        fieldBusy: source.element.closest('[aria-busy="true"]') !== null,
      };
    };
    const settled = { messages: false, facts: false, factsBusy: "false", statusBusy: "false", fieldBusy: false };
    expect(updating()).toEqual(settled);
    expect(dialog().get('[role="status"]').text()).toBe("outputs_Tab3 can be added. The image is in the folder.");

    // Another key: Add waits at once; the last preview stays, marked as updating, and is not announced again.
    await field("Source").setValue("Tab34");
    await flushPromises();
    expect(button("Add").attributes("disabled")).toBeDefined();
    expect(updating()).toEqual({ messages: true, facts: true, factsBusy: "true", statusBusy: "true", fieldBusy: false });
    expect(dialog().get(".table-preview").text()).toContain("outputs_Tab3.tsv");
    expect(dialog().get('[role="status"]').text()).toBe("outputs_Tab3 can be added. The image is in the folder.");
    await dialog().get("form").trigger("submit");
    await flushPromises();
    expect(posted("/local/studies/tables")).toEqual([]);

    answers.get("Tab34")?.(
      json({ ...HARDER_PREVIEWS["outputs Tab3"], table: "outputs_Tab34", file: "outputs_Tab34.tsv", image_found: false }),
    );
    await flushPromises();
    expect(updating()).toEqual(settled);
    expect(dialog().get(".table-preview").text()).toContain("outputs_Tab34.tsv");
    expect(dialog().get('[role="status"]').text()).toBe("outputs_Tab34 can be added. The image is missing.");
    await click("Add");
    expect(posted("/local/studies/tables")).toEqual([
      { study: "caffeine/Harder1988", action: "add", kind: "outputs", source: "Tab34" },
    ]);
  });

  it("asks for the preview again when the folder gets the image or the table file", async () => {
    let files = [...harder.files];
    const tab4 = HARDER_PREVIEWS["raw Tab4"]!;
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: () => json({ ...harder, files }),
      // The local server answers for the files in the folder.
      "POST /local/studies/tables/preview": () =>
        json(
          files.includes(tab4.file)
            ? { ...tab4, image_found: true, issues: [issue(`${tab4.file} already exists`, { code: "table_exists" })] }
            : { ...tab4, image_found: files.includes("Harder1988_Tab4.png") },
        ),
    });
    await click("More actions");
    await click("Add table");
    radio("Raw table").click();
    await flushPromises();
    await field("Source").setValue("Tab4");
    await flushPromises();
    expect(dialog().get(".image-state").text()).toBe("Missing");

    files = [...files, "Harder1988_Tab4.png"];
    await useStudyStore().refresh();
    await flushPromises();
    expect(dialog().get(".image-state").text()).toBe("In the folder");
    expect(button("Add").attributes("disabled")).toBeUndefined();

    files = [...files, tab4.file];
    await useStudyStore().refresh();
    await flushPromises();
    expect(dialog().text()).toContain("Harder1988_Tab4.tsv already exists");
    expect(button("Add").attributes("disabled")).toBeDefined();
    expect(posted("/local/studies/tables/preview")).toHaveLength(3);
  });

  it("asks for no preview while Add table is closed, when the folder or the local server changes", async () => {
    let files = [...harder.files];
    let stopped = false;
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: () => (stopped ? Promise.reject(new TypeError("Failed to fetch")) : json({ ...harder, files })),
      "POST /local/studies/tables/preview": harderPreview,
      "POST /local/studies/tables": tablesResult({ table: "outputs_Tab3", workbook_action: "regenerated" }),
    });
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    await click("Add");
    expect(posted("/local/studies/tables/preview")).toHaveLength(1);

    // The added table reaches the folder, and the local server stops and answers again.
    files = [...files, "outputs_Tab3.tsv"];
    await useStudyStore().refresh();
    await flushPromises();
    stopped = true;
    await useStudyStore().refresh();
    await flushPromises();
    stopped = false;
    await useStudyStore().refresh();
    await flushPromises();
    expect(posted("/local/studies/tables/preview")).toHaveLength(1);

    // The dialog opens again with an empty source and asks for nothing until a source is typed.
    await click("More actions");
    await click("Add table");
    await flushPromises();
    expect(field("Source").element.value).toBe("");
    expect(posted("/local/studies/tables/preview")).toHaveLength(1);
  });

  it("asks for a failed preview again once the local server answers again", async () => {
    let stopped = false;
    const stop = () => Promise.reject(new TypeError("Failed to fetch"));
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: () => (stopped ? stop() : json(harder)),
      "POST /local/studies/tables/preview": (body: Record<string, unknown> | null) =>
        stopped ? stop() : harderPreview(body),
    });
    stopped = true;
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    expect(dialog().text()).toContain("Could not reach the local server.");
    expect(button("Add").attributes("disabled")).toBeDefined();

    // The next poll fails too; once a poll succeeds, the preview is asked for again.
    await useStudyStore().refresh();
    await flushPromises();
    stopped = false;
    await useStudyStore().refresh();
    await flushPromises();
    expect(dialog().get(".table-preview").text()).toContain("outputs_Tab3.tsv");
    expect(button("Add").attributes("disabled")).toBeUndefined();
  });

  it("says once why the preview of a new table failed, with what went wrong and Details", async () => {
    const denied = "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Harder1988'";
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": () =>
        json(
          {
            error: "Could not preview the new table of caffeine/Harder1988.",
            code: "file_error",
            detail: denied,
            action: "Preview a table (POST /local/studies/tables/preview)",
            request_id: "3f9c2a71",
            time: "2026-10-12T14:03:11+02:00",
          },
          { status: 400 },
        ),
    });
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    const alert = dialog().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe("Could not preview the new table of caffeine/Harder1988.");
    expect(alert.get(".action-failure-detail").text()).toBe(denied);
    expect(alert.findAll(".failure-summary").map((summary) => summary.text())).toEqual(["Details"]);
    expect(dialog().text().split("Could not preview the new table")).toHaveLength(2);
    // The field is not wrong: its messages keep the hint.
    expect(dialog().find(".v-messages").text()).toBe("A paper table such as Tab3, a figure such as Fig2A, or Text.");
    expect(alert.find(".v-alert__close").exists()).toBe(false);
    expect(button("Add").attributes("disabled")).toBeDefined();
  });

  it("drops a late preview of the study that was open before", async () => {
    const answers: { study: unknown; resolve: (answer: Response) => void }[] = [];
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables/preview": (body: Record<string, unknown> | null) =>
        new Promise<Response>((resolve) => answers.push({ study: body?.study, resolve })),
    });
    await click("More actions");
    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    await router.push("/studies/caffeine/Example/data");
    await flushPromises();
    answers[0]?.resolve(json(HARDER_PREVIEWS["outputs Tab3"]));
    await flushPromises();
    expect(page().text()).not.toContain("Harder1988_Tab3.png");

    await click("Add table");
    await field("Source").setValue("Tab3");
    await flushPromises();
    expect(answers.map((answer) => answer.study)).toEqual(["caffeine/Harder1988", "caffeine/Example"]);
    answers[1]?.resolve(
      json({ ...HARDER_PREVIEWS["outputs Tab3"], image: "Example_Tab3.png", image_found: false }),
    );
    await flushPromises();
    expect(dialog().get(".table-preview").text()).toContain("Example_Tab3.png");
    expect(page().text()).not.toContain("Harder1988_Tab3.png");
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

  it("says once why the study could not be read, with what went wrong and Details", async () => {
    const denied = "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Harder1988/outputs_Tab2.tsv'";
    await mountPage("/studies/caffeine/Harder1988/review", {
      [`GET ${HARDER}`]: () =>
        json(
          {
            error: "Could not read caffeine/Harder1988.",
            code: "file_error",
            detail: denied,
            action: "Read the study (GET /local/studies/caffeine/Harder1988)",
            request_id: "3f9c2a71",
            time: "2026-10-12T14:03:11+02:00",
          },
          { status: 400 },
        ),
    });
    const alert = page().get(".study-load-failure");
    expect(alert.get(".action-failure-text").text()).toBe("Could not read caffeine/Harder1988.");
    expect(alert.get(".action-failure-detail").text()).toBe(denied);
    expect(alert.findAll(".failure-summary").map((summary) => summary.text())).toEqual(["Details"]);
    expect(alert.get(".failure-facts").text()).toContain("3f9c2a71");
    expect(page().text().split("Could not read caffeine/Harder1988.")).toHaveLength(2);
    expect(page().text()).not.toContain("could not be loaded");
    // It goes once the study can be read again: it has no close button.
    expect(alert.find(".v-alert__close").exists()).toBe(false);
  });

  it("shows what failed when Open tables fails, with a link to its entry in the activity", async () => {
    await mountPage("/studies/caffeine/Harder1988/review", {
      "POST /local/studies/tables": () =>
        json(
          {
            error: "Could not open the tables of caffeine/Harder1988.",
            code: "open_failed",
            detail:
              "CalledProcessError: xdg-open exited with status 4\nno method available for opening",
            action: "Open tables (POST /local/studies/tables)",
            request_id: "3f9c2a71",
            time: "2026-10-12T14:03:11+02:00",
            activity_id: "0123456789abcdef0123456789abcdef",
          },
          { status: 500 },
        ),
    });
    await click("Open tables");
    const alert = page().get(".study-alert");
    expect(alert.get(".action-failure-text").text()).toBe(
      "Could not open the tables of caffeine/Harder1988.",
    );
    expect(alert.get(".action-failure-detail").text()).toBe(
      "CalledProcessError: xdg-open exited with status 4\nno method available for opening",
    );
    expect(alert.get(".action-failure-activity").attributes("href")).toBe(
      "#/studies/caffeine/Harder1988/activity?entry=0123456789abcdef0123456789abcdef",
    );
  });
});

describe("the save shortcut", () => {
  const METADATA = "/local/studies/metadata";
  const written = () => json({ revision: "study-2", reference: null, reference_error: null });

  /** Sends the keydown of S with `init` to the focused part of the page; whether the page prevented the default. */
  function press(init: KeyboardEventInit): boolean {
    const event = new KeyboardEvent("keydown", { key: "s", bubbles: true, cancelable: true, ...init });
    (document.activeElement ?? document.body).dispatchEvent(event);
    return event.defaultPrevented;
  }

  it("saves the draft with Ctrl+S or Cmd+S from any section, and keeps the save dialog of the browser closed", async () => {
    await mountPage("/studies/caffeine/Example/review", { [`POST ${METADATA}`]: written });
    useStudyStore().draft.form!.creator = "janekg";
    await flushPromises();
    expect(press({ ctrlKey: true })).toBe(true);
    await flushPromises();
    expect(posted(METADATA)).toHaveLength(1);

    useStudyStore().draft.form!.creator = "mkoenig";
    await flushPromises();
    expect(press({ metaKey: true })).toBe(true);
    await flushPromises();
    expect(posted(METADATA)).toHaveLength(2);
  });

  it("writes nothing without unsaved changes, with Shift or Alt, or while a dialog is open", async () => {
    await mountPage("/studies/caffeine/Example/metadata", { [`POST ${METADATA}`]: written });
    // Without changes the browser's save dialog stays closed too.
    expect(press({ ctrlKey: true })).toBe(true);
    useStudyStore().draft.form!.creator = "janekg";
    await flushPromises();
    expect(press({ ctrlKey: true, shiftKey: true })).toBe(false);
    expect(press({ ctrlKey: true, altKey: true })).toBe(false);
    expect(press({})).toBe(false);

    // The dialog of leaving answers with its own buttons.
    void router.push("/");
    await vi.waitFor(() => expect(buttons("Stay")).toHaveLength(1));
    expect(press({ ctrlKey: true })).toBe(true);
    await flushPromises();
    expect(posted(METADATA)).toEqual([]);
  });

  it("writes once when Ctrl+S repeats while the save runs", async () => {
    let answer: (response: Response) => void = () => {};
    await mountPage("/studies/caffeine/Example/metadata", {
      [`POST ${METADATA}`]: (() => new Promise<Response>((resolve) => (answer = resolve))) satisfies Handler,
    });
    useStudyStore().draft.form!.creator = "janekg";
    await flushPromises();
    press({ ctrlKey: true });
    press({ ctrlKey: true, repeat: true });
    await flushPromises();
    press({ ctrlKey: true });
    await flushPromises();
    expect(posted(METADATA)).toHaveLength(1);
    answer(written());
    await flushPromises();
    expect(useStudyStore().draft.dirty).toBe(false);
  });

  it("leaves Ctrl+S to the browser once the study page closed", async () => {
    await mountPage("/studies/caffeine/Example/metadata");
    await router.push("/");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("Overview");
    expect(press({ ctrlKey: true })).toBe(false);
  });
});

describe("the unsaved banner", () => {
  /** The banner stands after the tabs and the live region of its notices, before the section. */
  const placed = () => page().find(".section-tabs-line + .unsaved-banner-notice + .unsaved-banner + .study-section");

  // Its place in Data is a test of curation-data-section.spec.ts, which serves the tables.
  it("stands under the section tabs in Metadata and Review while study.json has unsaved changes", async () => {
    await mountPage("/studies/caffeine/Example/metadata");
    expect(page().find(".unsaved-banner").exists()).toBe(false);
    useStudyStore().draft.form!.provenance.source_key = "pkdb.edited";
    await flushPromises();
    for (const section of ["metadata", "review"]) {
      await router.push(`/studies/caffeine/Example/${section}`);
      await flushPromises();
      expect(placed().exists(), section).toBe(true);
      expect(page().get(".unsaved-banner").text()).toContain("Unsaved changes to study.json: Source key");
      expect(page().get(".unsaved-banner").classes()).toContain("unsaved-banner--dirty");
    }
  });

  it("names the changed fields by their labels, three of them and how many more", async () => {
    await mountPage("/studies/caffeine/Example/metadata");
    const form = useStudyStore().draft.form!;
    form.provenance.source_key = "pkdb.edited";
    form.notes.outputs.descriptions.push("Read from Table 2.");
    await flushPromises();
    expect(page().get(".unsaved-banner-text").text()).toBe(
      "Unsaved changes to study.json: Source key, Notes of the outputs",
    );
    form.reference.doi = "10.1000/xyz";
    form.licence = "closed";
    form.notes.outputs.comments.push({ user: "curator", text: "Check the unit." });
    form.notes.subjects.descriptions.push("Healthy adults.");
    await flushPromises();
    expect(page().get(".unsaved-banner-text").text()).toBe(
      "Unsaved changes to study.json: DOI, Licence, Source key and 2 more",
    );
  });

  it("says New study.json for a new study.json whose fields are all still empty", async () => {
    await mountPage("/studies/caffeine/Example/metadata");
    const draft = useStudyStore().draft;
    draft.startNew(toForm({}, noteKinds(useStudyStore().detail!)));
    await flushPromises();
    expect(draft.changed).toEqual([]);
    expect(page().get(".unsaved-banner-text").text()).toBe("Unsaved changes to study.json: New study.json");
    draft.form!.creator = "janekg";
    await flushPromises();
    expect(page().get(".unsaved-banner-text").text()).toBe("Unsaved changes to study.json: Creator");
  });

  it("shows the shortcut beside Save and names it for assistive technology", async () => {
    await mountPage("/studies/caffeine/Example/metadata");
    useStudyStore().draft.form!.creator = "janekg";
    await flushPromises();
    expect(page().get(".unsaved-banner-key").text()).toBe("Ctrl+S");
    expect(button("Save").attributes("aria-keyshortcuts")).toBe("Control+S");
  });
});
