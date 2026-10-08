import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

interface OverlayPoint {
  role: "raw" | "mapped";
  px: number;
  py: number;
  file: string;
  line: number | null;
}

interface SourceView {
  image_size: [number, number];
  overlay: OverlayPoint[];
}

/** The source view that the app draws, from the local API of the page's session. */
function sourceView(page: Page, source: string): Promise<SourceView> {
  return page.evaluate(
    async (url) => (await (await fetch(url)).json()) as SourceView,
    `/local/studies/caffeine/Demo2020/sources/${source}`,
  );
}

test.beforeEach(async ({ app }) => {
  await app.open("#/studies/caffeine/Demo2020/sources");
});

test("the Fig1 overlay shows the row of a mapped point and opens it in the Tables section", async ({ page }) => {
  await page.getByRole("tab", { name: "Fig1" }).click();
  const figure = page.getByRole("img", {
    name: /^Figure Fig1 with \d+ digitized points, \d+ digitized error bar ends and \d+ mapped rows/,
  });
  await expect(figure).toBeVisible();
  // Plotly keeps the traces that it drew on its element.
  await expect
    .poll(() => figure.evaluate((element) => (element as HTMLElement & { data?: unknown[] }).data?.length ?? 0))
    .toBeGreaterThan(0);
  await expect(page.getByRole("list", { name: "Series" })).toContainText("caf_plasma_100mg");

  // The misplaced point of line 6 has no digitized point near it, so the cross is alone there.
  const view = await sourceView(page, "Fig1");
  const point = view.overlay.find((entry) => entry.role === "mapped" && entry.line === 6);
  expect(point).toMatchObject({ file: "timecourses_Fig1.tsv" });
  const box = await figure.boundingBox();
  if (!point || !box) throw new Error("The overlay has no point of line 6");
  const [width, height] = view.image_size;
  const x = box.x + (point.px * box.width) / width;
  const y = box.y + (point.py * box.height) / height;
  await page.mouse.move(x, y);
  await expect(page.getByText("timecourses_Fig1.tsv line 6")).toBeVisible();

  await page.mouse.click(x, y);
  await expect(page.getByRole("heading", { name: "Tables", level: 2 })).toBeVisible();
  await expect(page.getByRole("tab", { name: /^timecourses_Fig1\.tsv/, selected: true })).toBeVisible();
  const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(grid.getByRole("rowheader", { name: "6", exact: true })).toBeFocused();
});

test("the Tab2 source shows the table image, the raw extraction and the mapped rows", async ({ page }) => {
  await page.getByRole("tab", { name: "Tab2" }).click();
  await expect(page.getByRole("img", { name: "Tab2 of caffeine/Demo2020" })).toBeVisible();
  const raw = page.getByRole("region", { name: "Raw extraction Demo2020_Tab2.tsv" });
  await expect(raw.getByRole("cell", { name: "AUC0-inf (mg·h/l)" })).toBeVisible();
  await expect(raw.getByRole("cell", { name: "36.1 ± 8.5" })).toBeVisible();
  const mapped = page
    .getByRole("region", { name: "Mapped rows" })
    .getByRole("region", { name: "outputs_Tab2.tsv", exact: true });
  await expect(mapped).toContainText("8 rows");
  await expect(mapped.getByRole("link", { name: "Show line 2 of outputs_Tab2.tsv in the Tables section" })).toBeVisible();
});
