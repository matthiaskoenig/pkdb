import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import DataNavigator from "../../src/curation-app/components/DataNavigator.vue";
import type { Problem, StudyDetail } from "../../src/curation-app/api/types";
import { reviewItem, sourceSummary, studyDetail } from "../unit/curation-fixtures";

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

/** The text of `element` that screen readers read: without the parts hidden from them. */
function spoken(element: Element): string {
  const copy = element.cloneNode(true) as Element;
  for (const hidden of copy.querySelectorAll('[aria-hidden="true"]')) hidden.remove();
  return (copy.textContent ?? "").replace(/\s+/g, " ").trim();
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
    expect(wrapper.findAll(".nav-file .nav-file-name").map((entry) => entry.text())).toEqual([
      "subjects.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Example_Tab2.tsv",
    ]);
  });

  it("shows a table file without .tsv and keeps the end of its name, which a cut shortens before", () => {
    const wrapper = mountNavigator();
    const entry = wrapper.findAll(".nav-file")[2]!;
    const name = entry.get(".nav-name");
    expect(name.attributes("aria-hidden")).toBe("true");
    expect(name.get(".nav-name-start").text()).toBe("timecourses");
    expect(name.get(".nav-name-end").text()).toBe("_Fig1");
    expect(name.attributes("title")).toBe("timecourses_Fig1.tsv");
    // Screen readers read the name in full, first.
    expect(entry.get(".nav-file-name").classes()).toContain("d-sr-only");
    expect(entry.get(".nav-file-name").text()).toBe("timecourses_Fig1.tsv");
    expect(spoken(entry.element)).toBe("timecourses_Fig1.tsv");
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

  it("tells the counts of a file apart by an icon or a pill, each with a title", () => {
    const review = {
      revision: "review-1",
      value: { status: "draft" as const, reviewers: [], items: [reviewItem({ target: { file: "outputs_Tab2.tsv" } })] },
      issues: [],
    };
    const wrapper = mountNavigator({
      detail: detail({ review }),
      source: "Tab2",
      file: "outputs_Tab2.tsv",
      rows: new Map([["outputs_Tab2.tsv", 18]]),
    });
    const entry = wrapper.findAll(".nav-file")[1]!;
    const problems = entry.get(".nav-count--problems");
    expect(problems.find("i.fa-circle-exclamation").attributes("aria-hidden")).toBe("true");
    expect(problems.attributes("title")).toBe("2 problems");
    const items = entry.get(".nav-count:not(.nav-count--problems)");
    expect(items.find("i.fa-comment").attributes("aria-hidden")).toBe("true");
    expect(items.attributes("title")).toBe("1 open review item");
    const rows = entry.get(".nav-rows");
    expect(rows.find("i").exists()).toBe(false);
    expect(rows.attributes("title")).toBe("18 rows of Tab2");
    // Screen readers read each number with its meaning.
    expect(problems.get(".d-sr-only").text()).toBe("2 problems");
    expect(items.get(".d-sr-only").text()).toBe("1 open review item");
    expect(rows.get(".d-sr-only").text()).toBe("18 rows of Tab2");
  });

  it("names every source and file in full in the title of its name, which the navigator may cut", () => {
    const wrapper = mountNavigator();
    expect(wrapper.findAll(".nav-source .nav-name").map((name) => name.attributes("title"))).toEqual(["Fig1", "Tab2"]);
    expect(wrapper.findAll(".nav-file .nav-name").map((name) => name.attributes("title"))).toEqual([
      "subjects.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Example_Tab2.tsv",
    ]);
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
