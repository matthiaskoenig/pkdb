import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "./fixtures.ts";

const PROJECT = "caffeine/Demo2020/Demo2020_Fig1.wpd.json";
const REASON = "The legend of the figure is no series.";

interface Project {
  datasetColl: { name: string; axesName: string; data: unknown[] }[];
}

interface ReviewJson {
  items: { acknowledges?: string; target?: object; text: string }[];
}

test("acknowledges one dataset of a WebPlotDigitizer project and keeps the warning of another", async ({ app, page }) => {
  const path = join(app.server.workspace, PROJECT);
  const project = JSON.parse(readFileSync(path, "utf8")) as Project;
  const axes = project.datasetColl[0]?.axesName ?? "XY";
  project.datasetColl.push({ name: "legend", axesName: axes, data: [] }, { name: "axis_labels", axesName: axes, data: [] });
  writeFileSync(path, JSON.stringify(project));
  await app.open("#/studies/caffeine/Demo2020/problems");
  const figure = page.getByRole("region", { name: "Demo2020_Fig1.wpd.json", exact: true });
  const legend = figure.getByRole("listitem").filter({ hasText: "'legend'" });
  const labels = figure.getByRole("listitem").filter({ hasText: "'axis_labels'" });
  await expect(legend).toBeVisible();
  await expect(labels).toBeVisible();

  await legend.getByRole("button", { name: "Acknowledge" }).click();
  const dialog = page.getByRole("dialog", { name: "Acknowledge warning" });
  await expect(dialog).toContainText("Demo2020_Fig1.wpd.json · legend");
  await expect(dialog).not.toContainText("Covers every");
  await dialog.getByRole("textbox", { name: "Reason" }).fill(REASON);
  await dialog.getByRole("button", { name: "Acknowledge" }).click();
  await expect(dialog).toBeHidden();

  // The next validation leaves out only the acknowledged dataset.
  const acknowledged = page.getByRole("region", { name: "Acknowledged warnings (1)" });
  await expect(acknowledged).toContainText("Demo2020_Fig1.wpd.json · legend");
  await expect(acknowledged).not.toContainText("Covers every");
  await expect(legend).toHaveCount(0);
  await expect(labels).toBeVisible();
  await expect(labels.getByRole("button", { name: "Acknowledge" })).toBeEnabled();
  const review = JSON.parse(
    readFileSync(join(app.server.workspace, "caffeine/Demo2020/review.json"), "utf8"),
  ) as ReviewJson;
  expect(review.items.filter((item) => item.acknowledges === "unknown_dataset")).toEqual([
    expect.objectContaining({ text: REASON, target: { file: "Demo2020_Fig1.wpd.json", key: "legend" } }),
  ]);
});
