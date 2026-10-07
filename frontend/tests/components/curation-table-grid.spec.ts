import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
    { line: 2, cells: ["Example", "Fig1", "caf_plasma_D150", "0.5", "2.419", ""] },
    { line: 3, cells: ["Example", "Fig1", "caf_plasma_D150", "1", "3.1", ""] },
    { line: 4, cells: ["Example", "Fig1", "caf_plasma_D75", "0.5", "1.2", ""] },
  ],
};

/** A timecourse table with `count` rows on the lines 2 to `count + 1`. */
function large(count = 5000): TableResponse {
  return {
    file: "timecourses_Fig1.tsv",
    kind: "table",
    header: HEADER,
    rows: Array.from({ length: count }, (_, index) => ({
      line: index + 2,
      cells: ["Example", "Fig1", `series_${Math.floor(index / 50)}`, String(index % 50), String(index / 10), ""],
    })),
  };
}

let scrolled: Element[];

beforeEach(() => {
  scrolled = [];
  // jsdom has no layout: scrolling an element into view records it.
  Element.prototype.scrollIntoView = vi.fn(function (this: Element) {
    scrolled.push(this);
  });
});

afterEach(() => {
  // @ts-expect-error jsdom has no scrollIntoView; the stub goes again.
  delete Element.prototype.scrollIntoView;
});

function lines(wrapper: VueWrapper): string[] {
  return wrapper.findAll("tbody tr:not([aria-hidden])").map((row) => row.get("th").text());
}

function region(wrapper: VueWrapper): HTMLElement {
  return wrapper.get<HTMLElement>('[role="region"]').element;
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
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", ...HEADER]);
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
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
      [3, new Map<string, CellIssues>([["mean", { severity: "error", messages: ["The mean is not a number."] }]])],
      [4, new Map<string, CellIssues>([[ROW, { severity: "warning", messages: ["The row repeats line 2."] }]])],
    ]);
    const wrapper = mount(TableGrid, {
      props: { table: small, highlightLines: new Set([2, 4]), issueCells: issues },
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
    expect(description(line.element)).toBe("Targeted by an open review item. The row repeats line 2.");
    // The descriptions add no text to the cells.
    expect(cell.text()).toBe("3.1");
  });

  it("marks a column, and hides empty columns except the ones to show", () => {
    const issues: IssueCells = new Map([
      [2, new Map<string, CellIssues>([["comment", { severity: "warning", messages: ["Add a comment."] }]])],
    ]);
    const wrapper = mount(TableGrid, { props: { table: small, markColumn: "mean", hideEmpty: true } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual([
      "Line",
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
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "mean", "label"]);
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
      "#line-2",
      "#line-3",
      "#line-4",
    ]);
  });

  it("leaves out the line column without a line header", () => {
    const wrapper = mount(TableGrid, { props: { table: small, lineHeader: null } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(HEADER);
    expect(wrapper.find("tbody th").exists()).toBe(false);
    expect(region(wrapper).classList).not.toContain("rows-scroll--sticky-line");
  });
});

describe("TableGrid with many rows", () => {
  it("renders only the rows near the view of a large table and follows the scrolling", async () => {
    const wrapper = mount(TableGrid, { props: { table: large(), highlightLines: new Set([2101, 2102]) } });
    const rendered = wrapper.findAll("tbody tr:not([aria-hidden])");
    expect(rendered.length).toBeGreaterThan(10);
    expect(rendered.length).toBeLessThan(100);
    expect(lines(wrapper)[0]).toBe("2");
    expect(wrapper.get("table").attributes("aria-rowcount")).toBe("5001");
    expect(rendered[0]?.attributes("aria-rowindex")).toBe("2");

    // Down to the row of line 2,102 (the 2,101st row).
    const element = region(wrapper);
    element.scrollTop = 2100 * 32;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    const shown = lines(wrapper).map(Number);
    expect(shown.length).toBeLessThan(100);
    expect(shown).toContain(2102);
    expect(shown).toEqual(Array.from({ length: shown.length }, (_, index) => shown[0]! + index));
    const row = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "2102")!;
    expect(row.attributes("aria-rowindex")).toBe("2102");
    expect(row.classes()).toContain("grid-row--target");
    const other = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "2103")!;
    expect(other.classes()).not.toContain("grid-row--target");
    // Spacers keep the height of the rows that are not rendered.
    const spacers = wrapper.findAll("tbody tr[aria-hidden]");
    expect(spacers).toHaveLength(2);
  });

  it("renders every row up to 500 rows", () => {
    const wrapper = mount(TableGrid, { props: { table: large(500) } });
    expect(wrapper.findAll("tbody tr")).toHaveLength(500);
  });

  it("scrolls to the focused line, marks its cell and moves the focus there", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: large(), focus: { line: 4001, column: "mean" } },
      attachTo: document.body,
    });
    await flushPromises();
    expect(region(wrapper).scrollTop).toBeGreaterThan(3900 * 32);
    const row = wrapper.findAll("tbody tr:not([aria-hidden])").find((entry) => entry.get("th").text() === "4001")!;
    const cell = row.findAll("td")[4]!;
    expect(cell.text()).toBe("399.9");
    expect(cell.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(cell.element);
    expect(scrolled).toContain(cell.element);
  });

  it("marks the line of a focused line without a column", async () => {
    const wrapper = mount(TableGrid, { props: { table: small, focus: { line: 3 } }, attachTo: document.body });
    await flushPromises();
    const line = wrapper.findAll("tbody tr")[1]!.get("th");
    expect(line.classes()).toContain("grid-cell--focus");
    expect(document.activeElement).toBe(line.element);
  });

  it("keeps the focus where it is when the same focus comes again, as after a reload", async () => {
    const wrapper = mount(TableGrid, { props: { table: small, focus: { line: 3 } }, attachTo: document.body });
    await flushPromises();
    region(wrapper).focus();
    await wrapper.setProps({ focus: { line: 3 }, table: { ...small, rows: [...small.rows] } });
    await flushPromises();
    expect(document.activeElement).toBe(region(wrapper));
  });

  it("moves the focus to the region before the focused cell scrolls away", async () => {
    const wrapper = mount(TableGrid, {
      props: { table: large(), focus: { line: 4001, column: "mean" } },
      attachTo: document.body,
    });
    await flushPromises();
    const element = region(wrapper);
    element.scrollTop = 0;
    element.dispatchEvent(new Event("scroll"));
    await flushPromises();
    expect(lines(wrapper)).not.toContain("4001");
    expect(document.activeElement).toBe(element);
  });
});
