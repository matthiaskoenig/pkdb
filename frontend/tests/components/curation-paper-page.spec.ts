import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import App from "../../src/curation-app/App.vue";
import AppHeader from "../../src/curation-app/components/AppHeader.vue";
import { makeRouter } from "../../src/curation-app/router";
import { snapshot } from "../unit/curation-fixtures";
import { serveApi } from "./curation-dom";

enableAutoUnmount(afterEach);

describe("the paper in a tab of its own", () => {
  it("shows the PDF without the app bar, under a head that links the study to its paper in the Data section", async () => {
    serveApi({ "GET /local/state": snapshot() });
    const pinia = createPinia();
    setActivePinia(pinia);
    const router = makeRouter();
    await router.push("/studies/caffeine/Demo2020/paper/Demo2020%20Supp.pdf");
    await router.isReady();
    const title = document.title;
    const wrapper = mount(App, { attachTo: document.body, global: { plugins: [pinia, router], stubs: { PaperViewer: true } } });
    await flushPromises();
    expect(wrapper.findComponent(AppHeader).exists()).toBe(false);
    expect(wrapper.get("h1").text()).toBe("Demo2020 Supp.pdf");
    const study = wrapper.get("a.paper-page-study");
    expect(study.text()).toBe("caffeine/Demo2020");
    expect(study.attributes("href")).toBe("#/studies/caffeine/Demo2020/data?source=paper");
    expect(wrapper.findComponent({ name: "PaperViewer" }).props()).toMatchObject({
      url: "/local/studies/caffeine/Demo2020/files/Demo2020%20Supp.pdf",
      file: "Demo2020 Supp.pdf",
    });
    expect(document.title).toBe("Demo2020 Supp.pdf · caffeine/Demo2020 · PK-DB");
    wrapper.unmount();
    expect(document.title).toBe(title);
  });
});
