import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { defineComponent, h } from "vue";
import ActionFailureAlert from "../../src/curation-app/components/ActionFailureAlert.vue";
import DataNavigator from "../../src/curation-app/components/DataNavigator.vue";
import ProblemItem from "../../src/curation-app/components/ProblemItem.vue";
import ReviewItemDetail from "../../src/curation-app/components/ReviewItemDetail.vue";
import RowsPane from "../../src/curation-app/components/RowsPane.vue";
import SectionTabs from "../../src/curation-app/components/SectionTabs.vue";
import SourceOverlay from "../../src/curation-app/components/SourceOverlay.vue";
import SourcePane from "../../src/curation-app/components/SourcePane.vue";
import StudyHeader from "../../src/curation-app/components/StudyHeader.vue";
import StudyTable from "../../src/curation-app/components/StudyTable.vue";
import TableGrid from "../../src/curation-app/components/TableGrid.vue";
import TargetView from "../../src/curation-app/components/TargetView.vue";
import DataSection from "../../src/curation-app/sections/DataSection.vue";
import ProblemsSection from "../../src/curation-app/sections/ProblemsSection.vue";
import ReviewSection from "../../src/curation-app/sections/ReviewSection.vue";
import StudyFilters from "../../src/study-views/components/StudyFilters.vue";
import type { StudyCapabilities } from "../../src/study-views/context";
import { ALL_ROWS } from "../../src/study-views/data";
import { actionFailure } from "../../src/study-views/study";
import type { Problem, SourceView, StudyDetail, TableResponse } from "../../src/study-views/types";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";
import {
  beyondLimitsDetail,
  paperFile,
  reviewItem,
  roster,
  sourceSummary,
  studyDetail,
  studyRow,
} from "../unit/curation-fixtures";
import { setViewport } from "./curation-dom";
import { CURATOR, EVERYTHING, memoryData, mountViews, PUBLIC, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => {
  setActivePinia(undefined);
  setViewport(1440);
});

const ERROR: Problem = {
  code: "unit_unknown",
  severity: "error",
  message: "Unknown unit mg/dl.",
  source: { file: "outputs_Tab2.tsv", row: 1, header: "unit" },
  acknowledgeable: false,
};
const WARNING: Problem = {
  code: "value_range",
  severity: "warning",
  message: "The mean is high.",
  source: { file: "outputs_Tab2.tsv", row: 1, header: "mean" },
  acknowledgeable: true,
};
const ITEM = reviewItem({ id: "01A", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } });
const DETAIL: StudyDetail = studyDetail({
  status: "validating",
  counts: { errors: 1, warnings: 1 },
  problems: [ERROR, WARNING],
  issue: { number: 2158, state: null, labels: [], assignees: [], url: "https://github.com/matthiaskoenig/pkdb_data/issues/2158" },
  review: { revision: "review-1", value: { status: "in_review", reviewers: [], items: [ITEM] }, issues: [] },
  targets: { "01A": { lines: [1], series: null, total: 1 } },
  papers: [paperFile("Example.pdf")],
  summary: { ...studyRow().summary, release: { pkdb_id: "PKDB00198", date: "2026-09-28" } },
});
const OUTPUTS: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label", "unit", "mean"],
  rows: [{ line: 1, cells: ["Example", "Tab2", "caf_cl", "mg/dl", "9"] }],
};
const SUBJECTS: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
};

function view(source: string, changes: Partial<SourceView> = {}): SourceView {
  return {
    source,
    image: null,
    image_url: null,
    image_size: null,
    raw_grid: null,
    digitization: null,
    mapped: [],
    overlay: [],
    unmatched: [],
    layout: "side_by_side",
    points: [],
    series: [],
    log_x: false,
    log_y: false,
    ...changes,
  };
}
const TAB2 = view("Tab2", {
  image: "Example_Tab2.png",
  image_url: "/files/Example_Tab2.png",
  image_size: [640, 220],
  raw_grid: [["", "Caffeine 150 mg"], ["CL [ml/min/kg]", "1.20"]],
  mapped: [{ file: "outputs_Tab2.tsv", kind: "outputs", header: OUTPUTS.header, rows: [[1, OUTPUTS.rows[0]!.cells]], shared: false }],
});

/** A figure with a digitization that the curation app draws on its image. */
const FIG1: SourceView = { ...(sourceFixture as unknown as SourceView), source: "Fig1" };
/** A reader of the curation of a study without its files, which no page of the website has yet. */
const CURATION_ONLY: StudyCapabilities = { edit: false, curation: true, files: false, jobs: false };

/** The context of a page that shows DETAIL to a reader with `capabilities`. */
function context(capabilities: StudyCapabilities) {
  return viewsContext({
    capabilities,
    data: memoryData({
      detail: DETAIL,
      tables: { "outputs_Tab2.tsv": OUTPUTS, "subjects.tsv": SUBJECTS },
      sources: { Tab2: TAB2, Fig1: FIG1 },
      rows: [studyRow()],
      profiles: roster(),
      repository: "matthiaskoenig/pkdb_data",
    }),
  });
}

async function routerAt(path: string) {
  const router = websiteRouter();
  await router.push(path);
  return router;
}

/** The names of the controls that the keyboard reaches in `wrapper`. */
function reachable(wrapper: VueWrapper): string[] {
  return wrapper
    .findAll("a[href], button, input, select, textarea, [tabindex]")
    .filter((element) => element.attributes("disabled") === undefined && element.attributes("tabindex") !== "-1")
    .map((element) => (element.attributes("aria-label") ?? element.text()).replace(/\s+/g, " ").trim());
}

/** The names of the controls of writes and local actions. */
const EDIT_ACTIONS = [
  "Open sheet",
  "Sync",
  "Add table",
  "Open tables",
  "Open in tables",
  "Open in PDF program",
  "Acknowledge",
  "Validate",
  "Upload",
  "Reply",
  "Resolve",
  "Dismiss",
  "Reopen",
  "New item",
  "More actions",
];

/** Slots as the curation app fills them, to prove that a page without `edit` does not show them. */
const PAGE_SLOTS = {
  actions: () => h("button", { type: "button" }, "Validate"),
  after: () => h("p", { class: "page-after" }, "Upload queued."),
  toolbar: () => h("button", { type: "button" }, "Open sheet"),
  status: () => h("p", { class: "page-status" }, "The workbook opened."),
  rows: () => h("button", { type: "button" }, "Sync"),
  tools: () => h("button", { type: "button" }, "New item"),
  detail: () => h("p", { class: "page-detail" }, "Reply posted."),
  dialogs: () => h("p", { class: "page-dialogs" }, "Dialogs"),
  "group-actions": () => h("button", { type: "button" }, "Open tables"),
};

describe("the sections of a study", () => {
  for (const [capabilities, labels] of [
    [PUBLIC, ["Metadata", "Data"]],
    [CURATOR, ["Metadata", "Data", "Problems", "Review"]],
    [EVERYTHING, ["Metadata", "Data", "Problems", "Review", "Activity"]],
  ] as const) {
    it(`are ${labels.join(", ")} for ${JSON.stringify(capabilities)}`, async () => {
      const wrapper = mountViews(SectionTabs, {
        context: context(capabilities),
        props: { substance: "caffeine", name: "Example", active: "data", counts: { review: 1, problems: 2 }, unsaved: [] },
        plugins: [await routerAt("/data/caffeine/Example/data")],
      });
      expect(wrapper.findAll(".section-tab-label").map((label) => label.attributes("data-label"))).toEqual([...labels]);
    });
  }
});

describe("the study header", () => {
  it("shows the public the study and its release, and nothing of its curation or jobs", () => {
    const wrapper = mountViews(StudyHeader, { context: context(PUBLIC), props: { detail: DETAIL }, slots: PAGE_SLOTS });
    expect(wrapper.get(".study-identity").text()).toBe("caffeine/Example");
    expect(wrapper.find(".release-chip").exists()).toBe(true);
    expect(wrapper.find(".fact-pmid").exists()).toBe(true);
    for (const part of [".issue-chip", ".fact-sync", ".fact-problems", ".fact-activity", ".fact-review", ".page-after"])
      expect(wrapper.find(part).exists(), part).toBe(false);
    expect(reachable(wrapper)).toEqual(["3678553"]);
  });

  it("shows a curator of the website the issue, the review status, the sync and the problems, without actions", () => {
    const wrapper = mountViews(StudyHeader, { context: context(CURATOR), props: { detail: DETAIL }, slots: PAGE_SLOTS });
    expect(wrapper.get(".issue-chip").text()).toBe("#2158");
    expect(wrapper.get(".fact-review").text()).toBe("In review");
    expect(wrapper.get(".fact-sync").text()).toBe("In sync");
    expect(wrapper.findAll(".fact-problems .v-chip").map((chip) => chip.text())).toEqual(["1 error", "1 warning"]);
    expect(wrapper.find(".fact-activity").exists()).toBe(false);
    expect(wrapper.find(".page-after").exists()).toBe(false);
    expect(reachable(wrapper).filter((name) => EDIT_ACTIONS.includes(name))).toEqual([]);
  });

  it("shows the curation app what the study is doing and its actions instead of the status chip", () => {
    const wrapper = mountViews(StudyHeader, { context: context(EVERYTHING), props: { detail: DETAIL }, slots: PAGE_SLOTS });
    expect(wrapper.get(".fact-activity").text()).toBe("Validating");
    expect(wrapper.find(".fact-review").exists()).toBe(false);
    expect(wrapper.find(".page-after").exists()).toBe(true);
    expect(reachable(wrapper)).toContain("Validate");
  });
});

describe("the navigator of the Data section", () => {
  const props = { detail: DETAIL, source: "Tab2", file: "outputs_Tab2.tsv" };

  it("shows the public no paper, no raw extractions, no thumbnails and no counts", () => {
    const wrapper = mountViews(DataNavigator, { context: context(PUBLIC), props });
    expect(wrapper.find(".nav-paper").exists()).toBe(false);
    expect(wrapper.find("img.nav-thumb").exists()).toBe(false);
    expect(wrapper.findAll(".nav-group-heading").map((heading) => heading.text())).not.toContain("Raw extractions");
    expect(wrapper.find(".nav-count").exists()).toBe(false);
  });

  it("shows a curator the paper, the raw extractions, the thumbnails and the counts", () => {
    const wrapper = mountViews(DataNavigator, { context: context(CURATOR), props });
    expect(wrapper.find(".nav-paper").exists()).toBe(true);
    expect(wrapper.find("img.nav-thumb").exists()).toBe(true);
    expect(wrapper.findAll(".nav-group-heading").map((heading) => heading.text())).toContain("Raw extractions");
    expect(wrapper.find(".nav-count").exists()).toBe(true);
  });
});

describe("the rows pane", () => {
  const props = {
    detail: DETAIL,
    file: "outputs_Tab2.tsv",
    table: OUTPUTS,
    rowsDetail: DETAIL,
    loading: false,
    error: null,
    focus: null,
    filter: ALL_ROWS,
    hideEmpty: false,
  };

  it("marks no review items and outlines no problems for the public", () => {
    const wrapper = mountViews(RowsPane, { context: context(PUBLIC), props });
    expect(wrapper.find(".rows-pane-notes").exists()).toBe(false);
    const grid = wrapper.findComponent(TableGrid);
    expect((grid.props("highlightLines") as Set<number>).size).toBe(0);
    expect((grid.props("issueCells") as Map<unknown, unknown>).size).toBe(0);
  });

  it("marks the review items and outlines the problems for a curator", () => {
    const wrapper = mountViews(RowsPane, { context: context(CURATOR), props });
    expect(wrapper.get(".rows-pane-notes").text()).toContain("Open review items target 1 row.");
    expect(wrapper.get(".rows-pane-notes").text()).toContain("2 problems are outlined.");
  });
});

describe("the source pane", () => {
  const props = {
    summary: sourceSummary({ source: "Tab2", image: "Example_Tab2.png", raw: "Example_Tab2.tsv", raw_kind: "table", tables: ["outputs_Tab2.tsv"] }),
    view: TAB2,
    loading: false,
    error: null,
    selected: null,
  };

  it("shows the public neither the image nor the raw extraction of a table, and says so, and no problems", async () => {
    const wrapper = mountViews(SourcePane, { context: context(PUBLIC), props, plugins: [await routerAt("/data/caffeine/Example/data")] });
    await flushPromises();
    for (const part of ["img.source-image", ".zoom", ".source-raw", ".source-problems"])
      expect(wrapper.find(part).exists(), part).toBe(false);
    expect(wrapper.get(".source-files-note").text()).toBe("The image and the raw extraction of this table are not public.");
  });

  it("shows a curator the image, the raw extraction and the problems, and a missing image without the hints of the curation app", async () => {
    const router = await routerAt("/data/caffeine/Example/data");
    const wrapper = mountViews(SourcePane, { context: context(CURATOR), props, plugins: [router] });
    await flushPromises();
    for (const part of ["img.source-image", ".source-raw", ".source-problems"])
      expect(wrapper.find(part).exists(), part).toBe(true);
    const missing = mountViews(SourcePane, {
      context: context(CURATOR),
      props: { ...props, summary: { ...props.summary, image: null, image_url: null, missing_image: "Example_Tab2.png" }, view: { ...TAB2, image: null, image_url: null } },
      plugins: [router],
    });
    await flushPromises();
    expect(missing.get(".pane-missing-text").text()).toBe("No image.");
  });
});

describe("a digitized figure without the files", () => {
  /** The overlays of `wrapper`: their mode and whether their view has an image. */
  const overlays = (wrapper: VueWrapper) =>
    wrapper.findAllComponents(SourceOverlay).map((overlay) => ({
      mode: overlay.props("mode") as string | undefined,
      image: (overlay.props("view") as SourceView).image_url !== null,
    }));

  it("is a plot of every mapped series in the source pane, not the digitization on the image", async () => {
    const summary = sourceSummary({ source: "Fig1", kind: "figure", image: "Example_Fig1.png", tables: ["timecourses_Fig1.tsv"] });
    const props = { summary, view: FIG1, loading: false, error: null, selected: null };
    const router = await routerAt("/data/caffeine/Example/data");
    const curator = mountViews(SourcePane, { context: context(CURATOR), props, plugins: [router], stubs: { SourceOverlay: true } });
    expect(overlays(curator)).toEqual([{ mode: "overlay", image: true }]);
    const reader = mountViews(SourcePane, { context: context(PUBLIC), props, plugins: [router], stubs: { SourceOverlay: true } });
    expect(overlays(reader)).toEqual([{ mode: "plot", image: false }]);
    expect(reader.findAll(".pane-heading").map((heading) => heading.text())).toEqual(["Plot of the mapped rows"]);
  });

  it("is a plot of the series of a review item, not the digitization on the image", async () => {
    const item = reviewItem({ id: "01B", target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_100mg" } } });
    const target = { "01B": { lines: null, series: { source: "Fig1", series: "caf_plasma_100mg" }, total: null } };
    const shown = async (capabilities: StudyCapabilities) => {
      const wrapper = mountViews(TargetView, {
        context: viewsContext({
          capabilities,
          data: memoryData({ detail: studyDetail({ targets: target }), sources: { Fig1: FIG1 } }),
        }),
        props: { item },
        plugins: [await routerAt("/data/caffeine/Example/review")],
        stubs: { SourceOverlay: true },
      });
      await flushPromises();
      return overlays(wrapper);
    };
    expect(await shown(CURATOR)).toEqual([{ mode: undefined, image: true }]);
    expect(await shown(CURATION_ONLY)).toEqual([{ mode: undefined, image: false }]);
  });
});

describe("a review item on a raw table", () => {
  it("shows its table only with the files", async () => {
    const raw: TableResponse = { file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["CL", "1.20"] }] };
    const item = reviewItem({ id: "01C", target: { file: "Example_Tab2.tsv" } });
    const target = async (capabilities: StudyCapabilities) => {
      const wrapper = mountViews(TargetView, {
        context: viewsContext({
          capabilities,
          data: memoryData({ detail: studyDetail(), tables: { "Example_Tab2.tsv": raw } }),
        }),
        props: { item },
        plugins: [await routerAt("/data/caffeine/Example/review")],
      });
      await flushPromises();
      return wrapper.find(".review-target");
    };
    expect((await target(CURATOR)).text()).toContain("This is a raw table.");
    expect((await target(CURATION_ONLY)).exists()).toBe(false);
  });
});

describe("the actions on a problem and on a review item", () => {
  it("are links only for a curator of the website", async () => {
    const wrapper = mountViews(ProblemItem, {
      context: context(CURATOR),
      props: {
        issue: WARNING,
        study: "caffeine/Example",
        idBase: "problem",
        showable: true,
        pending: false,
        automatic: false,
        disabled: false,
        validating: false,
        opensTables: true,
      },
      plugins: [await routerAt("/data/caffeine/Example/problems")],
    });
    expect(reachable(wrapper)).toEqual(["Show in table"]);
  });

  it("show the thread of an item without the reply and its actions for a curator of the website", () => {
    const wrapper = mountViews(ReviewItemDetail, {
      context: context(CURATOR),
      props: { item: ITEM, profiles: new Map(), busy: null, writable: true, blocked: false, canReopen: true, draft: "" },
    });
    expect(wrapper.text()).toContain("No replies yet.");
    expect(wrapper.find(".review-reply").exists()).toBe(false);
    expect(wrapper.findAll("button")).toHaveLength(0);
  });
});

describe("a failed action", () => {
  const details = {
    status: 500,
    code: "open_failed",
    detail: "CalledProcessError: exit 4",
    action: "Open tables (POST /local/studies/tables)",
    requestId: "3f9c2a71",
    time: "2026-10-12T10:00:00+02:00",
    traceback: null,
    activityId: "01JA",
  };
  const failure = actionFailure("The sync found problems.", [], { section: "problems", label: "Show the problems" }, details);
  /** Details that render their links, as FailureDetails.vue does. */
  const Details = defineComponent({ setup: (_, { slots }) => () => h("div", { class: "stub-details" }, slots.default?.()) });

  for (const [capabilities, link, activity] of [
    [PUBLIC, false, false],
    [CURATOR, true, false],
    [EVERYTHING, true, true],
  ] as const) {
    it(`links to Problems: ${link}, to Activity: ${activity}, for ${JSON.stringify(capabilities)}`, async () => {
      const wrapper = mountViews(ActionFailureAlert, {
        context: { ...context(capabilities), parts: { failureDetails: Details } },
        props: { failure, study: "caffeine/Example" },
        plugins: [await routerAt("/data/caffeine/Example/data")],
      });
      expect(wrapper.find(".action-failure-link").exists()).toBe(link);
      expect(wrapper.find(".action-failure-activity").exists()).toBe(activity);
    });
  }
});

describe("the study list", () => {
  const headers = (wrapper: VueWrapper) => wrapper.findAll("thead th").map((cell) => cell.text());

  for (const [capabilities, columns, select] of [
    [PUBLIC, ["Study", "Release", "Curators"], false],
    [CURATOR, ["Study", "Release", "Issue", "Curators", "Review", "Open items", "Problems", "Sync"], false],
    [EVERYTHING, ["", "Study", "Release", "Issue", "Curators", "Review", "Open items", "Problems", "Sync", "Last upload"], true],
  ] as const) {
    it(`has the columns ${columns.join(", ")} for ${JSON.stringify(capabilities)}`, async () => {
      const wrapper = mountViews(StudyTable, {
        context: context(capabilities),
        props: { rows: [studyRow()], sort: { key: "study", descending: false } },
        plugins: [await routerAt("/studies")],
      });
      await flushPromises();
      expect(headers(wrapper)).toEqual([...columns]);
      expect(wrapper.find("tr.study-row .cell-select").exists()).toBe(select);
      expect(wrapper.get("tr.study-row").findAll("td")).toHaveLength(columns.length);
    });
  }

  it("has status chips only with the curation", () => {
    const props = { counts: { all: 1, attention: 0, draft: 1, in_review: 0, approved: 0 }, shown: 1, me: null, search: "", substance: "", curator: "", chip: "all" };
    expect(mountViews(StudyFilters, { context: context(PUBLIC), props }).find(".overview-chips").exists()).toBe(false);
    expect(mountViews(StudyFilters, { context: context(CURATOR), props }).find(".overview-chips").exists()).toBe(true);
  });
});

describe("the Data section without the files", () => {
  async function mountData(query: string) {
    const wrapper = mountViews(DataSection, {
      context: context(PUBLIC),
      plugins: [await routerAt(`/data/caffeine/Example/data?${query}`)],
      slots: PAGE_SLOTS,
      stubs: { SourceOverlay: true, PaperViewer: true },
      attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
  }

  it("shows no paper for a link to the paper, but the table and its source", async () => {
    const wrapper = await mountData("source=paper&file=outputs_Tab2.tsv");
    expect(wrapper.find(".paper-pane").exists()).toBe(false);
    expect(wrapper.get(".source-pane").attributes("aria-label")).toBe("Source Tab2");
    expect(wrapper.get(".rows-pane").attributes("aria-label")).toBe("Table outputs_Tab2.tsv");
  });

  it("shows the default table for a link to a raw table", async () => {
    const wrapper = await mountData("source=Tab2&file=Example_Tab2.tsv");
    expect(wrapper.get(".rows-pane").attributes("aria-label")).toBe("Table outputs_Tab2.tsv");
  });

  it("shows nothing that its page puts into its slots", async () => {
    const wrapper = await mountData("file=outputs_Tab2.tsv");
    for (const part of [".page-status", ".page-dialogs"]) expect(wrapper.find(part).exists(), part).toBe(false);
    expect(reachable(wrapper).filter((name) => EDIT_ACTIONS.includes(name))).toEqual([]);
  });
});

describe("the notes of the Data section", () => {
  async function note(detail: StudyDetail, capabilities: StudyCapabilities) {
    const wrapper = mountViews(DataSection, {
      context: viewsContext({ capabilities, data: memoryData({ detail }) }),
      plugins: [await routerAt("/data/caffeine/Example/data")],
      stubs: { SourceOverlay: true, PaperViewer: true },
    });
    await flushPromises();
    return wrapper.findAll(".data-empty").map((element) => element.text().replace(/\s+/g, " "));
  }

  it("link to Problems beyond the upload limits only with the curation", async () => {
    const limited = "This study is beyond the upload limits, so the app cannot show its sources and tables.";
    expect(await note(beyondLimitsDetail(), CURATOR)).toEqual([`${limited} See Problems.`]);
    expect(await note(beyondLimitsDetail(), PUBLIC)).toEqual([limited]);
  });

  it("say how to add a table only with edit", async () => {
    const empty = studyDetail({ tables: [] });
    expect(await note(empty, EVERYTHING)).toContain("The study has no tables yet. Add table adds a sheet to the workbook.");
    expect(await note(empty, CURATOR)).toContain("The study has no tables yet.");
  });
});

describe("a curator of the website (Review Focus 3)", () => {
  for (const [component, section] of [
    [DataSection, "data"],
    [ProblemsSection, "problems"],
    [ReviewSection, "review"],
  ] as const) {
    it(`reaches no write and no local action in the section ${section}`, async () => {
      const wrapper = mountViews(component, {
        context: context(CURATOR),
        plugins: [await routerAt(`/data/caffeine/Example/${section}`)],
        slots: PAGE_SLOTS,
        stubs: { SourceOverlay: true, PaperViewer: true },
        attachTo: document.body,
      });
      await flushPromises();
      expect(reachable(wrapper).filter((name) => EDIT_ACTIONS.includes(name))).toEqual([]);
      expect(reachable(wrapper).length).toBeGreaterThan(0);
    });
  }
});
