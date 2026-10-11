import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import type { TableResponse } from "../../src/curation-app/api/types";
import RowsPane from "../../src/curation-app/components/RowsPane.vue";
import { sourceSummary, studyDetail } from "../unit/curation-fixtures";

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
  tables: [{ file: "subjects.tsv", kind: "subjects" }],
});

function mountPane(props: Record<string, unknown> = {}) {
  return mount(RowsPane, {
    props: {
      detail,
      file: "subjects.tsv",
      table: subjects,
      rowsDetail: detail,
      loading: false,
      error: null,
      focus: null,
      source: "Tab2",
      onlySource: true,
      hideEmpty: true,
      ...props,
    },
  });
}

const lines = (wrapper: ReturnType<typeof mountPane>) =>
  wrapper.findAll("tbody tr:not([aria-hidden])").map((row) => row.get("th").text());

describe("rows pane", () => {
  it("shows the rows of the source of a shared table", () => {
    const wrapper = mountPane();
    expect(lines(wrapper)).toEqual(["3", "4"]);
    expect(wrapper.get(".pane-head").text()).toContain("2 of 3 rows");
  });

  it("shows the line of the route although the filter would hide it", () => {
    const wrapper = mountPane({ focus: { line: 2 } });
    expect(lines(wrapper)).toEqual(["2", "3", "4"]);
    expect(wrapper.get(".pane-head").text()).toContain("Line 2");
  });

  it("offers all rows when the source has none in the table", async () => {
    const wrapper = mountPane({ source: "Other" });
    expect(wrapper.get('[role="status"]').text()).toBe("No rows of Other in subjects.tsv.");
    await wrapper.get(".pane-missing button").trigger("click");
    expect(wrapper.emitted("show-all")).toHaveLength(1);
  });

  it("emits the line of a clicked row", async () => {
    const wrapper = mountPane();
    await wrapper.findAll("tbody tr:not([aria-hidden])")[0]!.trigger("click");
    expect(wrapper.emitted("select-line")).toEqual([[3]]);
  });
});
