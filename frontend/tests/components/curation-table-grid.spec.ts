import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { h } from "vue";
import type { ColumnClass, StudyNameLines, TableResponse, ValidationIssue } from "../../src/study-views/types";
import TableGrid from "../../src/curation-app/components/TableGrid.vue";
import { VTooltip } from "vuetify/components";
import { TIP_DELAY, TIP_LINGER } from "../../src/study-views/composables/useCellTip";
import { HEADER_LINE, issueCells, ROW, type CellIssues, type IssueCells } from "../../src/study-views/grid";
import { setViewport } from "./curation-dom";

enableAutoUnmount(afterEach);

/** The problems of a cell with these messages, as `issueCells` gives them. */
function cellIssues(severity: ValidationIssue["severity"], ...messages: string[]): CellIssues {
  return { severity, issues: messages.map((message) => ({ code: "problem", severity, message })) };
}

const HEADER = ["study", "source", "label", "time", "mean", "comment"];

const small: TableResponse = {
  file: "timecourses_Fig1.tsv",
  kind: "table",
  header: HEADER,
  rows: [
    { line: 1, cells: ["Example", "Fig1", "caf_plasma_D150", "0.5", "2.419", ""] },
    { line: 2, cells: ["Example", "Fig1", "caf_plasma_D150", "1", "3.1", ""] },
    { line: 3, cells: ["Example", "Fig1", "caf_plasma_D75", "0.5", "1.2", ""] },
  ],
};

/** The lines of the names of the subjects and the interventions, as the study page has them. */
const NAMES: StudyNameLines = {
  subjects: { file: "subjects.tsv", lines: { all: 1, S1: 2 } },
  interventions: { file: "interventions.tsv", lines: { D1: 1, D2: 2 } },
};

/** Rows whose cells name subjects and interventions, known and unknown; `name` names no other row. */
const named: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "subjects", "interventions", "measurement", "name"],
  rows: [
    { line: 1, cells: ["Example", "Tab2", "all", "D1,D2", "cmax", "all"] },
    { line: 2, cells: ["Example", "Tab2", "S9", "D1, D9", "tmax", ""] },
  ],
};

/** The classes of the columns of HEADER, as the local server classes a timecourse table. */
const CLASSES: ColumnClass[] = ["meta", "meta", "data", "data", "data", "data"];

/** A timecourse table with `count` rows on the lines 1 to `count`, and the classes of its columns when given. */
function large(count = 5000, classes?: ColumnClass[]): TableResponse {
  return {
    file: "timecourses_Fig1.tsv",
    kind: "table",
    header: HEADER,
    ...(classes ? { classes } : {}),
    rows: Array.from({ length: count }, (_, index) => ({
      line: index + 1,
      cells: ["Example", "Fig1", `series_${Math.floor(index / 50)}`, String(index % 50), String(index / 10), ""],
    })),
  };
}

/** The classes of `classed`. */
const CLASSED: ColumnClass[] = ["meta", "meta", "data", "subjects", "interventions", "data", "data"];

/** A timecourse table as the local server serves it, with the class of each column; `comment` is empty. */
const classed: TableResponse = {
  file: "timecourses_Fig1.tsv",
  kind: "table",
  header: ["study", "source", "label", "subjects", "interventions", "mean", "comment"],
  classes: CLASSED,
  rows: [
    { line: 1, cells: ["Example", "Fig1", "caf_plasma_D150", "all", "D150", "2.419", ""] },
    { line: 2, cells: ["Example", "Fig1", "caf_plasma_D150", "all", "D150", "3.1", ""] },
  ],
};

/** A raw table as printed. */
const printed: TableResponse = { file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["CL", "1.20 ± 0.3"] }] };

/** The class of a cell of the grid by its `grid-info--` class; null without one. */
function infoOf(cell: DOMWrapper<Element>): string | null {
  return cell.classes().find((name) => name.startsWith("grid-info--"))?.slice("grid-info--".length) ?? null;
}

let scrolled: Element[];

beforeEach(() => {
  scrolled = [];
  // jsdom has no layout: scrolling an element into view records it.
  vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(function (this: Element) {
    scrolled.push(this);
  });
});

function lines(wrapper: VueWrapper): string[] {
  return wrapper.findAll("tbody tr:not([aria-hidden])").map((row) => row.get("th").text());
}

function region(wrapper: VueWrapper): HTMLElement {
  return wrapper.get<HTMLElement>('[role="region"]').element;
}

/**
 * The rules of the style of TableGrid, read from its source, as jsdom applies no style of a
 * component. Scoped selectors match without their attribute.
 */
function gridRules(): CSSStyleRule[] {
  // In a variable: Vite turns `new URL` of a literal into the URL of an asset.
  const source = "../../src/curation-app/components/TableGrid.vue";
  const path = fileURLToPath(new URL(source, import.meta.url).href);
  const style = document.createElement("style");
  style.textContent = /<style scoped>([\s\S]*)<\/style>/.exec(readFileSync(path, "utf8"))![1]!;
  document.head.append(style);
  const rules = [...style.sheet!.cssRules].filter((rule): rule is CSSStyleRule => "selectorText" in rule);
  style.remove();
  return rules;
}

/** What the rules of TableGrid that match `element` declare for `property`, in their order; jsdom matches no `:hover`. */
function declared(element: Element, property: string): string[] {
  return gridRules()
    .filter((rule) => rule.style.getPropertyValue(property) && !rule.selectorText.includes("::") && element.matches(rule.selectorText))
    .map((rule) => rule.style.getPropertyValue(property));
}

/** The text of the elements that describe `element`. */
function description(element: Element): string {
  return (element.getAttribute("aria-describedby") ?? "")
    .split(" ")
    .filter(Boolean)
    .map((id) => document.getElementById(id)?.textContent ?? "")
    .join(" ");
}

describe("TableGrid", () => {
  it("shows the header and the rows with their lines in the file", () => {
    const wrapper = mount(TableGrid, { props: { table: small } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line 0", ...HEADER]);
    expect(lines(wrapper)).toEqual(["1", "2", "3"]);
    expect(wrapper.findAll("tbody tr")[1]?.findAll("td").map((cell) => cell.text())).toEqual([
      "Example",
      "Fig1",
      "caf_plasma_D150",
      "1",
      "3.1",
      "",
    ]);
    expect(region(wrapper).getAttribute("aria-label")).toBe("Rows of timecourses_Fig1.tsv");
    expect(region(wrapper).classList).toContain("rows-scroll--sticky-line");
    expect(wrapper.get("table").attributes("aria-rowcount")).toBe("4");
  });

  it("colors the rows of open review items amber and outlines the cells with problems", () => {
    const issues: IssueCells = new Map([
      [2, new Map<string, CellIssues>([["mean", cellIssues("error", "The mean is not a number.")]])],
      [3, new Map<string, CellIssues>([[ROW, cellIssues("warning", "The row repeats line 1.")]])],
    ]);
    const wrapper = mount(TableGrid, {
      props: { table: small, highlightLines: new Set([1, 3]), issueCells: issues },
      attachTo: document.body,
    });
    const rows = wrapper.findAll("tbody tr");
    expect(rows.map((row) => row.classes().includes("grid-row--target"))).toEqual([true, false, true]);
    expect(description(rows[0]!.get("th").element)).toBe("Targeted by an open review item.");

    const cell = rows[1]!.findAll("td")[4]!;
    expect(cell.classes()).toContain("grid-cell--error");
    expect(description(cell.element)).toBe("Error: The mean is not a number.");
    // An issue of the whole row outlines its line.
    const line = rows[2]!.get("th");
    expect(line.classes()).toContain("grid-cell--warning");
    expect(description(line.element)).toBe("Targeted by an open review item. Warning: The row repeats line 1.");
    // The descriptions add no text to the cells.
    expect(cell.text()).toBe("3.1");
  });

  it("shows line 0 in the line cell of the header of a table, and the title of the column otherwise", () => {
    const table = mount(TableGrid, { props: { table: small } });
    const corner = table.get("thead th.rows-line");
    expect(corner.text()).toBe("Line 0");
    expect(corner.get(".d-sr-only").text()).toBe("Line");
    const raw: TableResponse = { file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["a"] }] };
    expect(mount(TableGrid, { props: { table: raw } }).get("thead th.rows-line").text()).toBe("Line");
    const versions = mount(TableGrid, { props: { table: small, lineHeader: "Version", headerLine: false } });
    expect(versions.get("thead th.rows-line").text()).toBe("Version");
  });

  it("outlines a header cell with a problem of the header, line 0 of a table", () => {
    const issues: IssueCells = new Map([
      [0, new Map<string, CellIssues>([["mean", cellIssues("error", "Unknown column 'meen'.")]])],
    ]);
    const wrapper = mount(TableGrid, { props: { table: small, issueCells: issues }, attachTo: document.body });
    const header = wrapper.findAll("thead th").find((cell) => cell.text() === "mean")!;
    expect(header.classes()).toContain("grid-cell--error");
    expect(description(header.element)).toBe("Error: Unknown column 'meen'.");
  });

  it("marks a column, and hides empty columns except the ones to show", () => {
    const issues: IssueCells = new Map([
      [2, new Map<string, CellIssues>([["comment", cellIssues("warning", "Add a comment.")]])],
    ]);
    const wrapper = mount(TableGrid, { props: { table: small, markColumn: "mean", hideEmpty: true } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual([
      "Line 0",
      "study",
      "source",
      "label",
      "time",
      "mean, the marked column",
    ]);
    expect(wrapper.findAll("tbody .grid-cell--marked").map((cell) => cell.text())).toEqual(["2.419", "3.1", "1.2"]);

    // The column of an issue stays when it is empty.
    const kept = mount(TableGrid, { props: { table: small, hideEmpty: true, issueCells: issues } });
    expect(kept.findAll("thead th").at(-1)?.text()).toBe("comment");
  });

  it("marks several columns", () => {
    const wrapper = mount(TableGrid, { props: { table: small, markColumn: ["time", "mean"], markText: "changed" } });
    expect(wrapper.findAll("thead .grid-cell--marked").map((cell) => cell.text())).toEqual([
      "time, changed",
      "mean, changed",
    ]);
  });

  it("shows the columns that it is given in their order", () => {
    const wrapper = mount(TableGrid, { props: { table: small, columns: [4, 2] } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line 0", "mean", "label"]);
  });

  it("shows a raw table as printed, with the column letters of its sheet", () => {
    const raw: TableResponse = {
      file: "Example_Tab2.tsv",
      kind: "raw",
      rows: [
        { line: 1, cells: ["  a  b ", "c"] },
        { line: 2, cells: ["d", "e", "f"] },
      ],
    };
    const wrapper = mount(TableGrid, { props: { table: raw, label: "Raw extraction Example_Tab2.tsv" } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B", "C"]);
    // text() trims, so the DOM text is compared: the spaces stay, and short rows are padded.
    expect(wrapper.findAll("tbody tr")[0]?.findAll("td").map((cell) => cell.element.textContent)).toEqual([
      "  a  b ",
      "c",
      "",
    ]);
    expect(wrapper.findAll("td")[0]?.classes()).toContain("grid-raw");
    expect(region(wrapper).getAttribute("aria-label")).toBe("Raw extraction Example_Tab2.tsv");
  });

  it("fills the line cells from its slot", () => {
    const wrapper = mount(TableGrid, {
      props: { table: small },
      slots: { line: ({ line }: { line: number }) => h("a", { href: `#line-${line}` }, String(line)) },
    });
    expect(wrapper.findAll("tbody th a").map((link) => link.attributes("href"))).toEqual([
      "#line-1",
      "#line-2",
      "#line-3",
    ]);
  });

  it("leaves out the line column without a line header", () => {
    const wrapper = mount(TableGrid, { props: { table: small, lineHeader: null } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(HEADER);
    expect(wrapper.find("tbody th").exists()).toBe(false);
    expect(region(wrapper).classList).not.toContain("rows-scroll--sticky-line");
  });

  it("tints its rows only when asked", () => {
    expect(mount(TableGrid, { props: { table: classed } }).get(".table-grid").classes()).not.toContain("table-grid--tinted");
    expect(mount(TableGrid, { props: { table: classed, tinted: true } }).get(".table-grid").classes()).toContain(
      "table-grid--tinted",
    );
  });

  it("tints each column in the color of what it names, and mutes study and source in italics without a tint", () => {
    const wrapper = mount(TableGrid, { props: { table: classed, tinted: true } });
    const head = wrapper.findAll("thead th").slice(1);
    expect(head.map(infoOf)).toEqual(CLASSED);
    expect(head.map((cell) => cell.attributes("data-info"))).toEqual(CLASSED);
    const cells = wrapper.findAll("tbody tr[data-index]")[0]!.findAll("td");
    expect(cells.map(infoOf)).toEqual(CLASSED);
    // Each tinted column takes the color and the shares of its class.
    expect(declared(cells[3]!.element, "--info")).toEqual(["var(--v-theme-info-subjects)"]);
    expect(declared(cells[4]!.element, "--info")).toEqual(["var(--v-theme-info-interventions)"]);
    expect(declared(cells[2]!.element, "--info")).toEqual(["var(--v-theme-info-data)"]);
    expect(declared(cells[3]!.element, "--info-cell-tint")).toEqual(["var(--v-info-cell-tint)"]);
    expect(declared(cells[2]!.element, "--info-cell-tint")).toEqual(["var(--v-info-data-cell-tint)"]);
    expect(declared(head[2]!.element, "--info-head-tint")).toEqual(["var(--v-info-data-head-tint)"]);
    for (const index of [2, 3, 4, 5, 6])
      expect(declared(cells[index]!.element, "background-color")).toEqual([expect.stringContaining("var(--info-cell-tint)")]);
    expect(declared(head[3]!.element, "background-color")).toEqual([expect.stringContaining("var(--info-head-tint)")]);
    // study and source: muted, in italics and without a tint, in the header and the rows; the line column has no tint either.
    for (const cell of [head[0]!, head[1]!, cells[0]!, cells[1]!]) {
      expect(declared(cell.element, "background-color")).toEqual([]);
      expect(declared(cell.element, "font-style")).toEqual(["italic"]);
      expect(declared(cell.element, "color")).toEqual([expect.stringContaining("var(--v-medium-emphasis-opacity)")]);
    }
    expect(declared(wrapper.get("tbody tr[data-index] th").element, "background-color")).toEqual([]);
  });

  it("keeps the class of each column when empty columns are hidden or the columns come in another order", () => {
    const hidden = mount(TableGrid, { props: { table: classed, tinted: true, hideEmpty: true } });
    expect(hidden.findAll("thead th").slice(1).map((cell) => [cell.text(), infoOf(cell)])).toEqual([
      ["study", "meta"],
      ["source", "meta"],
      ["label", "data"],
      ["subjects", "subjects"],
      ["interventions", "interventions"],
      ["mean", "data"],
    ]);
    const ordered = mount(TableGrid, { props: { table: classed, tinted: true, columns: [4, 3, 0] } });
    expect(ordered.findAll("tbody tr[data-index]")[0]!.findAll("td").map(infoOf)).toEqual(["interventions", "subjects", "meta"]);
  });

  it("tints no column of a table without classes, of a raw table, or of a grid that is not tinted", () => {
    const cases: { table: TableResponse; tinted: boolean }[] = [
      { table: small, tinted: true },
      { table: printed, tinted: true },
      { table: classed, tinted: false },
    ];
    for (const props of cases) {
      const wrapper = mount(TableGrid, { props });
      expect(wrapper.findAll("th, td").map(infoOf).filter((info) => info !== null)).toEqual([]);
      expect(wrapper.find("th[data-info]").exists()).toBe(false);
    }
  });

  it("keeps the tints of the selected row and of the targeted rows above the tint of a column", () => {
    // One rule tints the cells, with the specificity of one class, so that the rules of the rows win.
    const tints = gridRules().filter((rule) => rule.style.getPropertyValue("background-color").includes("var(--info-cell-tint)"));
    expect(tints).toHaveLength(1);
    expect(tints[0]!.selectorText).toMatch(/^\.table-grid--tinted :where\(/);
    const wrapper = mount(TableGrid, {
      props: { table: classed, tinted: true, selectable: true, focus: { line: 1 }, highlightLines: new Set([2]) },
    });
    const [focused, targeted] = wrapper.findAll("tbody tr[data-index]");
    expect(declared(focused!.findAll("td")[3]!.element, "background-color").at(-1)).toContain("var(--v-theme-primary)");
    expect(declared(targeted!.findAll("td")[3]!.element, "background-color").at(-1)).toContain("var(--v-theme-warning)");
  });
});

describe("TableGrid with many rows", () => {
  it("renders only the rows near the view of a large table and follows the scrolling", async () => {
    const wrapper = mount(TableGrid, { props: { table: large(), highlightLines: new Set([2100, 2101]) } });
    const rendered = wrapper.findAll("tbody tr:not([aria-hidden])");
    expect(rendered.length).toBeGreaterThan(10);
    expect(rendered.length).toBeLessThan(100);
    expect(lines(wrapper)[0]).toBe("1");
    expect(wrapper.get("table").attributes("aria-rowcount")).toBe("5001");
    expect(rendered[0]?.attributes("aria-rowindex")).toBe("2");

    // Down to the row of line 2,101 (the 2,101st row).
    const element = region(wrapper);
    element.scrollTop = 2100 * 22;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    const shown = lines(wrapper).map(Number);
    expect(shown.length).toBeLessThan(100);
    expect(shown).toContain(2101);
    expect(shown).toEqual(Array.from({ length: shown.length }, (_, index) => shown[0]! + index));
    const row = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "2101")!;
    expect(row.attributes("aria-rowindex")).toBe("2102");
    expect(row.classes()).toContain("grid-row--target");
    const other = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "2102")!;
    expect(other.classes()).not.toContain("grid-row--target");
    // Spacers keep the height of the rows that are not rendered.
    const spacers = wrapper.findAll("tbody tr[aria-hidden]");
    expect(spacers).toHaveLength(2);
    // The rows pass below the header, which stays in view with its background.
    expect(element.classList).toContain("rows-scroll--stuck");
    element.scrollTop = 0;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(element.classList).not.toContain("rows-scroll--stuck");
  });

  it("tints the rendered rows and the spacers of a large tinted table column by column", async () => {
    const wrapper = mount(TableGrid, { props: { table: large(5000, CLASSES), tinted: true } });
    const element = region(wrapper);
    element.scrollTop = 2100 * 22;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    const spacers = wrapper.findAll("tbody tr[aria-hidden]");
    expect(spacers).toHaveLength(2);
    const row = wrapper.get("tbody tr[data-index]");
    for (const cells of [...spacers.map((spacer) => spacer.findAll("td")), row.findAll("td")]) {
      expect(cells.map(infoOf)).toEqual(CLASSES);
      for (const cell of cells)
        expect(declared(cell.element, "background-color")).toEqual(
          infoOf(cell) === "meta" ? [] : [expect.stringContaining("var(--info-cell-tint)")],
        );
    }
    // The line column has no tint, in the spacers and in the rows; the spacers keep the height of the rows they stand for.
    for (const line of [...spacers.map((spacer) => spacer.get("th")), row.get("th")])
      expect(declared(line.element, "background-color")).toEqual([]);
    expect(spacers[0]!.attributes("style")).toMatch(/height: \d+px/);
  });

  it("renders every row up to 500 rows", () => {
    const wrapper = mount(TableGrid, { props: { table: large(500) } });
    expect(wrapper.findAll("tbody tr")).toHaveLength(500);
  });

  it("scrolls to the focused line, marks its cell and moves the focus there", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: large(), focus: { line: 4000, column: "mean" } },
      attachTo: document.body,
    });
    await flushPromises();
    expect(region(wrapper).scrollTop).toBeGreaterThan(3900 * 22);
    const row = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "4000")!;
    const cell = row.findAll("td")[4]!;
    expect(cell.text()).toBe("399.9");
    expect(cell.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(cell.element);
    // The cell scrolls within the region, and the page brings the region into view, clear of the app bar.
    expect(scrolled).toEqual([region(wrapper)]);
  });

  it("marks the line of a focused line without a column", async () => {
    const wrapper = mount(TableGrid, { props: { table: small, focus: { line: 2 } }, attachTo: document.body });
    await flushPromises();
    const line = wrapper.findAll("tbody tr")[1]!.get("th");
    expect(line.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(line.element);
  });

  it("fades the rows out at the end while more columns follow, inside the scroll bars", async () => {
    const wrapper = mount(TableGrid, { props: { table: small }, attachTo: document.body });
    const element = region(wrapper);
    // jsdom has no layout: a region of 300 of 900 pixels, with scroll bars of 15 pixels.
    const sizes = { clientWidth: 300, scrollWidth: 900, offsetWidth: 317, clientHeight: 200, offsetHeight: 217 };
    for (const [name, value] of Object.entries(sizes)) Object.defineProperty(element, name, { configurable: true, value });
    element.style.border = "1px solid";
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    const grid = wrapper.get(".table-grid");
    expect(grid.classes()).toContain("table-grid--more");
    expect(grid.attributes("style")).toContain("--grid-scrollbar-x: 15px");
    expect(grid.attributes("style")).toContain("--grid-scrollbar-y: 15px");

    // Scrolled to the end, the last column shows whole.
    element.scrollLeft = 600;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(grid.classes()).not.toContain("table-grid--more");
  });

  it("keeps the focus where it is when the same focus comes again, as after a reload", async () => {
    const wrapper = mount(TableGrid, { props: { table: small, focus: { line: 2 } }, attachTo: document.body });
    await flushPromises();
    region(wrapper).focus();
    await wrapper.setProps({ focus: { line: 2 }, table: { ...small, rows: [...small.rows] } });
    await flushPromises();
    expect(document.activeElement).toBe(region(wrapper));
  });

  it("moves the focus to the region before the focused cell scrolls away", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: large(), focus: { line: 4000, column: "mean" } },
      attachTo: document.body,
    });
    await flushPromises();
    const element = region(wrapper);
    element.scrollTop = 0;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(lines(wrapper)).not.toContain("4000");
    expect(document.activeElement).toBe(element);
  });
});

/**
 * A layout for jsdom, which has none: the region is 600 × 300 pixels at the top of the window,
 * the header and each row 22 pixels high, the line column 64 pixels wide and each column 80.
 */
function layOut(): void {
  const row = (element: Element) => Number(element.closest("tr[data-index]")?.getAttribute("data-index") ?? -1);
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
    const scroller = this.closest<HTMLElement>(".rows-scroll");
    if (this === scroller) return new DOMRect(0, 0, 600, 300);
    if (!scroller) return new DOMRect();
    const top = (this.closest("thead") ? 0 : 22 + row(this) * 22) - scroller.scrollTop;
    const cell = this.closest("th, td");
    const column = cell ? [...cell.parentElement!.children].indexOf(cell) : 0;
    const left = column === 0 ? 0 : 64 + (column - 1) * 80 - scroller.scrollLeft;
    return new DOMRect(left, top, column === 0 ? 64 : 80, 22);
  });
  for (const [name, value] of Object.entries({ clientHeight: 300, clientWidth: 600 }))
    Object.defineProperty(HTMLElement.prototype, name, { configurable: true, value });
}

describe("revealing the focus", () => {
  afterEach(() => {
    for (const name of ["clientHeight", "clientWidth"]) Reflect.deleteProperty(HTMLElement.prototype, name);
  });

  it("leaves the rows in place for a focus that is in view, as after a click on a row", async () => {
    layOut();
    const wrapper = mount(TableGrid, { props: { table: large(60), selectable: true }, attachTo: document.body });
    const element = region(wrapper);
    element.scrollTop = 220;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    // Line 13 is the 13th row, 66 pixels below the top of the region.
    await wrapper.setProps({ focus: { line: 13 } });
    await flushPromises();
    expect(element.scrollTop).toBe(220);
    expect(scrolled).toEqual([]);
    expect(document.activeElement?.textContent?.trim()).toBe("13");
  });

  it("scrolls a focus that is out of view to the middle of the rows", async () => {
    layOut();
    const wrapper = mount(TableGrid, { props: { table: large(60) }, attachTo: document.body });
    const element = region(wrapper);
    // Line 49 is the 49th row, 1,078 pixels below the top of the region.
    await wrapper.setProps({ focus: { line: 49, column: "mean" } });
    await flushPromises();
    expect(element.scrollTop).toBe(1078 - 22 - (300 - 22 - 22) / 2);
    expect(scrolled).toEqual([element]);
    expect(document.activeElement?.textContent?.trim()).toBe("4.8");
  });

  it("brings the region into view for a focus under the app bar or the stuck banner of unsaved changes", async () => {
    layOut();
    const style = document.documentElement.style;
    onTestFinished(() => {
      for (const name of ["--v-layout-top", "--unsaved-banner-top", "--unsaved-banner-height"]) style.removeProperty(name);
    });
    const wrapper = mount(TableGrid, { props: { table: large(60), selectable: true }, attachTo: document.body });
    const element = region(wrapper);
    // Line 2 is the 2nd row, 44 to 66 pixels from the top of the window: in the region, but under
    // an app bar of 64 pixels.
    style.setProperty("--v-layout-top", "64px");
    await wrapper.setProps({ focus: { line: 2 } });
    await flushPromises();
    expect(element.scrollTop).toBe(0);
    expect(scrolled).toEqual([element]);

    // Line 4 is the 4th row, 88 to 110 pixels: below the app bar, under the banner that sticks below it.
    style.setProperty("--unsaved-banner-top", "64px");
    style.setProperty("--unsaved-banner-height", "50px");
    await wrapper.setProps({ focus: { line: 4 } });
    await flushPromises();
    expect(scrolled).toEqual([element, element]);

    // Line 6 is the 6th row, 132 to 154 pixels: below the banner, in view.
    await wrapper.setProps({ focus: { line: 6 } });
    await flushPromises();
    expect(scrolled).toEqual([element, element]);
    expect(document.activeElement?.textContent?.trim()).toBe("6");
  });

  it("scrolls a focus that is partly in view by the least amount", async () => {
    layOut();
    const wrapper = mount(TableGrid, { props: { table: large(60) }, attachTo: document.body });
    const element = region(wrapper);
    // Line 13 is the 13th row: 286 to 308 pixels, of which 8 are below the region.
    await wrapper.setProps({ focus: { line: 13 } });
    await flushPromises();
    expect(element.scrollTop).toBe(8);
  });

  it("scrolls sideways only to a cell that is out of view, clear of the line column", async () => {
    layOut();
    const wide: TableResponse = { ...small, header: [...HEADER, ...HEADER.map((name) => `${name}_2`)] };
    const wrapper = mount(TableGrid, { props: { table: wide }, attachTo: document.body });
    const element = region(wrapper);
    await wrapper.setProps({ focus: { line: 2, column: "mean" } });
    await flushPromises();
    expect(element.scrollLeft).toBe(0);
    // The 12th column starts at 944 pixels.
    await wrapper.setProps({ focus: { line: 2, column: "comment_2" } });
    await flushPromises();
    expect(element.scrollLeft).toBe(944 - 64 - (600 - 64 - 80) / 2);
    expect(element.scrollTop).toBe(0);
  });

  it("fades the header row out to the tint of the column at the end of the view, and to the surface at study", async () => {
    layOut();
    // The view of 600 pixels ends in the 7th column (64 + 6 × 80 = 544 to 624), then in the next ones as it scrolls.
    const header = ["study", "source", "label", "time", "mean", "sd", "subjects", "interventions", "unit", "comment"];
    const classes: ColumnClass[] = ["meta", "meta", "data", "data", "data", "data", "subjects", "interventions", "data", "data"];
    const table: TableResponse = {
      file: "timecourses_Fig1.tsv",
      kind: "table",
      header,
      classes,
      rows: [{ line: 1, cells: header.map(() => "x") }],
    };
    async function mounted(columns: number[] | null) {
      const wrapper = mount(TableGrid, { props: { table, tinted: true, columns }, attachTo: document.body });
      Object.defineProperty(region(wrapper), "scrollWidth", { configurable: true, value: 64 + 10 * 80 });
      return wrapper;
    }
    async function scroll(wrapper: VueWrapper, left: number): Promise<string[]> {
      const element = region(wrapper);
      element.scrollLeft = left;
      element.dispatchEvent(new Event("scroll"));
      await flushPromises();
      return wrapper.get(".table-grid").classes().filter((name) => name.startsWith("grid-info--"));
    }
    const wrapper = await mounted(null);
    expect(await scroll(wrapper, 0)).toEqual(["grid-info--subjects"]);
    expect(await scroll(wrapper, 80)).toEqual(["grid-info--interventions"]);
    expect(await scroll(wrapper, 160)).toEqual(["grid-info--data"]);
    // The header fades to the head tint of that class, the rows to the surface.
    expect(declared(wrapper.get(".table-grid").element, "--grid-head")).toEqual([expect.stringContaining("var(--info-head-tint)")]);
    // Scrolled to the end, nothing fades.
    expect(await scroll(wrapper, 264)).toEqual([]);
    expect(wrapper.get(".table-grid").classes()).not.toContain("table-grid--more");

    // study at the end of the view: the header fades to the surface, as the rows do.
    const muted = await mounted([2, 3, 4, 5, 8, 9, 0, 1, 6, 7]);
    expect(await scroll(muted, 0)).toEqual([]);
    expect(muted.get(".table-grid").classes()).toContain("table-grid--more");
  });
});

function mountGrid(props: Record<string, unknown>) {
  return mount(TableGrid, { props: { table: small, ...props } });
}

describe("selection and the line filter", () => {
  it("emits the line of a clicked row and of its line button", async () => {
    const wrapper = mountGrid({ selectable: true });
    await wrapper.findAll("tbody tr[data-index]")[1]!.find("td").trigger("click");
    await wrapper.get('th[scope="row"] button[title="Select line 3"]').trigger("click");
    expect(wrapper.emitted("select-line")).toEqual([[2], [3]]);
  });

  it("names the line button by its line number, so the row header reads as the line", () => {
    const wrapper = mountGrid({ selectable: true });
    const header = wrapper.findAll("tbody tr[data-index]")[2]!.get("th[scope=row]");
    expect(header.text()).toBe("3");
    expect(header.get("button").attributes("aria-label")).toBeUndefined();
    expect(header.get("button").attributes("title")).toBe("Select line 3");
  });

  it("marks a selectable grid, whose rows show the pointer and a tint under it", () => {
    expect(mountGrid({ selectable: true }).get(".table-grid").classes()).toContain("table-grid--selectable");
    expect(mountGrid({}).get(".table-grid").classes()).not.toContain("table-grid--selectable");
  });

  it("renders no buttons and emits nothing when not selectable", async () => {
    const wrapper = mountGrid({});
    expect(wrapper.find(".grid-line-button").exists()).toBe(false);
    await wrapper.findAll("tbody tr[data-index]")[0]!.find("td").trigger("click");
    expect(wrapper.emitted("select-line")).toBeUndefined();
  });

  it("shows only the visible lines and counts them for screen readers", () => {
    const wrapper = mountGrid({ visibleLines: new Set([1, 3]) });
    expect(wrapper.findAll("tbody tr[data-index]").map((row) => row.get("th").text())).toEqual(["1", "3"]);
    expect(wrapper.get("table").attributes("aria-rowcount")).toBe("3");
  });

  it("frames the only cell of the selected row on all four sides", () => {
    const names: TableResponse = { ...small, header: ["label"], rows: small.rows.map(({ line, cells }) => ({ line, cells: [cells[2]!] })) };
    const wrapper = mount(TableGrid, { props: { table: names, lineHeader: null, focus: { line: 2 } } });
    const cell = wrapper.get("tr.grid-row--focus > td").element;
    // The first cell draws the start of the frame and the last its end: the only cell both.
    expect(declared(cell, "--grid-frame-start")).toEqual(["1px"]);
    expect(declared(cell, "--grid-frame-end")).toEqual(["1px"]);
  });

  it("tints the row of the focus", () => {
    const wrapper = mountGrid({ focus: { line: 2 } });
    expect(wrapper.findAll("tbody tr[data-index]")[1]!.classes()).toContain("grid-row--focus");
  });

  it("scrolls a filtered large table to the focus line and numbers the shown rows", async () => {
    // Every second row shows: the lines 1, 3, 5 and so on.
    const visibleLines = new Set(Array.from({ length: 2500 }, (_, index) => index * 2 + 1));
    const wrapper = mount(TableGrid, {
      props: { table: large(), visibleLines, focus: { line: 4001 } },
      attachTo: document.body,
    });
    await flushPromises();
    expect(wrapper.get("table").attributes("aria-rowcount")).toBe("2501");
    // Line 4001 is the 2,001st shown row.
    const row = wrapper.findAll("tbody tr[data-index]").find((entry) => entry.get("th").text() === "4001")!;
    expect(row.attributes("aria-rowindex")).toBe("2002");
    expect(row.classes()).toContain("grid-row--focus");
    expect(region(wrapper).scrollTop).toBeGreaterThan(1900 * 22);
    expect(lines(wrapper).every((line) => Number(line) % 2 === 1)).toBe(true);
  });
});

describe("links of names", () => {
  /** The text and the title of each link of a row. */
  function links(row: DOMWrapper<Element>): [string, string | undefined][] {
    return row.findAll(".grid-link").map((entry) => [entry.text(), entry.attributes("title")]);
  }

  it("links each name of a column of names to its row, and leaves the other names and columns as text", () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES } });
    const [first, second] = wrapper.findAll("tbody tr[data-index]");
    expect(links(first!)).toEqual([
      ["all", "Line 1 of subjects.tsv"],
      ["D1", "Line 1 of interventions.tsv"],
      ["D2", "Line 2 of interventions.tsv"],
    ]);
    // S9 and D9 are no rows of their tables.
    expect(links(second!)).toEqual([["D1", "Line 1 of interventions.tsv"]]);
    // The cells read as before, with their commas and spaces.
    expect(first!.findAll("td").map((cell) => cell.text())).toEqual(["Example", "Tab2", "all", "D1,D2", "cmax", "all"]);
    expect(second!.findAll("td")[3]!.text()).toBe("D1, D9");
    expect(first!.findAll("td")[5]!.find(".grid-link").exists()).toBe(false);
    for (const entry of wrapper.findAll(".grid-link")) {
      expect(entry.element.tagName).toBe("BUTTON");
      expect(entry.attributes("type")).toBe("button");
      expect(entry.attributes("tabindex")).toBe("-1");
    }
    expect(wrapper.findAll(".grid-link").map((entry) => entry.classes().find((name) => name.startsWith("grid-link--")))).toEqual([
      "grid-link--subjects",
      "grid-link--interventions",
      "grid-link--interventions",
      "grid-link--interventions",
    ]);
  });

  it("describes where a link goes", () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES }, attachTo: document.body });
    const [subject, dose] = wrapper.findAll(".grid-link");
    expect(description(subject!.element)).toBe("Goes to line 1 of subjects.tsv.");
    expect(description(dose!.element)).toBe("Goes to line 1 of interventions.tsv.");
  });

  it("emits the link of a clicked name with the line of its row, and selects no row", async () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES } });
    await wrapper.findAll(".grid-link")[2]!.trigger("click");
    expect(wrapper.emitted("follow")).toEqual([[{ file: "interventions.tsv", line: 2 }, 1]]);
    expect(wrapper.emitted("select-line")).toBeUndefined();
  });

  it("renders no links without the lines of the names, in a grid that is not selectable, or in a raw table", () => {
    const printed: TableResponse = { file: "Example_Tab2.tsv", kind: "raw", rows: [{ line: 1, cells: ["all", "D1"] }] };
    const cases: { table: TableResponse; selectable?: boolean; names?: StudyNameLines }[] = [
      { table: named, selectable: true },
      { table: named, names: NAMES },
      { table: printed, selectable: true, names: NAMES },
    ];
    for (const props of cases) expect(mount(TableGrid, { props }).find(".grid-link").exists()).toBe(false);
  });
});

describe("the keyboard in a selectable grid", () => {
  /** The tab indices of the line buttons in the order of the rows. */
  function stops(wrapper: VueWrapper): (string | undefined)[] {
    return wrapper.findAll(".grid-line-button").map((entry) => entry.attributes("tabindex"));
  }

  function lineButton(wrapper: VueWrapper, line: number) {
    return wrapper.get<HTMLButtonElement>(`button[title="Select line ${line}"]`);
  }

  async function press(element: Element, key: string): Promise<void> {
    element.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    await flushPromises();
  }

  it("is one Tab stop: the button of the focus line, else of the first row", async () => {
    const wrapper = mountGrid({ selectable: true });
    expect(stops(wrapper)).toEqual(["0", "-1", "-1"]);
    await wrapper.setProps({ focus: { line: 2 } });
    expect(stops(wrapper)).toEqual(["-1", "0", "-1"]);
  });

  it("moves the focus to the row above or below with the arrow keys, and to the first or last with Home and End", async () => {
    const wrapper = mount(TableGrid, { props: { table: small, selectable: true }, attachTo: document.body });
    const button = (line: number) => lineButton(wrapper, line).element;
    button(1).focus();
    await press(button(1), "ArrowDown");
    expect(document.activeElement).toBe(button(2));
    expect(stops(wrapper)).toEqual(["-1", "0", "-1"]);
    await press(button(2), "End");
    expect(document.activeElement).toBe(button(3));
    await press(button(3), "ArrowDown");
    expect(document.activeElement).toBe(button(3));
    await press(button(3), "Home");
    expect(document.activeElement).toBe(button(1));
    await press(button(1), "ArrowUp");
    expect(document.activeElement).toBe(button(1));
    expect(stops(wrapper)).toEqual(["0", "-1", "-1"]);
    // Moving selects nothing; Enter and Space press the button.
    expect(wrapper.emitted("select-line")).toBeUndefined();
  });

  it("moves on from the line cell that the focus of the route focused", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: small, selectable: true, focus: { line: 2 } },
      attachTo: document.body,
    });
    await flushPromises();
    const cell = wrapper.findAll("tbody tr")[1]!.get("th").element;
    expect(document.activeElement).toBe(cell);
    await press(cell, "ArrowDown");
    expect(document.activeElement).toBe(lineButton(wrapper, 3).element);
  });

  it("renders the row that it moves to in a large table", async () => {
    const wrapper = mount(TableGrid, { props: { table: large(), selectable: true }, attachTo: document.body });
    lineButton(wrapper, 1).element.focus();
    await press(lineButton(wrapper, 1).element, "End");
    expect(document.activeElement?.textContent?.trim()).toBe("5000");
    expect(stops(wrapper).filter((stop) => stop === "0")).toHaveLength(1);
    await press(document.activeElement!, "ArrowUp");
    expect(document.activeElement?.textContent?.trim()).toBe("4999");
  });

  it("moves from the line button to the links of its row and back with Right and Left, and on to other rows from a link", async () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES }, attachTo: document.body });
    const links = (index: number) =>
      wrapper.findAll("tbody tr[data-index]")[index]!.findAll<HTMLElement>(".grid-link").map((entry) => entry.element);
    lineButton(wrapper, 1).element.focus();
    await press(lineButton(wrapper, 1).element, "ArrowRight");
    expect(document.activeElement).toBe(links(0)[0]);
    await press(links(0)[0]!, "ArrowRight");
    await press(links(0)[1]!, "ArrowRight");
    expect(document.activeElement).toBe(links(0)[2]);
    // Right stays at the last link and Left at the line button: no wrapping.
    await press(links(0)[2]!, "ArrowRight");
    expect(document.activeElement).toBe(links(0)[2]);
    await press(links(0)[2]!, "ArrowLeft");
    expect(document.activeElement).toBe(links(0)[1]);
    // Down from a link moves to the line button of the next row, which becomes the Tab stop.
    await press(links(0)[1]!, "ArrowDown");
    expect(document.activeElement).toBe(lineButton(wrapper, 2).element);
    expect(stops(wrapper)).toEqual(["-1", "0"]);
    await press(lineButton(wrapper, 2).element, "ArrowRight");
    expect(document.activeElement).toBe(links(1)[0]);
    await press(links(1)[0]!, "ArrowLeft");
    expect(document.activeElement).toBe(lineButton(wrapper, 2).element);
    await press(lineButton(wrapper, 2).element, "ArrowLeft");
    expect(document.activeElement).toBe(lineButton(wrapper, 2).element);
    // A focused link makes its row the Tab stop. Moving selects and follows nothing; Enter and Space press the button.
    links(0)[0]!.focus();
    await flushPromises();
    expect(stops(wrapper)).toEqual(["0", "-1"]);
    expect(wrapper.emitted("select-line")).toBeUndefined();
    expect(wrapper.emitted("follow")).toBeUndefined();
  });

  it("leaves Right to the browser where the focus has nowhere to move", async () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES }, attachTo: document.body });
    const send = (element: Element, key: string): KeyboardEvent => {
      const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
      element.dispatchEvent(event);
      return event;
    };
    // Row 2 has the link D1, so a table without links of names is mounted for the row without links.
    const plainWrapper = mount(TableGrid, {
      props: { table: { ...named, rows: [{ line: 1, cells: ["Example", "Tab2", "S9", "D9", "cmax", ""] }] }, selectable: true, names: NAMES },
      attachTo: document.body,
    });
    expect(send(lineButton(plainWrapper, 1).element, "ArrowRight").defaultPrevented).toBe(false);
    expect(send(lineButton(plainWrapper, 1).element, "ArrowLeft").defaultPrevented).toBe(false);
    const links = wrapper.findAll("tbody tr[data-index]")[0]!.findAll<HTMLElement>(".grid-link").map((entry) => entry.element);
    expect(send(links[2]!, "ArrowRight").defaultPrevented).toBe(false);
    // Where it moves, the keys are taken.
    expect(send(links[1]!, "ArrowRight").defaultPrevented).toBe(true);
    expect(send(lineButton(wrapper, 1).element, "ArrowRight").defaultPrevented).toBe(true);
  });

  it("ignores the second click of a double-click on a link", async () => {
    const wrapper = mount(TableGrid, { props: { table: named, selectable: true, names: NAMES } });
    const link = wrapper.get(".grid-link");
    link.element.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 1 }));
    link.element.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 2 }));
    await flushPromises();
    expect(wrapper.emitted("follow")).toHaveLength(1);
  });

  it("moves to the links from the line cell that the focus of the route focused", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: named, selectable: true, names: NAMES, focus: { line: 1 } },
      attachTo: document.body,
    });
    await flushPromises();
    const cell = wrapper.findAll("tbody tr")[0]!.get("th").element;
    expect(document.activeElement).toBe(cell);
    await press(cell, "ArrowRight");
    expect(document.activeElement?.textContent).toBe("all");
  });

  it("leaves the keys of a cell that the route focused", async () => {
    mount(TableGrid, {
      props: { table: named, selectable: true, names: NAMES, focus: { line: 1, column: "measurement" } },
      attachTo: document.body,
    });
    await flushPromises();
    const cell = document.activeElement as HTMLElement;
    expect(cell.textContent?.trim()).toBe("cmax");
    await press(cell, "ArrowRight");
    await press(cell, "ArrowDown");
    expect(document.activeElement).toBe(cell);
  });
});

/** The `matches` of jsdom, which guesses `:focus-visible` from the events before a focus. */
const MATCHES = Element.prototype.matches;

/** Whether a focus shows its ring, as after a key (`true`) or after a click (`false`). */
function focusRing(shown: boolean): void {
  vi.spyOn(Element.prototype, "matches").mockImplementation(function (this: Element, selector: string): boolean {
    return selector === ":focus-visible" ? shown && this === document.activeElement : MATCHES.call(this, selector);
  });
}

describe("the tooltip of the problems", () => {
  const [, second, third] = small.rows.map((row) => row.line) as [number, number, number];
  const MEAN = HEADER.indexOf("mean");

  /** A warning of `small` at `line` and the column `header`, or of the whole row for null. */
  function problem(code: string, line: number, header: string | null, changes: Partial<ValidationIssue> = {}): ValidationIssue {
    const source = header === null ? { file: small.file, row: line } : { file: small.file, row: line, header };
    return { code, severity: "warning", message: `${code} at line ${line}`, source, ...changes };
  }

  function mountTips(issues: ValidationIssue[], props: Record<string, unknown> = {}) {
    return mount(TableGrid, {
      props: { table: small, issueCells: issueCells(issues, small.file), ...props },
      attachTo: document.body,
    });
  }

  /** The cell of `small` at `line` and the column index `column`. */
  function cellAt(wrapper: VueWrapper, line: number, column: number): HTMLElement {
    const row = wrapper.findAll("tbody tr[data-index]").find((entry) => entry.get("th").text() === String(line))!;
    return row.findAll("td")[column]!.element;
  }

  /** The tooltip while it shows; null while it is hidden. */
  function shownTip(): HTMLElement | null {
    return document.querySelector<HTMLElement>(".v-overlay--active .problem-tooltip");
  }

  async function hover(element: Element): Promise<void> {
    element.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: document.body }));
    vi.advanceTimersByTime(TIP_DELAY);
    await flushPromises();
  }

  beforeEach(() => {
    // Vuetify places the tooltip in the visual viewport.
    setViewport();
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  });
  afterEach(() => vi.useRealTimers());

  it("shows the problems of an outlined cell 300 ms after the pointer rests on it, and keeps its description", async () => {
    const hint = { kind: "inspect_source", message: "Check the digitization against the figure." };
    const wrapper = mountTips([problem("digitized_mismatch", second, "mean", { suggestions: [hint] })]);
    const cell = cellAt(wrapper, second, MEAN);
    expect(cell.dataset.tip).toBe(`${second}:${MEAN}`);
    cell.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: document.body }));
    vi.advanceTimersByTime(TIP_DELAY - 1);
    await flushPromises();
    expect(shownTip()).toBeNull();
    vi.advanceTimersByTime(1);
    await flushPromises();
    const tip = shownTip()!;
    expect(tip.querySelector(".v-chip")?.textContent?.trim()).toBe("Warning");
    expect(tip.querySelector(".problem-tip-code")?.textContent).toBe("digitized_mismatch");
    expect(tip.querySelector(".problem-tip-message")?.textContent).toBe(`digitized_mismatch at line ${second}`);
    expect(tip.querySelector(".problem-tip-hint")?.textContent).toBe("Check the digitization against the figure.");
    // The description for screen readers stays, and reads what the tooltip shows.
    expect(description(cell)).toBe(`Warning: digitized_mismatch at line ${second}. Check the digitization against the figure.`);
  });

  it("shows the problems of a hovered header cell, and every problem of its line at a hovered line cell, whose button leaves its title to the tooltip", async () => {
    const wrapper = mountTips(
      [problem("unknown_column", HEADER_LINE, "comment"), problem("duplicate_row", third, null), problem("unknown_term", third, "label")],
      { selectable: true },
    );
    await hover(wrapper.findAll("thead th").at(-1)!.element);
    expect(shownTip()?.textContent).toContain("unknown_column");
    const line = wrapper.findAll("tbody tr[data-index]")[2]!.get("th");
    expect(line.attributes("data-tip")).toBe(`${third}:line`);
    await hover(line.get("button").element);
    expect([...shownTip()!.querySelectorAll(".problem-tip-code")].map((code) => code.textContent)).toEqual([
      "duplicate_row",
      "unknown_term",
    ]);
    expect(line.get("button").attributes("title")).toBeUndefined();
    expect(wrapper.findAll("tbody tr[data-index]")[1]!.get("th button").attributes("title")).toBe(`Select line ${second}`);
  });

  it("describes the problems of a line once: by its line button, which carries all of them, else by its line cell", () => {
    const issues = [problem("duplicate_row", third, null), problem("unknown_term", third, "label")];
    const lineCell = (wrapper: VueWrapper) => wrapper.findAll("tbody tr[data-index]")[2]!.get("th");
    const buttons = mountTips(issues, { selectable: true, highlightLines: new Set([third]) });
    expect(description(lineCell(buttons).element)).toBe("Targeted by an open review item.");
    expect(description(lineCell(buttons).get("button").element)).toBe(
      `Warning: duplicate_row at line ${third}. Warning: unknown_term at line ${third}.`,
    );
    expect(description(lineCell(mountTips(issues)).element)).toBe(`Warning: duplicate_row at line ${third}.`);
    const slotted = mount(TableGrid, {
      props: { table: small, issueCells: issueCells(issues, small.file), selectable: true },
      slots: { line: ({ line }: { line: number }) => h("a", { href: `#${line}` }, String(line)) },
    });
    expect(description(lineCell(slotted).element)).toBe(`Warning: duplicate_row at line ${third}.`);
  });

  it("places the tooltip of a line from the start of its line cell, so that it extends over its row, and that of a cell below its middle", async () => {
    const wrapper = mountTips([problem("unknown_term", third, "label")], { selectable: true });
    const line = wrapper.findAll("tbody tr[data-index]")[2]!.get("th").element;
    await hover(line);
    expect(shownTip()).not.toBeNull();
    expect(wrapper.findComponent(VTooltip).props("location")).toBe("bottom start");
    cellAt(wrapper, third, HEADER.indexOf("label")).dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: line }));
    vi.advanceTimersByTime(TIP_LINGER);
    await flushPromises();
    expect(wrapper.findComponent(VTooltip).props("location")).toBe("bottom");
  });

  it("adds no Tab stop for outlined cells, and shows every problem of a line when the keyboard moves to its line button", async () => {
    focusRing(true);
    const wrapper = mountTips(
      [problem("digitized_mismatch", second, "mean"), problem("duplicate_row", second, null), problem("unknown_term", third, "label")],
      { selectable: true },
    );
    expect(wrapper.findAll("tbody td[tabindex]")).toHaveLength(0);
    expect(wrapper.findAll("thead th[tabindex]")).toHaveLength(0);
    const buttons = wrapper.findAll<HTMLButtonElement>(".grid-line-button").map((entry) => entry.element);
    expect(buttons.map((button) => button.tabIndex)).toEqual([0, -1, -1]);
    // The button reads what its tooltip shows.
    expect(description(buttons[1]!)).toBe(`Warning: digitized_mismatch at line ${second}. Warning: duplicate_row at line ${second}.`);
    buttons[1]!.focus();
    await flushPromises();
    expect([...shownTip()!.querySelectorAll(".problem-tip-code")].map((code) => code.textContent)).toEqual([
      "digitized_mismatch",
      "duplicate_row",
    ]);
    buttons[1]!.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true }));
    await flushPromises();
    expect(document.activeElement).toBe(buttons[2]);
    expect(shownTip()?.textContent).toContain("unknown_term");
    buttons[2]!.dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true, cancelable: true }));
    await flushPromises();
    expect(document.activeElement).toBe(buttons[0]);
    expect(shownTip()).toBeNull();
  });

  it("makes the Line header a Tab stop only while the header has problems, and lists every problem of the header there", async () => {
    focusRing(true);
    const wrapper = mountTips([problem("unknown_column", HEADER_LINE, "comment"), problem("missing_header", HEADER_LINE, null)], {
      selectable: true,
    });
    const header = wrapper.get<HTMLElement>("thead th.rows-line");
    expect(header.attributes("tabindex")).toBe("0");
    expect(description(header.element)).toBe(
      `Warning: unknown_column at line ${HEADER_LINE}. Warning: missing_header at line ${HEADER_LINE}.`,
    );
    header.element.focus();
    await flushPromises();
    expect([...shownTip()!.querySelectorAll(".problem-tip-code")].map((code) => code.textContent)).toEqual([
      "unknown_column",
      "missing_header",
    ]);
    const clean = mountTips([problem("digitized_mismatch", second, "mean")], { selectable: true });
    expect(clean.get("thead th.rows-line").attributes("tabindex")).toBeUndefined();
  });

  it("shows the tooltip at the cell that the route focuses only when the focus shows its ring", async () => {
    focusRing(false);
    mountTips([problem("digitized_mismatch", second, "mean")], { focus: { line: second, column: "mean" } });
    await flushPromises();
    expect(document.activeElement?.textContent?.trim()).toBe(small.rows[1]!.cells[MEAN]);
    expect(shownTip()).toBeNull();
  });

  it("shows the tooltip at the cell that the route focuses after a key", async () => {
    focusRing(true);
    mountTips([problem("digitized_mismatch", second, "mean")], { focus: { line: second, column: "mean" } });
    await flushPromises();
    expect(shownTip()?.textContent).toContain("digitized_mismatch");
  });

  it("lists at most five problems of a cell, errors first, and counts the others", async () => {
    const issues = [
      ...Array.from({ length: 6 }, (_, index) => problem(`warning_${index}`, second, "mean")),
      problem("missing_value", second, "mean", { severity: "error" }),
    ];
    const wrapper = mountTips(issues);
    await hover(cellAt(wrapper, second, MEAN));
    const tip = shownTip()!;
    expect([...tip.querySelectorAll(".problem-tip-code")].map((code) => code.textContent)).toEqual([
      "missing_value",
      "warning_0",
      "warning_1",
      "warning_2",
      "warning_3",
    ]);
    expect(tip.querySelector(".problem-tip-more")?.textContent).toBe("and 2 more");
  });

  it("has one tooltip for all cells, which moves from cell to cell, and none without problems", async () => {
    const table = large(2000);
    const issues = table.rows.map(
      (row): ValidationIssue => ({
        code: "digitized_mismatch",
        severity: "warning",
        message: `Mismatch of line ${row.line}.`,
        source: { file: table.file, row: row.line, header: "mean" },
      }),
    );
    const wrapper = mount(TableGrid, { props: { table, issueCells: issueCells(issues, table.file) }, attachTo: document.body });
    expect(wrapper.findAllComponents(VTooltip)).toHaveLength(1);
    const cells = wrapper.findAll("tbody td.grid-cell--warning");
    expect(cells.length).toBeGreaterThan(10);
    expect(cells.length).toBeLessThan(100);
    await hover(cells[0]!.element);
    expect(shownTip()?.textContent).toContain(`Mismatch of line ${table.rows[0]!.line}.`);
    cells[1]!.element.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: cells[0]!.element }));
    vi.advanceTimersByTime(TIP_LINGER);
    await flushPromises();
    expect(shownTip()?.textContent).toContain(`Mismatch of line ${table.rows[1]!.line}.`);
    expect(document.querySelectorAll(".problem-tooltip")).toHaveLength(1);
    expect(mount(TableGrid, { props: { table: small } }).findAllComponents(VTooltip)).toHaveLength(0);
  });

  it("hides the tooltip on Escape until the pointer left its cell, when the rows scroll, and when its cell loses its problems", async () => {
    const wrapper = mountTips([problem("digitized_mismatch", second, "mean")]);
    const cell = cellAt(wrapper, second, MEAN);
    await hover(cell);
    expect(shownTip()).not.toBeNull();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    expect(shownTip()).toBeNull();
    await hover(cell);
    expect(shownTip()).toBeNull();
    cell.dispatchEvent(new MouseEvent("mouseout", { bubbles: true, relatedTarget: document.body }));

    await hover(cell);
    expect(shownTip()).not.toBeNull();
    region(wrapper).dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(shownTip()).toBeNull();

    await hover(cell);
    expect(shownTip()).not.toBeNull();
    await wrapper.setProps({ issueCells: new Map() });
    await flushPromises();
    expect(shownTip()).toBeNull();
  });

  it("renders the rows once, not again when the tooltip shows, moves or hides", async () => {
    let renders = 0;
    const issues = [problem("digitized_mismatch", second, "mean"), problem("unknown_term", third, "label")];
    const wrapper = mount(TableGrid, {
      props: { table: small, issueCells: issueCells(issues, small.file) },
      // Each render of the grid renders the line cell of each row.
      slots: {
        line: ({ line }: { line: number }) => {
          renders++;
          return String(line);
        },
      },
      attachTo: document.body,
    });
    await flushPromises();
    renders = 0;
    const [mean, label] = [cellAt(wrapper, second, MEAN), cellAt(wrapper, third, HEADER.indexOf("label"))];
    await hover(mean);
    expect(shownTip()?.textContent).toContain("digitized_mismatch");
    label.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: mean }));
    vi.advanceTimersByTime(TIP_LINGER);
    await flushPromises();
    expect(shownTip()?.textContent).toContain("unknown_term");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    expect(shownTip()).toBeNull();
    expect(renders).toBe(0);
  });

  it("keeps the problems in a hiding tooltip, which fades out", async () => {
    const wrapper = mountTips([problem("digitized_mismatch", second, "mean")]);
    await hover(cellAt(wrapper, second, MEAN));
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushPromises();
    expect(shownTip()).toBeNull();
    expect(document.querySelector(".problem-tooltip .problem-tip-code")?.textContent).toBe("digitized_mismatch");
  });

  it("hides a tooltip of the focus whose cell scrolls out of the rendered rows", async () => {
    focusRing(true);
    const table = large();
    const issues: ValidationIssue[] = [
      { code: "digitized_mismatch", severity: "warning", message: "Far down.", source: { file: table.file, row: 4001, header: "mean" } },
    ];
    const wrapper = mount(TableGrid, {
      props: { table, issueCells: issueCells(issues, table.file), focus: { line: 4001, column: "mean" } },
      attachTo: document.body,
    });
    await flushPromises();
    expect(shownTip()?.textContent).toContain("Far down.");
    const element = region(wrapper);
    element.scrollTop = 0;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(lines(wrapper)).not.toContain("4001");
    expect(shownTip()).toBeNull();
  });

  it("shows and describes the problems of an outlined cell when the keyboard reaches a link in it", async () => {
    focusRing(true);
    const table: TableResponse = {
      file: small.file,
      kind: "table",
      header: ["study", "subjects"],
      rows: [{ line: 1, cells: ["Example", "S9,all"] }],
    };
    const unknown: ValidationIssue = {
      code: "unknown_reference",
      severity: "error",
      message: "subjects.tsv has no row named 'S9'",
      source: { file: small.file, row: 1, header: "subjects" },
    };
    const wrapper = mount(TableGrid, {
      props: { table, selectable: true, names: NAMES, issueCells: issueCells([unknown], small.file) },
      attachTo: document.body,
    });
    const link = wrapper.get<HTMLElement>(".grid-link").element;
    expect(link.textContent).toBe("all");
    // The tooltip of the cell shows its problems: the link has no title of its own.
    expect(link.title).toBe("");
    expect(description(link)).toContain("Goes to line 1 of subjects.tsv.");
    expect(description(link)).toContain("subjects.tsv has no row named 'S9'");
    const button = wrapper.get<HTMLButtonElement>(".grid-line-button").element;
    button.focus();
    button.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true }));
    await flushPromises();
    expect(document.activeElement).toBe(link);
    expect(shownTip()?.textContent).toContain("unknown_reference");
  });
});
