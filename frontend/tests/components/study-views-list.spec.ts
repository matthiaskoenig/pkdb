import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { VSelect } from "vuetify/components";
import StudyTable from "../../src/curation-app/components/StudyTable.vue";
import StudyFilters from "../../src/study-views/components/StudyFilters.vue";
import { roster, studyRow } from "../unit/curation-fixtures";
import { memoryData, mountViews, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => setActivePinia(undefined));

const ROWS = [
  studyRow({ id: "caffeine/A2020", name: "A2020", path: "studies/caffeine/A2020", summary: { ...studyRow().summary, curators: ["mkoenig"] } }),
  studyRow({ id: "codeine/B2021", name: "B2021", substance: "codeine", path: "studies/codeine/B2021", summary: { ...studyRow().summary, curators: ["janekg"] } }),
  studyRow({ id: "caffeine/C2022", name: "C2022", path: "studies/caffeine/C2022", summary: { ...studyRow().summary, curators: ["mkoenig"] } }),
];
const COUNTS = { all: 3, attention: 0, draft: 3, in_review: 0, approved: 0 };

function filters(me: string | null = "mkoenig") {
  return mountViews(StudyFilters, {
    context: viewsContext({ data: memoryData({ rows: ROWS, profiles: roster() }) }),
    props: { counts: COUNTS, shown: 2, me, search: "", substance: "", curator: "", chip: "all" },
  });
}

describe("the filter line of the study list", () => {
  it("counts the shown studies of the page and offers its substances and curators, the reader first", () => {
    const wrapper = filters();
    expect(wrapper.get(".overview-count").text()).toBe("2 of 3 studies");
    const [substances, curators] = wrapper.findAllComponents(VSelect);
    expect(substances!.props("items")).toEqual([
      { title: "All substances", value: "" },
      { title: "caffeine", value: "caffeine" },
      { title: "codeine", value: "codeine" },
    ]);
    expect(curators!.props("items")).toEqual([
      { title: "All curators", value: "" },
      { title: "Me: Matthias König (2)", value: "mkoenig" },
      { title: "Jan Grzegorzewski (1)", value: "janekg" },
    ]);
  });

  it("filters by the search 150 ms after the last keystroke", async () => {
    const wrapper = filters(null);
    await wrapper.get(".overview-search input").setValue("cod");
    expect(wrapper.findComponent(StudyFilters).emitted("update:search")).toBeUndefined();
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(wrapper.findComponent(StudyFilters).emitted("update:search")).toEqual([["cod"]]);
  });
});

describe("the study table", () => {
  it("links the issue and shows the curators by the repository and the profiles of the page, also without a selection of its page", async () => {
    const router = websiteRouter();
    await router.push("/studies");
    const row = studyRow({ issue: { number: 2158, state: null, labels: [], assignees: [], url: null }, summary: { ...studyRow().summary, curators: ["mkoenig"] } });
    const wrapper = mountViews(StudyTable, {
      context: viewsContext({ data: memoryData({ profiles: roster(), repository: "matthiaskoenig/pkdb_data" }) }),
      props: { rows: [row], sort: { key: "study", descending: false }, caption: "Studies" },
      plugins: [router],
    });
    await flushPromises();
    expect(wrapper.get("caption").text()).toBe("Studies");
    const shown = wrapper.get("tr.study-row");
    expect(shown.get(".cell-issue a").attributes("href")).toBe("https://github.com/matthiaskoenig/pkdb_data/issues/2158");
    expect(shown.get("img.curator-photo").attributes("alt")).toBe("Matthias König");
    await shown.get(".cell-select input").setValue(true);
    expect(shown.classes()).toContain("study-row--selected");
  });
});
