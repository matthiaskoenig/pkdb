import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

interface ReviewJson {
  status: string;
  items: { kind: string; state: string; text: string; target?: object; thread?: { author: string; text: string }[] }[];
}

const REPLY = "The methods planned a 400 mg arm that was dropped. D400 stays to document it.";
const ISSUE = "The 4 h mean of the 100 mg series differs from the results text.";

function card(page: Page, text: string | RegExp): Locator {
  return page.getByRole("list", { name: "Review items" }).getByRole("button", { name: text });
}

/**
 * Choose `option` in the Vuetify select labelled `label` as a keyboard does: in the open menu,
 * typing the start of an item selects and focuses it, also one that the virtual list had not
 * rendered yet; Escape then closes the menu.
 */
async function choose(page: Page, scope: Locator | Page, label: string, option: string): Promise<void> {
  const select = scope.getByRole("combobox", { name: label, exact: true });
  await select.focus();
  await select.press("ArrowDown");
  await expect(select).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.type(option);
  await expect(page.getByRole("option", { name: option, exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(select).toHaveAttribute("aria-expanded", "false");
}

test.beforeEach(async ({ app }) => {
  await app.open("#/studies/caffeine/Demo2020/review");
});

function onDisk(workspace: string): ReviewJson {
  return JSON.parse(readFileSync(join(workspace, "caffeine/Demo2020/review.json"), "utf8")) as ReviewJson;
}

test("replies to an open item and resolves it", async ({ app, page }) => {
  await expect(page.getByRole("group", { name: "Filter by state" }).getByRole("button", { name: /^Open/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await card(page, /Should D400 stay\?/).click();
  const item = page.getByRole("article", { name: "Question" });
  await expect(item).toContainText("interventions.tsv · name = D400");
  await item.getByRole("textbox", { name: "Reply" }).fill(REPLY);
  await item.getByRole("button", { name: "Reply", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Reply posted." })).toBeVisible();
  const thread = item.getByRole("region", { name: "Thread" });
  await expect(thread.getByRole("listitem")).toHaveCount(1);
  await expect(thread.getByRole("listitem")).toContainText(REPLY);

  await item.getByRole("button", { name: "Resolve" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Item resolved." })).toBeVisible();
  await expect(item).toContainText("Resolved");
  await expect(thread).toContainText(REPLY);
  const question = onDisk(app.server.workspace).items.find((entry) => entry.kind === "question");
  expect(question).toMatchObject({ state: "resolved", thread: [{ author: "curator", text: REPLY }] });
});

test("adds an item about a row and a column of a table", async ({ app, page }) => {
  await page.getByRole("button", { name: "New item" }).click();
  const dialog = page.getByRole("dialog", { name: "New review item" });
  await dialog.getByRole("radio", { name: "Issue" }).check();
  await dialog.getByRole("textbox", { name: "Text" }).fill(ISSUE);
  await choose(page, dialog, "File", "timecourses_Fig1.tsv");
  await expect(dialog.getByRole("combobox", { name: "File", exact: true })).toHaveValue("timecourses_Fig1.tsv");
  await dialog.getByRole("button", { name: "Add row filter" }).click();
  await choose(page, dialog, "Column 1", "label");
  await dialog.getByRole("combobox", { name: "Value 1" }).fill("caf_plasma_100mg");
  await dialog.getByRole("button", { name: "Add row filter" }).click();
  await choose(page, dialog, "Column 2", "time");
  await dialog.getByRole("combobox", { name: "Value 2" }).fill("4");
  await expect(dialog.getByRole("status")).toHaveText("Matches 1 of 18 rows.");
  await choose(page, dialog, "Column", "mean");
  await dialog.getByRole("button", { name: "Add", exact: true }).click();

  await expect(dialog).toBeHidden();
  await expect(page.getByRole("status").filter({ hasText: "Item added." })).toBeVisible();
  const item = page.getByRole("article", { name: "Issue" });
  await expect(item).toContainText(ISSUE);
  await expect(item).toContainText("timecourses_Fig1.tsv · label = caf_plasma_100mg, time = 4 · column mean");
  const added = onDisk(app.server.workspace).items.find((entry) => entry.text === ISSUE);
  expect(added).toMatchObject({
    kind: "issue",
    state: "open",
    target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_100mg", time: "4" }, column: "mean" },
  });
});

test("refuses Approved while review items are open", async ({ app, page }) => {
  app.allowFailedRequest("/local/studies/review", 422);
  // Choosing an item sets the status at once and disables the select, so the item is clicked.
  const status = page.getByRole("combobox", { name: "Review status" });
  await status.focus();
  await status.press("ArrowDown");
  await page.getByRole("option", { name: "Approved", exact: true }).click();
  const refusal = page.getByText("Approved needs zero open review items and zero validation errors.");
  await expect(refusal).toHaveText(
    /^Approved needs zero open review items and zero validation errors\. \d+ review items? (is|are) open\.$/,
  );
  await expect(page.getByRole("link", { name: "Show the open items" })).toBeVisible();
  // The select shows the saved status again.
  await expect(page.getByRole("combobox", { name: "Review status" })).toHaveValue("In review");
  expect(onDisk(app.server.workspace).status).toBe("in_review");
});
