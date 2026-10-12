import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import type { StudyDetail } from "../../src/curation-app/api/types";
import App from "../../src/curation-app/App.vue";
import AppHeader from "../../src/curation-app/components/AppHeader.vue";
import { makeRouter } from "../../src/curation-app/router";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { json, paperFile, snapshot, studyDetail } from "../unit/curation-fixtures";
import { serveApi, type Handler } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const PAPERS = [paperFile("Example.pdf"), paperFile("Example Supp.pdf", 4_590_032)];

let served: StudyDetail;

/** The app on the tab of the PDF `file` of caffeine/Example, whose study page is `detail`. */
async function mountTab(file: string, detail: StudyDetail | null = studyDetail({ papers: PAPERS })) {
  served = detail ?? studyDetail();
  serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: (() =>
      detail ? json(served) : json({ error: "caffeine/Example is not a study of this workspace" }, { status: 404 })) satisfies Handler,
  });
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = makeRouter();
  await router.push(`/studies/caffeine/Example/paper/${encodeURIComponent(file)}`);
  await router.isReady();
  const wrapper = mount(App, { attachTo: document.body, global: { plugins: [pinia, router], stubs: { PaperViewer: true } } });
  await flushPromises();
  return wrapper;
}

describe("the paper in a tab of its own", () => {
  it("shows the PDF without the app bar, under a head that links the study to its paper in the Data section", async () => {
    const title = document.title;
    const wrapper = await mountTab("Example Supp.pdf");
    expect(wrapper.findComponent(AppHeader).exists()).toBe(false);
    expect(wrapper.get("h1").text()).toBe("Example Supp.pdf");
    const study = wrapper.get("a.paper-page-study");
    expect(study.text()).toBe("caffeine/Example");
    expect(study.attributes("href")).toBe("#/studies/caffeine/Example/data?source=paper");
    expect(wrapper.findComponent({ name: "PaperViewer" }).props()).toMatchObject({
      url: PAPERS[1]!.url,
      file: "Example Supp.pdf",
    });
    expect(wrapper.find(".action-failure").exists()).toBe(false);
    expect(document.title).toBe("Example Supp.pdf · caffeine/Example · PK-DB");
    wrapper.unmount();
    expect(document.title).toBe(title);
  });

  it("says that a file of the address that is no PDF of the study is none, instead of showing it", async () => {
    const wrapper = await mountTab("Example_Fig1.png");
    expect(wrapper.get("h1").text()).toBe("Example_Fig1.png");
    expect(wrapper.findComponent({ name: "PaperViewer" }).exists()).toBe(false);
    expect(wrapper.get(".action-failure").text()).toContain("Example_Fig1.png is not a PDF of this study.");
  });

  it("says that the PDF is no longer in the study folder while it is gone, and shows it again once it is back", async () => {
    const wrapper = await mountTab("Example Supp.pdf");
    served = studyDetail({ papers: PAPERS.slice(0, 1) });
    await useStudyStore().refresh();
    await flushPromises();
    expect(wrapper.findComponent({ name: "PaperViewer" }).exists()).toBe(false);
    expect(wrapper.get(".action-failure").text()).toContain("Example Supp.pdf is no longer in the study folder.");
    served = studyDetail({ papers: PAPERS });
    await useStudyStore().refresh();
    await flushPromises();
    expect(wrapper.findComponent({ name: "PaperViewer" }).props("file")).toBe("Example Supp.pdf");
    expect(wrapper.find(".action-failure").exists()).toBe(false);
  });

  it("says that the study is not in the workspace", async () => {
    const wrapper = await mountTab("Example.pdf", null);
    expect(wrapper.findComponent({ name: "PaperViewer" }).exists()).toBe(false);
    expect(wrapper.get(".action-failure").text()).toContain("There is no study folder caffeine/Example in the workspace.");
  });
});
