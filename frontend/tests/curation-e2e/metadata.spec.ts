import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "./fixtures.ts";

interface StudyJson {
  licence: string;
  descriptions: string[];
}

const EDITED = "This is a synthetic test study of the PK-DB curation app. The curator edited this description.";
const ON_DISK = "Added in an editor while the form was open.";

test("saves the metadata form to study.json and keeps the edits through a conflict", async ({ app, page }) => {
  const path = join(app.server.workspace, "caffeine/Demo2020/study.json");
  const onDisk = (): StudyJson => JSON.parse(readFileSync(path, "utf8")) as StudyJson;
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const description = page.getByRole("textbox", { name: "Description 1" });
  const save = page.getByRole("button", { name: "Save", exact: true });
  await expect(page.getByRole("radio", { name: "Closed" })).toBeChecked();

  await page.getByRole("radio", { name: "Open" }).check();
  await description.fill(EDITED);
  await expect(page.getByText("Unsaved changes in study.json")).toBeVisible();
  await save.click();
  await expect(page.getByText("study.json saved.").first()).toBeVisible();
  await expect.poll(onDisk).toMatchObject({ licence: "open", descriptions: [EDITED] });

  // Another edit, while an editor appends a description to study.json in canonical form.
  await page.getByRole("radio", { name: "Closed" }).check();
  const changed = onDisk();
  changed.descriptions.push(ON_DISK);
  writeFileSync(path, `${JSON.stringify(changed, null, 2)}\n`);
  app.allowFailedRequest("/local/studies/metadata", 409);
  await save.click();
  await expect(page.getByText("study.json changed on disk after you opened this form.")).toHaveText(
    "study.json changed on disk after you opened this form. Reload it to keep your edits on top of the new version.",
  );
  expect(onDisk()).toMatchObject({ licence: "open", descriptions: [EDITED, ON_DISK] });

  // The reloaded form keeps the edit and marks the field that changed on disk.
  await page.getByRole("button", { name: "Reload", exact: true }).click();
  await expect(page.getByText("Reloaded study.json from disk.")).toBeVisible();
  await expect(page.getByRole("radio", { name: "Closed" })).toBeChecked();
  await expect(description).toHaveValue(EDITED);
  await expect(page.getByRole("textbox", { name: "Description 2" })).toHaveValue(ON_DISK);
  await expect(page.getByText("Changed on disk", { exact: true })).toBeVisible();
  await save.click();
  await expect(page.getByText("study.json saved.").first()).toBeVisible();
  await expect.poll(onDisk).toMatchObject({ licence: "closed", descriptions: [EDITED, ON_DISK] });
  await expect(page.getByText("Unsaved changes in study.json")).toBeHidden();
});
