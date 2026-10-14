import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { createPinia } from "pinia";
import ActionFailureAlert from "../../src/curation-app/components/ActionFailureAlert.vue";
import PaperPane from "../../src/curation-app/components/PaperPane.vue";
import ProblemItem from "../../src/curation-app/components/ProblemItem.vue";
import SectionTabs from "../../src/curation-app/components/SectionTabs.vue";
import StudyTableRow from "../../src/curation-app/components/StudyTableRow.vue";
import { actionFailure } from "../../src/study-views/study";
import { rowItem } from "../../src/study-views/studyTable";
import type { Problem } from "../../src/study-views/types";
import { paperFile, studyRow } from "../unit/curation-fixtures";
import { mountViews, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);

async function routerAt(path = "/data/caffeine/Example/data") {
  const router = websiteRouter();
  await router.push(path);
  return router;
}

const ISSUE: Problem = {
  code: "unit_unknown",
  severity: "warning",
  message: "Unknown unit mg/dl.",
  source: { file: "outputs_Tab2.tsv", row: 2 },
  acknowledgeable: false,
};

describe("the links of the shared study views", () => {
  it("go to the sections of a study by the routes of the page", async () => {
    const wrapper = mountViews(SectionTabs, {
      context: viewsContext(),
      props: { substance: "caffeine", name: "Example", active: "data", counts: {}, unsaved: [] },
      plugins: [await routerAt()],
    });
    expect(wrapper.findAll("a.section-tab").map((link) => link.attributes("href"))).toEqual([
      "/data/caffeine/Example/metadata",
      "/data/caffeine/Example/data",
      "/data/caffeine/Example/problems",
      "/data/caffeine/Example/review",
      "/data/caffeine/Example/activity",
    ]);
  });

  it("open a study of the list by the route of the page, by its link and by a click on its row", async () => {
    const router = await routerAt("/studies");
    const wrapper = mountViews(StudyTableRow, {
      context: viewsContext(),
      props: { item: rowItem(studyRow(), new Map(), ""), selected: false, rowIndex: 2 },
      plugins: [router],
    });
    expect(wrapper.get("a.study-identity").attributes("href")).toBe("/data/caffeine/Example");
    await wrapper.get("tr").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe("/data/caffeine/Example");
  });

  it("show the row and the notes of a problem by the route of the page", async () => {
    const wrapper = mountViews(ProblemItem, {
      context: viewsContext(),
      props: {
        issue: ISSUE,
        study: "caffeine/Example",
        idBase: "problem",
        showable: true,
        pending: false,
        automatic: true,
        disabled: false,
        validating: false,
        notesQuery: { file: "subjects.tsv", notes: "subjects" },
      },
      plugins: [await routerAt()],
    });
    expect(wrapper.findAll("a").map((link) => link.attributes("href"))).toEqual([
      "/data/caffeine/Example/data?file=outputs_Tab2.tsv&line=2",
      "/data/caffeine/Example/data?file=subjects.tsv&notes=subjects",
    ]);
  });

  it("leave out New tab of the paper when the page has no page of its own for a PDF", async () => {
    const wrapper = mountViews(PaperPane, {
      context: viewsContext(),
      props: { study: "caffeine/Example", papers: [paperFile("Example.pdf")], file: null },
      plugins: [await routerAt(), createPinia()],
      stubs: { PaperViewer: true },
    });
    expect(wrapper.get(".paper-pane").attributes("aria-label")).toBe("Paper Example.pdf");
    expect(wrapper.find("a.paper-action").exists()).toBe(false);
  });

  it("link a failure to its section by the route of the page, and show the details of a server only when the page has them", async () => {
    const failure = actionFailure("The sync found problems.", ["A sheet conflicts with its table."], {
      section: "problems",
      label: "Show the problems",
    }, {
      status: 500,
      code: "open_failed",
      detail: "CalledProcessError: exit 4",
      action: "Open tables (POST /local/studies/tables)",
      requestId: "3f9c2a71",
      time: "2026-10-12T10:00:00+02:00",
      traceback: null,
      activityId: "01JA",
    });
    const wrapper = mountViews(ActionFailureAlert, {
      context: viewsContext(),
      props: { failure, study: "caffeine/Example" },
      plugins: [await routerAt()],
    });
    expect(wrapper.get("a.action-failure-link").attributes("href")).toBe("/data/caffeine/Example/problems");
    expect(wrapper.get(".action-failure-detail").text()).toBe("CalledProcessError: exit 4");
    expect(wrapper.find(".failure-details").exists()).toBe(false);
    expect(wrapper.find(".action-failure-activity").exists()).toBe(false);
  });
});
