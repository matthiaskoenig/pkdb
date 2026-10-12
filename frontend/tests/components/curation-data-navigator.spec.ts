import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import DataNavigator from "../../src/curation-app/components/DataNavigator.vue";
import type { Problem, StudyDetail } from "../../src/curation-app/api/types";
import { PAPER } from "../../src/curation-app/data";
import { paperFile, reviewItem, sourceSummary, studyDetail, tableEntry } from "../unit/curation-fixtures";

enableAutoUnmount(afterEach);

const problem = (file: string, severity: Problem["severity"] = "error"): Problem => ({
  code: "c",
  severity,
  message: "m",
  source: { file },
  acknowledgeable: false,
});

function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
    sources: [
      sourceSummary({ source: "Fig1", kind: "figure", image: "Example_Fig1.png", tables: ["timecourses_Fig1.tsv", "subjects.tsv"] }),
      sourceSummary({ source: "Tab2", raw: "Example_Tab2.tsv", raw_kind: "table", tables: ["outputs_Tab2.tsv"] }),
    ],
    tables: [
      tableEntry("subjects.tsv", "subjects", 32),
      tableEntry("characteristica.tsv", "characteristica", 12),
      tableEntry("interventions.tsv", "interventions", 4),
      tableEntry("outputs_Tab2.tsv", "outputs", 18),
      tableEntry("timecourses_Fig1.tsv", "timecourses", 14),
      tableEntry("Example_Tab2.tsv", "raw", 9),
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
    props: { detail: detail(), source: "Fig1", file: "timecourses_Fig1.tsv", ...props },
  });
}

const fileNames = (wrapper: ReturnType<typeof mountNavigator>) =>
  wrapper.findAll(".nav-file .nav-file-name").map((entry) => entry.text());

describe("data navigator", () => {
  it("lists the tables first, under the headings of their class in the order of the sheets, then the sources", () => {
    const wrapper = mountNavigator();
    expect(wrapper.get("nav").attributes("aria-label")).toBe("Tables and sources");
    expect(wrapper.findAll("h3, h4").map((heading) => heading.text())).toEqual([
      "Tables",
      "Subjects",
      "Interventions",
      "Data",
      "Raw extractions",
      "Sources",
    ]);
    const lists = wrapper.findAll("ul");
    const names = (list: (typeof lists)[number]) => list.findAll(".nav-file-name").map((entry) => entry.text());
    expect(lists.slice(0, 4).map(names)).toEqual([
      ["subjects.tsv", "characteristica.tsv"],
      ["interventions.tsv"],
      ["outputs_Tab2.tsv", "timecourses_Fig1.tsv"],
      ["Example_Tab2.tsv"],
    ]);
    // Each list is named by its heading.
    expect(wrapper.get(`[id="${lists[0]!.attributes("aria-labelledby")}"]`).text()).toBe("Subjects");
    expect(wrapper.findAll(".nav-source .nav-name").map((entry) => entry.text())).toEqual(["Fig1", "Tab2"]);
  });

  it("leaves out the heading of a class without tables", () => {
    const wrapper = mountNavigator({ detail: detail({ tables: [tableEntry("subjects.tsv", "subjects")] }) });
    expect(wrapper.findAll("h4").map((heading) => heading.text())).toEqual(["Subjects"]);
  });

  it("marks each table with a bar in the color of its class", () => {
    const wrapper = mountNavigator();
    const styles = wrapper.findAll(".nav-file").map((entry) => entry.attributes("style"));
    expect(styles[0]).toContain("--info: var(--v-theme-info-subjects)");
    expect(styles[2]).toContain("--info: var(--v-theme-info-interventions)");
    expect(styles[3]).toContain("--info: var(--v-theme-info-data)");
    expect(styles[5]).toContain("--info: var(--v-theme-info-raw)");
    expect(wrapper.findAll(".nav-file .nav-bar").every((bar) => bar.attributes("aria-hidden") === "true")).toBe(true);
  });

  it("shows a long table name without .tsv, cut at its end, and names it in full in its title and for screen readers", () => {
    const long = "timecourses_Fig12A_plasma_and_saliva.tsv";
    const wrapper = mountNavigator({ detail: detail({ tables: [tableEntry(long, "timecourses")] }), file: long });
    const entry = wrapper.get(".nav-file");
    const name = entry.get(".nav-name");
    expect(name.text()).toBe("timecourses_Fig12A_plasma_and_saliva");
    expect(name.attributes("title")).toBe(long);
    expect(name.attributes("aria-hidden")).toBe("true");
    expect(name.find(".nav-name-start").exists()).toBe(false);
    // Screen readers read the file name in full first, then the rows; the cut name is hidden from them.
    expect(spoken(entry.element).startsWith(long)).toBe(true);
    expect(spoken(entry.element)).toContain("3 rows");
    expect(spoken(entry.element).match(/timecourses_Fig12A/g)).toHaveLength(1);
  });

  it("marks the selected source and file", () => {
    const wrapper = mountNavigator();
    expect(wrapper.findAll(".nav-source")[0]!.attributes("aria-current")).toBe("true");
    const current = wrapper.findAll(".nav-file").filter((entry) => entry.attributes("aria-current") === "true");
    expect(current.map((entry) => entry.get(".nav-file-name").text())).toEqual(["timecourses_Fig1.tsv"]);
  });

  it("shows the problems, the open review items and the rows of a table, each with its meaning", () => {
    const review = {
      revision: "review-1",
      value: { status: "draft" as const, reviewers: [], items: [reviewItem({ target: { file: "outputs_Tab2.tsv" } })] },
      issues: [],
    };
    const wrapper = mountNavigator({ detail: detail({ review }) });
    const entry = wrapper.findAll(".nav-file")[3]!;
    expect(entry.get(".nav-count--error").attributes("title")).toBe("2 errors");
    expect(entry.get(".nav-count:not(.nav-count--error)").attributes("title")).toBe("1 open review item");
    const rows = entry.get(".nav-rows");
    expect(rows.attributes("title")).toBe("18 rows");
    expect(rows.get(".d-sr-only").text()).toBe("18 rows");
    const said = spoken(entry.element);
    expect(said.startsWith("outputs_Tab2.tsv")).toBe(true);
    for (const part of ["2 errors", "1 open review item", "18 rows"]) expect(said).toContain(part);
    expect(wrapper.findAll(".nav-source")[1]!.text()).toContain("2 errors");
  });

  it("shows warnings in the warning tone with a triangle, and one number for both severities", () => {
    const wrapper = mountNavigator({
      detail: detail({
        problems: [
          problem("timecourses_Fig1.tsv", "warning"),
          problem("timecourses_Fig1.tsv", "warning"),
          problem("outputs_Tab2.tsv"),
          problem("outputs_Tab2.tsv", "warning"),
        ],
      }),
    });
    const files = wrapper.findAll(".nav-file");
    const [subjects, tab2, fig1] = [files[0]!, files[3]!, files[4]!];
    const warnings = fig1.get(".nav-count--warning");
    expect(fig1.find(".nav-count--error").exists()).toBe(false);
    expect(warnings.find("i.fa-triangle-exclamation").exists()).toBe(true);
    expect(warnings.attributes("title")).toBe("2 warnings");
    const mixed = tab2.get(".nav-count--error");
    expect(mixed.attributes("title")).toBe("1 error, 1 warning");
    expect(mixed.get('[aria-hidden="true"]:not(i)').text()).toBe("2");
    expect(subjects.find(".nav-count").exists()).toBe(false);
    const sources = wrapper.findAll(".nav-source");
    expect(sources[0]!.get(".nav-count--warning").attributes("title")).toBe("2 warnings");
    expect(sources[1]!.get(".nav-count--error").attributes("title")).toBe("1 error, 1 warning");
  });

  it("shows no row count for a table that cannot be read", () => {
    const wrapper = mountNavigator({ detail: detail({ tables: [tableEntry("timecourses_Fig1.tsv", "timecourses", null)] }) });
    expect(fileNames(wrapper)).toEqual(["timecourses_Fig1.tsv"]);
    expect(wrapper.find(".nav-rows").exists()).toBe(false);
  });

  it("names every source in full in the title of its name", () => {
    const wrapper = mountNavigator();
    expect(wrapper.findAll(".nav-source .nav-name").map((name) => name.attributes("title"))).toEqual(["Fig1", "Tab2"]);
    const thumbnail = wrapper.findAll(".nav-source")[0]!.get("img");
    expect(thumbnail.attributes("src")).toBe("/local/studies/caffeine/Example/files/Example_Fig1.png");
    expect(thumbnail.attributes("alt")).toBe("");
    expect(wrapper.findAll(".nav-source")[1]!.find("img").exists()).toBe(false);
  });

  it("lets the browser decode a thumbnail while it paints it, which never leaves a large image white", () => {
    const thumbnail = mountNavigator().get(".nav-source img");
    expect(thumbnail.attributes("loading")).toBe("lazy");
    expect(thumbnail.attributes("decoding")).toBeUndefined();
  });

  it("emits the chosen source and file", async () => {
    const wrapper = mountNavigator();
    await wrapper.findAll(".nav-source")[1]!.trigger("click");
    await wrapper.findAll(".nav-file")[0]!.trigger("click");
    expect(wrapper.emitted("select-source")).toEqual([["Tab2"]]);
    expect(wrapper.emitted("select-file")).toEqual([["subjects.tsv"]]);
  });

  it("lists the paper first among the sources, with its PDF, and emits it", async () => {
    const wrapper = mountNavigator({ detail: detail({ papers: [paperFile("Example.pdf")] }), source: PAPER });
    const entries = wrapper.findAll(".nav-paper, .nav-source");
    expect(entries.map((entry) => entry.get(".nav-name").text())).toEqual(["Paper", "Fig1", "Tab2"]);
    const paper = entries[0]!;
    expect(paper.classes()).toContain("nav-paper");
    expect(paper.get(".nav-kind").text()).toBe("Example.pdf");
    expect(paper.attributes("disabled")).toBeUndefined();
    expect(paper.attributes("aria-current")).toBe("true");
    expect(wrapper.findAll(".nav-source").some((entry) => entry.attributes("aria-current") === "true")).toBe(false);
    await paper.trigger("click");
    expect(wrapper.emitted("select-source")).toEqual([[PAPER]]);
  });

  it("names the first PDF and how many more the folder has", () => {
    const wrapper = mountNavigator({ detail: detail({ papers: [paperFile("Example.pdf"), paperFile("Example_Supp.pdf")] }) });
    expect(wrapper.get(".nav-paper .nav-kind").text()).toBe("Example.pdf and 1 more");
  });

  it("shows the paper of a study without a PDF as a disabled entry that names the missing PDF", () => {
    const paper = mountNavigator().get(".nav-paper");
    expect(paper.attributes("disabled")).toBeDefined();
    expect(paper.get(".nav-kind").text()).toBe("No Example.pdf");
  });
});
