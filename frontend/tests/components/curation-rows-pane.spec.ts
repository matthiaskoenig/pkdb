import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import type { TableResponse } from "../../src/curation-app/api/types";
import RowsPane from "../../src/curation-app/components/RowsPane.vue";
import type { RowFilter } from "../../src/curation-app/data";
import { sourceSummary, studyDetail, tableEntry } from "../unit/curation-fixtures";

enableAutoUnmount(afterEach);

const subjects: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "source", "name", "count"],
  rows: [
    { line: 2, cells: ["Example", "Fig1", "all", "8"] },
    { line: 3, cells: ["Example", "Tab2", "men", "4"] },
    { line: 4, cells: ["Example", "Tab2", "women", "4"] },
  ],
};

const detail = studyDetail({
  sources: [
    sourceSummary({ source: "Fig1", kind: "figure", tables: ["subjects.tsv"] }),
    sourceSummary({ source: "Tab2", tables: ["subjects.tsv"] }),
  ],
  tables: [tableEntry("subjects.tsv", "subjects")],
});

function mountPane(props: Record<string, unknown> = {}, slots: Record<string, string> = {}) {
  return mount(RowsPane, {
    slots,
    props: {
      detail,
      file: "subjects.tsv",
      table: subjects,
      rowsDetail: detail,
      loading: false,
      error: null,
      focus: null,
      filter: { kind: "all" } satisfies RowFilter,
      hideEmpty: true,
      ...props,
    },
  });
}

const lines = (wrapper: ReturnType<typeof mountPane>) =>
  wrapper.findAll("tbody tr:not([aria-hidden])").map((row) => row.get("th").text());

const select = (wrapper: ReturnType<typeof mountPane>) => wrapper.get<HTMLSelectElement>("select.pane-head-select");

describe("rows pane", () => {
  it("shows every row of a shared table until the curator chooses a source", () => {
    const wrapper = mountPane();
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
    expect(wrapper.get(".pane-head").text()).toContain("3 rows");
    expect(select(wrapper).element.value).toBe("all");
  });

  it("offers All, the sources of the rows and No source in the head", () => {
    const wrapper = mountPane();
    expect(select(wrapper).attributes("aria-label")).toBe("Source of the rows");
    expect(select(wrapper).findAll("option").map((option) => [option.attributes("value"), option.text()])).toEqual([
      ["all", "All (3)"],
      ["source:Fig1", "Fig1 (1)"],
      ["source:Tab2", "Tab2 (2)"],
      ["none", "No source (0)"],
    ]);
  });

  it("shows the rows of the chosen source, and tells the section the choice", async () => {
    const wrapper = mountPane({ filter: { kind: "source", source: "Tab2" } });
    expect(lines(wrapper)).toEqual(["3", "4"]);
    expect(wrapper.get(".pane-head .d-sr-only").text()).toBe("2 of 3 rows.");
    await select(wrapper).setValue("source:Fig1");
    expect(wrapper.emitted("update:filter")).toEqual([[{ kind: "source", source: "Fig1" }]]);
  });

  it("shows the line of the route although the filter would hide it", () => {
    const wrapper = mountPane({ filter: { kind: "source", source: "Tab2" }, focus: { line: 2 } });
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
    expect(wrapper.get(".pane-head").text()).toContain("Line 2");
  });

  it("shows all rows for a source that the rows no longer name", () => {
    const wrapper = mountPane({ filter: { kind: "source", source: "Fig9" } });
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
    expect(select(wrapper).element.value).toBe("all");
  });

  it("offers all rows when no row has the chosen filter", async () => {
    const wrapper = mountPane({ filter: { kind: "none" } });
    expect(wrapper.get('[role="status"]').text()).toBe("Every row of subjects.tsv names a source.");
    await wrapper.get(".pane-missing button").trigger("click");
    expect(wrapper.emitted("update:filter")).toEqual([[{ kind: "all" }]]);
  });

  it("has no Source select for a table of one source", () => {
    const outputs = studyDetail({ tables: [tableEntry("outputs_Tab2.tsv", "outputs")] });
    const table: TableResponse = { ...subjects, file: "outputs_Tab2.tsv" };
    const wrapper = mountPane({ detail: outputs, rowsDetail: outputs, file: "outputs_Tab2.tsv", table });
    expect(wrapper.find("select").exists()).toBe(false);
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
  });

  it("emits the line of a clicked row", async () => {
    const wrapper = mountPane();
    await wrapper.findAll("tbody tr:not([aria-hidden])")[0]!.trigger("click");
    expect(wrapper.emitted("select-line")).toEqual([[2]]);
  });

  it("shows the kind of the table in the color of its class, which tints its grid", () => {
    const wrapper = mountPane();
    expect(wrapper.get("section").attributes("style")).toContain("--info: var(--v-theme-info-subjects)");
    const chip = wrapper.get(".pane-head-kind");
    expect(chip.text()).toBe("Subjects");
    expect(chip.classes()).toEqual(expect.arrayContaining(["text-info-subjects", "status-chip"]));
    expect(wrapper.get(".table-grid").classes()).toContain("table-grid--tinted");
  });

  it("puts the content of the section below the head and the sentences about the rows right above the grid", () => {
    const rows = subjects.rows.map((row) => ({ ...row, cells: [...row.cells.slice(0, 3), ""] }));
    const wrapper = mountPane({ table: { ...subjects, rows } }, { default: '<div class="section-content">Notes</div>' });
    expect(wrapper.get(".rows-pane-notes").text()).toBe("1 empty column is hidden.");
    const order = [...wrapper.get("section").element.children].map((child) => child.classList[0]);
    expect(order).toEqual(["pane-head", "section-content", "rows-pane-notes", "table-grid"]);
  });
});
