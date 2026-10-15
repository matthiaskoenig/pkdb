import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import NotesView from "../../src/study-views/components/NotesView.vue";
import DataSection from "../../src/study-views/sections/DataSection.vue";
import type { TableResponse } from "../../src/study-views/types";
import { fullStudyMetadata, profile, studyDetail } from "../unit/curation-fixtures";
import { setViewport } from "./curation-dom";
import { memoryData, mountViews, PUBLIC, viewsContext, websiteRouter } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => {
  setActivePinia(undefined);
  setViewport(1440);
});

const DETAIL = studyDetail({
  metadata: { revision: null, value: fullStudyMetadata(), issues: [] },
  people: { creator: null, curators: [{ user: "janekg", rating: null, profile: profile("janekg", "Jan Grzegorzewski") }], collaborators: [] },
});
const OUTPUTS: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label"],
  rows: [{ line: 1, cells: ["Example", "Tab2", "caf_cl"] }],
};

const SUBJECTS: TableResponse = {
  file: "subjects.tsv",
  kind: "table",
  header: ["study", "name", "source"],
  rows: [{ line: 1, cells: ["Example", "all", "Tab2"] }],
};

function notes(props: Record<string, unknown>) {
  return mountViews(NotesView, {
    context: viewsContext({ capabilities: PUBLIC, data: memoryData({ detail: DETAIL }) }),
    props,
    attachTo: document.body,
  });
}

describe("the notes of a table kind, read only", () => {
  it("start closed with what they hold, and open with their toggle", async () => {
    const wrapper = notes({ kind: "outputs" });
    const toggle = wrapper.get("button.notes-view-toggle");
    expect(toggle.text()).toContain("Notes of the outputs");
    expect(toggle.text()).toContain("1 description · 1 comment");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".notes-view-body").text()).toContain("Clearance from Table 2.");
    expect(wrapper.get(".notes-view-author").text()).toBe("Jan Grzegorzewski");
    expect(wrapper.get(".notes-view-comment").text()).toContain("AUC rounded.");
  });

  it("name the author of a comment by the curators that the page knows", async () => {
    const metadata = fullStudyMetadata({
      notes: { outputs: { descriptions: [], comments: [{ user: "reviewer", text: "Units checked." }] } },
    });
    const detail = { ...DETAIL, metadata: { revision: null, value: metadata, issues: [] } };
    const wrapper = mountViews(NotesView, {
      context: viewsContext({
        capabilities: PUBLIC,
        data: memoryData({ detail, profiles: [profile("reviewer", "Rita Reviewer")] }),
      }),
      props: { kind: "outputs" },
    });
    await flushPromises();
    await wrapper.get("button.notes-view-toggle").trigger("click");
    expect(wrapper.get(".notes-view-author").text()).toBe("Rita Reviewer");
  });

  it("open and take the focus once when a link names them", async () => {
    const wrapper = notes({ kind: "outputs", focused: true });
    await flushPromises();
    const toggle = wrapper.get("button.notes-view-toggle");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(toggle.element);
    expect(wrapper.findComponent(NotesView).emitted("took-focus")).toHaveLength(1);
  });

  it("show nothing for a kind without notes, and let a link that names them go at once", async () => {
    expect(notes({ kind: "subjects" }).find(".notes-view").exists()).toBe(false);
    const linked = notes({ kind: "subjects", focused: true });
    await flushPromises();
    expect(linked.find(".notes-view").exists()).toBe(false);
    expect(linked.findComponent(NotesView).emitted("took-focus")).toHaveLength(1);
    expect(document.activeElement).toBe(document.body);
  });

  it("stand above the rows of the Data section of a page without edit", async () => {
    const router = websiteRouter();
    await router.push("/data/caffeine/Example/data?file=outputs_Tab2.tsv&notes=outputs");
    const wrapper = mountViews(DataSection, {
      context: viewsContext({ capabilities: PUBLIC, data: memoryData({ detail: DETAIL, tables: { "outputs_Tab2.tsv": OUTPUTS } }) }),
      plugins: [router],
      stubs: { SourceOverlay: true, PaperViewer: true, SourcePane: true },
      attachTo: document.body,
    });
    await flushPromises();
    const toggle = wrapper.get(".rows-pane .notes-view-toggle");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(toggle.element);
    expect(router.currentRoute.value.query.notes).toBeUndefined();
  });

  it("let the Data section forget a link to the notes of a kind without notes", async () => {
    const router = websiteRouter();
    await router.push("/data/caffeine/Example/data?file=subjects.tsv&notes=subjects");
    const wrapper = mountViews(DataSection, {
      context: viewsContext({ capabilities: PUBLIC, data: memoryData({ detail: DETAIL, tables: { "subjects.tsv": SUBJECTS } }) }),
      plugins: [router],
      stubs: { SourceOverlay: true, PaperViewer: true, SourcePane: true },
      attachTo: document.body,
    });
    await flushPromises();
    const view = wrapper.findComponent(NotesView);
    expect(view.props("kind")).toBe("subjects");
    expect(view.emitted("took-focus")).toHaveLength(1);
    expect(view.props("focused")).toBe(false);
    expect(wrapper.find(".notes-view").exists()).toBe(false);
    expect(router.currentRoute.value.query.notes).toBeUndefined();
  });

  it("stay open for the study when they mount again, as the page keeps which notes are open", async () => {
    const data = memoryData({ detail: DETAIL });
    const context = viewsContext({ capabilities: PUBLIC, data });
    const first = mountViews(NotesView, { context, props: { kind: "outputs" }, attachTo: document.body });
    await first.get("button.notes-view-toggle").trigger("click");
    expect([...data.notesOpen.value]).toEqual(["outputs"]);
    first.unmount();
    const again = mountViews(NotesView, { context, props: { kind: "outputs" }, attachTo: document.body });
    expect(again.get("button.notes-view-toggle").attributes("aria-expanded")).toBe("true");
    await again.get("button.notes-view-toggle").trigger("click");
    expect(data.notesOpen.value.size).toBe(0);
  });
});
