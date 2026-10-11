import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import DataNavigator from "../../src/curation-app/components/DataNavigator.vue";
import type { Problem, StudyDetail } from "../../src/curation-app/api/types";
import { sourceSummary, studyDetail } from "../unit/curation-fixtures";

enableAutoUnmount(afterEach);

const problem = (file: string): Problem => ({ code: "c", severity: "error", message: "m", source: { file }, acknowledgeable: false });

function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
    sources: [
      sourceSummary({ source: "Fig1", kind: "figure", image: "Example_Fig1.png", tables: ["timecourses_Fig1.tsv", "subjects.tsv"] }),
      sourceSummary({ source: "Tab2", raw: "Example_Tab2.tsv", raw_kind: "table", tables: ["outputs_Tab2.tsv"] }),
    ],
    tables: [
      { file: "subjects.tsv", kind: "subjects" },
      { file: "outputs_Tab2.tsv", kind: "outputs" },
      { file: "timecourses_Fig1.tsv", kind: "timecourses" },
      { file: "Example_Tab2.tsv", kind: "raw" },
    ],
    problems: [problem("outputs_Tab2.tsv"), problem("outputs_Tab2.tsv")],
    ...changes,
  });
}

function mountNavigator(props: Record<string, unknown> = {}) {
  return mount(DataNavigator, {
    props: { detail: detail(), source: "Fig1", file: "timecourses_Fig1.tsv", rows: null, ...props },
  });
}

describe("data navigator", () => {
  it("lists the sources with a thumbnail or the icon of their kind, and the tables in workbook order", () => {
    const wrapper = mountNavigator();
    const sources = wrapper.findAll(".nav-source");
    expect(sources.map((entry) => entry.get(".nav-name").text())).toEqual(["Fig1", "Tab2"]);
    const thumbnail = sources[0]!.get("img");
    expect(thumbnail.attributes("src")).toBe("/local/studies/caffeine/Example/files/Example_Fig1.png");
    expect(thumbnail.attributes("loading")).toBe("lazy");
    expect(thumbnail.attributes("alt")).toBe("");
    expect(sources[1]!.find("img").exists()).toBe(false);
    expect(wrapper.findAll(".nav-file .nav-name").map((entry) => entry.text())).toEqual([
      "subjects.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Example_Tab2.tsv",
    ]);
  });

  it("marks the selected source and file", () => {
    const wrapper = mountNavigator();
    expect(wrapper.findAll(".nav-source")[0]!.attributes("aria-current")).toBe("true");
    expect(wrapper.findAll(".nav-file")[2]!.attributes("aria-current")).toBe("true");
  });

  it("shows the problems of a source and of a file, with their meaning for screen readers", () => {
    const wrapper = mountNavigator();
    expect(wrapper.findAll(".nav-source")[1]!.text()).toContain("2 problems");
    expect(wrapper.findAll(".nav-file")[1]!.text()).toContain("2 problems");
  });

  it("shows the rows of the selected source per file and dims the files without them", () => {
    const wrapper = mountNavigator({ rows: new Map([["timecourses_Fig1.tsv", 14], ["subjects.tsv", 1]]) });
    const files = wrapper.findAll(".nav-file");
    expect(files[2]!.text()).toContain("14");
    expect(files[1]!.classes()).toContain("nav-file--other");
    expect(files[0]!.classes()).not.toContain("nav-file--other");
  });

  it("emits the chosen source and file", async () => {
    const wrapper = mountNavigator();
    await wrapper.findAll(".nav-source")[1]!.trigger("click");
    await wrapper.findAll(".nav-file")[0]!.trigger("click");
    expect(wrapper.emitted("select-source")).toEqual([["Tab2"]]);
    expect(wrapper.emitted("select-file")).toEqual([["subjects.tsv"]]);
  });
});
