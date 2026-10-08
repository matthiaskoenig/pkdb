import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import { RouterView, type Router } from "vue-router";
import type { SourcePoint, SourceView, StudyDetail, ValidationIssue } from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, snapshot, sourceSummary, studyDetail } from "../unit/curation-fixtures";
import { button, click, page, serveApi, setViewport, type Handler, type ServedRequest } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const SECTION = "/studies/caffeine/Example/sources";

const OUTPUTS_HEADER = ["study", "source", "label", "measurement", "mean", "sd", "unit", "comment"];
const TIMECOURSES_HEADER = ["study", "source", "label", "time", "time_unit", "mean", "unit", "error_bar"];

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
      header: ["study", "source", "name", "count"],
      rows: [[4, ["Example", "Tab2", "all", "8"]]],
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
      { file: "subjects.tsv", kind: "subjects" },
      { file: "interventions.tsv", kind: "interventions" },
      { file: "characteristica.tsv", kind: "characteristica" },
      { file: "outputs_Tab2.tsv", kind: "outputs" },
      { file: "timecourses_Fig1.tsv", kind: "timecourses" },
      { file: "timecourses_Fig2.tsv", kind: "timecourses" },
      { file: "Example_Tab2.tsv", kind: "raw" },
    ],
    ...changes,
  });
}

/** The figure overlay is drawn by Plotly; the section passes it the view and the mode, and follows its row clicks. */
const OverlayStub = defineComponent({
  name: "SourceOverlay",
  props: {
    view: { type: Object as PropType<SourceView>, required: true },
    highlight: { type: String as PropType<string | null>, default: null },
    mode: { type: String as PropType<"overlay" | "plot">, default: undefined },
  },
  emits: ["select-row"],
  setup(props, { emit }) {
    return () =>
      h("div", { class: "overlay-stub", "data-mode": props.mode ?? "auto" }, [
        `${props.view.source} overlay`,
        h(
          "button",
          { type: "button", onClick: () => emit("select-row", { file: "timecourses_Fig1.tsv", line: 3 }) },
          `Select line 3 of ${props.view.source} ${props.mode ?? "auto"}`,
        ),
      ]);
  },
});

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];

async function mountSection(served: StudyDetail = detail(), routes: Record<string, unknown> = {}, path = SECTION) {
  requests = serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: served,
    "GET /local/curators": { curators: [] },
    [`GET ${EXAMPLE}/sources/Fig1`]: digitized,
    [`GET ${EXAMPLE}/sources/Fig2`]: plain,
    [`GET ${EXAMPLE}/sources/Tab2`]: table,
    [`GET ${EXAMPLE}/sources/Tab3`]: missing,
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(path);
  await router.isReady();
  const wrapper = mount(RouterView, {
    attachTo: document.body,
    global: { plugins: [pinia, router], stubs: { SourceOverlay: OverlayStub } },
  });
  await flushPromises();
  return wrapper;
}

function tabs(): DOMWrapper<Element>[] {
  return page().findAll('[role="tab"]');
}

/** The panel of the chosen source. */
function panel() {
  return page().get('[role="tabpanel"]');
}

async function openTab(name: string): Promise<void> {
  const tab = tabs().find((entry) => entry.text() === name);
  if (!tab) throw new Error(`No tab ${name}`);
  await tab.trigger("click");
  await flushPromises();
}

function fetched(path: string): number {
  return requests.filter((request) => request.method === "GET" && request.path === path).length;
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("tabs", () => {
  it("shows one tab per source and opens the first", async () => {
    await mountSection();
    expect(tabs().map((tab) => tab.text())).toEqual(["Fig1", "Fig2", "Tab2", "Tab3"]);
    expect(tabs()[0]?.attributes("aria-selected")).toBe("true");
    expect(panel().attributes("aria-labelledby")).toBe(tabs()[0]?.attributes("id"));
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(1);
    expect(fetched(`${EXAMPLE}/sources/Tab2`)).toBe(0);
  });

  it("puts the chosen source in the route", async () => {
    await mountSection();
    await openTab("Tab2");
    await vi.waitFor(() => expect(router.currentRoute.value.query.source).toBe("Tab2"));
    expect(tabs()[2]?.attributes("aria-selected")).toBe("true");
    expect(panel().text()).toContain("Caffeine 150 mg");
    expect(panel().attributes("aria-labelledby")).toBe(tabs()[2]?.attributes("id"));
  });

  it("opens the source of the route", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig2`);
    expect(tabs()[1]?.attributes("aria-selected")).toBe("true");
    expect(fetched(`${EXAMPLE}/sources/Fig2`)).toBe(1);
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(0);
  });

  it("lets the keyboard reach the panel, whose first content is no control", async () => {
    await mountSection();
    expect(panel().attributes("tabindex")).toBe("0");
  });

  it("opens the first source for a source that the study does not have", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Fig9`);
    expect(tabs()[0]?.attributes("aria-selected")).toBe("true");
  });

  it("says so when the study has no sources", async () => {
    await mountSection(detail({ sources: [] }));
    expect(tabs()).toHaveLength(0);
    expect(page().text()).toContain("The study has no sources yet.");
  });
});

describe("table sources", () => {
  it("shows the image, the raw extraction as printed and the mapped rows by table with their lines", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab2`);
    const image = panel().get("img");
    expect(image.attributes("alt")).toBe("Tab2 of caffeine/Example");
    expect(image.attributes("src")).toBe(`${EXAMPLE}/files/Example_Tab2.png`);
    expect(image.attributes("width")).toBe("640");
    expect(image.attributes("height")).toBe("220");

    const raw = panel().get('[aria-label="Raw extraction Example_Tab2.tsv"]');
    const cells = raw.findAll("td").map((cell) => cell.text());
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
    expect(raw.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B", "C"]);
    expect(raw.findAll("tbody th").map((cell) => cell.text())).toEqual(["1", "2", "3"]);

    const groups = panel().findAll(".mapped-table");
    expect(groups.map((group) => group.get("h4").text())).toEqual(["outputs_Tab2.tsv", "subjects.tsv"]);
    const outputs = groups[0]!;
    // The study and source columns and empty columns are left out.
    expect(outputs.findAll("thead th").map((cell) => cell.text())).toEqual([
      "Line",
      "label",
      "measurement",
      "mean",
      "sd",
      "unit",
    ]);
    expect(outputs.findAll("tbody th").map((cell) => cell.text())).toEqual(["2", "3"]);
    expect(outputs.findAll("tbody tr")[0]?.findAll("td").map((cell) => cell.text())).toEqual([
      "caf_cl",
      "clearance",
      "1.2",
      "0.3",
      "ml/min/kg",
    ]);
  });

  it("links each mapped row to its line in the Tables section", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab2`);
    const link = panel().get('a[aria-label="Show line 3 of outputs_Tab2.tsv in the Tables section"]');
    expect(link.attributes("href")).toBe("#/studies/caffeine/Example/tables?file=outputs_Tab2.tsv&line=3");
  });

  it("names the missing files of a paper table", async () => {
    await mountSection(detail(), {}, `${SECTION}?source=Tab3`);
    expect(panel().text()).toContain("No image: add Example_Tab3.png");
    expect(panel().text()).toContain("No raw extraction: add Example_Tab3.tsv");
    expect(panel().text()).toContain("Use Add table in the study menu to add it as a sheet of the workbook.");
    expect(panel().text()).toContain("No rows of the tables name Tab3 as their source.");
    expect(panel().find("img").exists()).toBe(false);
  });
});

describe("figure sources", () => {
  it("draws the digitized figure with the overlay and lists the series without a dataset", async () => {
    const wrapper = await mountSection();
    const overlays = wrapper.findAllComponents(OverlayStub);
    expect(overlays[0]?.props("view")).toEqual(digitized);
    expect(overlays[0]?.props("mode")).toBe("overlay");
    expect(panel().text()).toContain("Not digitized: caf_plasma_D75");
    // The rows without a dataset are drawn beside the figure.
    expect(overlays[1]?.props("mode")).toBe("plot");
    expect(overlays).toHaveLength(2);
    expect(panel().findAll(".mapped-table").map((group) => group.get("h4").text())).toEqual(["timecourses_Fig1.tsv"]);
    expect(panel().text()).not.toContain("No raw extraction");
  });

  it("draws no plot beside the overlay when every series has a dataset", async () => {
    const wrapper = await mountSection(detail(), { [`GET ${EXAMPLE}/sources/Fig1`]: { ...digitized, unmatched: [] } });
    expect(wrapper.findAllComponents(OverlayStub).map((overlay) => overlay.props("mode"))).toEqual(["overlay"]);
    expect(panel().text()).not.toContain("Not digitized");
  });

  it("shows the image beside a plot of the mapped rows without a digitization", async () => {
    const wrapper = await mountSection(detail(), {}, `${SECTION}?source=Fig2`);
    const image = panel().get("img");
    expect(image.attributes("alt")).toBe("Fig2 of caffeine/Example");
    const overlays = wrapper.findAllComponents(OverlayStub);
    expect(overlays).toHaveLength(1);
    expect(overlays[0]?.props("mode")).toBe("plot");
    expect(overlays[0]?.props("view")).toEqual(plain);
    expect(panel().text()).toContain("No raw extraction: add Example_Fig2.wpd.json");
    expect(panel().text()).not.toContain("Not digitized");
  });

  it("names the missing image of a figure", async () => {
    const view: SourceView = { ...plain, image: null, image_url: null, image_size: null };
    const base = detail();
    const sources = base.sources.map((entry) =>
      entry.source === "Fig2" ? { ...entry, image: null, missing_image: "Example_Fig2.png" } : entry,
    );
    await mountSection({ ...base, sources }, { [`GET ${EXAMPLE}/sources/Fig2`]: view }, `${SECTION}?source=Fig2`);
    expect(panel().text()).toContain("No image: add Example_Fig2.png");
    expect(panel().find("img").exists()).toBe(false);
  });

  it("opens the Tables section at the file and line of a clicked mapped point", async () => {
    await mountSection();
    await click("Select line 3 of Fig1 overlay");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/studies/caffeine/Example/tables"));
    expect(router.currentRoute.value.query).toEqual({ file: "timecourses_Fig1.tsv", line: "3" });
  });
});

describe("loading", () => {
  it("shows why a source could not be loaded and loads it again on Retry", async () => {
    let failing = true;
    const answer: Handler = () => (failing ? json({ error: "The image cannot be read." }, { status: 500 }) : json(table));
    await mountSection(detail(), { [`GET ${EXAMPLE}/sources/Tab2`]: answer }, `${SECTION}?source=Tab2`);
    expect(panel().text()).toContain("Tab2 could not be loaded.");
    failing = false;
    await click("Retry");
    expect(panel().text()).not.toContain("could not be loaded");
    expect(panel().get("img").attributes("alt")).toBe("Tab2 of caffeine/Example");
  });
});

describe("problems", () => {
  const mismatch: ValidationIssue = {
    code: "digitized_mismatch",
    severity: "warning",
    message: "Line 3 lies 4.1 pixels from every point of dataset caf_plasma_D150.",
    source: { file: "timecourses_Fig1.tsv", sheet: "timecourses_Fig1", row: 3, column: "F", cell: "F3", header: "mean" },
  };
  const other: ValidationIssue = {
    code: "unused_intervention",
    severity: "warning",
    message: "'caf_po_300' is not referenced by any row",
    source: { file: "interventions.tsv", sheet: "interventions", row: 3, column: "B", cell: "B3", header: "name" },
  };

  it("lists the problems of the files of the source with a link to the cell", async () => {
    await mountSection(detail({ problems: [mismatch, other], counts: { errors: 0, warnings: 2 } }));
    const problems = panel().get(".source-problems");
    expect(problems.text()).toContain("digitized_mismatch");
    expect(problems.text()).toContain(mismatch.message);
    expect(problems.text()).not.toContain("unused_intervention");
    const link = problems.get("a");
    expect(link.text()).toBe("Show in table");
    expect(link.attributes("href")).toBe("#/studies/caffeine/Example/tables?file=timecourses_Fig1.tsv&line=3&column=mean");
  });

  it("shows the problems as the Problems section does: by file, errors first, without Acknowledge", async () => {
    const unknown: ValidationIssue = {
      code: "invalid_digitization",
      severity: "error",
      message: "The project has no calibration.",
      source: { file: "Example_Fig1.wpd.json", path: [] },
    };
    await mountSection(detail({ problems: [mismatch, unknown], counts: { errors: 1, warnings: 1 } }));
    const problems = panel().get(".source-problems");
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
    expect(panel().find(".source-problems").exists()).toBe(false);
    expect(button("Select line 3 of Fig1 overlay").exists()).toBe(true);
  });
});
