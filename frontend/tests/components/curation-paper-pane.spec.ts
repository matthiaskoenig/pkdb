import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import CurationPaperPane from "../../src/curation-app/components/CurationPaperPane.vue";
import type { PaperPlace } from "../../src/study-views/paper";
import { makeRouter } from "../../src/curation-app/router";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, paperFile, snapshot } from "../unit/curation-fixtures";
import { page, serveApi, type Handler } from "./curation-dom";

enableAutoUnmount(afterEach);

const PAPERS = [paperFile("Example.pdf", 19_507), paperFile("Example Supp.pdf", 4_590_032)];

async function mountPane(props: Record<string, unknown> = {}, routes: Record<string, unknown> = {}) {
  const requests = serveApi({ "GET /local/state": snapshot(), ...routes });
  const pinia = createPinia();
  setActivePinia(pinia);
  await useOverviewStore().refresh();
  const wrapper = mount(CurationPaperPane, {
    props: { study: "caffeine/Example", papers: PAPERS, file: null, ...props },
    attachTo: document.body,
    global: { plugins: [pinia, makeRouter()], stubs: { PaperViewer: true } },
  });
  await flushPromises();
  return { wrapper, requests };
}

describe("paper pane", () => {
  it("names the PDF with its size, opens it in a new tab of the app, and shows it in the viewer", async () => {
    const { wrapper } = await mountPane({ papers: PAPERS.slice(0, 1) });
    expect(wrapper.get("section").attributes("aria-label")).toBe("Paper Example.pdf");
    expect(wrapper.get(".pane-head-name").text()).toBe("Paper");
    expect(wrapper.find("select").exists()).toBe(false);
    expect(wrapper.get(".pane-head").text()).toContain("Example.pdf");
    expect(wrapper.get(".pane-head").text()).toContain("20 kB");
    expect(wrapper.get("a.paper-action").attributes()).toMatchObject({
      href: "#/studies/caffeine/Example/paper/Example.pdf",
      target: "_blank",
      rel: "noopener",
      "aria-label": "New tab",
    });
    expect(wrapper.findComponent({ name: "PaperViewer" }).props()).toEqual({
      url: PAPERS[0]!.url,
      file: "Example.pdf",
      version: PAPERS[0]!.version,
      place: null,
    });
  });

  it("offers the PDFs of the folder in their order, shows the chosen one, and the first when the chosen one is gone", async () => {
    const { wrapper } = await mountPane({ file: "Example Supp.pdf" });
    const select = wrapper.get<HTMLSelectElement>("select.pane-head-select");
    expect(select.attributes("aria-label")).toBe("PDF of the paper");
    expect(select.findAll("option").map((option) => option.text())).toEqual(["Example.pdf", "Example Supp.pdf"]);
    expect(select.element.value).toBe("Example Supp.pdf");
    expect(wrapper.get("a.paper-action").attributes("href")).toBe("#/studies/caffeine/Example/paper/Example%20Supp.pdf");
    expect(wrapper.get(".pane-head").text()).toContain("4.6 MB");
    await select.setValue("Example.pdf");
    expect(wrapper.emitted("update:file")).toEqual([["Example.pdf"]]);
    await wrapper.setProps({ papers: PAPERS.slice(0, 1) });
    expect(wrapper.findComponent({ name: "PaperViewer" }).props("file")).toBe("Example.pdf");
  });

  it("hands the place of the viewer to its parent and back, which keeps it when the pane mounts again", async () => {
    const kept: PaperPlace = { url: PAPERS[1]!.url, page: 3, fit: null, scale: 1.25 };
    const { wrapper } = await mountPane({ file: "Example Supp.pdf", place: kept });
    const viewer = wrapper.findComponent({ name: "PaperViewer" });
    expect(viewer.props("place")).toEqual(kept);
    const moved: PaperPlace = { ...kept, page: 4 };
    viewer.vm.$emit("update:place", moved);
    expect(wrapper.emitted("update:place")).toEqual([[moved]]);
  });

  it("opens the PDF in the PDF program of the system", async () => {
    const { wrapper, requests } = await mountPane({ file: "Example Supp.pdf" }, { "POST /local/files/open": { ok: true } });
    await wrapper.get("button[aria-label='Open in PDF program']").trigger("click");
    await flushPromises();
    expect(requests.find((request) => request.path === "/local/files/open")?.body).toEqual({
      study_id: "caffeine/Example",
      file: "Example Supp.pdf",
    });
    expect(page().get(".paper-pane [role='status']").text()).toBe("Example Supp.pdf opened in the PDF program.");
  });

  it("says why the PDF program could not open the PDF", async () => {
    const failing: Handler = () =>
      json(
        {
          error: "Could not open Example.pdf of caffeine/Example.",
          code: "open_failed",
          detail: "CalledProcessError: xdg-open exited with status 4",
          action: "Open file (POST /local/files/open)",
          request_id: "3f9c2a71",
          time: "2026-10-12T10:00:00+02:00",
        },
        { status: 500 },
      );
    const { wrapper } = await mountPane({}, { "POST /local/files/open": failing });
    await wrapper.get("button[aria-label='Open in PDF program']").trigger("click");
    await flushPromises();
    const alert = wrapper.get(".action-failure");
    expect(alert.text()).toContain("Could not open Example.pdf of caffeine/Example.");
    expect(alert.get(".action-failure-detail").text()).toBe("CalledProcessError: xdg-open exited with status 4");
  });
});
