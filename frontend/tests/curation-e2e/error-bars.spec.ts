import { copyFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

const DRAFT = "caffeine/Draft2021";
const TABLE = "timecourses_Fig2.tsv";
const IMAGE = "Draft2021_Fig2.png";
const FIG2 = `#/studies/${DRAFT}/data?source=Fig2&file=${TABLE}`;
const FIG1 = "#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv";

/** The columns of a timecourse table, as timecourses_Fig1.tsv of Demo2020 has them. */
const HEADER = [
  "study", "source", "label", "subjects", "interventions", "measurement", "calculation", "substance", "tissue", "method",
  "choice", "time", "time_unit", "count", "mean", "sd", "se", "cv", "gmean", "gsd", "gcv", "median", "min", "max", "unit",
  "error_bar", "error_type", "comment",
];

/** A row of caffeine in plasma after D150 in Fig2 of Draft2021. */
function row(label: string, time: string, statistics: Record<string, string>): string {
  const cells: Record<string, string> = {
    study: "Draft2021",
    source: "Fig2",
    label,
    subjects: "all",
    interventions: "D150",
    measurement: "concentration",
    substance: "caffeine",
    tissue: "plasma",
    time,
    time_unit: "hr",
    unit: "mg/l",
    ...statistics,
  };
  return HEADER.map((name) => cells[name] ?? "").join("\t");
}

/**
 * Fig2 as a converted study without a digitization has it, in the order of pkdb format: a
 * digitized error bar of type sd, a gmean with its gsd, sd and se, and an sd at 2 h that reaches
 * below 0.
 */
const ROWS = [
  row("bar_series", "0.5", { mean: "1", error_bar: "1.4", error_type: "sd" }),
  row("gsd_series", "0.5", { gmean: "4", gsd: "2" }),
  row("gsd_series", "1", { gmean: "6", gsd: "1.5" }),
  row("sd_series", "0.5", { mean: "2", sd: "0.5" }),
  row("sd_series", "1", { mean: "3", sd: "0.6" }),
  row("sd_series", "2", { mean: "1", sd: "1.5" }),
  row("se_series", "0.5", { mean: "1.5", se: "0.2" }),
  row("se_series", "1", { mean: "2.5", se: "0.3" }),
];

/** Add Fig2 with its table and an image to Draft2021, which has no workbook; the function removes them again. */
function addFigure(workspace: string): () => void {
  const folder = join(workspace, DRAFT);
  writeFileSync(join(folder, TABLE), `${[HEADER.join("\t"), ...ROWS].join("\n")}\n`);
  copyFileSync(join(workspace, "caffeine/Demo2020/Demo2020_Fig1.png"), join(folder, IMAGE));
  return () => {
    rmSync(join(folder, TABLE), { force: true });
    rmSync(join(folder, IMAGE), { force: true });
  };
}

/** The ends of the error bars that Plotly computed, by series: [low, high] of each point, null without a bar. */
async function drawnBars(plot: Locator): Promise<Record<string, ([number, number] | null)[]>> {
  return plot.evaluate((element) => {
    const host = element as HTMLElement & { data?: { meta?: string }[]; calcdata?: { ys?: number; yh?: number }[][] };
    const round = (value: number) => Number(value.toPrecision(6));
    const bars: Record<string, ([number, number] | null)[]> = {};
    host.calcdata?.forEach((points, index) => {
      const meta = host.data?.[index]?.meta ?? "";
      if (!meta.startsWith("plot ")) return;
      bars[meta.slice("plot ".length)] = points.map((point) =>
        point.ys === undefined || point.yh === undefined ? null : [round(point.ys), round(point.yh)],
      );
    });
    return bars;
  });
}

/** The caps of each error bar that Plotly drew: 2, or 1 where a log axis cut the bar at its bottom. */
async function caps(plot: Locator): Promise<number[]> {
  return plot.locator("path.yerror").evaluateAll((paths) => paths.map((path) => (path.getAttribute("d")?.match(/h/g) ?? []).length));
}

/** The range of the y axis that Plotly chose, in powers of 10 on a log axis. */
async function yRange(plot: Locator): Promise<[number, number]> {
  return plot.evaluate(
    (element) => (element as HTMLElement & { _fullLayout: { yaxis: { range: [number, number] } } })._fullLayout.yaxis.range,
  );
}

test("the overlay of Fig1 draws the error bar of each mapped row from its low to its high end", async ({ app, page }) => {
  await app.open(FIG1);
  const figure = page.getByRole("img", { name: /^Figure Fig1 with/ });
  await expect(figure).toBeVisible();
  const view = (await page.evaluate(async () => (await fetch("/local/studies/caffeine/Demo2020/sources/Fig1")).json())) as {
    overlay: { series: string; role: string; py: number; error_low_px: [number, number] | null; error_high_px: [number, number] | null }[];
  };
  const rows = view.overlay.filter((point) => point.role === "mapped" && point.series === "caf_plasma_100mg");
  expect(rows).toHaveLength(9);
  // The digitized error bar ends of Fig1 are of type sd: each bar reaches as far below its cross as above it.
  for (const point of rows) expect(point.error_low_px![1] - point.py).toBeCloseTo(point.py - point.error_high_px![1], 2);
  await expect
    .poll(() =>
      figure.evaluate(
        (element) =>
          (element as HTMLElement & { data?: { meta?: string; y?: unknown[] }[] }).data?.find(
            (trace) => trace.meta === "error caf_plasma_100mg",
          )?.y,
      ),
    )
    .toEqual(rows.flatMap((point) => [point.error_low_px![1], point.error_high_px![1], null]));
});

test("the plot of a figure without a digitization draws the error bars of sd, se, gsd and a digitized error bar", async ({
  app,
  page,
}, testInfo) => {
  const remove = addFigure(app.server.workspace);
  try {
    await app.open(FIG2);
    const pane = page.getByRole("region", { name: "Source Fig2" });
    const plot = pane.getByRole("img", { name: /^Plot of 8 mapped rows of Fig2/ });
    await expect(plot).toBeVisible();
    await expect
      .poll(() => drawnBars(plot))
      .toEqual({
        bar_series: [[0.6, 1.4]],
        gsd_series: [
          [2, 8],
          [4, 9],
        ],
        sd_series: [
          [1.5, 2.5],
          [2.4, 3.6],
          [-0.5, 2.5],
        ],
        se_series: [
          [1.3, 1.7],
          [2.2, 2.8],
        ],
      });
    // The linear axis reaches down to the end of the bar below 0.
    expect((await yRange(plot))[0]).toBeLessThan(-0.5);

    await pane.getByRole("group", { name: "Scale of the y axis" }).getByRole("button", { name: "log" }).click();
    // Every value is above 0: the log axis keeps all points and cuts the bar of sd_series at 2 h,
    // which reaches -0.5, at its bottom, without the cap there.
    await expect(pane.locator(".plot-scales-note")).toHaveText("");
    await expect.poll(async () => (await caps(plot)).filter((count) => count === 1)).toHaveLength(1);
    expect(await caps(plot)).toHaveLength(8);
    expect(await plot.locator("path.yerror").evaluateAll((paths) => paths.every((path) => !path.getAttribute("d")?.includes("NaN")))).toBe(
      true,
    );
    // The log axis spans the ends of the bars above 0, up to the 9 of gsd_series.
    expect(10 ** (await yRange(plot))[1]).toBeGreaterThanOrEqual(9);

    for (const width of [1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      for (const theme of ["light", "dark"] as const) {
        await page.emulateMedia({ colorScheme: theme });
        await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
        await expectAccessible(page);
        const name = `error-bars-${width}-${theme}.png`;
        const shot = await pane.screenshot({ path: testInfo.outputPath(name) });
        await testInfo.attach(name, { body: shot, contentType: "image/png" });
      }
    }
  } finally {
    remove();
  }
});
