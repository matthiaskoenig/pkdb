import { renameSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
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
    // Every time of Demo2020 is above 0: no point is left out.
    await expect(pane.locator(".plot-scales-note")).toHaveText("");

    // The local server keeps the choice of the figure with its settings, for the next start too.
    const state = (await page.evaluate(async () => (await fetch("/local/state")).json())) as {
      plot_scales: Record<string, unknown>;
    };
    expect(state.plot_scales["caffeine/Demo2020/Fig1"]).toEqual({ x: "linear", y: "log" });
    await page.reload();
    await expect(pane.getByRole("group", { name: "Scale of the y axis" }).getByRole("button", { name: "log" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect.poll(() => axisTypes(page)).toEqual(["linear", "log"]);

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
