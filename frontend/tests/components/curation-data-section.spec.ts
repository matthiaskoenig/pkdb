import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import { RouterView, type Router } from "vue-router";
import { VSelect } from "vuetify/components";
import type {
  Problem,
  SourcePoint,
  SourceView,
  StudyDetail,
  StudyMetadata,
  SyncState,
  TableResponse,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import {
  beyondLimitsDetail,
  conflictAnswer,
  FILE_DELETED_CONFLICT,
  json,
  OUTPUTS_COLUMNS,
  paperFile,
  REGION_CONFLICT,
  REGION_ISSUE,
  reviewItem,
  ROWS_REMOVED_CONFLICT,
  snapshot,
  sourceSummary,
  studyDetail,
  studyMetadata,
  SUBJECTS_COLUMNS,
  tableEntry,
} from "../unit/curation-fixtures";
import {
  button,
  buttons,
  click,
  field,
  labeled,
  messagesOf,
  page,
  radio,
  scrollLayout,
  serveApi,
  setViewport,
  textArea,
  type Handler,
  type ServedRequest,
} from "./curation-dom";
import { paperViewer, PaperViewerStub } from "./curation-paper-stub";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const TABLES = "/local/studies/tables";
const SECTION = "/studies/caffeine/Example/data";
const METADATA = "/local/studies/metadata";

const OUTPUTS_HEADER = ["study", "source", "label", "measurement", "mean", "sd", "unit", "comment"];
const TIMECOURSES_HEADER = ["study", "source", "label", "time", "time_unit", "mean", "unit", "error_bar"];

// The views of the sources

const table: SourceView = {
  source: "Tab2",
  image: "Example_Tab2.png",
  image_url: `${EXAMPLE}/files/Example_Tab2.png`,
  image_size: [640, 220],
  raw_grid: [
    ["", "Caffeine 150 mg", "Caffeine 300 mg"],
    ["CL [ml/min/kg]", "1.20 ± 0.3", "1.10 ± 0.2"],
    ["t1/2 [h]", "007", "4.8ᵃ"],
  ],
  digitization: null,
  mapped: [
    {
      file: "outputs_Tab2.tsv",
      kind: "outputs",
      header: OUTPUTS_HEADER,
      rows: [
        [2, ["Example", "Tab2", "caf_cl", "clearance", "1.2", "0.3", "ml/min/kg", ""]],
        [3, ["Example", "Tab2", "caf_thalf", "thalf", "4.8", "", "h", ""]],
      ],
      shared: false,
    },
    {
      file: "subjects.tsv",
      kind: "subjects",
      header: ["study", "name", "source"],
      rows: [
        [2, ["Example", "all", "Tab2"]],
        [4, ["Example", "women", "Tab2"]],
      ],
      shared: true,
    },
  ],
  overlay: [],
  unmatched: [],
  layout: "side_by_side",
  points: [],
  series: [],
};

const timecourses = {
  file: "timecourses_Fig1.tsv",
  kind: "timecourses",
  header: TIMECOURSES_HEADER,
  rows: [
    [2, ["Example", "Fig1", "caf_plasma_D150", "0.5", "h", "2.419", "µg/ml", "3.051"]],
    [3, ["Example", "Fig1", "caf_plasma_D75", "0.5", "h", "1.2", "µg/ml", ""]],
  ],
  shared: false,
} satisfies SourceView["mapped"][number];

function points(file: string): SourcePoint[] {
  const base = { kind: "timecourses", file, x: 0.5, x_text: "0.5" } as const;
  return [
    { ...base, series: "caf_plasma_D150", line: 2, y: 2.419, y_text: "2.419", error_bar: 3.051 },
    { ...base, series: "caf_plasma_D75", line: 3, y: 1.2, y_text: "1.2", error_bar: null },
  ];
}

const SERIES: SourceView["series"] = [
  { name: "caf_plasma_D150", color: "#2a78d6", dark_color: "#3987e5", x_label: "time (h)", y_label: "c (µg/ml)" },
  { name: "caf_plasma_D75", color: "#d65a24", dark_color: "#d95926", x_label: "time (h)", y_label: "c (µg/ml)" },
];

const digitized: SourceView = {
  source: "Fig1",
  image: "Example_Fig1.png",
  image_url: `${EXAMPLE}/files/Example_Fig1.png`,
  image_size: [800, 600],
  raw_grid: null,
  digitization: "Example_Fig1.wpd.json",
  mapped: [timecourses],
  overlay: [
    {
      series: "caf_plasma_D150",
      role: "raw",
      px: 120,
      py: 300,
      x: 0.5,
      y: 2.42,
      file: "Example_Fig1.wpd.json",
      line: null,
      error_px: null,
      x_text: "0.5",
      y_text: "2.42",
      error_bar_end: false,
    },
    {
      series: "caf_plasma_D150",
      role: "mapped",
      px: 120,
      py: 301,
      x: 0.5,
      y: 2.419,
      file: "timecourses_Fig1.tsv",
      line: 2,
      error_px: [120, 250],
      x_text: "0.5",
      y_text: "2.419",
      error_bar_end: false,
    },
  ],
  unmatched: ["caf_plasma_D75"],
  layout: "overlay",
  points: points("timecourses_Fig1.tsv"),
  series: SERIES,
};

const plain: SourceView = {
  source: "Fig2",
  image: "Example_Fig2.png",
  image_url: `${EXAMPLE}/files/Example_Fig2.png`,
  image_size: [500, 400],
  raw_grid: null,
  digitization: null,
  mapped: [{ ...timecourses, file: "timecourses_Fig2.tsv" }],
  overlay: [],
  unmatched: ["caf_plasma_D150", "caf_plasma_D75"],
  layout: "side_by_side",
  points: points("timecourses_Fig2.tsv"),
  series: SERIES,
};

const missing: SourceView = {
  source: "Tab3",
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
};

// The rows of the tables

const outputs: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: OUTPUTS_HEADER,
  rows: [
    { line: 2, cells: ["Example", "Tab2", "caf_cl", "clearance", "1.2", "0.3", "ml/min/kg", ""] },
    { line: 3, cells: ["Example", "Tab2", "caf_thalf", "thalf", "4.8", "", "h", ""] },
    { line: 4, cells: ["Example", "Tab2", "caf_vd", "vd", "0.7", "", "l/kg", ""] },
  ],
};
/** A shared table: its rows name their source, and line 5 one that the study does not have. */
const subjects: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [
    { line: 2, cells: ["Example", "all", "Tab2"] },
    { line: 3, cells: ["Example", "men", "Fig1"] },
    { line: 4, cells: ["Example", "women", "Tab2"] },
    { line: 5, cells: ["Example", "old", "Fig9"] },
  ],
};
const figureRows: TableResponse = {
  file: "timecourses_Fig1.tsv",
  kind: "table",
  header: TIMECOURSES_HEADER,
  rows: timecourses.rows.map(([line, cells]) => ({ line, cells })),
};
const raw: TableResponse = {
  file: "Example_Tab2.tsv",
  kind: "raw",
  rows: [
    { line: 1, cells: ["", "Caffeine 150 mg"] },
    { line: 2, cells: ["CL [ml/min/kg]", "1.20 ± 0.3"] },
  ],
};

function empty(file: string): TableResponse {
  return { file, kind: "table", header: ["study", "source", "label"], rows: [] };
}

/** The tables of the real conflicts, whose rows have the columns that the library writes. */
const CONFLICT_TABLES = {
  [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: {
    file: "outputs_Tab2.tsv",
    kind: "table",
    header: OUTPUTS_COLUMNS,
    rows: [],
  },
  [`GET ${EXAMPLE}/tables/subjects.tsv`]: { file: "subjects.tsv", kind: "table", header: SUBJECTS_COLUMNS, rows: [] },
} satisfies Record<string, TableResponse>;

const synced: TablesResult = { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [] };

// The study

/** A problem of a row of a table file. */
function problemAt(file: string, row: number): Problem {
  return { code: "c", severity: "error", message: "m", source: { file, row }, acknowledgeable: false };
}

/** A problem of a cell of outputs_Tab2.tsv. */
function problem(code: string, row: number, header: string, severity: ValidationIssue["severity"] = "error"): Problem {
  return {
    code,
    severity,
    acknowledgeable: severity === "warning",
    message: `${code} at line ${row}`,
    source: { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row, header },
  };
}

/** The study with a digitized figure, a figure without digitization and two paper tables. */
function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  const base = studyDetail();
  return studyDetail({
    sources: [
      sourceSummary({
        source: "Fig1",
        kind: "figure",
        image: "Example_Fig1.png",
        raw: "Example_Fig1.wpd.json",
        raw_kind: "digitization",
        tables: ["timecourses_Fig1.tsv"],
      }),
      sourceSummary({
        source: "Fig2",
        kind: "figure",
        image: "Example_Fig2.png",
        tables: ["timecourses_Fig2.tsv"],
        missing_raw: "Example_Fig2.wpd.json",
      }),
      sourceSummary({
        source: "Tab2",
        image: "Example_Tab2.png",
        raw: "Example_Tab2.tsv",
        raw_kind: "table",
        tables: ["outputs_Tab2.tsv", "subjects.tsv"],
      }),
      // The library names the files that a source lacks.
      sourceSummary({ source: "Tab3", missing_image: "Example_Tab3.png", missing_raw: "Example_Tab3.tsv" }),
    ],
    files: [...base.files, "Example_Fig1.wpd.json", "Example_Fig2.png", "timecourses_Fig2.tsv"].sort(),
    tables: [
      tableEntry("subjects.tsv", "subjects"),
      tableEntry("interventions.tsv", "interventions"),
      tableEntry("characteristica.tsv", "characteristica"),
      tableEntry("outputs_Tab2.tsv", "outputs"),
      tableEntry("timecourses_Fig1.tsv", "timecourses"),
      tableEntry("timecourses_Fig2.tsv", "timecourses"),
      tableEntry("Example_Tab2.tsv", "raw"),
    ],
    ...changes,
  });
}

/**
 * The study with an open and a resolved review item on rows of outputs_Tab2.tsv, and two
 * problems in its cells, which make Tab2 the source that the section opens on.
 */
function reviewed(changes: Partial<StudyDetail> = {}): StudyDetail {
  return detail({
    review: {
      revision: "review-1",
      value: {
        status: "in_review",
        reviewers: [],
        items: [
          reviewItem({ id: "a", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_vd" }, column: "mean" } }),
          reviewItem({ id: "b", state: "resolved", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_cl" } } }),
        ],
      },
      issues: [],
    },
    // As the local server matches the targets in the rows of `outputs`.
    targets: { a: { lines: [4], series: null, total: 3 }, b: { lines: [2], series: null, total: 3 } },
    problems: [problem("invalid_number", 3, "mean"), problem("unknown_unit", 4, "unit", "warning")],
    counts: { errors: 1, warnings: 1 },
    ...changes,
  });
}

function sync(status: SyncState["status"], changes = 0): Pick<StudyDetail, "sync"> {
  return { sync: { status, changes, conflicts: status === "conflict" ? 1 : 0 } };
}

/**
 * The figure overlay is drawn by Plotly; the section passes it the view, the mode and the
 * selected row, and follows its row clicks.
 */
const OverlayStub = defineComponent({
  name: "SourceOverlay",
  props: {
    view: { type: Object as PropType<SourceView>, required: true },
    highlight: { type: String as PropType<string | null>, default: null },
    mode: { type: String as PropType<"overlay" | "plot">, default: undefined },
    selected: { type: Object as PropType<{ file: string; line: number } | null>, default: null },
  },
  emits: ["select-row"],
  setup(props, { emit }) {
    return () =>
      h(
        "div",
        {
          class: "overlay-stub",
          "data-mode": props.mode ?? "auto",
          "data-selected": props.selected ? `${props.selected.file}:${props.selected.line}` : undefined,
        },
        [
          `${props.view.source} overlay`,
          h(
            "button",
            { type: "button", onClick: () => emit("select-row", { file: "timecourses_Fig1.tsv", line: 3 }) },
            `Select line 3 of ${props.view.source} ${props.mode ?? "auto"}`,
          ),
        ],
      );
  },
});

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];
let served: StudyDetail;

async function mountSection(value: StudyDetail = detail(), routes: Record<string, unknown> = {}, path = SECTION) {
  served = value;
  requests = serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
    "GET /local/curators": { curators: [] },
    [`GET ${EXAMPLE}/sources/Fig1`]: digitized,
    [`GET ${EXAMPLE}/sources/Fig2`]: plain,
    [`GET ${EXAMPLE}/sources/Tab2`]: table,
    [`GET ${EXAMPLE}/sources/Tab3`]: missing,
    [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: outputs,
    [`GET ${EXAMPLE}/tables/subjects.tsv`]: subjects,
    [`GET ${EXAMPLE}/tables/Example_Tab2.tsv`]: raw,
    [`GET ${EXAMPLE}/tables/interventions.tsv`]: empty("interventions.tsv"),
    [`GET ${EXAMPLE}/tables/characteristica.tsv`]: empty("characteristica.tsv"),
    [`GET ${EXAMPLE}/tables/timecourses_Fig1.tsv`]: figureRows,
    [`GET ${EXAMPLE}/tables/timecourses_Fig2.tsv`]: empty("timecourses_Fig2.tsv"),
    [`POST ${TABLES}`]: synced,
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(path);
  await router.isReady();
  const wrapper = mount(RouterView, {
    attachTo: document.body,
    global: { plugins: [pinia, router], stubs: { SourceOverlay: OverlayStub, PaperViewer: PaperViewerStub } },
  });
  await flushPromises();
  return wrapper;
}

function sources(): DOMWrapper<Element>[] {
  return page().findAll(".nav-source");
}

function files(): DOMWrapper<Element>[] {
  return page().findAll(".nav-file");
}

/** The name of a navigator entry; a table file has its full name for screen readers. */
function nameOf(entry: Pick<DOMWrapper<Element>, "find" | "get">): string {
  const file = entry.find(".nav-file-name");
  return (file.exists() ? file : entry.get(".nav-name")).text();
}

/** The source or the file that the section shows. */
function current(name: "source" | "file"): string {
  return nameOf(page().get(`.nav-${name}[aria-current='true']`));
}

async function choose(kind: "source" | "file", name: string): Promise<void> {
  const entry = page()
    .findAll(`.nav-${kind}`)
    .find((candidate) => nameOf(candidate) === name);
  if (!entry) throw new Error(`No ${kind} ${name}`);
  await entry.trigger("click");
  await flushPromises();
}

function sourcePane() {
  return page().get(".source-pane");
}

function rowsPane() {
  return page().get(".rows-pane");
}

/** The lines of the rows that the rows pane shows. */
function lines(): string[] {
  return rowsPane()
    .findAll("tbody tr[data-index]")
    .map((row) => row.get("th").text());
}

/** What the rows pane says about its rows to screen readers. */
function caption(): string {
  return rowsPane().get(".pane-head p.d-sr-only").text();
}

/** Turns the switch with the label `label` of the toolbar on or off. */
async function toggle(label: string): Promise<void> {
  const control = page()
    .findAll(".v-switch")
    .find((entry) => entry.text().includes(label));
  if (!control) throw new Error(`No switch ${label}`);
  const input = control.get<HTMLInputElement>("input");
  await input.setValue(!input.element.checked);
  await flushPromises();
}

/** The live region of the toolbar that says what the sync status means. */
function syncStatus() {
  return page().get('.data-toolbar [role="status"]');
}

function syncText(): string {
  return syncStatus().text();
}

function posted(): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === TABLES).map(({ body }) => body);
}

function fetched(path: string): number {
  return requests.filter((request) => request.method === "GET" && request.path === path).length;
}

/** Waits for the route that a click asked for: the router starts the navigation after the click returned. */
async function routed(query: Record<string, string>, match: "exactly" | "partly" = "exactly"): Promise<void> {
  await vi.waitFor(() =>
    match === "exactly"
      ? expect(router.currentRoute.value.query).toEqual(query)
      : expect(router.currentRoute.value.query).toMatchObject(query),
  );
  await flushPromises();
}

/** Clicks the button `name` of the section; the header has buttons of the same names. */
async function press(name: string): Promise<void> {
  const found = page()
    .get(".data-section")
    .findAll("button")
    .filter((candidate) => candidate.text().replace(/\s+/g, " ").trim() === name);
  if (found.length !== 1) throw new Error(`Expected one button "${name}", found ${found.length}`);
  await found[0]!.trigger("click");
  await flushPromises();
}

beforeEach(() => {
  setViewport(1440);
  paperViewer.mounts = 0;
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("sources", () => {
  it("opens the first table beside the first source when the study has no problems", async () => {
    await mountSection();
    expect(sources().map(nameOf)).toEqual(["Fig1", "Fig2", "Tab2", "Tab3"]);
    expect(sources()[0]?.attributes("aria-current")).toBe("true");
    expect(sourcePane().attributes("aria-label")).toBe("Source Fig1");
    expect(rowsPane().attributes("aria-label")).toBe("Table subjects.tsv");
    expect(page().get('[role="separator"]').attributes("aria-label")).toBe("Resize the source and the rows");
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(1);
    expect(fetched(`${EXAMPLE}/sources/Tab2`)).toBe(0);
  });

  it("puts the chosen source and its table in the route, and shows the rows of the table", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1`);
    await choose("source", "Tab2");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    expect(sources()[2]?.attributes("aria-current")).toBe("true");
    expect(sourcePane().text()).toContain("Caffeine 150 mg");
    expect(rowsPane().attributes("aria-label")).toBe("Table outputs_Tab2.tsv");
    expect(lines()).toEqual(["2", "3", "4"]);
  });

  it("opens the source of the route", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig2`);
    expect(sources()[1]?.attributes("aria-current")).toBe("true");
    expect(current("file")).toBe("timecourses_Fig2.tsv");
    expect(fetched(`${EXAMPLE}/sources/Fig2`)).toBe(1);
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(0);
  });

  it("lets the keyboard reach the source pane, whose first content is no control", async () => {
    await mountSection();
    expect(sourcePane().get(".pane-body").attributes("tabindex")).toBe("0");
  });

  it("opens the first source for a source that the study does not have", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig9`);
    expect(sources()[0]?.attributes("aria-current")).toBe("true");
  });

  it("says so when the study has no sources", async () => {
    await mountSection(detail({ sources: [] }));
    expect(sources()).toHaveLength(0);
    expect(page().find(".source-pane").exists()).toBe(false);
    expect(page().text()).toContain("The study has no sources yet.");
  });
});

describe("table sources", () => {
  it("shows the image and the raw extraction as printed", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab2`);
    const image = sourcePane().get("img");
    expect(image.attributes("alt")).toBe("Tab2 of caffeine/Example");
    expect(image.attributes("src")).toBe(`${EXAMPLE}/files/Example_Tab2.png`);
    expect(image.attributes("width")).toBe("640");
    expect(image.attributes("height")).toBe("220");

    const rawGrid = sourcePane().get('[aria-label="Raw extraction Example_Tab2.tsv"]');
    const cells = rawGrid.findAll("td").map((cell) => cell.text());
    expect(cells).toEqual([
      "",
      "Caffeine 150 mg",
      "Caffeine 300 mg",
      "CL [ml/min/kg]",
      "1.20 ± 0.3",
      "1.10 ± 0.2",
      "t1/2 [h]",
      "007",
      "4.8ᵃ",
    ]);
    // Spreadsheet columns and the lines of the file, as in the workbook sheet.
    expect(rawGrid.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B", "C"]);
    expect(rawGrid.findAll("tbody th").map((cell) => cell.text())).toEqual(["1", "2", "3"]);
  });

  it("names the missing files of a paper table, and the rows pane shows every row of the first table", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab3`);
    expect(sourcePane().text()).toContain("No image: add Example_Tab3.png");
    expect(sourcePane().text()).toContain("No raw extraction: add Example_Tab3.tsv with Add table.");
    expect(sourcePane().find("img").exists()).toBe(false);
    // Tab3 has no table, so the section shows the first table, a shared one with all of its rows.
    expect(rowsPane().attributes("aria-label")).toBe("Table subjects.tsv");
    expect(lines()).toEqual(["2", "3", "4", "5"]);
  });
});

describe("figure sources", () => {
  it("draws the digitized figure with the overlay and lists the series without a dataset", async () => {
    const wrapper = await mountSection(detail(), {}, `${SECTION}?source=Fig1`);
    const overlays = wrapper.findAllComponents(OverlayStub);
    expect(overlays[0]?.props("view")).toEqual(digitized);
    expect(overlays[0]?.props("mode")).toBe("overlay");
    expect(sourcePane().text()).toContain("Not digitized: caf_plasma_D75");
    // The rows without a dataset are drawn beside the figure.
    expect(overlays[1]?.props("mode")).toBe("plot");
    expect(overlays).toHaveLength(2);
    expect(lines()).toEqual(["2", "3"]);
    expect(sourcePane().text()).not.toContain("No digitization");
  });

  it("draws no plot beside the overlay when every series has a dataset", async () => {
    const wrapper = await mountSection(detail(), { [`GET ${EXAMPLE}/sources/Fig1`]: { ...digitized, unmatched: [] } });
    expect(wrapper.findAllComponents(OverlayStub).map((overlay) => overlay.props("mode"))).toEqual(["overlay"]);
    expect(sourcePane().text()).not.toContain("Not digitized");
  });

  it("shows the image above a plot of the mapped rows without a digitization", async () => {
    const wrapper = await mountSection(detail(), {}, `${SECTION}?source=Fig2`);
    const image = sourcePane().get("img");
    expect(image.attributes("alt")).toBe("Fig2 of caffeine/Example");
    const overlays = wrapper.findAllComponents(OverlayStub);
    expect(overlays).toHaveLength(1);
    expect(overlays[0]?.props("mode")).toBe("plot");
    expect(overlays[0]?.props("view")).toEqual(plain);
    expect(sourcePane().text()).toContain("No digitization: add Example_Fig2.wpd.json");
    expect(sourcePane().text()).not.toContain("Not digitized");
  });

  it("names the missing image of a figure", async () => {
    const view: SourceView = { ...plain, image: null, image_url: null, image_size: null };
    const base = detail();
    const changed = base.sources.map((entry) =>
      entry.source === "Fig2" ? { ...entry, image: null, image_url: null, missing_image: "Example_Fig2.png" } : entry,
    );
    await mountSection({ ...base, sources: changed }, { [`GET ${EXAMPLE}/sources/Fig2`]: view }, `${SECTION}?source=Fig2`);
    expect(sourcePane().text()).toContain("No image: add Example_Fig2.png");
    expect(sourcePane().find("img").exists()).toBe(false);
  });

  it("selects the row of a clicked point in the rows pane", async () => {
    await mountSection();
    await click("Select line 3 of Fig1 overlay");
    await routed({ source: "Fig1", file: "timecourses_Fig1.tsv", line: "3" });
    expect(router.currentRoute.value.params.section).toBe("data");
    expect(rowsPane().get("tr.grid-row--focus th").text()).toBe("3");
  });
});

describe("loading", () => {
  it("shows why a source could not be loaded and loads it again on Retry", async () => {
    let failing = true;
    const answer: Handler = () => (failing ? json({ error: "The image cannot be read." }, { status: 500 }) : json(table));
    await mountSection(detail(), { [`GET ${EXAMPLE}/sources/Tab2`]: answer }, `${SECTION}?source=Tab2`);
    expect(sourcePane().text()).toContain("Tab2 could not be loaded.");
    failing = false;
    await click("Retry");
    expect(sourcePane().text()).not.toContain("could not be loaded");
    expect(sourcePane().get("img").attributes("alt")).toBe("Tab2 of caffeine/Example");
  });
});

describe("a failed read of the local server", () => {
  /** The error body of the local server for a file of caffeine/Example that it cannot read. */
  function unreadable(error: string, path: string) {
    return json(
      {
        error,
        code: "file_error",
        detail: "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Example/outputs_Tab2.tsv'",
        action: `Read (GET ${path})`,
        request_id: "3f9c2a71",
        time: "2026-10-12T14:03:11+02:00",
      },
      { status: 400 },
    );
  }

  /** The alert of `pane`: the message once, what went wrong, Details, Retry and no close button. */
  function expectFailure(pane: ReturnType<typeof rowsPane>, message: string) {
    const alert = pane.get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe(message);
    expect(alert.get(".action-failure-detail").text()).toBe(
      "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Example/outputs_Tab2.tsv'",
    );
    expect(alert.findAll(".failure-summary").map((summary) => summary.text())).toEqual(["Details"]);
    expect(pane.text().split(message)).toHaveLength(2);
    expect(pane.text()).not.toContain("could not be loaded");
    expect(alert.find(".v-alert__close").exists()).toBe(false);
    expect(alert.findAll("button").map((button) => button.text())).toContain("Retry");
  }

  it("says once why a table could not be read, with what went wrong and Details", async () => {
    const path = `${EXAMPLE}/tables/outputs_Tab2.tsv`;
    await mountSection(
      detail(),
      { [`GET ${path}`]: () => unreadable("Could not read outputs_Tab2.tsv of caffeine/Example.", path) },
      `${SECTION}?source=Tab2`,
    );
    expectFailure(rowsPane(), "Could not read outputs_Tab2.tsv of caffeine/Example.");
  });

  it("says once why a source could not be read, with what went wrong and Details", async () => {
    const path = `${EXAMPLE}/sources/Tab2`;
    await mountSection(
      detail(),
      { [`GET ${path}`]: () => unreadable("Could not read the source Tab2 of caffeine/Example.", path) },
      `${SECTION}?source=Tab2`,
    );
    expectFailure(sourcePane(), "Could not read the source Tab2 of caffeine/Example.");
  });
});

describe("problems of a source", () => {
  const mismatch: Problem = {
    code: "digitized_mismatch",
    severity: "warning",
    acknowledgeable: true,
    message: "Line 3 lies 4.1 pixels from every point of dataset caf_plasma_D150.",
    source: { file: "timecourses_Fig1.tsv", sheet: "timecourses_Fig1", row: 3, column: "F", cell: "F3", header: "mean" },
  };
  const other: Problem = {
    code: "unused_intervention",
    severity: "warning",
    acknowledgeable: true,
    message: "'caf_po_300' is not referenced by any row",
    source: { file: "interventions.tsv", sheet: "interventions", row: 3, column: "B", cell: "B3", header: "name" },
  };

  it("lists the problems of the files of the source with a link to the cell", async () => {
    await mountSection(detail({ problems: [mismatch, other], counts: { errors: 0, warnings: 2 } }));
    const problems = sourcePane().get(".source-problems");
    expect(problems.text()).toContain("digitized_mismatch");
    expect(problems.text()).toContain(mismatch.message);
    expect(problems.text()).not.toContain("unused_intervention");
    const link = problems.get("a");
    expect(link.text()).toBe("Show in table");
    expect(link.attributes("href")).toBe("#/studies/caffeine/Example/data?file=timecourses_Fig1.tsv&line=3&column=mean");
  });

  it("shows the problems as the Problems section does: by file, errors first, without Acknowledge", async () => {
    const unknown: Problem = {
      code: "invalid_digitization",
      severity: "error",
      acknowledgeable: false,
      message: "The project has no calibration.",
      source: { file: "Example_Fig1.wpd.json", path: [] },
    };
    await mountSection(detail({ problems: [mismatch, unknown], counts: { errors: 1, warnings: 1 } }));
    const problems = sourcePane().get(".source-problems");
    expect(problems.findAll(".problem-file").map((heading) => heading.text())).toEqual([
      "Example_Fig1.wpd.json",
      "timecourses_Fig1.tsv",
    ]);
    expect(problems.findAll(".problem-severity").map((chip) => chip.text())).toEqual(["Error", "Warning"]);
    expect(problems.get(".problem-location").text()).toBe("line 3 · mean · sheet cell timecourses_Fig1!F3");
    expect(problems.findAll("button").filter((control) => control.text() === "Acknowledge")).toHaveLength(0);
  });

  it("lists nothing for a source without problems", async () => {
    await mountSection(detail({ problems: [other], counts: { errors: 0, warnings: 1 } }));
    expect(sourcePane().find(".source-problems").exists()).toBe(false);
    expect(button("Select line 3 of Fig1 overlay").exists()).toBe(true);
  });
});

describe("linked selection", () => {
  it("opens the first table with problems beside its source when the route names nothing", async () => {
    await mountSection(detail({ problems: [problemAt("outputs_Tab2.tsv", 2)] }));
    expect(current("source")).toBe("Tab2");
    expect(current("file")).toBe("outputs_Tab2.tsv");
    // The default selection is written into the route, so that only the curator changes it.
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
  });

  it("keeps the source that it opened on when the problems change", async () => {
    await mountSection(detail({ problems: [problemAt("outputs_Tab2.tsv", 2)] }));
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    // The problem of Tab2 is fixed, and Fig2 has one now: the default would be Fig2.
    served = detail({ problems: [problemAt("timecourses_Fig2.tsv", 2)] });
    await useStudyStore().refresh();
    await flushPromises();
    expect(current("source")).toBe("Tab2");
    expect(current("file")).toBe("outputs_Tab2.tsv");
    expect(router.currentRoute.value.query).toEqual({ source: "Tab2", file: "outputs_Tab2.tsv" });
  });

  it("writes no default selection into the route of another section", async () => {
    await mountSection(detail());
    await routed({ source: "Fig1", file: "subjects.tsv" });
    await router.push("/studies/caffeine/Example/metadata");
    await flushPromises();
    expect(router.currentRoute.value.fullPath).toBe("/studies/caffeine/Example/metadata");
  });

  it("selects the owner of a table file that a link names without a source", async () => {
    // The default source is Fig1; outputs_Tab2.tsv belongs to Tab2.
    await mountSection(detail(), {}, `${SECTION}?file=outputs_Tab2.tsv`);
    expect(current("source")).toBe("Tab2");
    expect(current("file")).toBe("outputs_Tab2.tsv");
  });

  it("selects the source named in the linked row of a shared table once its rows load", async () => {
    // The default source is Fig1; line 4 of subjects.tsv names Tab2, and a shared table has no owner.
    await mountSection(detail(), {}, `${SECTION}?file=subjects.tsv&line=4`);
    expect(current("source")).toBe("Tab2");
    expect(current("file")).toBe("subjects.tsv");
  });

  it("switches the source with a row of a shared table that names another source", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1&file=subjects.tsv`);
    await page().get('th[scope="row"] button[title="Select line 4"]').trigger("click");
    await flushPromises();
    await routed({ source: "Tab2", file: "subjects.tsv", line: "4" }, "partly");
  });

  it("keeps the source for a row naming an unknown source", async () => {
    // subjects.tsv line 5 names "Fig9", which the study does not have.
    await mountSection(detail(), {}, `${SECTION}?source=Fig1&file=subjects.tsv`);
    await page().get('th[scope="row"] button[title="Select line 5"]').trigger("click");
    await flushPromises();
    await routed({ source: "Fig1", line: "5" }, "partly");
  });

  it("selects the owner of a clicked table file", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1`);
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
  });

  it("opens the first table of a chosen source, also from a shared table that has rows of it", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1&file=subjects.tsv`);
    await choose("source", "Tab2");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    expect(rowsPane().attributes("aria-label")).toBe("Table outputs_Tab2.tsv");
  });

  it("opens the first table naming a chosen source without tables of its own, from a table of another source", async () => {
    const text = sourceSummary({ source: "Text", kind: "text", tables: ["subjects.tsv"] });
    await mountSection(
      detail({ sources: [...detail().sources, text] }),
      { [`GET ${EXAMPLE}/sources/Text`]: { ...missing, source: "Text" } },
      `${SECTION}?source=Tab2&file=outputs_Tab2.tsv`,
    );
    await choose("source", "Text");
    await routed({ source: "Text", file: "subjects.tsv" });
    expect(rowsPane().attributes("aria-label")).toBe("Table subjects.tsv");
  });

  it("keeps the shared table for a chosen source without tables of its own", async () => {
    // A text has no tables of its own; its rows live in the shared tables.
    const text = sourceSummary({ source: "Text", kind: "text", tables: ["subjects.tsv"] });
    await mountSection(
      detail({ sources: [...detail().sources, text] }),
      { [`GET ${EXAMPLE}/sources/Text`]: { ...missing, source: "Text" } },
      `${SECTION}?source=Fig1&file=subjects.tsv`,
    );
    await choose("source", "Text");
    await routed({ source: "Text", file: "subjects.tsv" });
    expect(rowsPane().attributes("aria-label")).toBe("Table subjects.tsv");
  });

  it("keeps the source for a clicked shared table", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1`);
    await choose("file", "subjects.tsv");
    await routed({ source: "Fig1", file: "subjects.tsv" });
  });

  it("passes the selected row to the overlay", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig1&file=timecourses_Fig1.tsv&line=2`);
    expect(page().get(".overlay-stub").attributes("data-selected")).toBe("timecourses_Fig1.tsv:2");
  });

  it("shows every row of a shared table, whichever source is selected", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig2&file=subjects.tsv`);
    expect(lines()).toEqual(["2", "3", "4", "5"]);
    expect(page().text()).not.toContain("Rows of Fig2 only");
  });

  it("keeps the Source filter of each shared table while other tables are chosen", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab2&file=subjects.tsv`);
    const filter = () => page().get<HTMLSelectElement>(".rows-pane select.pane-head-select");
    await filter().setValue("source:Tab2");
    await flushPromises();
    expect(lines()).toEqual(["2", "4"]);
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    // A table of one source has no filter.
    expect(page().find(".rows-pane select").exists()).toBe(false);
    await choose("file", "subjects.tsv");
    await routed({ source: "Tab2", file: "subjects.tsv" });
    expect(filter().element.value).toBe("source:Tab2");
    expect(lines()).toEqual(["2", "4"]);
  });

  it("offers Show all rows when no row of the shared table has the chosen source", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig2&file=subjects.tsv`);
    await page().get<HTMLSelectElement>(".rows-pane select.pane-head-select").setValue("none");
    await flushPromises();
    expect(rowsPane().text()).toContain("Every row of subjects.tsv names a source.");
    await click(/Show all rows/);
    expect(lines()).toEqual(["2", "3", "4", "5"]);
  });

  it("falls back for a source and a file the study does not have", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig9&file=gone.tsv`);
    expect(page().get(".nav-source[aria-current='true']").text()).toContain("Fig1");
    expect(page().get(".nav-file[aria-current='true']").text()).toContain("subjects.tsv");
  });

  it("a study without sources shows its first table and says it has no sources", async () => {
    await mountSection(detail({ sources: [] }));
    expect(page().text()).toContain("The study has no sources yet.");
    expect(page().get(".nav-file[aria-current='true']").text()).toContain("subjects.tsv");
  });
});

describe("routes", () => {
  it("redirects the old Sources and Tables addresses with their query", async () => {
    await mountSection(detail(), {}, "/studies/caffeine/Example/tables?file=outputs_Tab2.tsv&line=3");
    expect(router.currentRoute.value.params.section).toBe("data");
    expect(router.currentRoute.value.query).toEqual({ file: "outputs_Tab2.tsv", line: "3" });
    await router.push("/studies/caffeine/Example/sources?source=Fig2");
    expect(router.currentRoute.value.fullPath).toBe("/studies/caffeine/Example/data?source=Fig2");
  });
});

describe("narrow windows", () => {
  it("offers the sources and the tables as two selects instead of the navigator below 1100 px", async () => {
    setViewport(1000);
    const wrapper = await mountSection();
    expect(page().find(".data-navigator").exists()).toBe(false);
    const sourceSelect = labeled(wrapper, VSelect, "Source");
    const tableSelect = labeled(wrapper, VSelect, "Table");
    // The Table select comes first, grouped as the navigator.
    const labels = wrapper.findAllComponents(VSelect).map((select) => select.props("label"));
    expect(labels.filter((label) => label === "Table" || label === "Source")).toEqual(["Table", "Source"]);
    expect(tableSelect.props("items")).toEqual([
      { type: "subheader", title: "Subjects", info: "subjects" },
      { type: "item", title: "subjects.tsv", value: "subjects.tsv", info: "subjects" },
      { type: "item", title: "characteristica.tsv", value: "characteristica.tsv", info: "subjects" },
      { type: "subheader", title: "Interventions", info: "interventions" },
      { type: "item", title: "interventions.tsv", value: "interventions.tsv", info: "interventions" },
      { type: "subheader", title: "Data", info: "data" },
      { type: "item", title: "outputs_Tab2.tsv", value: "outputs_Tab2.tsv", info: "data" },
      { type: "item", title: "timecourses_Fig1.tsv", value: "timecourses_Fig1.tsv", info: "data" },
      { type: "item", title: "timecourses_Fig2.tsv", value: "timecourses_Fig2.tsv", info: "data" },
      { type: "subheader", title: "Raw extractions", info: "raw" },
      { type: "item", title: "Example_Tab2.tsv", value: "Example_Tab2.tsv", info: "raw" },
    ]);
    expect(sourceSelect.props("modelValue")).toBe("Fig1");
    expect(sourceSelect.props("items")).toEqual([
      { title: "No Example.pdf", value: "paper", props: { disabled: true } },
      { title: "Fig1", value: "Fig1" },
      { title: "Fig2", value: "Fig2" },
      { title: "Tab2", value: "Tab2" },
      { title: "Tab3", value: "Tab3" },
    ]);
    expect(tableSelect.props("modelValue")).toBe("subjects.tsv");
    // The panes stay side by side.
    expect(page().find('[role="separator"]').exists()).toBe(true);

    await sourceSelect.setValue("Tab2");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    await tableSelect.setValue("timecourses_Fig1.tsv");
    await routed({ source: "Fig1", file: "timecourses_Fig1.tsv" });
  });

  it("marks each option of the Table select with a dot in the color of its class, under the heading of its class", async () => {
    setViewport(1000);
    const wrapper = await mountSection();
    await labeled(wrapper, VSelect, "Table").find(".v-field").trigger("mousedown");
    const menu = () => page().get(".v-overlay--active .v-list");
    await vi.waitFor(() => expect(menu().findAll('[role="option"]')).toHaveLength(7));
    expect(menu().findAll(".v-list-subheader").map((heading) => heading.text())).toEqual([
      "Subjects",
      "Interventions",
      "Data",
      "Raw extractions",
    ]);
    const options = menu().findAll('[role="option"]');
    const dots = options.map((option) => option.get(".data-option-dot"));
    expect(options.map((option) => option.text())).toEqual([
      "subjects.tsv",
      "characteristica.tsv",
      "interventions.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "timecourses_Fig2.tsv",
      "Example_Tab2.tsv",
    ]);
    expect(dots.map((dot) => /--info: var\(--v-theme-(info-\w+)\)/.exec(dot.attributes("style") ?? "")?.[1])).toEqual([
      "info-subjects",
      "info-subjects",
      "info-interventions",
      "info-data",
      "info-data",
      "info-data",
      "info-raw",
    ]);
    expect(dots.every((dot) => dot.attributes("aria-hidden") === "true")).toBe(true);
  });

  it("stacks the source above the rows without a separator below 960 px", async () => {
    setViewport(900);
    await mountSection();
    expect(page().find('[role="separator"]').exists()).toBe(false);
    const order = sourcePane().element.compareDocumentPosition(rowsPane().element);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("sync status", () => {
  it.each([
    ["in_sync", 0, ""],
    ["workbook_open", 0, "Workbook open: close it to sync"],
    ["syncing", 0, "Syncing"],
    ["changed", 3, "Changed: the next sync changes 3 files"],
    ["no_workbook", 0, "No workbook yet: Open tables creates it"],
    ["not_checked", 0, "Not checked yet"],
  ] as const)("says what %s means in the toolbar, before the panes", async (status, changes, text) => {
    await mountSection(reviewed(sync(status, changes)));
    expect(syncText()).toBe(text);
    const toolbar = page().get(".data-section .data-toolbar");
    // Its controls are reached with Tab; a toolbar role would promise arrow keys.
    expect(toolbar.attributes("role")).toBeUndefined();
    expect(toolbar.find('[role="status"]').exists()).toBe(true);
    const order = toolbar.element.compareDocumentPosition(page().get(".data-panes").element);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("names the conflicting file in muted text, without an alert", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), CONFLICT_TABLES);
    expect(syncText()).toBe("Conflict in outputs_Tab2.tsv");
    expect(page().find(".data-section .v-alert").exists()).toBe(false);
  });

  it("announces a sync status that changes outside the app, in a live region that stays while empty", async () => {
    await mountSection(reviewed(sync("in_sync")), CONFLICT_TABLES);
    const status = syncStatus();
    expect(status.attributes("aria-live")).toBe("polite");
    expect(status.text()).toBe("");
    // The workbook and the tables changed on disk: the next poll brings the conflict.
    served = reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] });
    await useStudyStore().refresh();
    await flushPromises();
    expect(syncStatus().element).toBe(status.element);
    expect(status.text()).toBe("Conflict in outputs_Tab2.tsv");
  });

  it("syncs, and then says what the sync did", async () => {
    await mountSection(reviewed(sync("changed", 1)), {
      [`POST ${TABLES}`]: (() => {
        served = reviewed(sync("in_sync"));
        return json({ ...synced, changes: [{ file: "outputs_Tab2.tsv", action: "write" }] });
      }) satisfies Handler,
    });
    await press("Sync");
    expect(posted()).toEqual([{ action: "sync", study: "caffeine/Example" }]);
    expect(syncText()).toBe("The last sync in the app wrote outputs_Tab2.tsv.");
    expect(page().get(".data-notice").text()).toBe("Synced the workbook and the tables.");
  });

  it("lists the problems of a failed sync until they are dismissed", async () => {
    await mountSection(reviewed(sync("changed", 1)), {
      [`POST ${TABLES}`]: {
        ...synced,
        ok: false,
        issues: [{ code: "invalid_cell", severity: "error", message: "Cell E4 of outputs_Tab2 is not a number." }],
      },
    });
    await press("Sync");
    expect(page().get(".action-failure").text()).toContain("The sync found problems.");
    expect(page().get(".action-failure").text()).toContain("Cell E4 of outputs_Tab2 is not a number.");
    await page().get(".action-failure .v-alert__close button").trigger("click");
    await flushPromises();
    expect(page().find(".action-failure").exists()).toBe(false);
  });

  it("leaves Open tables to the study header, and shows the progress on the running button only", async () => {
    let finish: (response: Response) => void = () => undefined;
    await mountSection(reviewed(sync("changed", 1)), {
      [`POST ${TABLES}`]: (() => new Promise<Response>((resolve) => (finish = resolve))) satisfies Handler,
    });
    const names = () =>
      page()
        .get(".data-section")
        .findAll("button")
        .map((control) => control.text().trim());
    expect(names()).not.toContain("Open tables");
    expect(names()).toEqual(expect.arrayContaining(["Sync", "Add table"]));
    void press("Sync");
    await flushPromises();
    const loading = page()
      .get(".data-section")
      .findAll(".v-btn--loading")
      .map((control) => control.text().trim());
    expect(loading).toEqual(["Sync"]);
    finish(json(synced));
    await flushPromises();
  });
});

describe("conflicts", () => {
  /** The rows of the conflict grid: the version of each row and the cells of its first columns. */
  function conflictRows(): string[][] {
    return page()
      .get(".conflict-panel")
      .findAll("tbody tr")
      .map((row) => [row.get("th").text(), ...row.findAll("td").map((cell) => cell.text())]);
  }

  it("shows the last sync, the workbook and the tables in one grid at the top of the rows pane", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), CONFLICT_TABLES);
    const panelElement = rowsPane().get(".conflict-panel");
    const order = panelElement.element.compareDocumentPosition(rowsPane().get(".rows-pane-grid").element);
    expect(order & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(panelElement.get(".conflict-file-name").text()).toBe("outputs_Tab2.tsv");
    expect(panelElement.findAll('[role="region"]')).toHaveLength(1);
    expect(panelElement.findAll("thead th").map((cell) => cell.text())).toEqual([
      "Version",
      "mean, changed",
      "study",
      "source",
      "subjects",
      "interventions",
      "measurement",
      "substance",
      "tissue",
      "sd",
      "unit",
    ]);
    expect(conflictRows().map((row) => row.slice(0, 2))).toEqual([
      ["Last sync", "5.9"],
      ["Workbook row 2", "6.1"],
      ["Tables line 2", "6.3"],
    ]);
  });

  it("explains the conflicts of two files in sentences", async () => {
    await mountSection(
      reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT, ROWS_REMOVED_CONFLICT] }),
      CONFLICT_TABLES,
    );
    expect(page().get(".conflict-text").text()).toBe(
      "The workbook and the tables changed the same rows since the last sync. Keep one side. To combine both, edit " +
        "the rows in the workbook, save it, and then keep the workbook. The columns that differ come first and are " +
        "marked. Keep workbook and Keep tables resolve all conflicts.",
    );
  });

  it("syncs during a conflict without a second alert: the panel explains the conflict", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), {
      ...CONFLICT_TABLES,
      [`POST ${TABLES}`]: conflictAnswer([[REGION_CONFLICT, REGION_ISSUE]]),
    });
    await press("Sync");
    expect(posted()).toEqual([{ action: "sync", study: "caffeine/Example" }]);
    expect(page().find(".action-failure").exists()).toBe(false);
    expect(page().get(".data-notice").text()).toBe("The workbook and the tables conflict.");
    expect(page().find(".conflict-panel").exists()).toBe(true);
  });

  it("says that the workbook removed the rows that the table changed", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [ROWS_REMOVED_CONFLICT] }), CONFLICT_TABLES);
    expect(page().get(".conflict-note").text()).toBe("The workbook removed these rows, and the tables changed them.");
    expect(conflictRows().map((row) => row.slice(0, 2))).toEqual([
      ["Last sync", "1"],
      ["Tables line 3", "2"],
    ]);
  });

  it("shows a deleted table without its header as a row", async () => {
    // The file is gone: its rows have the header of the sheet.
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [FILE_DELETED_CONFLICT] }), CONFLICT_TABLES);
    expect(page().get(".conflict-note").text()).toBe(
      "scatters_Fig2.tsv was deleted, but its sheet changed since the last sync.",
    );
    expect(conflictRows().map((row) => row.slice(0, 2))).toEqual([
      ["Last sync", "30"],
      ["Last sync", "40"],
      ["Workbook row 2", "31"],
      ["Workbook row 3", "40"],
    ]);
    expect(page().get(".conflict-panel thead th:nth-child(2)").text()).toBe("x_mean, changed");
    // A deleted table is not requested.
    expect(requests.some((request) => request.path.endsWith("/scatters_Fig2.tsv"))).toBe(false);
  });

  it("fades out the bottom of the conflicts while more of them follow below, and not at their end", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), CONFLICT_TABLES);
    const body = rowsPane().get(".conflict-panel > .conflict-body").element;
    await scrollLayout(body, 150, 400);
    expect(rowsPane().get(".conflict-panel > .pane-more").attributes("aria-hidden")).toBe("true");
    await scrollLayout(body, 150, 400, 250);
    expect(rowsPane().find(".conflict-panel .pane-more").exists()).toBe(false);
  });

  it("offers to keep a side when the conflicting rows cannot be read", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [] }), {
      [`POST ${TABLES}`]: (() => {
        served = reviewed(sync("in_sync"));
        return json({ ...synced, workbook_action: "regenerated" });
      }) satisfies Handler,
    });
    expect(syncText()).toBe("Conflict between the workbook and the tables");
    expect(page().get(".conflict-panel").text()).toContain("The conflicting rows could not be read.");
    await press("Keep tables");
    expect(posted()).toEqual([{ action: "resolve", keep: "tables", study: "caffeine/Example" }]);
    expect(page().find(".conflict-panel").exists()).toBe(false);
  });

  it("keeps the workbook and lists the problems of the sync that follows", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), {
      ...CONFLICT_TABLES,
      [`POST ${TABLES}`]: (() => {
        served = reviewed(sync("unknown"));
        return json({
          ...synced,
          ok: false,
          conflicts: [{ ...REGION_CONFLICT, kept: "workbook" }],
          issues: [{ code: "invalid_number", severity: "error", message: "The mean on row 2 is not a number." }],
        });
      }) satisfies Handler,
    });
    await press("Keep workbook");
    expect(posted()).toEqual([{ action: "resolve", keep: "workbook", study: "caffeine/Example" }]);
    const failure = page().get(".action-failure").text();
    expect(failure).toContain("Kept the workbook rows, but the sync found problems.");
    expect(failure).toContain("The mean on row 2 is not a number.");
    expect(page().find(".conflict-panel").exists()).toBe(false);
  });

  it("keeps the tables", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), {
      ...CONFLICT_TABLES,
      [`POST ${TABLES}`]: (() => {
        served = reviewed(sync("in_sync"));
        return json({ ...synced, workbook_action: "regenerated", conflicts: [{ ...REGION_CONFLICT, kept: "tables" }] });
      }) satisfies Handler,
    });
    await press("Keep tables");
    expect(posted()).toEqual([{ action: "resolve", keep: "tables", study: "caffeine/Example" }]);
    expect(page().get(".data-notice").text()).toBe("Kept the table rows. The workbook and the tables are in sync.");
  });

  it("opens the workbook to edit the conflicting rows", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), {
      ...CONFLICT_TABLES,
      [`POST ${TABLES}`]: conflictAnswer([[REGION_CONFLICT, REGION_ISSUE]], { opened: true }),
    });
    await press("Open workbook");
    expect(posted()).toEqual([{ action: "open", study: "caffeine/Example" }]);
    // The panel shows the conflict already.
    expect(page().find(".action-failure").exists()).toBe(false);
    expect(page().get(".data-notice").text()).toBe("The workbook opened.");
  });

  it("shows the conflicts of a study without tables", async () => {
    await mountSection(reviewed({ ...sync("conflict"), conflicts: [FILE_DELETED_CONFLICT], sources: [], tables: [] }));
    expect(page().text()).toContain("The study has no tables yet.");
    expect(page().get(".conflict-note").text()).toBe(
      "scatters_Fig2.tsv was deleted, but its sheet changed since the last sync.",
    );
  });
});

describe("beyond the upload limits", () => {
  it("says in place of the panes that the app cannot show the sources and tables, and counts neither", async () => {
    await mountSection(beyondLimitsDetail(sync("changed", 1)));
    expect(page().find(".data-navigator").exists()).toBe(false);
    expect(page().find(".data-panes").exists()).toBe(false);
    const text = page().get(".data-empty");
    expect(text.text()).toBe(
      "This study is beyond the upload limits, so the app cannot show its sources and tables. See Problems.",
    );
    expect(text.get("a").attributes("href")).toBe("#/studies/caffeine/Example/problems");
    expect(page().text()).not.toContain("no sources yet");
    expect(page().text()).not.toContain("no tables yet");
    // The workbook still syncs: the toolbar keeps its actions and the meaning of the sync status.
    const toolbar = page().get(".data-section .data-toolbar");
    expect(toolbar.findAll("button").map((control) => control.text().trim())).toEqual(["Sync", "Add table"]);
    expect(toolbar.find(".v-switch").exists()).toBe(false);
    expect(syncText()).toBe("Changed: the next sync changes 1 file");
    expect(requests.filter((request) => /\/(tables|sources)\//.test(request.path))).toEqual([]);
    // The tabs claim no count of the data that the study page cannot list.
    const tab = (label: string) =>
      page()
        .findAll(".section-tab")
        .find((link) => link.get(".section-tab-label").text().startsWith(label));
    expect(tab("Data")!.find(".section-tab-count").exists()).toBe(false);
    expect(tab("Problems")!.get(".section-tab-count").text()).toBe("1");
    expect(tab("Sources")).toBeUndefined();
    expect(tab("Tables")).toBeUndefined();
  });

  it("shows the conflicts and syncs, so that Show the conflicts lands on them", async () => {
    await mountSection(beyondLimitsDetail({ ...sync("conflict"), conflicts: [REGION_CONFLICT] }), {
      [`POST ${TABLES}`]: conflictAnswer([[REGION_CONFLICT, REGION_ISSUE]]),
    });
    expect(syncText()).toBe("Conflict in outputs_Tab2.tsv");
    expect(page().get(".conflict-panel .conflict-file-name").text()).toBe("outputs_Tab2.tsv");
    expect(page().get(".data-empty").text()).toContain("beyond the upload limits");
    await press("Sync");
    expect(posted()).toEqual([{ action: "sync", study: "caffeine/Example" }]);
    expect(page().get(".data-notice").text()).toBe("The workbook and the tables conflict.");
    // The rows of a study beyond the limits are not read.
    expect(requests.filter((request) => /\/(tables|sources)\//.test(request.path))).toEqual([]);
  });

  it("offers the kinds of a new table, which the study page describes without listing tables", async () => {
    await mountSection(beyondLimitsDetail());
    await press("Add table");
    expect(["Outputs", "Timecourses", "Scatters", "Raw table"].map((label) => radio(label).disabled)).toEqual([
      false,
      false,
      false,
      false,
    ]);
    expect(radio("Outputs").checked).toBe(true);
  });
});

describe("the height of the section", () => {
  it("fills the window below the page above it while the panes stand side by side, and else scrolls with the page", async () => {
    // jsdom has no layout: the CSS of the section and of the page around it fills the window
    // (the end-to-end tests measure it); the section says when.
    await mountSection();
    expect(page().get(".data-section").classes()).toContain("data-section--fill");
    expect(page().get(".data-section").attributes("style")).toBeUndefined();
  });

  it("scrolls with the page while the panes stack", async () => {
    setViewport(900);
    await mountSection();
    expect(page().get(".data-section").classes()).not.toContain("data-section--fill");
  });

  it("scrolls with the page beyond the upload limits", async () => {
    await mountSection(beyondLimitsDetail(sync("changed", 1)));
    expect(page().get(".data-section").classes()).not.toContain("data-section--fill");
  });
});

describe("tables", () => {
  it("lists every table under the heading of its class, with its problems and open items", async () => {
    await mountSection(reviewed());
    expect(files().map(nameOf)).toEqual([
      "subjects.tsv",
      "characteristica.tsv",
      "interventions.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "timecourses_Fig2.tsv",
      "Example_Tab2.tsv",
    ]);
    const entry = files()[3]!;
    expect(entry.get(".nav-count--error .d-sr-only").text()).toBe("1 error, 1 warning");
    expect(entry.get(".nav-count:not(.nav-count--error) .d-sr-only").text()).toBe("1 open review item");
    expect(files()[0]!.find(".nav-count").exists()).toBe(false);
    // The source with problems opens on its table.
    expect(entry.attributes("aria-current")).toBe("true");
    expect(rowsPane().attributes("aria-label")).toBe("Table outputs_Tab2.tsv");
  });

  it("shows the rows of the chosen table with the targets of open items and the cells with problems", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?source=Fig1`);
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    expect(lines()).toEqual(["2", "3", "4"]);
    const rows = rowsPane().findAll("tbody tr[data-index]");
    expect(rows.map((row) => row.classes().includes("grid-row--target"))).toEqual([false, false, true]);
    expect(rows[1]!.findAll("td")[4]!.classes()).toContain("grid-cell--error");
    expect(rows[2]!.findAll("td")[6]!.classes()).toContain("grid-cell--warning");
    expect(caption()).toBe("3 rows. Open review items target 1 row. 2 problems are outlined. 1 empty column is hidden.");
  });

  it("counts the open items about the whole table and those that match no row", async () => {
    const value = reviewed();
    const items = [
      reviewItem({ id: "c", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "d", target: { file: "outputs_Tab2.tsv", rows: {} } }),
      reviewItem({ id: "e", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_auc" } } }),
    ];
    const targets = {
      c: { lines: null, series: null, total: 3 },
      d: { lines: null, series: null, total: 3 },
      e: { lines: [], series: null, total: 3 },
    };
    await mountSection(
      { ...value, review: { ...value.review, value: { ...value.review.value!, items } }, targets, problems: [] },
      {},
      `${SECTION}?file=outputs_Tab2.tsv`,
    );
    expect(caption()).toBe(
      "3 rows. 2 open review items are about the whole table. 1 open review item matches no row. 1 empty column is hidden.",
    );
  });

  it("marks the rows that the page of these rows targets, until the rows of a newer page arrive", async () => {
    let answerRows: ((response: Response) => void) | null = null;
    let hold = false;
    const rowsAt = (line: number) => outputs.rows.find((row) => row.line === line)!;
    // The table after an edit: caf_vd moved from line 4 to line 2.
    const edited: TableResponse = {
      ...outputs,
      rows: [
        { ...rowsAt(4), line: 2 },
        { ...rowsAt(3), line: 3 },
        { ...rowsAt(2), line: 4 },
      ],
    };
    const marked = () =>
      rowsPane()
        .findAll("tbody tr.grid-row--target")
        .map((row) => `${row.get("th").text()} ${row.findAll("td")[2]?.text()}`);
    await mountSection(
      reviewed(),
      {
        [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: () =>
          hold ? new Promise<Response>((resolve) => (answerRows = resolve)) : json(outputs),
      },
      `${SECTION}?file=outputs_Tab2.tsv`,
    );
    expect(marked()).toEqual(["4 caf_vd"]);

    // The page with the new line of caf_vd arrives before the edited rows.
    hold = true;
    served = { ...served, files_version: "files-2", targets: { ...served.targets, a: { lines: [2], series: null, total: 3 } } };
    await useStudyStore().refresh();
    await flushPromises();
    expect(answerRows).not.toBeNull();
    expect(marked()).toEqual(["4 caf_vd"]);

    answerRows!(json(edited));
    await flushPromises();
    expect(marked()).toEqual(["2 caf_vd"]);
  });

  it("shows a raw table with the letters of its columns", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=Example_Tab2.tsv`);
    expect(rowsPane().findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B"]);
    expect(rowsPane().findAll("tbody td").map((cell) => cell.text())).toEqual([
      "",
      "Caffeine 150 mg",
      "CL [ml/min/kg]",
      "1.20 ± 0.3",
    ]);
  });

  it("hides empty columns until the switch shows them", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=outputs_Tab2.tsv`);
    const hideEmpty = page()
      .findAll(".v-switch")
      .find((entry) => entry.text().includes("Hide empty columns"))!;
    expect(hideEmpty.get("input").element).toHaveProperty("checked", true);
    expect(rowsPane().findAll("thead th").map((cell) => cell.text())).toEqual([
      "Line",
      "study",
      "source",
      "label",
      "measurement",
      "mean",
      "sd",
      "unit",
    ]);
    expect(caption()).toContain("1 empty column is hidden.");
    await toggle("Hide empty columns");
    expect(rowsPane().findAll("thead th")).toHaveLength(OUTPUTS_HEADER.length + 1);
    expect(caption()).not.toContain("hidden");
  });

  it("opens the table of a problem and moves the focus to its cell", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=outputs_Tab2.tsv&line=3&column=mean`);
    expect(current("file")).toBe("outputs_Tab2.tsv");
    const cell = rowsPane().findAll("tbody tr[data-index]")[1]!.findAll("td")[4]!;
    expect(cell.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(cell.element);
  });

  it("focuses the cell of a raw table by its column letter", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=Example_Tab2.tsv&line=2&column=B`);
    const cell = rowsPane().findAll("tbody tr[data-index]")[1]!.findAll("td")[1]!;
    expect(cell.text()).toBe("1.20 ± 0.3");
    expect(document.activeElement).toBe(cell.element);
  });

  it("says when the line of the route is not a row of the table", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=outputs_Tab2.tsv&line=40`);
    expect(rowsPane().text()).toContain("Line 40 is not a row of outputs_Tab2.tsv.");
  });

  it("opens the table of the source for a file that the study does not have", async () => {
    await mountSection(reviewed(), {}, `${SECTION}?file=missing.tsv`);
    expect(current("source")).toBe("Tab2");
    expect(current("file")).toBe("outputs_Tab2.tsv");
  });

  it("says so when the study has no tables", async () => {
    await mountSection(detail({ sources: [], tables: [] }));
    expect(files()).toHaveLength(0);
    expect(page().find(".rows-pane").exists()).toBe(false);
    expect(page().text()).toContain("The study has no tables yet. Add table adds a sheet to the workbook.");
  });

  it("adds a table with the Add table dialog", async () => {
    await mountSection();
    await press("Add table");
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain("Adds an empty sheet to the workbook.");
    expect(button("Cancel").exists()).toBe(true);
  });
});

describe("loading of the rows", () => {
  it("shows why a table could not be loaded and loads it again on Retry", async () => {
    let failing = true;
    const answer: Handler = () =>
      failing ? json({ error: "The table cannot be read." }, { status: 500 }) : json(outputs);
    await mountSection(detail(), { [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: answer }, `${SECTION}?source=Tab2`);
    expect(rowsPane().text()).toContain("outputs_Tab2.tsv could not be loaded.");
    failing = false;
    await click("Retry");
    expect(rowsPane().text()).not.toContain("could not be loaded");
    expect(lines()).toEqual(["2", "3", "4"]);
  });
});

describe("notes of the tables", () => {
  /** The label of the tab of a section with what screen readers hear after it. */
  function tabLabel(label: string): string | undefined {
    return page()
      .findAll('nav[aria-label="Study sections"] .section-tab-label')
      .map((entry) => entry.text())
      .find((text) => text === label || text.startsWith(`${label},`));
  }

  /** The study with a description of the subjects in study.json. */
  function withNotes(): StudyDetail {
    return detail({
      metadata: {
        revision: "study-1",
        value: studyMetadata({ notes: { subjects: { descriptions: ["Healthy volunteers."], comments: [] } } }),
        issues: [],
      },
    });
  }

  /** Writes study.json as the local server would: the detail has the new revision afterwards. */
  const write: Handler = (body) => {
    served = { ...served, metadata: { revision: "study-2", value: body?.metadata as StudyMetadata, issues: [] } };
    return json({ revision: "study-2", reference: null, reference_error: null });
  };

  const toggle = () => rowsPane().get(".table-notes-toggle");

  /** Refuses study.json with the issues of `fields` and their messages, as the local server does. */
  function refuse(fields: Record<string, string>): Handler {
    const issues: ValidationIssue[] = Object.entries(fields).map(([at, detail]) => ({
      code: "invalid_study_json",
      severity: "error",
      message: `${at}: ${detail}`,
      field: at,
      context: { detail },
    }));
    return () => json({ error: "Invalid study.json", issues }, { status: 422 });
  }

  /** The alert of the failed save in the banner, as the Data section shows it. */
  const failure = () => page().get(".unsaved-banner-failure");

  it("shows the notes of the kind of a table between its head and its rows, and none for a raw table", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=subjects.tsv`);
    expect(toggle().text()).toBe("Notes of the subjects 1 description");
    const order = [...rowsPane().element.children].map((child) => child.classList);
    expect(order.findIndex((classes) => classes.contains("pane-head"))).toBe(0);
    expect(order.findIndex((classes) => classes.contains("table-notes"))).toBeLessThan(
      order.findIndex((classes) => classes.contains("rows-pane-grid")),
    );

    await choose("file", "Example_Tab2.tsv");
    await routed({ file: "Example_Tab2.tsv" }, "partly");
    expect(rowsPane().find(".table-notes").exists()).toBe(false);
  });

  it("shows the same notes for every table of a kind, open or closed", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=timecourses_Fig1.tsv`);
    expect(toggle().text()).toBe("Notes of the timecourses No notes");
    await toggle().trigger("click");
    await choose("file", "timecourses_Fig2.tsv");
    await routed({ file: "timecourses_Fig2.tsv" }, "partly");
    expect(toggle().text()).toBe("Notes of the timecourses No notes");
    expect(toggle().attributes("aria-expanded")).toBe("true");
    await choose("file", "subjects.tsv");
    await routed({ file: "subjects.tsv" }, "partly");
    expect(toggle().attributes("aria-expanded")).toBe("false");
  });

  it("edits the notes in the draft of study.json, marks the Data tab and saves from the banner under the tabs", async () => {
    await mountSection(withNotes(), { [`POST ${METADATA}`]: write }, `${SECTION}?file=subjects.tsv`);
    expect(page().find(".unsaved-banner").exists()).toBe(false);
    await toggle().trigger("click");
    await textArea("Description 1", rowsPane().element).setValue("Healthy adult volunteers.");

    const banner = page().get(".unsaved-banner");
    expect(banner.text()).toContain("Unsaved changes to study.json: Notes of the subjects");
    // Under the section tabs, above the panes of the section.
    expect(page().find(".unsaved-banner + .study-section .data-section").exists()).toBe(true);
    expect(tabLabel("Data")).toBe("Data, unsaved changes");
    expect(tabLabel("Metadata")).toBe("Metadata");

    await click("Save");
    const saves = requests.filter((request) => request.method === "POST" && request.path === METADATA);
    expect(saves.map(({ body }) => body)).toEqual([
      {
        study: "caffeine/Example",
        revision: "study-1",
        metadata: { ...studyMetadata(), notes: { subjects: { descriptions: ["Healthy adult volunteers."], comments: [] } } },
      },
    ]);
    expect(page().get(".unsaved-banner").text()).toContain("study.json saved.");
    expect(tabLabel("Data")).toBe("Data");
  });

  it("lists the issues of a refused save that Data does not show, such as a wrong PMID, with their fields", async () => {
    await mountSection(
      withNotes(),
      {
        [`POST ${METADATA}`]: refuse({
          "reference.pmid": "A PubMed ID has only digits.",
          "curators.0.user": "A user name has no spaces.",
        }),
      },
      `${SECTION}?file=subjects.tsv`,
    );
    // Edits of Metadata, saved from the banner in Data.
    const form = useStudyStore().draft.form!;
    form.reference.pmid = "abc";
    form.curators = [{ user: "the curator", rating: 4 }];
    await flushPromises();
    await click("Save");

    expect(failure().get(".action-failure-text").text()).toBe("study.json was not saved.");
    expect(failure().findAll("li").map((item) => item.text())).toEqual([
      "PMID: A PubMed ID has only digits.",
      "Curators: A user name has no spaces.",
    ]);
  });

  it("marks an issue in the notes of the selected table at its field, and lists those of other notes", async () => {
    await mountSection(
      detail({
        metadata: {
          revision: "study-1",
          value: studyMetadata({
            notes: {
              subjects: { descriptions: ["Healthy volunteers."], comments: [] },
              outputs: { descriptions: ["Read from Table 2."], comments: [] },
            },
          }),
          issues: [],
        },
      }),
      {
        [`POST ${METADATA}`]: refuse({
          "notes.subjects.descriptions.0": "Enter some text or remove this entry.",
          "notes.outputs.descriptions.0": "Enter some text or remove this entry.",
        }),
      },
      `${SECTION}?file=subjects.tsv`,
    );
    await toggle().trigger("click");
    await textArea("Description 1", rowsPane().element).setValue(" ");
    useStudyStore().draft.form!.notes.outputs.descriptions[0] = " ";
    await click("Save");

    expect(messagesOf(textArea("Description 1", rowsPane().element))).toBe("Enter some text or remove this entry.");
    expect(failure().get(".action-failure-text").text()).toBe("study.json was not saved. Fix the marked fields.");
    expect(failure().findAll("li").map((item) => item.text())).toEqual([
      "Descriptions of outputs: Enter some text or remove this entry.",
    ]);
  });

  it("says in Data when study.json changed on disk after the edits started, and reloads it", async () => {
    const disk = studyMetadata({ notes: { subjects: { descriptions: ["Healthy volunteers."], comments: [] } }, licence: "open" });
    await mountSection(
      withNotes(),
      {
        [`POST ${METADATA}`]: () =>
          json({ error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) }, { status: 409 }),
      },
      `${SECTION}?file=subjects.tsv`,
    );
    await toggle().trigger("click");
    await textArea("Description 1", rowsPane().element).setValue("Edited.");
    await click("Save");
    expect(page().get(".unsaved-banner-conflict").text()).toBe(
      "study.json changed on disk after you started editing it. Reload it to keep your edits on top of the new version. Reload",
    );
    await click("Reload");
    expect(useStudyStore().draft.form?.licence).toBe("open");
    expect(textArea("Description 1", rowsPane().element).element.value).toBe("Edited.");
  });

  it("keeps the edits of the notes and the banner while another section opens", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=subjects.tsv`);
    await toggle().trigger("click");
    await textArea("Description 1", rowsPane().element).setValue("Edited.");

    await router.push("/studies/caffeine/Example/metadata");
    await flushPromises();
    expect(buttons("Stay")).toHaveLength(0);
    expect(page().get(".unsaved-banner").text()).toContain("Unsaved changes to study.json");

    await router.push(`${SECTION}?file=subjects.tsv`);
    await flushPromises();
    expect(toggle().attributes("aria-expanded")).toBe("true");
    expect(textArea("Description 1", rowsPane().element).element.value).toBe("Edited.");
  });

  it("shows the banner of an edit in Metadata, which marks the Metadata tab", async () => {
    await mountSection(withNotes(), {}, "/studies/caffeine/Example/metadata");
    await field("Source key").setValue("pkdb.edited");
    await router.push(`${SECTION}?file=subjects.tsv`);
    await flushPromises();

    expect(page().get(".unsaved-banner").text()).toContain("Unsaved changes to study.json");
    expect(tabLabel("Metadata")).toBe("Metadata, unsaved changes");
    expect(tabLabel("Data")).toBe("Data");
  });

  it("opens the notes that a link names, focuses them, and keeps only the selection in the address", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=subjects.tsv&notes=subjects`);
    await routed({ file: "subjects.tsv" });
    expect(toggle().attributes("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(toggle().element);
  });

  it("focuses the notes of a link once, also when the panes stack afterwards", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=subjects.tsv&notes=subjects`);
    await routed({ file: "subjects.tsv" });
    expect(document.activeElement).toBe(toggle().element);
    const sync = button("Sync").element;
    sync.focus();

    // The rows pane and its notes mount again below the source pane.
    setViewport(900);
    await flushPromises();
    expect(page().find(".data-stack .table-notes").exists()).toBe(true);
    expect(toggle().attributes("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(sync);
  });

  it("ignores a link to the notes of a kind that the study does not describe", async () => {
    await mountSection(withNotes(), {}, `${SECTION}?file=subjects.tsv&notes=unknown`);
    await routed({ file: "subjects.tsv" });
    expect(toggle().attributes("aria-expanded")).toBe("false");
  });
});

describe("the paper in the Data section", () => {
  const papers = () => [paperFile("Example.pdf"), paperFile("Example_Supp.pdf", 4_200_000)];
  const paperPane = () => page().find(".paper-pane");

  it("opens a shared table beside the paper when the study has a PDF", async () => {
    await mountSection(detail({ papers: papers() }));
    await routed({ source: "paper", file: "subjects.tsv" });
    expect(paperPane().isVisible()).toBe(true);
    expect(paperPane().attributes("aria-label")).toBe("Paper Example.pdf");
    expect(page().find(".source-pane").exists()).toBe(false);
    expect(page().get(".nav-paper").attributes("aria-current")).toBe("true");
    expect(requests.some((request) => request.path.startsWith(`${EXAMPLE}/sources/`))).toBe(false);
  });

  it("shows a table of one source beside it and keeps the viewer of the paper mounted until the paper shows again", async () => {
    await mountSection(detail({ papers: papers() }));
    await routed({ source: "paper", file: "subjects.tsv" });
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    expect(paperPane().isVisible()).toBe(false);
    expect(page().get(".source-pane").attributes("aria-label")).toBe("Source Tab2");
    // A shared table keeps the source.
    await choose("file", "subjects.tsv");
    await routed({ source: "Tab2", file: "subjects.tsv" });
    await page().get(".nav-paper").trigger("click");
    await routed({ source: "paper", file: "subjects.tsv" });
    expect(paperPane().isVisible()).toBe(true);
    expect(paperViewer.mounts).toBe(1);
  });

  it("keeps the table and its row when the paper is chosen, and a shared table keeps the paper", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=Fig1&file=subjects.tsv&line=3`);
    await page().get(".nav-paper").trigger("click");
    await routed({ source: "paper", file: "subjects.tsv", line: "3" });
    await choose("file", "interventions.tsv");
    await routed({ source: "paper", file: "interventions.tsv" });
  });

  it("keeps the paper when a row of a shared table that names a source is selected beside it", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper&file=subjects.tsv`);
    // Line 4 names Tab2: the curator reads the paper against the rows.
    await page().get('th[scope="row"] button[title="Select line 4"]').trigger("click");
    await routed({ source: "paper", file: "subjects.tsv", line: "4" });
    expect(paperPane().isVisible()).toBe(true);
    expect(page().find(".source-pane").exists()).toBe(false);
  });

  it("shows the source of a linked row of a shared table without drawing the paper while the rows load", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?file=subjects.tsv&line=4`);
    expect(page().get(".source-pane").attributes("aria-label")).toBe("Source Tab2");
    expect(paperPane().exists()).toBe(false);
    expect(paperViewer.mounts).toBe(0);
    // A row without a known source shows the paper, as the table would without a row.
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?file=subjects.tsv&line=5`);
    expect(paperPane().isVisible()).toBe(true);
  });

  it("shows the PDF chosen in the head of the pane, which the address names", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper`);
    await page().get<HTMLSelectElement>(".paper-pane select").setValue("Example_Supp.pdf");
    await routed({ source: "paper", pdf: "Example_Supp.pdf" });
    expect(paperPane().attributes("aria-label")).toBe("Paper Example_Supp.pdf");
    expect(page().get(".paper-viewer-stub").attributes("data-url")).toBe(`${EXAMPLE}/files/Example_Supp.pdf`);
  });

  it("shows the PDF that the address names, as after a reload, and the first one for a PDF that the study lacks", async () => {
    const reloaded = await mountSection(
      detail({ papers: papers() }),
      {},
      `${SECTION}?source=paper&pdf=Example_Supp.pdf&file=subjects.tsv`,
    );
    expect(paperPane().attributes("aria-label")).toBe("Paper Example_Supp.pdf");
    // A row of the table keeps the PDF in the address.
    await page().get('th[scope="row"] button[title="Select line 4"]').trigger("click");
    await routed({ source: "paper", pdf: "Example_Supp.pdf", file: "subjects.tsv", line: "4" });
    expect(paperPane().attributes("aria-label")).toBe("Paper Example_Supp.pdf");
    reloaded.unmount();
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper&pdf=Gone.pdf`);
    expect(paperPane().attributes("aria-label")).toBe("Paper Example.pdf");
  });

  it("names the PDF that the pane shows in the navigator, also while another source shows", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper&file=subjects.tsv`);
    const line = () => page().get(".nav-paper .nav-kind").text();
    expect(line()).toBe("Example.pdf");
    await page().get<HTMLSelectElement>(".paper-pane select").setValue("Example_Supp.pdf");
    await routed({ source: "paper", pdf: "Example_Supp.pdf", file: "subjects.tsv" });
    expect(line()).toBe("Example_Supp.pdf");
    expect(page().get(".nav-paper .nav-more").attributes("title")).toBe("Example.pdf");
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    expect(line()).toBe("Example_Supp.pdf");
  });

  it("keeps the chosen PDF while another source shows, which leaves it out of the address, and names it again with the paper", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper&pdf=Example_Supp.pdf&file=subjects.tsv`);
    await choose("file", "outputs_Tab2.tsv");
    await routed({ source: "Tab2", file: "outputs_Tab2.tsv" });
    await page().get(".nav-paper").trigger("click");
    await routed({ source: "paper", pdf: "Example_Supp.pdf", file: "outputs_Tab2.tsv" });
    expect(paperPane().attributes("aria-label")).toBe("Paper Example_Supp.pdf");
    expect(paperViewer.mounts).toBe(1);
  });

  it("gives the viewer the version of the PDF, which changes when the PDF is written, also at the same size", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper`);
    const viewer = () => page().get(".paper-viewer-stub");
    expect(viewer().attributes("data-version")).toBe(papers()[0]!.version);
    served = detail({ papers: [paperFile("Example.pdf", 19_507, "0b7c3f9d2e6a1458"), papers()[1]!] });
    await useStudyStore().refresh();
    await flushPromises();
    expect(viewer().attributes("data-version")).toBe("0b7c3f9d2e6a1458");
    expect(paperViewer.mounts).toBe(1);
  });

  it("gives the viewer its place back when the panes stack and stand side by side again", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper`);
    await page().get(".paper-viewer-stub button").trigger("click");
    setViewport(900);
    await flushPromises();
    expect(page().find(".data-stack .paper-pane").exists()).toBe(true);
    expect(page().get(".paper-viewer-stub").attributes("data-page")).toBe("3");
    setViewport(1440);
    await flushPromises();
    expect(page().find(".data-split .paper-pane").exists()).toBe(true);
    expect(page().get(".paper-viewer-stub").attributes("data-page")).toBe("3");
    expect(paperViewer.mounts).toBe(3);
  });

  it("shows the source of the table while the PDF is gone from the folder, and the paper again once it is back", async () => {
    await mountSection(detail({ papers: papers() }), {}, `${SECTION}?source=paper&file=subjects.tsv`);
    expect(paperPane().isVisible()).toBe(true);
    served = detail({ papers: [] });
    await useStudyStore().refresh();
    await flushPromises();
    expect(paperPane().exists()).toBe(false);
    expect(page().get(".source-pane").attributes("aria-label")).toBe("Source Fig1");
    expect(page().get(".nav-paper").attributes("disabled")).toBeDefined();
    // The address still asks for the paper, which shows again with its PDF.
    expect(router.currentRoute.value.query).toEqual({ source: "paper", file: "subjects.tsv" });
    served = detail({ papers: papers() });
    await useStudyStore().refresh();
    await flushPromises();
    expect(paperPane().isVisible()).toBe(true);
    expect(paperPane().attributes("aria-label")).toBe("Paper Example.pdf");
    expect(page().find(".source-pane").exists()).toBe(false);
    expect(page().get(".nav-paper").attributes("aria-current")).toBe("true");
  });

  it("falls back to the sources for source=paper without a PDF, whose entry is disabled", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=paper&file=subjects.tsv`);
    expect(paperPane().exists()).toBe(false);
    expect(page().get(".source-pane").attributes("aria-label")).toBe("Source Fig1");
    const entry = page().get(".nav-paper");
    expect(entry.attributes("disabled")).toBeDefined();
    expect(entry.text()).toContain("No Example.pdf");
  });

  it("offers Paper first in the Source select below 1100 px, disabled without a PDF", async () => {
    setViewport(1000);
    const sources = [
      { title: "Fig1", value: "Fig1" },
      { title: "Fig2", value: "Fig2" },
      { title: "Tab2", value: "Tab2" },
      { title: "Tab3", value: "Tab3" },
    ];
    const withPaper = await mountSection(detail({ papers: papers() }));
    expect(labeled(withPaper, VSelect, "Source").props("items")).toEqual([{ title: "Paper", value: "paper" }, ...sources]);
    expect(labeled(withPaper, VSelect, "Source").props("modelValue")).toBe("paper");
    withPaper.unmount();
    const without = await mountSection(detail());
    expect(labeled(without, VSelect, "Source").props("items")).toEqual([
      { title: "No Example.pdf", value: "paper", props: { disabled: true } },
      ...sources,
    ]);
  });

  it("offers no Source select below 1100 px for a study without sources and a PDF, and the paper alone for one with a PDF", async () => {
    setViewport(1000);
    const without = await mountSection(detail({ sources: [] }));
    expect(() => labeled(without, VSelect, "Source")).toThrow('No field "Source"');
    expect(page().get(".data-pane-note").text()).toBe("The study has no sources yet.");
    without.unmount();
    const withPaper = await mountSection(detail({ sources: [], papers: papers() }));
    expect(labeled(withPaper, VSelect, "Source").props("items")).toEqual([{ title: "Paper", value: "paper" }]);
    expect(paperPane().isVisible()).toBe(true);
  });
});
