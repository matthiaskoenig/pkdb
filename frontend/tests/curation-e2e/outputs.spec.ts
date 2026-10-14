import { copyFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

const DRAFT = "caffeine/Draft2021";
const TABLE = "outputs_Fig2.tsv";
const IMAGE = "Draft2021_Fig2.png";
const FIG2 = `#/studies/${DRAFT}/data?source=Fig2&file=${TABLE}`;
const PLASMA = "all · D150 · concentration · caffeine · plasma";
const URINE = "all · D150 · concentration · caffeine · urine";

/** The columns of an outputs table, as outputs_Tab1.tsv of Draft2021 has them. */
const HEADER = [
  "study", "source", "subjects", "interventions", "measurement", "calculation", "substance", "tissue", "method", "choice",
  "time", "time_unit", "count", "mean", "sd", "se", "cv", "gmean", "gsd", "gcv", "median", "min", "max", "unit",
  "error_bar", "error_type", "comment",
];

/** A row of caffeine after D150 in Fig2 of Draft2021. */
function row(measurement: string, tissue: string, time: string, mean: string, unit = "mg/l", sd = ""): string {
  const cells: Record<string, string> = {
    study: "Draft2021",
    source: "Fig2",
    subjects: "all",
    interventions: "D150",
    measurement,
    substance: "caffeine",
    tissue,
    time,
    time_unit: time ? "hr" : "",
    mean,
    sd,
    unit,
  };
  return HEADER.map((name) => cells[name] ?? "").join("\t");
}

/**
 * Fig2 as a time profile of a paper has it, curated as outputs, with the rows deliberately out of time
 * order: an AUC without a time (line 1), the plasma series (lines 2 to 5, the point at 2 h with an sd)
 * and the urine series (6 and 7).
 */
const ROWS = [
  row("auc_inf", "plasma", "", "17", "mg/l*hr"),
  row("concentration", "plasma", "1", "3"),
  row("concentration", "plasma", "0.5", "2.1"),
  row("concentration", "plasma", "2", "2.4", "mg/l", "0.3"),
  row("concentration", "plasma", "4", "1.2"),
  row("concentration", "urine", "2", "12"),
  row("concentration", "urine", "4", "20"),
];

/** Add Fig2 with its outputs and an image to Draft2021, which has no workbook; the function removes them again. */
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

/** The point of the page at which the plot draws the value (x, y). */
async function pixelOf(plot: Locator, x: number, y: number): Promise<{ x: number; y: number }> {
  const box = await plot.boundingBox();
  if (!box) throw new Error("The plot has no box");
  const at = await plot.evaluate(
    (element, [x, y]) => {
      type Axis = { _offset: number; l2p(value: number): number };
      const { xaxis, yaxis } = (element as HTMLElement & { _fullLayout: { xaxis: Axis; yaxis: Axis } })._fullLayout;
      return { x: xaxis._offset + xaxis.l2p(x), y: yaxis._offset + yaxis.l2p(y) };
    },
    [x, y] as const,
  );
  return { x: box.x + at.x, y: box.y + at.y };
}

test("the plot of a figure draws its outputs with a time as series by time, and a click selects the row", async ({
  app,
  page,
}, testInfo) => {
  const remove = addFigure(app.server.workspace);
  try {
    await app.open(FIG2);
    const pane = page.getByRole("region", { name: "Source Fig2" });
    const plot = pane.getByRole("img", { name: new RegExp(`^Plot of 6 mapped rows of Fig2 of the series "${PLASMA}", "${URINE}"`) });
    await expect(plot).toBeVisible();
    await expect(pane.getByRole("list", { name: "Series" })).toContainText(PLASMA);
    await expect
      .poll(() =>
        plot.evaluate((element) =>
          ((element as HTMLElement & { data?: { meta?: string; mode?: string; x?: number[] }[] }).data ?? [])
            .filter((trace) => trace.meta?.startsWith("plot "))
            .map((trace) => [trace.meta, trace.mode, trace.x]),
        ),
      )
      .toEqual([
        [`plot ${PLASMA}`, "lines+markers", [0.5, 1, 2, 4]],
        [`plot ${URINE}`, "lines+markers", [2, 4]],
      ]);

    // The point at 2 h has an sd, which is its error bar; the points of the series are in time order.
    await expect
      .poll(() => drawnBars(plot))
      .toEqual({ [PLASMA]: [null, null, [2.1, 2.7], null], [URINE]: [null, null] });

    // The point of line 4, plasma at 2 h, names its row on hover and selects it on a click.
    const point = await pixelOf(plot, 2, 2.4);
    await page.mouse.move(point.x, point.y);
    await expect(page.getByText(`${TABLE} line 4`)).toBeVisible();
    await page.mouse.click(point.x, point.y);
    const grid = page.getByRole("region", { name: `Rows of ${TABLE}` });
    await expect(grid.getByRole("rowheader", { name: "4", exact: true })).toBeFocused();

    for (const width of [1280, 1440]) {
      await page.setViewportSize({ width, height: 1150 });
      for (const theme of ["light", "dark"] as const) {
        await page.emulateMedia({ colorScheme: theme });
        await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
        await expectAccessible(page);
        const name = `outputs-${width}-${theme}.png`;
        const shot = await pane.screenshot({ path: testInfo.outputPath(name) });
        await testInfo.attach(name, { body: shot, contentType: "image/png" });
      }
    }
  } finally {
    remove();
  }
});
