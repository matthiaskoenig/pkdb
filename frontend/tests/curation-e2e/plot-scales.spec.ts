import { renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

const PROJECT = "caffeine/Demo2020/Demo2020_Fig1.wpd.json";
const FIG1 = "#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv";

/** The types of the axes of the plot of mapped rows, as Plotly drew them. */
async function axisTypes(page: Page): Promise<string[]> {
  return page.locator(".overlay-frame--plot .overlay-host").evaluate((element) => {
    const layout = (element as HTMLElement & { _fullLayout?: { xaxis: { type: string }; yaxis: { type: string } } })
      ._fullLayout;
    return layout ? [layout.xaxis.type, layout.yaxis.type] : [];
  });
}

/** The labels of the ticks of an axis of a plot, with their boxes on the page. */
async function tickLabels(plot: Locator, axis: "x" | "y") {
  return plot.locator(`.${axis}tick text`).evaluateAll((elements) =>
    elements.map((element) => {
      const { left, right, top, bottom } = element.getBoundingClientRect();
      return { text: element.textContent ?? "", left, right, top, bottom };
    }),
  );
}

type Label = Awaited<ReturnType<typeof tickLabels>>[number];

/** The pairs of labels whose boxes overlap. */
function overlapping(labels: Label[]): [string, string][] {
  return labels.flatMap((a, index) =>
    labels
      .slice(index + 1)
      .filter((b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom)
      .map((b): [string, string] => [a.text, b.text]),
  );
}

/**
 * The contrast (WCAG 2) of the fill of the pressed button of a group against the fill of the other
 * button, which shows through to the first opaque background below it.
 */
async function pressedContrast(group: Locator): Promise<number> {
  return group.evaluate((element) => {
    const fill = (node: Element): number[] => {
      for (let current: Element | null = node; current; current = current.parentElement) {
        const [r = 0, g = 0, b = 0, alpha = 1] = (getComputedStyle(current).backgroundColor.match(/[\d.]+/g) ?? []).map(Number);
        if (alpha === 1) return [r, g, b];
      }
      return [255, 255, 255];
    };
    const luminance = (rgb: number[]) => {
      const [r = 0, g = 0, b = 0] = rgb.map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const [pressed, other] = ["true", "false"].map((state) =>
      luminance(fill(element.querySelector(`button[aria-pressed="${state}"]`)!)),
    ) as [number, number];
    return (Math.max(pressed, other) + 0.05) / (Math.min(pressed, other) + 0.05);
  });
}

test("a log y axis of the plot of mapped rows is kept for the figure and reads well in both themes", async ({
  app,
  page,
}, testInfo) => {
  // Without its WebPlotDigitizer project, Fig1 shows its image beside a plot of its 18 mapped rows.
  const project = join(app.server.workspace, PROJECT);
  renameSync(project, `${project}.away`);
  try {
    await app.open(FIG1);
    const pane = page.getByRole("region", { name: "Source Fig1" });
    const plot = pane.getByRole("img", { name: /^Plot of 18 mapped rows of Fig1/ });
    await expect(plot).toBeVisible();
    const y = pane.getByRole("group", { name: "Scale of the y axis" });
    await expect(y.getByRole("button", { name: "lin" })).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => axisTypes(page)).toEqual(["linear", "linear"]);

    await y.getByRole("button", { name: "log" }).click();
    await expect(y.getByRole("button", { name: "log" })).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => axisTypes(page)).toEqual(["linear", "log"]);
    await expect(plot).toHaveAccessibleName(/, with a log y axis$/);
    // Every concentration of Demo2020 is above 0: the log y axis leaves out no point.
    await expect(pane.locator(".plot-scales-note")).toHaveText("");

    // The local server keeps the choice of the figure with its settings, for the next start too.
    // The choice is applied at once and saved after it: wait for the save before the reload.
    const savedScales = () =>
      page.evaluate(async () => {
        const state = (await (await fetch("/local/state")).json()) as { plot_scales: Record<string, unknown> };
        return state.plot_scales["caffeine/Demo2020/Fig1"];
      });
    await expect.poll(savedScales).toEqual({ x: "linear", y: "log" });
    await page.reload();
    await expect(pane.getByRole("group", { name: "Scale of the y axis" }).getByRole("button", { name: "log" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect.poll(() => axisTypes(page)).toEqual(["linear", "log"]);

    // The log axis labels full values, so a 5 is not taken for 0.5: each label is a different number.
    const ticks = await plot.locator(".ytick text").allTextContents();
    expect(ticks).toEqual(expect.arrayContaining(["0.5", "1"]));
    expect(new Set(ticks).size).toBe(ticks.length);
    expect(ticks.every((tick) => Number.isFinite(Number(tick)))).toBe(true);
    expect(overlapping(await tickLabels(plot, "y"))).toEqual([]);

    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await expectAccessible(page);
      const shot = await pane.screenshot({ path: testInfo.outputPath(`log-plot-${theme}.png`) });
      await testInfo.attach(`log-plot-${theme}.png`, { body: shot, contentType: "image/png" });
    }
  } finally {
    renameSync(`${project}.away`, project);
  }
});

test("a figure drawn on its image has no scales to switch", async ({ app, page }) => {
  await app.open(FIG1);
  const pane = page.getByRole("region", { name: "Source Fig1" });
  await expect(pane.getByRole("img", { name: /^Figure Fig1 with/ })).toBeVisible();
  await expect(pane.getByRole("group", { name: /^Scale of the/ })).toHaveCount(0);
});

test("a log axis over 1.3 decades labels 1, 2 and 5 of each decade apart from each other in both themes", async ({
  app,
  page,
}, testInfo) => {
  // Fig1 beside its image, with its 18 concentrations spread from 1 to 20 mg/l: there, Plotly
  // labels every digit of a decade by default (0.8 0.9 1 2 3 ... 9 10 20), and the labels overlap.
  const project = join(app.server.workspace, PROJECT);
  renameSync(project, `${project}.away`);
  await page.route("**/local/studies/caffeine/Demo2020/sources/Fig1", async (route) => {
    const response = await route.fetch();
    const view = (await response.json()) as { points: { y: number; y_text: string; error_bar: number | null }[] };
    const last = view.points.length - 1;
    view.points = view.points.map((point, index) => {
      const y = Number((10 ** ((1.3 * index) / last)).toPrecision(3));
      return { ...point, y, y_text: String(y), error_bar: null };
    });
    await route.fulfill({ response, json: view });
  });
  try {
    await app.open(FIG1);
    const pane = page.getByRole("region", { name: "Source Fig1" });
    const plot = pane.getByRole("img", { name: /^Plot of 18 mapped rows of Fig1/ });
    await expect(plot).toBeVisible();
    await pane.getByRole("group", { name: "Scale of the y axis" }).getByRole("button", { name: "log" }).click();
    await expect.poll(() => axisTypes(page)).toEqual(["linear", "log"]);

    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      const labels = await tickLabels(plot, "y");
      // Full values, each once, and no two labels on top of each other.
      expect(labels.map((label) => label.text)).toEqual(["1", "2", "5", "10", "20"]);
      expect(overlapping(labels)).toEqual([]);
      expect(overlapping(await tickLabels(plot, "x"))).toEqual([]);
      // The pressed button of the scales and of the zoom of the image stands out from the other one.
      const contrasts: Record<string, number> = {};
      for (const name of ["Image size", "Scale of the x axis", "Scale of the y axis"]) {
        contrasts[name] = await pressedContrast(pane.getByRole("group", { name }));
        expect(contrasts[name], name).toBeGreaterThanOrEqual(3);
      }
      const measured = testInfo.outputPath(`pressed-contrast-${theme}.json`);
      writeFileSync(measured, JSON.stringify(contrasts));
      await testInfo.attach(`pressed-contrast-${theme}.json`, { path: measured, contentType: "application/json" });
      await expectAccessible(page);
      const shot = await pane.screenshot({ path: testInfo.outputPath(`log-ticks-${theme}.png`) });
      await testInfo.attach(`log-ticks-${theme}.png`, { body: shot, contentType: "image/png" });
    }
  } finally {
    await page.unroute("**/local/studies/caffeine/Demo2020/sources/Fig1");
    renameSync(`${project}.away`, project);
  }
});
