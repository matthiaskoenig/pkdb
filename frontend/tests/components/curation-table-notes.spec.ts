import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import type { Router } from "vue-router";
import type { StudyDetail, TableKind, ValidationIssue } from "../../src/curation-app/api/types";
import TableNotes from "../../src/curation-app/components/TableNotes.vue";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { fullStudyMetadata, json, roster, snapshot, studyDetail } from "../unit/curation-fixtures";
import { click, scrollLayout, serveApi, setViewport, textArea } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const METADATA = "/local/studies/metadata";

let pinia: Pinia;
let router: Router;

/** The detail of caffeine/Example with the study.json of `fullStudyMetadata`, with `changes`. */
function detail(changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({ metadata: { revision: "study-1", value: fullStudyMetadata(), issues: [] }, ...changes });
}

/** An issue of study.json as the library gives it: the message names the field, the detail does not. */
function issue(field: string, message: string): ValidationIssue {
  return { code: "invalid_study_json", severity: "error", message: `${field}: ${message}`, field, context: { detail: message } };
}

/** The panel of the notes of `kind` in the open study `value`, with `routes` besides the defaults. */
async function mountNotes(
  kind: TableKind,
  value: StudyDetail = detail(),
  routes: Record<string, unknown> = {},
  props: Record<string, unknown> = {},
) {
  serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: value,
    "GET /local/curators": { curators: roster() },
    ...routes,
  });
  await useOverviewStore().refresh();
  await useStudyStore().open("caffeine", "Example");
  router = makeRouter();
  await router.push("/studies/caffeine/Example/data");
  await router.isReady();
  const wrapper = mountPanel(kind, props);
  await flushPromises();
  return wrapper;
}

function mountPanel(kind: TableKind, props: Record<string, unknown> = {}) {
  return mount(TableNotes, { props: { kind, ...props }, attachTo: document.body, global: { plugins: [pinia, router] } });
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("notes of a table kind", () => {
  it("names the kind and what its notes hold, and starts closed", async () => {
    const wrapper = await mountNotes("outputs");
    const toggle = wrapper.get(".table-notes-toggle");
    expect(toggle.text()).toBe("Notes of the outputs 1 description · 1 comment");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(toggle.attributes("aria-controls")).toBe(wrapper.get(".table-notes-body").attributes("id"));
    expect(wrapper.get(".table-notes-body").isVisible()).toBe(false);
    expect(wrapper.get("h4").text()).toBe(toggle.text());
    expect(mountPanel("subjects").get(".table-notes-toggle").text()).toBe("Notes of the subjects No notes");
    expect(mountPanel("timecourses").get(".table-notes-toggle").text()).toBe("Notes of the timecourses 1 description");
  });

  it("opens and closes, and the study keeps that per kind", async () => {
    const first = await mountNotes("subjects");
    await first.get(".table-notes-toggle").trigger("click");
    expect(first.get(".table-notes-toggle").attributes("aria-expanded")).toBe("true");
    expect(first.get(".table-notes-body").isVisible()).toBe(true);

    // Another table of the kind shows the same notes, open; another kind keeps its own state.
    expect(mountPanel("subjects").get(".table-notes-toggle").attributes("aria-expanded")).toBe("true");
    expect(mountPanel("outputs").get(".table-notes-toggle").attributes("aria-expanded")).toBe("false");
    expect([...useStudyStore().draft.notesOpen]).toEqual(["subjects"]);
  });

  it("heads its descriptions and comments one level below its own heading", async () => {
    const wrapper = await mountNotes("outputs");
    await wrapper.get(".table-notes-toggle").trigger("click");
    const headings = wrapper.findAll("h4, h5").map((heading) => [heading.element.tagName, heading.text()]);
    expect(headings).toEqual([
      ["H4", "Notes of the outputs 1 description · 1 comment"],
      ["H5", "Descriptions"],
      ["H5", "Comments"],
    ]);
  });

  it("edits the notes of its kind in the draft of study.json", async () => {
    const wrapper = await mountNotes("outputs");
    await wrapper.get(".table-notes-toggle").trigger("click");
    expect(textArea("Description 1", wrapper.element).element.value).toBe("Clearance from Table 2.");
    await click("Add description to outputs");
    await textArea("Description 2", wrapper.element).setValue("AUC from 0 to 24 h.");

    const draft = useStudyStore().draft;
    expect(draft.form?.notes.outputs.descriptions).toEqual(["Clearance from Table 2.", "AUC from 0 to 24 h."]);
    expect(draft.unsaved).toEqual(["data"]);
    expect(wrapper.get(".table-notes-toggle").text()).toBe("Notes of the outputs 2 descriptions · 1 comment");
  });

  it("opens by itself when a save is refused for a field of its notes", async () => {
    const wrapper = await mountNotes("outputs", detail(), {
      [`POST ${METADATA}`]: () =>
        json(
          { error: "Invalid study.json", issues: [issue("notes.outputs.descriptions.0", "Enter some text or remove this entry.")] },
          { status: 422 },
        ),
    });
    const draft = useStudyStore().draft;
    draft.form!.notes.outputs.descriptions[0] = " ";
    await draft.save();
    await flushPromises();
    expect(wrapper.get(".table-notes-toggle").attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".table-notes-body").text()).toContain("Enter some text or remove this entry.");
  });

  it("says when its notes changed on disk at a reload, and opens", async () => {
    const disk = fullStudyMetadata({
      notes: { ...fullStudyMetadata().notes, subjects: { descriptions: ["From disk."], comments: [] } },
    });
    const wrapper = await mountNotes("subjects", detail(), {
      [`POST ${METADATA}`]: () =>
        json({ error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) }, { status: 409 }),
    });
    const draft = useStudyStore().draft;
    draft.form!.creator = "janekg";
    await draft.save();
    draft.reload();
    await flushPromises();
    expect(wrapper.get(".table-notes-toggle").text()).toBe("Notes of the subjects 1 description · changed on disk");
    expect(wrapper.get(".table-notes-toggle").attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".descriptions-block").text()).toContain("Changed on disk");
  });

  it("says that study.json is not valid and lists the issues of its notes", async () => {
    const broken = detail({
      metadata: {
        revision: "broken-1",
        value: null,
        issues: [issue("notes.subjects.comments.0.user", "A user name has no spaces."), issue("creator", "Enter a user name.")],
      },
    });
    const wrapper = await mountNotes("subjects", broken);
    const toggle = wrapper.get(".table-notes-toggle");
    expect(toggle.text()).toBe("Notes of the subjects study.json is not valid");
    // It opened by itself for the issue in its notes.
    expect(toggle.attributes("aria-expanded")).toBe("true");
    const body = wrapper.get(".table-notes-body");
    expect(body.get(".table-notes-text").text()).toBe(
      "study.json is not valid, so its notes cannot show here. Fix it in your editor, or start a new one in Metadata.",
    );
    expect(body.get("a").attributes("href")).toBe("#/studies/caffeine/Example/metadata");
    expect(body.findAll(".table-notes-issues li").map((item) => item.text())).toEqual(["A user name has no spaces."]);
    expect(body.find("textarea").exists()).toBe(false);

    // Another kind has no issue: it stays closed and lists none.
    const outputs = mountPanel("outputs");
    expect(outputs.get(".table-notes-toggle").attributes("aria-expanded")).toBe("false");
    expect(outputs.find(".table-notes-issues").exists()).toBe(false);
  });

  it("fades out at the bottom of its body while more of its notes follow below, and not at their end", async () => {
    const wrapper = await mountNotes("outputs");
    await wrapper.get(".table-notes-toggle").trigger("click");
    const body = wrapper.get(".table-notes-body").element;
    await scrollLayout(body, 200, 500);
    expect(wrapper.get(".table-notes-frame > .pane-more").attributes("aria-hidden")).toBe("true");
    await scrollLayout(body, 200, 500, 300);
    expect(wrapper.find(".pane-more").exists()).toBe(false);

    // A closed panel has no body to fade.
    await scrollLayout(body, 200, 500);
    await wrapper.get(".table-notes-toggle").trigger("click");
    expect(wrapper.find(".pane-more").exists()).toBe(false);
  });

  it("focuses its toggle when a link opened it", async () => {
    const wrapper = await mountNotes("subjects", detail(), {}, { focused: true });
    await flushPromises();
    expect(document.activeElement).toBe(wrapper.get(".table-notes-toggle").element);
  });
});
