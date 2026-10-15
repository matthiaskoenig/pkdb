import { afterEach, describe, expect, it } from "vitest";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { validatesAfterWrite } from "../../src/curation-app/acknowledging";
import FailureDetails from "../../src/curation-app/components/FailureDetails.vue";
import { curationRoutes } from "../../src/curation-app/routes";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { curationStudyViews } from "../../src/curation-app/studyViews";
import { serveApi } from "../components/curation-dom";
import { roster, snapshot, studyDetail, studyRow } from "./curation-fixtures";

const EXAMPLE = "/local/studies/caffeine/Example";
const SUBJECTS = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
};

let pinia: Pinia | null = null;
afterEach(() => {
  if (pinia) disposePinia(pinia);
  pinia = null;
});

describe("the study views of the curation app", () => {
  it("show and do everything, with the routes of its router and the failure details of the local server", () => {
    const views = curationStudyViews();
    expect(views.capabilities.value).toEqual({ edit: true, curation: true, files: true, jobs: true });
    expect(views.routes).toBe(curationRoutes);
    expect(views.parts.failureDetails).toBe(FailureDetails);
    expect(views.data.pdfjsAssets()).toBe(new URL("pdfjs/", document.baseURI).href);
  });

  it("read the open study, its tables, the roster and the state of the local server through the stores, which they look up when they read", async () => {
    // Made before Pinia is active, as the plugin of tests/setup.ts makes it.
    const views = curationStudyViews();
    const state = snapshot({ studies: [studyRow()] });
    const requests = serveApi({
      "GET /local/state": state,
      [`GET ${EXAMPLE}`]: studyDetail(),
      [`GET ${EXAMPLE}/tables/subjects.tsv`]: SUBJECTS,
      "GET /local/curators": { curators: roster() },
    });
    pinia = createPinia();
    setActivePinia(pinia);
    await useOverviewStore().refresh();
    await useStudyStore().open("caffeine", "Example");
    expect(views.data.detail.value?.id).toBe("caffeine/Example");
    expect(views.data.error.value).toBeNull();
    expect(await views.data.table("subjects.tsv")).toEqual(SUBJECTS);
    expect(views.data.rows.value.map((row) => row.id)).toEqual(["caffeine/Example"]);
    expect(views.data.repository.value).toBe(state.github.repository);
    expect(views.data.validatesAfterWrite.value).toBe(validatesAfterWrite(state));
    expect(views.data.profiles.value.size).toBe(0);
    expect((await views.data.curators()).map((profile) => profile.username)).toEqual(["janekg", "mkoenig", "curator"]);
    // Every view that names people asks when it mounts: the store answers them all with one load.
    await Promise.all([views.data.curators(), views.data.curators()]);
    expect(requests.filter(({ path }) => path === "/local/curators")).toHaveLength(1);
    expect([...views.data.profiles.value.keys()]).toEqual(["janekg", "mkoenig", "curator"]);
    views.data.setRowFilter("subjects.tsv", { kind: "source", source: "Tab2" });
    expect(useStudyStore().rowFilter("subjects.tsv")).toEqual({ kind: "source", source: "Tab2" });
  });
});
