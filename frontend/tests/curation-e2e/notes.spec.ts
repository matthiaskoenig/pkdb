import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";
/** The first description and the comment of the notes of the subjects in study.json of the fixture. */
const DESCRIPTION = "Healthy adult volunteers who abstained from caffeine for 48 hours before the study day.";
const COMMENT = "The paper gives no sex distribution of the group.";

/** The rows pane of the table `file` in the Data section. */
function rowsPane(page: Page, file: string) {
  return page.getByRole("region", { name: `Table ${file}`, exact: true });
}

test("the notes of the subjects show above subjects.tsv in the Data section", async ({ app, page }) => {
  test.fail(true, "#918: the Data section does not show the notes of a table; Task 5 of the plan removes this line");
  await app.open(`${STUDY}/data?file=subjects.tsv`);
  const pane = rowsPane(page, "subjects.tsv");
  await expect(pane.getByRole("region", { name: "Rows of subjects.tsv" })).toBeVisible();
  const toggle = pane.getByRole("button", { name: /^Notes of the subjects/ });
  await expect(toggle).toHaveText("Notes of the subjects 2 descriptions · 1 comment");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(pane.getByRole("textbox", { name: "Description 1" })).toHaveValue(DESCRIPTION);
  await expect(pane.getByRole("textbox", { name: "Comment 1 by curator" })).toHaveValue(COMMENT);
});
