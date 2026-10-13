import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { h } from "vue";
import type { TableResponse } from "../../src/curation-app/api/types";
import TableGrid from "../../src/curation-app/components/TableGrid.vue";
import { ROW, type CellIssues, type IssueCells } from "../../src/curation-app/grid";

enableAutoUnmount(afterEach);

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

/** A timecourse table with `count` rows on the lines 1 to `count`. */
function large(count = 5000): TableResponse {
  return {
    file: "timecourses_Fig1.tsv",
    kind: "table",
    header: HEADER,
    rows: Array.from({ length: count }, (_, index) => ({
      line: index + 1,
      cells: ["Example", "Fig1", `series_${Math.floor(index / 50)}`, String(index % 50), String(index / 10), ""],
    })),
  };
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
      [2, new Map<string, CellIssues>([["mean", { severity: "error", messages: ["The mean is not a number."] }]])],
      [3, new Map<string, CellIssues>([[ROW, { severity: "warning", messages: ["The row repeats line 1."] }]])],
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
    expect(description(cell.element)).toBe("The mean is not a number.");
    // An issue of the whole row outlines its line.
    const line = rows[2]!.get("th");
    expect(line.classes()).toContain("grid-cell--warning");
    expect(description(line.element)).toBe("Targeted by an open review item. The row repeats line 1.");
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
      [0, new Map<string, CellIssues>([["mean", { severity: "error", messages: ["Unknown column 'meen'."] }]])],
    ]);
    const wrapper = mount(TableGrid, { props: { table: small, issueCells: issues }, attachTo: document.body });
    const header = wrapper.findAll("thead th").find((cell) => cell.text() === "mean")!;
    expect(header.classes()).toContain("grid-cell--error");
    expect(description(header.element)).toBe("Unknown column 'meen'.");
  });

  it("marks a column, and hides empty columns except the ones to show", () => {
    const issues: IssueCells = new Map([
      [2, new Map<string, CellIssues>([["comment", { severity: "warning", messages: ["Add a comment."] }]])],
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
    expect(mount(TableGrid, { props: { table: small } }).get(".table-grid").classes()).not.toContain("table-grid--tinted");
    expect(mount(TableGrid, { props: { table: small, tinted: true } }).get(".table-grid").classes()).toContain(
      "table-grid--tinted",
    );
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

  it("tints the rendered rows and the spacers of a large tinted table", async () => {
    const wrapper = mount(TableGrid, { props: { table: large(), tinted: true } });
    const element = region(wrapper);
    element.scrollTop = 2100 * 22;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    const spacers = wrapper.findAll("tbody tr[aria-hidden] > td");
    expect(spacers).toHaveLength(2);
    const row = wrapper.get("tbody tr[data-index]");
    for (const cell of [...spacers, ...row.findAll("td"), row.get("th")])
      expect(declared(cell.element, "background-color")).toEqual([expect.stringContaining("var(--v-info-cell-tint)")]);
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
});
