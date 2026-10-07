import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import type { StudyDetail } from "../../src/curation-app/api/types";
import ReferenceDialog from "../../src/curation-app/components/ReferenceDialog.vue";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { json, snapshot, studyDetail, studyMetadata } from "../unit/curation-fixtures";
import {
  button,
  click,
  field,
  page,
  serveApi,
  setViewport,
  textArea,
  type Handler,
  type ServedRequest,
} from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";

let pinia: Pinia;
let requests: ServedRequest[];

const saved = {
  sid: "3678553",
  name: "Example",
  pmid: "3678553",
  title: "Caffeine kinetics",
  journal: "Clin Pharmacokinet",
  publication_date: "1988",
  authors: [{ first_name: "Jan", last_name: "Smith" }, { organization: "Caffeine group" }],
};

const preview = {
  reference: { ...saved, title: "Caffeine kinetics in smokers", provenance: { warnings: ["PubMed was not asked."] } },
  changes: { title: { before: "Caffeine kinetics", after: "Caffeine kinetics in smokers" } },
  revision: "folder-1",
  token: "token-1",
};

/** The dialog for `caffeine/Example` with `detail` open in the study store and `routes` of the API. */
async function mountDialog(detail: StudyDetail = studyDetail(), routes: Record<string, unknown> = {}) {
  requests = serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: detail,
    "POST /local/reference/read": { reference: saved },
    ...routes,
  });
  await useOverviewStore().refresh();
  await useStudyStore().open("caffeine", "Example");
  const wrapper = mount(ReferenceDialog, {
    props: { modelValue: true, unsavedIdentifiers: false },
    attachTo: document.body,
    global: { plugins: [pinia] },
  });
  await flushPromises();
  return wrapper;
}

function posted(path: string): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === path).map(({ body }) => body);
}

function dialogText(): string {
  return page().get('.v-overlay--active[role="dialog"]').text();
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("ReferenceDialog", () => {
  it("reads reference.json into the correction fields", async () => {
    await mountDialog();
    expect(posted("/local/reference/read")).toEqual([{ id: "caffeine/Example" }]);
    expect(field("Title").element.value).toBe("Caffeine kinetics");
    expect(textArea("Authors").element.value).toBe("Smith, Jan");
    expect(field("Organizations").element.value).toBe("Caffeine group");
    expect(field("Journal").element.value).toBe("Clin Pharmacokinet");
    expect(field("Publication date").element.value).toBe("1988");
    expect(dialogText()).toContain("PMID 3678553");
  });

  it("previews only the changed fields", async () => {
    await mountDialog(studyDetail(), { "POST /local/reference/preview": preview });
    await field("Title").setValue("Caffeine kinetics in smokers");
    await textArea("Authors").setValue("Smith, Jan\nDoe");
    await click("Preview");
    expect(posted("/local/reference/preview")).toEqual([
      {
        id: "caffeine/Example",
        input: {
          title: "Caffeine kinetics in smokers",
          authors: [
            { last_name: "Smith", first_name: "Jan" },
            { last_name: "Doe", first_name: "" },
            { organization: "Caffeine group" },
          ],
        },
        refresh: false,
        reset_overrides: false,
      },
    ]);
    const text = dialogText();
    expect(text).toContain("Caffeine kinetics in smokers");
    expect(text).toContain("PubMed was not asked.");
    expect(text).toContain("Title: Caffeine kinetics → Caffeine kinetics in smokers");
  });

  it("saves only a current preview: Save waits for a preview and stops after any further edit", async () => {
    const wrapper = await mountDialog(studyDetail(), {
      "POST /local/reference/preview": preview,
      "POST /local/reference/save": { ok: true },
    });
    expect(button("Save reference").element.disabled).toBe(true);

    await field("Title").setValue("Caffeine kinetics in smokers");
    await click("Preview");
    expect(button("Save reference").element.disabled).toBe(false);

    await field("Journal").setValue("Eur J Clin Pharmacol");
    expect(button("Save reference").element.disabled).toBe(true);

    await click("Preview");
    await click("Save reference");
    expect(posted("/local/reference/save")).toEqual([{ id: "caffeine/Example", token: "token-1" }]);
    expect(wrapper.emitted("saved")).toHaveLength(1);
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  });

  it("drops a preview that answers after a further edit", async () => {
    let answer: (response: Response) => void = () => undefined;
    await mountDialog(studyDetail(), {
      "POST /local/reference/preview": (() => new Promise<Response>((resolve) => (answer = resolve))) satisfies Handler,
    });
    await field("Title").setValue("Caffeine kinetics in smokers");
    await button("Preview").trigger("click");
    await field("Journal").setValue("Eur J Clin Pharmacol");
    answer(json(preview));
    await flushPromises();
    expect(button("Save reference").element.disabled).toBe(true);
    expect(dialogText()).not.toContain("PubMed was not asked.");
  });

  it("shows why a preview failed", async () => {
    await mountDialog(studyDetail(), {
      "POST /local/reference/preview": () =>
        json({ error: "Manual references require a title and at least one author or organization" }, { status: 400 }),
    });
    await click("Preview");
    expect(dialogText()).toContain("Manual references require a title and at least one author or organization");
  });

  it("searches a citation for a study without identifiers and uses the DOI of a candidate", async () => {
    const value = studyMetadata();
    delete value.reference;
    const manual = studyDetail({ metadata: { revision: "study-1", value, issues: [] } });
    const wrapper = await mountDialog(manual, {
      "POST /local/reference/read": { reference: { sid: "Example", name: "Example", title: "Caffeine kinetics" } },
      "POST /local/reference/search": {
        candidates: [
          {
            doi: "10.1000/caffeine",
            pmid: null,
            title: "Caffeine kinetics in man",
            journal: "Clin Pharmacokinet",
            abstract: null,
            authors: [{ last_name: "Smith", first_name: "Jan" }],
            publication_date: "1988",
            date: null,
          },
        ],
      },
      "POST /local/reference/preview": preview,
    });
    expect(dialogText()).toContain("study.json names no PMID or DOI.");
    expect(field("Citation").element.value).toBe("Caffeine kinetics");

    await field("Citation").setValue("Caffeine kinetics Smith 1988");
    await click("Search");
    expect(posted("/local/reference/search")).toEqual([
      { id: "caffeine/Example", citation: "Caffeine kinetics Smith 1988" },
    ]);
    expect(dialogText()).toContain("Caffeine kinetics in man");
    expect(dialogText()).toContain("Smith · Clin Pharmacokinet · 1988");

    // A manual reference sends all of its fields.
    await click("Preview");
    expect(posted("/local/reference/preview")[0]?.input).toEqual({ title: "Caffeine kinetics" });

    await click("Use DOI 10.1000/caffeine");
    expect(wrapper.emitted("useDoi")).toEqual([["10.1000/caffeine"]]);
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  });

  it("warns that unsaved identifiers of the form are not used", async () => {
    const wrapper = await mountDialog();
    await wrapper.setProps({ unsavedIdentifiers: true });
    expect(dialogText()).toContain("Save study.json first");
  });
});
