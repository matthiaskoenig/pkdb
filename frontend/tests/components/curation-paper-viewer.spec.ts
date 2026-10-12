import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { defineComponent, h, ref } from "vue";
import PaperViewer from "../../src/curation-app/components/PaperViewer.vue";
import {
  PaperImportFailed,
  type PaperEvents,
  type PaperPlace,
  type PaperSession,
  type PaperStart,
} from "../../src/curation-app/paper";

// PDF.js does not run in jsdom: the viewer gets a fake engine, which records what it opened.
const engine = vi.hoisted(() => ({ openPaper: vi.fn() }));
vi.mock("../../src/curation-app/paperEngine", () => engine);

enableAutoUnmount(afterEach);

const URL_A = "/local/studies/caffeine/Example/files/Example.pdf";
const URL_SUPP = "/local/studies/caffeine/Example/files/Example_Supp.pdf";

/** A PDF that the fake engine opened: where, how it started, its events and its session. */
interface Opened {
  container: HTMLDivElement;
  url: string;
  events: PaperEvents;
  start: PaperStart;
  session: { [Name in keyof PaperSession]: Mock<PaperSession[Name]> };
}
let opened: Opened[];

beforeEach(() => {
  opened = [];
  engine.openPaper.mockImplementation(
    async (container: HTMLDivElement, url: string, events: PaperEvents, start: PaperStart) => {
      const session = {
        goTo: vi.fn<PaperSession["goTo"]>(),
        zoom: vi.fn<PaperSession["zoom"]>(),
        fit: vi.fn<PaperSession["fit"]>(),
        find: vi.fn<PaperSession["find"]>(),
        close: vi.fn<PaperSession["close"]>(async () => undefined),
      };
      opened.push({ container, url, events, start, session });
      return session;
    },
  );
});

async function mountViewer(props: Record<string, unknown> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  const wrapper = mount(PaperViewer, {
    props: { url: URL_A, file: "Example.pdf", bytes: 1000, ...props },
    attachTo: document.body,
    global: { plugins: [pinia] },
  });
  await flushPromises();
  return wrapper;
}

/** The PDF that the viewer opened last, once it reported `pages` pages, page 1 and Fit width. */
async function shown(pages = 3): Promise<Opened> {
  const last = opened.at(-1)!;
  last.events.opened(pages);
  last.events.page(1);
  last.events.scale(1, "page-width");
  await flushPromises();
  return last;
}

/** The error of PDF.js for an error status of the local server, which carries no answer. */
function responseError(status: number): Error {
  return Object.assign(new Error(`Unexpected server response (${status}) while retrieving PDF.`), {
    name: "ResponseException",
    status,
    missing: status === 404,
  });
}

describe("paper viewer", () => {
  it("opens the PDF in its scroll container on page 1 at Fit width, and shows the page of the pages", async () => {
    const wrapper = await mountViewer();
    expect(engine.openPaper).toHaveBeenCalledTimes(1);
    const pdf = await shown(3);
    expect(pdf.url).toBe(URL_A);
    expect(pdf.container.classList.contains("paper-scroll")).toBe(true);
    expect(pdf.container.firstElementChild?.className).toBe("pdfViewer");
    expect(pdf.start).toEqual({ page: 1, fit: "page-width", scale: 1 });
    expect(wrapper.get<HTMLInputElement>("input[aria-label='Page']").element.value).toBe("1");
    expect(wrapper.get(".paper-of").text()).toBe("of 3");
    expect(wrapper.get("button[aria-label='Previous page']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("button[aria-label='Next page']").attributes("disabled")).toBeUndefined();
  });

  it("goes to the next, the previous and a typed page, and shows the page in view again for a page that the PDF lacks", async () => {
    const wrapper = await mountViewer();
    const pdf = await shown(3);
    await wrapper.get("button[aria-label='Next page']").trigger("click");
    expect(pdf.session.goTo).toHaveBeenLastCalledWith(2);
    pdf.events.page(2);
    await flushPromises();
    await wrapper.get("button[aria-label='Previous page']").trigger("click");
    expect(pdf.session.goTo).toHaveBeenLastCalledWith(1);
    const field = wrapper.get<HTMLInputElement>("input[aria-label='Page']");
    field.element.value = "3";
    await field.trigger("change");
    expect(pdf.session.goTo).toHaveBeenLastCalledWith(3);
    field.element.value = "9";
    await field.trigger("change");
    expect(pdf.session.goTo).toHaveBeenCalledTimes(3);
    expect(field.element.value).toBe("2");
  });

  it("zooms out and in by a step, chooses a fit, and shows the scale of a step in the zoom select", async () => {
    const wrapper = await mountViewer();
    const pdf = await shown();
    const zoom = wrapper.get<HTMLSelectElement>("select[aria-label='Zoom']");
    expect(zoom.findAll("option").map((option) => option.text())).toEqual(["Fit width", "Fit page", "100 %"]);
    expect(zoom.element.value).toBe("page-width");
    await wrapper.get("button[aria-label='Zoom in']").trigger("click");
    await wrapper.get("button[aria-label='Zoom out']").trigger("click");
    expect(pdf.session.zoom.mock.calls).toEqual([[1], [-1]]);
    pdf.events.scale(1.25, null);
    await flushPromises();
    expect(zoom.element.value).toBe("custom");
    expect(zoom.get("option[value='custom']").text()).toBe("125 %");
    expect(zoom.get("option[value='custom']").attributes("disabled")).toBeDefined();
    await zoom.setValue("page-fit");
    expect(pdf.session.fit).toHaveBeenLastCalledWith("page-fit");
    expect(zoom.element.value).toBe("page-fit");
  });

  it("finds as the curator types, Enter goes to the next match and Shift+Enter to the previous one, with the count", async () => {
    const wrapper = await mountViewer();
    const pdf = await shown();
    const field = wrapper.get<HTMLInputElement>("input[aria-label='Find in the paper']");
    const count = wrapper.get(".paper-count");
    expect(count.attributes("role")).toBe("status");
    await field.setValue("the");
    expect(pdf.session.find).toHaveBeenLastCalledWith("the", { again: false, previous: false });
    pdf.events.found({ status: "pending", current: 0, total: 0 });
    await flushPromises();
    expect(count.text()).toBe("Finding…");
    pdf.events.found({ status: "found", current: 1, total: 3 });
    await flushPromises();
    expect(count.text()).toBe("1 of 3");
    await field.trigger("keydown", { key: "Enter" });
    expect(pdf.session.find).toHaveBeenLastCalledWith("the", { again: true, previous: false });
    await field.trigger("keydown", { key: "Enter", shiftKey: true });
    expect(pdf.session.find).toHaveBeenLastCalledWith("the", { again: true, previous: true });
    pdf.events.found({ status: "missing", current: 0, total: 0 });
    await flushPromises();
    expect(count.text()).toBe("No matches");
    await field.setValue("");
    expect(pdf.session.find).toHaveBeenLastCalledWith("", { again: false, previous: false });
    expect(count.text()).toBe("");
  });

  it("focuses the find field on Ctrl+F inside the viewer", async () => {
    const wrapper = await mountViewer();
    await shown();
    const pressed = new KeyboardEvent("keydown", { key: "f", ctrlKey: true, bubbles: true, cancelable: true });
    wrapper.get(".paper-scroll").element.dispatchEvent(pressed);
    expect(pressed.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(wrapper.get("input[aria-label='Find in the paper']").element);
  });

  it("shows a damaged PDF with the alert of a failed action and opens it again on Retry in the alert", async () => {
    engine.openPaper.mockRejectedValueOnce(
      Object.assign(new Error("Invalid PDF structure."), { name: "InvalidPDFException" }),
    );
    const fetch = vi.spyOn(globalThis, "fetch");
    const wrapper = await mountViewer();
    const alert = wrapper.get(".action-failure");
    expect(alert.text()).toContain("Example.pdf is damaged or not a PDF.");
    expect(alert.get(".action-failure-detail").text()).toBe("InvalidPDFException: Invalid PDF structure.");
    // The local server served the PDF: it is not asked again.
    expect(fetch).not.toHaveBeenCalled();
    expect(alert.findAll(".paper-retry button").map((button) => button.text())).toEqual(["Retry"]);
    await alert.get(".paper-retry button").trigger("click");
    await flushPromises();
    expect(engine.openPaper).toHaveBeenCalledTimes(2);
    expect(wrapper.find(".action-failure").exists()).toBe(false);
  });

  it("offers to reload the page when PDF.js could not be imported", async () => {
    engine.openPaper.mockRejectedValueOnce(
      new PaperImportFailed(new TypeError("Failed to fetch dynamically imported module")),
    );
    const wrapper = await mountViewer();
    const alert = wrapper.get(".action-failure");
    expect(alert.text()).toContain("The PDF viewer could not be loaded.");
    expect(alert.findAll(".paper-retry button").map((button) => button.text())).toEqual(["Retry", "Reload the page"]);
  });

  it.each([
    [
      404,
      { error: "Example.pdf is no longer in the study folder", code: "not_found", detail: null },
      "Example.pdf is no longer in the study folder.",
      `ResponseException: Unexpected server response (404) while retrieving PDF.`,
    ],
    [
      400,
      {
        error: "Could not read Example.pdf of caffeine/Example.",
        code: "file_error",
        detail: "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Example/Example.pdf'",
      },
      "Could not read Example.pdf: the local server answered 400.",
      "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Example/Example.pdf'",
    ],
  ])("explains an error status %d by the answer of the local server", async (status, body, text, detail) => {
    engine.openPaper.mockRejectedValueOnce(responseError(status));
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ ...body, action: `Read a file (GET ${URL_A})`, request_id: "0a1b2c3d" }), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
      );
    const wrapper = await mountViewer();
    expect(fetch).toHaveBeenCalledTimes(1);
    const alert = wrapper.get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe(text);
    expect(alert.get(".action-failure-detail").text()).toBe(detail);
    expect(alert.text()).toContain("0a1b2c3d");
  });

  it("opens a PDF that changed on disk again on its page and zoom, another PDF on page 1, and closes it when it unmounts", async () => {
    const wrapper = await mountViewer();
    const first = await shown(3);
    first.events.page(2);
    first.events.scale(1.5, "page-fit");
    await flushPromises();
    await wrapper.setProps({ bytes: 2000 });
    await flushPromises();
    expect(first.session.close).toHaveBeenCalledTimes(1);
    expect(opened).toHaveLength(2);
    expect(opened[1]!.start).toEqual({ page: 2, fit: "page-fit", scale: 1.5 });
    await wrapper.setProps({ url: URL_SUPP, file: "Example_Supp.pdf" });
    await flushPromises();
    expect(opened[1]!.session.close).toHaveBeenCalledTimes(1);
    expect(opened[2]!.start).toEqual({ page: 1, fit: "page-width", scale: 1 });
    wrapper.unmount();
    expect(opened[2]!.session.close).toHaveBeenCalledTimes(1);
  });

  it("gives its place to a parent that keeps it, and starts there again when it mounts again", async () => {
    const place = ref<PaperPlace | null>(null);
    const Host = defineComponent({
      props: { url: { type: String, required: true }, shown: { type: Boolean, required: true } },
      setup(props) {
        return () =>
          props.shown
            ? h(PaperViewer, {
                url: props.url,
                file: "Example.pdf",
                bytes: 1000,
                place: place.value,
                "onUpdate:place": (value: PaperPlace | null) => (place.value = value),
              })
            : null;
      },
    });
    const wrapper = mount(Host, { props: { url: URL_A, shown: true }, attachTo: document.body });
    await flushPromises();
    const first = await shown(3);
    expect(place.value).toEqual({ url: URL_A, page: 1, fit: "page-width", scale: 1 });
    first.events.page(3);
    first.events.scale(1.25, null);
    await flushPromises();
    expect(place.value).toEqual({ url: URL_A, page: 3, fit: null, scale: 1.25 });
    // The parent shows the viewer in another place of its layout: it mounts again.
    await wrapper.setProps({ shown: false });
    expect(first.session.close).toHaveBeenCalledTimes(1);
    await wrapper.setProps({ shown: true });
    await flushPromises();
    expect(opened[1]!.start).toEqual({ page: 3, fit: null, scale: 1.25 });
    // The place of one PDF is not the place of another.
    await wrapper.setProps({ shown: false });
    await wrapper.setProps({ url: URL_SUPP, shown: true });
    await flushPromises();
    expect(opened[2]!.start).toEqual({ page: 1, fit: "page-width", scale: 1 });
    expect(place.value).toEqual({ url: URL_SUPP, page: 1, fit: "page-width", scale: 1 });
  });
});
