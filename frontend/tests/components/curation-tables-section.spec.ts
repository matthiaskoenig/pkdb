import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { RouterView, type Router } from "vue-router";
import type {
  ConflictData,
  StudyDetail,
  SyncState,
  TableResponse,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, reviewItem, snapshot, studyDetail } from "../unit/curation-fixtures";
import { button, page, serveApi, setViewport, type Handler, type ServedRequest } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const TABLES = "/local/studies/tables";
const SECTION = "/studies/caffeine/Example/tables";

const OUTPUTS_HEADER = ["study", "source", "label", "measurement", "mean", "sd", "unit", "comment"];

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
const subjects: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "source", "name", "count"],
  rows: [{ line: 2, cells: ["Example", "Tab2", "all", "8"] }],
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

const conflict: ConflictData = {
  file: "outputs_Tab2.tsv",
  sheet: "outputs_Tab2",
  workbook_rows: [{ row: 4, text: "Example\tTab2\tcaf_thalf\tthalf\t4.9\t\th\t" }],
  table_lines: [{ line: 3, text: "Example\tTab2\tcaf_thalf\tthalf\t5.1\t\th\t" }],
  base_lines: ["Example\tTab2\tcaf_thalf\tthalf\t4.8\t\th\t"],
  kept: null,
};

const synced: TablesResult = { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [] };

function problem(
  code: string,
  row: number,
  header: string,
  severity: ValidationIssue["severity"] = "error",
): ValidationIssue {
  return {
    code,
    severity,
    message: `${code} at line ${row}`,
    source: { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row, header },
  };
}

function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
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
    problems: [problem("invalid_number", 3, "mean"), problem("unknown_unit", 4, "unit", "warning")],
    counts: { errors: 1, warnings: 1 },
    ...changes,
  });
}

function sync(status: SyncState["status"], changes = 0): Pick<StudyDetail, "sync"> {
  return { sync: { status, changes, conflicts: status === "conflict" ? 1 : 0 } };
}

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
    [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: outputs,
    [`GET ${EXAMPLE}/tables/subjects.tsv`]: subjects,
    [`GET ${EXAMPLE}/tables/Example_Tab2.tsv`]: raw,
    [`GET ${EXAMPLE}/tables/interventions.tsv`]: empty("interventions.tsv"),
    [`GET ${EXAMPLE}/tables/characteristica.tsv`]: empty("characteristica.tsv"),
    [`GET ${EXAMPLE}/tables/timecourses_Fig1.tsv`]: empty("timecourses_Fig1.tsv"),
    [`POST ${TABLES}`]: synced,
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(path);
  await router.isReady();
  const wrapper = mount(RouterView, { attachTo: document.body, global: { plugins: [pinia, router] } });
  await flushPromises();
  return wrapper;
}

function tabs(): DOMWrapper<Element>[] {
  return page().findAll('[role="tab"]');
}

function panel() {
  return page().get('[role="tabpanel"]');
}

function alertText(): string {
  return page().get(".tables-sync").text().replace(/\s+/g, " ").trim();
}

function posted(): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === TABLES).map(({ body }) => body);
}

/** Clicks the button `name` of the section; the header has buttons of the same names. */
async function press(name: string): Promise<void> {
  const found = page()
    .get(".tables")
    .findAll("button")
    .filter((candidate) => candidate.text().replace(/\s+/g, " ").trim() === name);
  if (found.length !== 1) throw new Error(`Expected one button "${name}", found ${found.length}`);
  await found[0]!.trigger("click");
  await flushPromises();
}

async function openTab(name: string): Promise<void> {
  const tab = tabs().find((entry) => entry.get(".tab-name").text() === name);
  if (!tab) throw new Error(`No tab ${name}`);
  await tab.trigger("click");
  await flushPromises();
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  disposePinia(pinia);
  // @ts-expect-error jsdom has no scrollIntoView; the stub goes again.
  delete Element.prototype.scrollIntoView;
});

describe("sync status", () => {
  it.each([
    ["in_sync", 0, "In sync"],
    ["workbook_open", 0, "Workbook open: close it to sync"],
    ["syncing", 0, "Syncing"],
    ["changed", 3, "Changed: the next sync writes 3 files"],
    ["no_workbook", 0, "No workbook yet: Open tables creates it"],
    ["not_checked", 0, "Not checked yet"],
  ] as const)("says %s first", async (status, changes, text) => {
    await mountSection(detail(sync(status, changes)));
    expect(alertText()).toBe(text);
    // The status comes before the tabs.
    const alert = page().get(".tables-sync").element;
    expect(alert.compareDocumentPosition(tabs()[0]!.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("names the conflicting file", async () => {
    await mountSection(detail({ ...sync("conflict"), conflicts: [conflict] }));
    expect(alertText()).toBe("Conflict in outputs_Tab2.tsv");
  });

  it("syncs, and then says what the sync did", async () => {
    await mountSection(detail(sync("changed", 1)), {
      [`POST ${TABLES}`]: (() => {
        served = detail(sync("in_sync"));
        return json({ ...synced, changes: [{ file: "outputs_Tab2.tsv", action: "write" }] });
      }) satisfies Handler,
    });
    await press("Sync");
    expect(posted()).toEqual([{ action: "sync", study: "caffeine/Example" }]);
    expect(page().get(".tables-sync-text").text()).toBe("In sync");
    expect(page().get(".tables-sync-summary").text()).toBe("The last sync in the app wrote outputs_Tab2.tsv.");
    expect(page().get(".tables-notice").text()).toBe("Synced the workbook and the tables.");
  });

  it("lists the problems of a failed sync until they are dismissed", async () => {
    await mountSection(detail(sync("changed", 1)), {
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

  it("opens the workbook with Open tables", async () => {
    await mountSection(detail(sync("no_workbook")), {
      [`POST ${TABLES}`]: { ...synced, workbook_action: "created", opened: true },
    });
    await press("Open tables");
    expect(posted()).toEqual([{ action: "open", study: "caffeine/Example" }]);
    expect(page().get(".tables-notice").text()).toBe("The workbook opened.");
  });
});

describe("conflicts", () => {
  it("shows the last sync, the workbook and the tables side by side in the cells of the table", async () => {
    await mountSection(detail({ ...sync("conflict"), conflicts: [conflict] }));
    const panelElement = page().get(".conflict-panel");
    expect(panelElement.get(".conflict-file-name").text()).toBe("outputs_Tab2.tsv");
    const sides = panelElement.findAll(".conflict-side");
    expect(sides.map((side) => side.get("h5").text())).toEqual(["Last sync", "Workbook", "Tables"]);
    // The columns with a value, under the header of the table; the column that differs first.
    expect(sides[1]!.findAll("thead th").map((cell) => cell.text())).toEqual([
      "Row",
      "mean, changed",
      "study",
      "source",
      "label",
      "measurement",
      "unit",
    ]);
    expect(sides[0]!.findAll("thead th")[0]?.text()).toBe("mean, changed");
    expect(sides[1]!.get("tbody th").text()).toBe("4");
    expect(sides[2]!.get("tbody th").text()).toBe("3");
    expect(sides.map((side) => side.findAll("tbody td")[0]?.text())).toEqual(["4.8", "4.9", "5.1"]);
  });

  it("keeps the workbook and lists the problems of the sync that follows", async () => {
    await mountSection(detail({ ...sync("conflict"), conflicts: [conflict] }), {
      [`POST ${TABLES}`]: (() => {
        served = detail(sync("unknown"));
        return json({
          ...synced,
          ok: false,
          conflicts: [{ ...conflict, kept: "workbook" }],
          issues: [{ code: "invalid_number", severity: "error", message: "The mean on row 4 is not a number." }],
        });
      }) satisfies Handler,
    });
    await press("Keep workbook");
    expect(posted()).toEqual([{ action: "resolve", keep: "workbook", study: "caffeine/Example" }]);
    const failure = page().get(".action-failure").text();
    expect(failure).toContain("Kept the workbook rows, but the sync found problems.");
    expect(failure).toContain("The mean on row 4 is not a number.");
    expect(page().find(".conflict-panel").exists()).toBe(false);
  });

  it("keeps the tables", async () => {
    await mountSection(detail({ ...sync("conflict"), conflicts: [conflict] }), {
      [`POST ${TABLES}`]: (() => {
        served = detail(sync("in_sync"));
        return json({ ...synced, workbook_action: "regenerated", conflicts: [{ ...conflict, kept: "tables" }] });
      }) satisfies Handler,
    });
    await press("Keep tables");
    expect(posted()).toEqual([{ action: "resolve", keep: "tables", study: "caffeine/Example" }]);
    expect(page().get(".tables-notice").text()).toBe("Kept the table rows. The workbook and the tables are in sync.");
  });

  it("opens the workbook to edit the conflicting rows", async () => {
    await mountSection(detail({ ...sync("conflict"), conflicts: [conflict] }), {
      [`POST ${TABLES}`]: { ...synced, ok: false, conflicts: [conflict], opened: true },
    });
    await press("Open workbook");
    expect(posted()).toEqual([{ action: "open", study: "caffeine/Example" }]);
    // The panel shows the conflict already.
    expect(page().find(".action-failure").exists()).toBe(false);
    expect(page().get(".tables-notice").text()).toBe("The workbook opened.");
  });
});

describe("tabs", () => {
  it("shows one tab per table and raw table in the workbook order, with their problems and open items", async () => {
    await mountSection();
    expect(tabs().map((tab) => tab.get(".tab-name").text())).toEqual([
      "subjects.tsv",
      "interventions.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Example_Tab2.tsv",
    ]);
    const tab = tabs()[3]!;
    expect(tab.get(".tab-count--problems").text()).toBe("2, 2 problems");
    expect(tab.get(".tab-count--items").text()).toBe("1, 1 open review item");
    expect(tabs()[0]!.find(".tab-count").exists()).toBe(false);
    expect(tabs()[0]?.attributes("aria-selected")).toBe("true");
    expect(panel().attributes("aria-labelledby")).toBe(tabs()[0]?.attributes("id"));
  });

  it("shows the rows of the chosen table with the targets of open items and the cells with problems", async () => {
    await mountSection();
    await openTab("outputs_Tab2.tsv");
    await vi.waitFor(() => expect(router.currentRoute.value.query.file).toBe("outputs_Tab2.tsv"));
    expect(panel().findAll("tbody th").map((cell) => cell.text())).toEqual(["2", "3", "4"]);
    const rows = panel().findAll("tbody tr");
    expect(rows.map((row) => row.classes().includes("grid-row--target"))).toEqual([false, false, true]);
    expect(rows[1]!.findAll("td")[4]!.classes()).toContain("grid-cell--error");
    expect(rows[2]!.findAll("td")[6]!.classes()).toContain("grid-cell--warning");
    expect(panel().get(".tables-caption").text()).toBe(
      "3 rows. Open review items target 1 row. 2 cells have problems.",
    );
  });

  it("counts the open items about the whole table and those that match no row", async () => {
    const value = detail();
    const items = [
      reviewItem({ id: "c", target: { file: "outputs_Tab2.tsv", column: "sd" } }),
      reviewItem({ id: "d", target: { file: "outputs_Tab2.tsv", rows: {} } }),
      reviewItem({ id: "e", target: { file: "outputs_Tab2.tsv", rows: { label: "caf_auc" } } }),
    ];
    await mountSection(
      { ...value, review: { ...value.review, value: { ...value.review.value!, items } }, problems: [] },
      {},
      `${SECTION}?file=outputs_Tab2.tsv`,
    );
    expect(panel().get(".tables-caption").text()).toBe(
      "3 rows. 2 open review items are about the whole table. 1 open review item matches no row.",
    );
  });

  it("shows a raw table with the letters of its columns", async () => {
    await mountSection(detail(), {}, `${SECTION}?file=Example_Tab2.tsv`);
    expect(panel().findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B"]);
    expect(panel().findAll("tbody td").map((cell) => cell.text())).toEqual([
      "",
      "Caffeine 150 mg",
      "CL [ml/min/kg]",
      "1.20 ± 0.3",
    ]);
  });

  it("hides empty columns", async () => {
    await mountSection(detail(), {}, `${SECTION}?file=outputs_Tab2.tsv`);
    expect(panel().findAll("thead th")).toHaveLength(OUTPUTS_HEADER.length + 1);
    await page().get('input[type="checkbox"]').setValue(true);
    await flushPromises();
    expect(panel().findAll("thead th").map((cell) => cell.text())).toEqual([
      "Line",
      "study",
      "source",
      "label",
      "measurement",
      "mean",
      "sd",
      "unit",
    ]);
    expect(panel().get(".tables-caption").text()).toContain("1 empty column is hidden.");
  });

  it("opens the table of a problem and moves the focus to its cell", async () => {
    await mountSection(detail(), {}, `${SECTION}?file=outputs_Tab2.tsv&line=3&column=mean`);
    expect(tabs()[3]?.attributes("aria-selected")).toBe("true");
    const cell = panel().findAll("tbody tr")[1]!.findAll("td")[4]!;
    expect(cell.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(cell.element);
  });

  it("says when the line of the route is not a row of the table", async () => {
    await mountSection(detail(), {}, `${SECTION}?file=outputs_Tab2.tsv&line=40`);
    expect(panel().text()).toContain("Line 40 is not a row of outputs_Tab2.tsv.");
  });

  it("opens the first table for a file that the study does not have", async () => {
    await mountSection(detail(), {}, `${SECTION}?file=missing.tsv`);
    expect(tabs()[0]?.attributes("aria-selected")).toBe("true");
  });

  it("adds a table with the Add table dialog", async () => {
    await mountSection();
    await press("Add table");
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain("Adds an empty sheet to the workbook.");
    expect(button("Cancel").exists()).toBe(true);
  });
});
