import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

interface StudyJson {
  licence: string;
  descriptions: string[];
}

const EDITED = "This is a synthetic test study of the PK-DB curation app. The curator edited this description.";
const ON_DISK = "Added in an editor while the form was open.";

test("saves the metadata form to study.json and keeps the edits through a conflict", async ({ app, page }) => {
  const path = join(app.server.workspace, "caffeine/Demo2020/study.json");
  const original = readFileSync(path, "utf8");
  try {
    const onDisk = (): StudyJson => JSON.parse(readFileSync(path, "utf8")) as StudyJson;
    await app.open("#/studies/caffeine/Demo2020/metadata");
    const description = page.getByRole("textbox", { name: "Description 1" });
    const save = page.getByRole("button", { name: "Save", exact: true });
    await expect(page.getByRole("radio", { name: "Closed" })).toBeChecked();

    await page.getByRole("radio", { name: "Open" }).check();
    await description.fill(EDITED);
    await expect(page.locator(".unsaved-banner")).toContainText("Unsaved changes to study.json: Licence, Descriptions");
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
    await expect(page.getByText("study.json changed on disk after you started editing it.")).toHaveText(
      "study.json changed on disk after you started editing it. Reload it to keep your edits on top of the new version.",
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
    await expect(page.locator(".unsaved-banner")).not.toContainText("Unsaved changes");
  } finally {
    writeFileSync(path, original);
  }
});

test("the avatar of a person stays clear of the label on the outline of its field", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const creator = page.getByRole("combobox", { name: "Creator" });
  await expect(creator).toBeVisible();
  // The floating label crosses the top of the outline, so the avatar keeps 4 px from both edges.
  const room = await page.locator(".creator-field .v-field").evaluate((field) => {
    const outline = field.getBoundingClientRect();
    const avatar = field.querySelector(".v-avatar")!.getBoundingClientRect();
    return { top: avatar.top - outline.top, bottom: outline.bottom - avatar.bottom };
  });
  expect(room.top).toBeGreaterThanOrEqual(4);
  expect(room.bottom).toBeGreaterThanOrEqual(4);
});

test("the card of the descriptions and comments takes the whole last row and points to the notes in Data", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const card = page.getByRole("region", { name: "Descriptions and comments" });
  await expect(card).toContainText("Notes of a table are in Data, above the table.");
  await expect(page.getByRole("region", { name: "Notes per table" })).toHaveCount(0);
  // Five cards in two columns: the last one closes the gap of its row.
  const form = await page.locator(".metadata-form").boundingBox();
  const box = await card.boundingBox();
  expect(Math.round(box!.width)).toBe(Math.round(form!.width));
  // Demo2020 has notes of the subjects only, and a subjects table: none show here.
  await expect(card.getByRole("button", { name: /^Notes of the/ })).toHaveCount(0);
  await card.getByRole("link", { name: "Data" }).click();
  await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data/);
});

/** The height of the outline of the field of `control`. */
function outlineHeight(control: Locator): Promise<number> {
  return control.evaluate((element) => element.closest(".v-field")!.getBoundingClientRect().height);
}

/** How far the middle of the remove button of the row of the text area `control` lies below the middle of its outline. */
function removeOffset(control: Locator): Promise<number> {
  return control.evaluate((element) => {
    const field = element.closest(".v-field")!.getBoundingClientRect();
    const remove = element.closest(".note-row")!.querySelector(":scope > .row-remove")!.getBoundingClientRect();
    return remove.top + remove.height / 2 - (field.top + field.height / 2);
  });
}

/** The room above and below the first line of text of `control`, and the height of the middle of that line below the top of its outline. */
function lineRoom(control: Locator): Promise<{ above: number; below: number; middle: number }> {
  return control.evaluate((element) => {
    const field = element.closest(".v-field")!.getBoundingClientRect();
    const box = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const line = element instanceof HTMLTextAreaElement ? parseFloat(style.lineHeight) : box.height;
    const top = element instanceof HTMLTextAreaElement ? box.top + parseFloat(style.paddingTop) : box.top;
    return { above: top - field.top, below: field.bottom - (top + line), middle: top + line / 2 - field.top };
  });
}

test("a description and a comment of one line are as high as the other fields, with their remove buttons beside them", async ({
  app,
  page,
}, testInfo) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const card = page.getByRole("region", { name: "Descriptions and comments" });
  const description = card.getByRole("textbox", { name: "Description 1", exact: true });
  await expect(description).toHaveValue(/^This is a synthetic test study/);
  await card.getByRole("button", { name: "Add comment", exact: true }).click();
  const comment = card.getByRole("textbox", { name: "Comment 1 by curator", exact: true });
  await expect(comment).toHaveValue("");
  // No label shows: the headings name the lists.
  await expect(card.locator("label")).toHaveCount(0);
  await expect(card.getByRole("heading", { name: "Descriptions", exact: true })).toBeVisible();
  await expect(card.getByRole("heading", { name: "Comments", exact: true })).toBeVisible();
  const sourceKey = page.getByRole("textbox", { name: "Source key", exact: true });

  for (const width of [1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    // The description of the study fits one line, and the new comment is empty.
    const line = await outlineHeight(sourceKey);
    expect(Math.abs((await outlineHeight(description)) - line)).toBeLessThanOrEqual(1);
    expect(Math.abs((await outlineHeight(comment)) - line)).toBeLessThanOrEqual(1);
    // The line of text stands in the middle of the field, at the height of the text of a text field.
    const reference = await lineRoom(sourceKey);
    for (const control of [description, comment]) {
      const room = await lineRoom(control);
      expect(Math.abs(room.above - room.below)).toBeLessThanOrEqual(1);
      expect(Math.abs(room.middle - reference.middle)).toBeLessThanOrEqual(1);
    }
    expect(Math.abs(await removeOffset(description))).toBeLessThanOrEqual(1);
    expect(Math.abs(await removeOffset(comment))).toBeLessThanOrEqual(1);
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await expectAccessible(page);
      const shot = await card.screenshot({ path: testInfo.outputPath(`descriptions-${theme}-${width}.png`) });
      await testInfo.attach(`descriptions-${theme}-${width}.png`, { body: shot, contentType: "image/png" });
    }
  }
});
