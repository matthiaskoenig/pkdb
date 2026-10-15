import { beforeEach, describe, expect, it } from "vitest";
import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { ref } from "vue";
import type { SourceView } from "../../src/study-views/types";
import { usePlotScales } from "../../src/curation-app/composables/usePlotScales";
import { plotFigure } from "../../src/study-views/plotScales";
import type { AxisScales } from "../../src/study-views/overlay";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, snapshot } from "../unit/curation-fixtures";
import { serveApi } from "./curation-dom";

const STUDY = "caffeine/Example";
const FIG1 = "caffeine/Example/Fig1";

function view(source: string, changes: Partial<SourceView> = {}): SourceView {
  return {
    source,
    image: null,
    image_url: null,
    image_size: null,
    raw_grid: null,
    digitization: null,
    mapped: [],
    overlay: [],
    unmatched: [],
    layout: "side_by_side",
    points: [],
    series: [],
    log_x: false,
    log_y: false,
    ...changes,
  };
}

/** The local server with the plot scales `saved`; a POST of a plot scale keeps it, or fails with `status`. */
async function serve(saved: Record<string, AxisScales> = {}, status = 200) {
  const kept = { ...saved };
  const requests = serveApi({
    "GET /local/state": () => json(snapshot({ plot_scales: { ...kept } })),
    "POST /local/settings": (body: Record<string, unknown> | null) => {
      if (status !== 200) return json({ error: "Could not save the settings.", code: "file_error" }, { status });
      const { figure, x, y } = body?.plot_scale as { figure: string } & AxisScales;
      kept[figure] = { x, y };
      return json(snapshot({ plot_scales: { ...kept } }));
    },
  });
  await useOverviewStore().refresh();
  return requests;
}

const posted = (requests: Awaited<ReturnType<typeof serve>>) =>
  requests.filter((request) => request.method === "POST" && request.path === "/local/settings").map((request) => request.body);

beforeEach(() => setActivePinia(createPinia()));

describe("usePlotScales", () => {
  it("names the figure by its study and source", () => {
    expect(plotFigure(STUDY, "Fig1")).toBe(FIG1);
  });

  it("takes the scales of the digitization without a saved choice, else linear", async () => {
    await serve();
    const shown = ref(view("Fig1"));
    const { scales } = usePlotScales(STUDY, shown);
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
    shown.value = view("Fig1", { log_y: true });
    expect(scales.value).toEqual({ x: "linear", y: "log" });
  });

  it("takes the saved scales of the figure over the digitization", async () => {
    await serve({ [FIG1]: { x: "log", y: "linear" } });
    const shown = ref(view("Fig1", { log_y: true }));
    const study = ref(STUDY);
    const { scales } = usePlotScales(study, shown);
    expect(scales.value).toEqual({ x: "log", y: "linear" });
    // Another figure and the same figure of another study have their own scales.
    shown.value = view("Fig2", { log_y: true });
    expect(scales.value).toEqual({ x: "linear", y: "log" });
    shown.value = view("Fig1");
    study.value = "caffeine/Other";
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
  });

  it("saves both scales of the figure that the curator changed", async () => {
    const requests = await serve();
    const shown = ref(view("Fig1", { log_y: true }));
    const { scales, choose } = usePlotScales(STUDY, shown);
    choose("x", "log");
    expect(scales.value).toEqual({ x: "log", y: "log" });
    await flushPromises();
    expect(posted(requests)).toEqual([{ plot_scale: { figure: FIG1, x: "log", y: "log" } }]);
    expect(useOverviewStore().snapshot?.plot_scales).toEqual({ [FIG1]: { x: "log", y: "log" } });
    // The next page reads the choice of the local server, whatever the digitization says.
    expect(usePlotScales(STUDY, view("Fig1")).scales.value).toEqual({ x: "log", y: "log" });
    shown.value = view("Fig2");
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
  });

  it("posts two quick choices in order: the second after the answer to the first", async () => {
    const events: string[] = [];
    let answerFirst = () => {};
    let kept: Record<string, AxisScales> = {};
    serveApi({
      "GET /local/state": () => json(snapshot({ plot_scales: kept })),
      // The local server keeps a choice when it answers; it holds back the answer to the first.
      "POST /local/settings": (body: Record<string, unknown> | null) => {
        const { figure, x, y } = body?.plot_scale as { figure: string } & AxisScales;
        events.push(`sent ${x} ${y}`);
        const answer = () => {
          kept = { [figure]: { x, y } };
          return json(snapshot({ plot_scales: kept }));
        };
        if (events.length > 1) return answer();
        return new Promise<Response>((resolve) => {
          answerFirst = () => {
            events.push("answered");
            resolve(answer());
          };
        });
      },
    });
    await useOverviewStore().refresh();
    const { scales, choose } = usePlotScales(STUDY, view("Fig1"));
    choose("x", "log");
    choose("y", "log");
    await flushPromises();
    // Both apply at once; the second save waits for the first.
    expect(scales.value).toEqual({ x: "log", y: "log" });
    expect(events).toEqual(["sent log linear"]);
    answerFirst();
    await flushPromises();
    expect(events).toEqual(["sent log linear", "answered", "sent log log"]);
    // The last answer of the local server has the last choice.
    expect(useOverviewStore().snapshot?.plot_scales).toEqual({ [FIG1]: { x: "log", y: "log" } });
  });

  it("posts the next choice after a save that failed", async () => {
    const requests = await serve({}, 500);
    const { choose } = usePlotScales(STUDY, view("Fig1"));
    choose("x", "log");
    choose("y", "log");
    await flushPromises();
    expect(posted(requests)).toEqual([
      { plot_scale: { figure: FIG1, x: "log", y: "linear" } },
      { plot_scale: { figure: FIG1, x: "log", y: "log" } },
    ]);
  });

  it("keeps the choice for the page when the local server cannot keep it", async () => {
    await serve({}, 500);
    const { scales, choose } = usePlotScales(STUDY, view("Fig1"));
    choose("y", "log");
    await flushPromises();
    expect(scales.value).toEqual({ x: "linear", y: "log" });
  });

  it("chooses nothing before the study and the view are known", async () => {
    const requests = await serve();
    const { scales, choose } = usePlotScales("", null);
    choose("y", "log");
    await flushPromises();
    expect(scales.value).toEqual({ x: "linear", y: "linear" });
    expect(posted(requests)).toEqual([]);
  });
});
