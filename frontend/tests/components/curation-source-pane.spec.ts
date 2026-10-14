import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import type { Problem, SourceView } from "../../src/study-views/types";
import SourcePane from "../../src/curation-app/components/SourcePane.vue";
import type { AxisScales } from "../../src/curation-app/overlay";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { snapshot, sourceSummary, studyDetail } from "../unit/curation-fixtures";
import { serveApi } from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";

const view: SourceView = {
  source: "Tab2",
  image: "Example_Tab2.png",
  image_url: `${EXAMPLE}/files/Example_Tab2.png`,
  image_size: [640, 220],
  raw_grid: [
    ["", "Caffeine 150 mg", "Caffeine 300 mg"],
    ["CL [ml/min/kg]", "1.20 ± 0.3", "1.10 ± 0.2"],
  ],
  digitization: null,
  mapped: [],
  overlay: [],
  unmatched: [],
  layout: "side_by_side",
  log_x: false,
  log_y: false,
  points: [],
  series: [],
};

const summary = sourceSummary({
  source: "Tab2",
  image: "Example_Tab2.png",
  raw: "Example_Tab2.tsv",
  raw_kind: "table",
});

function mountPane(props: Record<string, unknown> = {}) {
  const pinia = createPinia();
  setActivePinia(pinia);
  return mount(SourcePane, {
    props: { summary, view, loading: false, error: null, selected: null, ...props },
    global: { plugins: [pinia] },
  });
}

beforeEach(() => localStorage.clear());

describe("source pane", () => {
  it("shows the image and the raw extraction of a paper table", () => {
    const wrapper = mountPane();
    expect(wrapper.get("section").attributes("aria-label")).toBe("Source Tab2");
    expect(wrapper.get("img").attributes("src")).toBe(`${EXAMPLE}/files/Example_Tab2.png`);
    expect(wrapper.get('[role="region"]').attributes("aria-label")).toBe("Raw extraction Example_Tab2.tsv");
    expect(wrapper.get(".pane-head").text()).toContain("Tab2");
  });

  it("names a missing image in one line", () => {
    const wrapper = mountPane({
      summary: sourceSummary({ source: "Tab2", raw: "Example_Tab2.tsv", missing_image: "Example_Tab2.png" }),
      view: { ...view, image: null, image_url: null },
    });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".pane-missing").text()).toContain("No image: add Example_Tab2.png");
  });

  it("names each missing file and what to do about it in one text beside its icon", () => {
    /** The text of each note, which wraps as one paragraph in a narrow pane. */
    const notes = (wrapper: ReturnType<typeof mountPane>) =>
      wrapper.findAll(".pane-missing").map((note) => {
        expect(note.element.children).toHaveLength(2);
        return note.get(".pane-missing-text").text();
      });
    const table = mountPane({
      summary: sourceSummary({ source: "Tab3", missing_image: "Example_Tab3.png", missing_raw: "Example_Tab3.tsv" }),
      view: { ...view, source: "Tab3", image: null, image_url: null, raw_grid: null },
    });
    expect(notes(table)).toEqual([
      "No image: add Example_Tab3.png. Save it from the paper as a PNG image.",
      "No raw extraction: add Example_Tab3.tsv with Add table.",
    ]);
    const figure = mountPane({
      summary: sourceSummary({
        source: "Fig1",
        kind: "figure",
        image: "Example_Fig1.png",
        missing_raw: "Example_Fig1.wpd.json",
      }),
      view: { ...view, source: "Fig1", raw_grid: null },
    });
    expect(notes(figure)).toEqual([
      "No digitization: add Example_Fig1.wpd.json. Digitize it in WebPlotDigitizer and import it with pkdb digitize import.",
    ]);
  });

  it("toggles the zoom, which survives a storage that throws", async () => {
    const wrapper = mountPane();
    const [fit, full] = wrapper.findAll(".zoom button");
    expect(fit!.attributes("aria-pressed")).toBe("true");
    await full!.trigger("click");
    expect(full!.attributes("aria-pressed")).toBe("true");
    expect(fit!.attributes("aria-pressed")).toBe("false");
    expect(wrapper.get("img").classes()).toContain("source-image--full");
    expect(localStorage.getItem("pkdb-curation:source-zoom")).toBe("full");
    expect(mountPane().findAll(".zoom button")[1]!.attributes("aria-pressed")).toBe("true");

    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const blocked = mountPane();
    const buttons = blocked.findAll(".zoom button");
    expect(buttons[0]!.attributes("aria-pressed")).toBe("true");
    await buttons[1]!.trigger("click");
    expect(buttons[1]!.attributes("aria-pressed")).toBe("true");
    vi.restoreAllMocks();
  });
});

describe("problems of the source", () => {
  /** A problem of the raw extraction of a paper table. */
  const problem = (file: string): Problem => ({
    code: "raw_row_empty",
    severity: "warning",
    message: `${file} has an empty row.`,
    source: { file, row: 2 },
    acknowledgeable: false,
  });

  it("opens them again for the next source after the curator closed them", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    serveApi({
      "GET /local/state": snapshot(),
      [`GET ${EXAMPLE}`]: studyDetail({ problems: [problem("Example_Tab2.tsv"), problem("Example_Tab3.tsv")] }),
    });
    const study = useStudyStore();
    await study.open("caffeine", "Example");
    const tab3 = sourceSummary({ source: "Tab3", image: "Example_Tab3.png", raw: "Example_Tab3.tsv", raw_kind: "table" });
    const wrapper = mount(SourcePane, {
      props: { summary, view, loading: false, error: null, selected: null },
      global: { plugins: [pinia] },
    });
    const details = () => wrapper.get<HTMLDetailsElement>("details.source-problems").element;
    expect(wrapper.get(".source-problems").text()).toContain("Example_Tab2.tsv has an empty row.");
    expect(details().open).toBe(true);
    details().open = false;
    await wrapper.setProps({ summary: tab3, view: { ...view, source: "Tab3", image: "Example_Tab3.png" } });
    await flushPromises();
    expect(wrapper.get(".source-problems").text()).toContain("Example_Tab3.tsv has an empty row.");
    expect(details().open).toBe(true);
    study.close();
  });

  it("gives the plot of a figure the problems of the files of its source", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const mismatch: Problem = {
      code: "digitized_mismatch",
      severity: "warning",
      message: "mean 1.2 lies 12 pixels from its point.",
      source: { file: "timecourses_Fig1.tsv", row: 3, header: "mean" },
      acknowledgeable: true,
    };
    serveApi({ "GET /local/state": snapshot(), [`GET ${EXAMPLE}`]: studyDetail({ problems: [mismatch] }) });
    const study = useStudyStore();
    await study.open("caffeine", "Example");
    const figure: SourceView = {
      ...view,
      source: "Fig1",
      image: "Example_Fig1.png",
      image_url: `${EXAMPLE}/files/Example_Fig1.png`,
      raw_grid: null,
      mapped: [
        { file: "timecourses_Fig1.tsv", kind: "timecourses", header: ["label", "time", "mean"], rows: [[3, ["D75", "0.5", "1.2"]]], shared: false },
      ],
      points: [
        { series: "D75", kind: "timecourses", file: "timecourses_Fig1.tsv", line: 3, x: 0.5, y: 1.2, error_low: null, error_high: null, x_text: "0.5", y_text: "1.2" },
      ],
      series: [{ name: "D75", color: "#d65a24", dark_color: "#d95926", x_label: "time (h)", y_label: "c (mg/l)" }],
    };
    const wrapper = mount(SourcePane, {
      props: { summary: sourceSummary({ source: "Fig1", kind: "figure", image: "Example_Fig1.png" }), view: figure, loading: false, error: null, selected: null },
      global: { plugins: [pinia], stubs: { SourceOverlay: true } },
    });
    expect(wrapper.findComponent({ name: "SourceOverlay" }).props("problems")).toEqual([mismatch]);
    study.close();
  });
});

describe("scrolling", () => {
  /** Gives the body of the pane a view of 300 px over `content` px scrolled to `top`, as a layout would. */
  function layout(wrapper: ReturnType<typeof mountPane>, content: number, top = 0): HTMLElement {
    const body = wrapper.get(".pane-body").element as HTMLElement;
    Object.defineProperty(body, "clientHeight", { configurable: true, value: 300 });
    Object.defineProperty(body, "scrollHeight", { configurable: true, value: content });
    Object.defineProperty(body, "scrollTop", { configurable: true, writable: true, value: top });
    return body;
  }

  it("fades out at the bottom while more of the pane follows below, and not at its end", async () => {
    const wrapper = mountPane();
    const body = layout(wrapper, 900);
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.get(".pane-more").attributes("aria-hidden")).toBe("true");
    body.scrollTop = 600;
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.find(".pane-more").exists()).toBe(false);
  });

  it("does not fade out a pane that fits", async () => {
    const wrapper = mountPane();
    layout(wrapper, 300);
    await wrapper.get(".pane-body").trigger("scroll");
    expect(wrapper.find(".pane-more").exists()).toBe(false);
  });

  it("keeps the content in one column inside the body that scrolls and takes the focus", () => {
    const wrapper = mountPane();
    expect(wrapper.get(".pane-body").attributes("tabindex")).toBe("0");
    expect(wrapper.find(".pane-body > .pane-content").exists()).toBe(true);
  });
});

describe("scales of the plot", () => {
  /** The plot is drawn by Plotly; the pane passes it the view, the mode and the scales. */
  const OverlayStub = defineComponent({
    name: "SourceOverlay",
    props: {
      view: { type: Object as PropType<SourceView>, required: true },
      mode: { type: String, default: undefined },
      selected: { type: Object, default: null },
      scales: { type: Object as PropType<AxisScales>, default: undefined },
    },
    setup(props) {
      return () =>
        h("div", {
          class: "overlay-stub",
          "data-mode": props.mode,
          "data-scales": props.scales ? `${props.scales.x} ${props.scales.y}` : "",
        });
    },
  });

  const point = (line: number, x: number, y: number) => ({
    series: "drug_plasma",
    kind: "timecourses" as const,
    file: "timecourses_Fig2.tsv",
    line,
    x,
    y,
    error_low: null,
    error_high: null,
    x_text: String(x),
    y_text: String(y),
  });

  /** Fig2 beside its image, with a predose point at (0, 0) and a point at x 0. */
  const plotView: SourceView = {
    ...view,
    source: "Fig2",
    image: "Example_Fig2.png",
    image_url: `${EXAMPLE}/files/Example_Fig2.png`,
    raw_grid: null,
    points: [point(1, 0, 0), point(2, 0, 3), point(3, 1, 5), point(4, 2, 2.5)],
    series: [{ name: "drug_plasma", color: "#1a2b3c", dark_color: "#4d5e6f", x_label: "time (h)", y_label: "c (mg/l)" }],
  };
  const figure = sourceSummary({ source: "Fig2", kind: "figure", image: "Example_Fig2.png" });

  /** The pane of `shown` with the plot scales `saved` of the local server, which answers every save. */
  async function mountPlot(shown: SourceView = plotView, saved: Record<string, AxisScales> = {}) {
    const pinia = createPinia();
    setActivePinia(pinia);
    const requests = serveApi({
      "GET /local/state": snapshot({ plot_scales: saved }),
      "POST /local/settings": snapshot({ plot_scales: saved }),
      [`GET ${EXAMPLE}`]: studyDetail(),
    });
    await useOverviewStore().refresh();
    const study = useStudyStore();
    await study.open("caffeine", "Example");
    const wrapper = mount(SourcePane, {
      props: { summary: figure, view: shown, loading: false, error: null, selected: null },
      global: { plugins: [pinia], stubs: { SourceOverlay: OverlayStub } },
    });
    await flushPromises();
    return { wrapper, study, requests };
  }

  type Wrapper = Awaited<ReturnType<typeof mountPlot>>["wrapper"];

  const group = (wrapper: Wrapper, axis: "x" | "y") =>
    wrapper.get(`[role="group"][aria-label="Scale of the ${axis} axis"]`);
  const pressed = (wrapper: Wrapper, axis: "x" | "y") =>
    group(wrapper, axis)
      .findAll("button")
      .filter((button) => button.attributes("aria-pressed") === "true")
      .map((button) => button.text());
  const note = (wrapper: Wrapper) => wrapper.get(".plot-scales-note").text();

  it("shows lin and log for x and y above the plot, linear without a digitization", async () => {
    const { wrapper, study } = await mountPlot();
    expect(group(wrapper, "x").findAll("button").map((button) => button.text())).toEqual(["lin", "log"]);
    expect([pressed(wrapper, "x"), pressed(wrapper, "y")]).toEqual([["lin"], ["lin"]]);
    expect(wrapper.get(".overlay-stub").attributes("data-scales")).toBe("linear linear");
    // The switches come before the plot.
    const html = wrapper.html();
    expect(html.indexOf("Scale of the x axis")).toBeLessThan(html.indexOf("overlay-stub"));
    expect(note(wrapper)).toBe("");
    expect(wrapper.get(".plot-scales-note").attributes("aria-live")).toBe("polite");
    study.close();
  });

  it("draws the switches as the zoom of the image: native buttons joined in a named group", async () => {
    const { wrapper, study, requests } = await mountPlot();
    const zoom = wrapper.get('[role="group"][aria-label="Image size"]');
    for (const control of [zoom, group(wrapper, "x"), group(wrapper, "y")]) {
      expect(control.classes()).toContain("switch-group");
      expect(control.findAll("button").map((button) => button.attributes("type"))).toEqual(["button", "button"]);
      expect(control.find(".v-btn").exists()).toBe(false);
    }
    // A click on the pressed button changes and saves nothing.
    await group(wrapper, "y").findAll("button")[0]!.trigger("click");
    await flushPromises();
    expect(pressed(wrapper, "y")).toEqual(["lin"]);
    expect(requests.filter((request) => request.method === "POST")).toEqual([]);
    study.close();
  });

  it("takes the scales of the digitization and says how many points the log axis leaves out", async () => {
    const { wrapper, study } = await mountPlot({ ...plotView, log_y: true });
    expect(pressed(wrapper, "y")).toEqual(["log"]);
    expect(wrapper.get(".overlay-stub").attributes("data-scales")).toBe("linear log");
    expect(note(wrapper)).toBe("1 point at 0 or below is not shown on the log axis");
    study.close();
  });

  it("saves the choice of the curator for the figure of the study, which wins over the digitization", async () => {
    const { wrapper, study, requests } = await mountPlot();
    await group(wrapper, "x").findAll("button")[1]!.trigger("click");
    expect(pressed(wrapper, "x")).toEqual(["log"]);
    expect(note(wrapper)).toBe("2 points at 0 or below are not shown on the log axis");
    await group(wrapper, "y").findAll("button")[1]!.trigger("click");
    expect(wrapper.get(".overlay-stub").attributes("data-scales")).toBe("log log");
    expect(note(wrapper)).toBe("2 points at 0 or below are not shown on the log axes");
    await flushPromises();
    expect(
      requests.filter((request) => request.method === "POST" && request.path === "/local/settings").map((request) => request.body),
    ).toEqual([
      { plot_scale: { figure: "caffeine/Example/Fig2", x: "log", y: "linear" } },
      { plot_scale: { figure: "caffeine/Example/Fig2", x: "log", y: "log" } },
    ]);
    study.close();
    // The next page reads the scales that the local server kept.
    const again = await mountPlot(plotView, { "caffeine/Example/Fig2": { x: "log", y: "log" } });
    expect(again.wrapper.get(".overlay-stub").attributes("data-scales")).toBe("log log");
    again.study.close();
  });

  it("follows the figure when the pane shows another source", async () => {
    const { wrapper, study } = await mountPlot();
    await group(wrapper, "y").findAll("button")[1]!.trigger("click");
    await flushPromises();
    await wrapper.setProps({ summary: sourceSummary({ source: "Fig3", kind: "figure" }), view: { ...plotView, source: "Fig3" } });
    expect(wrapper.get(".overlay-stub").attributes("data-scales")).toBe("linear linear");
    expect(note(wrapper)).toBe("");
    study.close();
  });

  it("shows the switches above the plot of the series without a dataset, and not on the overlay or a table", async () => {
    const calibrated: SourceView = {
      ...plotView,
      digitization: "Example_Fig2.wpd.json",
      layout: "overlay",
      image_size: [640, 220],
      unmatched: ["drug_plasma"],
    };
    const { wrapper, study } = await mountPlot(calibrated);
    expect(wrapper.findAll('[role="group"][aria-label^="Scale of the"]')).toHaveLength(2);
    expect(wrapper.findAll(".overlay-stub").map((stub) => stub.attributes("data-scales"))).toEqual(["", "linear linear"]);
    await wrapper.setProps({ view: { ...calibrated, unmatched: [] } });
    expect(wrapper.find('[role="group"][aria-label^="Scale of the"]').exists()).toBe(false);
    await wrapper.setProps({ summary, view });
    expect(wrapper.find('[role="group"][aria-label^="Scale of the"]').exists()).toBe(false);
    study.close();
  });

  it("says that a figure without rows with a time or scatter rows has nothing to plot", () => {
    const wrapper = mountPane({
      summary: sourceSummary({ source: "Fig3", kind: "figure", image: "Example_Fig3.png" }),
      view: { ...view, source: "Fig3", image: "Example_Fig3.png", image_url: `${EXAMPLE}/files/Example_Fig3.png`, raw_grid: null },
    });
    expect(wrapper.text()).toContain("No rows with a time or scatter rows to plot.");
    expect(wrapper.find(".plot-scales").exists()).toBe(false);
  });
});
