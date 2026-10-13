import type { Locator, Page, TestInfo } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

// The screens and dialogs change nothing on the server, so their tests run in parallel.
test.describe.configure({ mode: "parallel" });

const STUDY = "#/studies/caffeine/Demo2020";
const NARROW = { width: 390, height: 844 };

/**
 * Wait until the viewer of the paper has drawn page 1, which the Data section shows beside a
 * shared table: axe checks the page as the curator sees it, not while PDF.js still draws.
 */
async function paperDrawn(page: Page): Promise<void> {
  await expect(page.locator('.page[data-page-number="1"][data-loaded="true"]')).toBeVisible();
  await expect(page.getByRole("searchbox", { name: "Find in the paper" })).toBeEnabled();
}

interface Screen {
  name: string;
  hash: string;
  /** Wait until the screen shows its content, also after the window changed its width. */
  ready(page: Page): Promise<void>;
}

/**
 * Open the notes of the subjects above subjects.tsv, if they are closed (the panel keeps its state
 * when the window narrows), and return the field of the first description.
 */
async function openSubjectNotes(page: Page): Promise<Locator> {
  const pane = page.getByRole("region", { name: "Table subjects.tsv", exact: true });
  const toggle = pane.getByRole("button", { name: /^Notes of the subjects/ });
  if ((await toggle.getAttribute("aria-expanded")) === "false") await toggle.click();
  return pane.getByRole("textbox", { name: "Description 1" });
}

const SCREENS: Screen[] = [
  {
    name: "overview",
    hash: "#/",
    ready: async (page) => {
      const table = page.getByRole("table", { name: "Studies of the workspace" });
      await expect(table.getByRole("cell", { name: "2 warnings" })).toBeVisible();
      await expect(table.getByRole("cell", { name: "1 error" })).toBeVisible();
    },
  },
  {
    name: "metadata",
    hash: `${STUDY}/metadata`,
    ready: async (page) => {
      await expect(page.getByRole("textbox", { name: "Description 1" })).toBeVisible();
    },
  },
  {
    name: "unsaved metadata",
    hash: `${STUDY}/metadata`,
    ready: async (page) => {
      const banner = page.locator(".unsaved-banner");
      // The draft stays while the window narrows, so the edit happens once.
      if (!(await banner.isVisible())) await page.getByRole("textbox", { name: "Source key" }).fill("pkdb.manual.edited");
      await expect(banner).toContainText("Unsaved changes to study.json: Source key");
    },
  },
  {
    name: "review",
    hash: `${STUDY}/review`,
    ready: async (page) => {
      await expect(page.getByRole("article", { name: "Question" })).toBeVisible();
    },
  },
  {
    name: "problems",
    hash: `${STUDY}/problems`,
    ready: async (page) => {
      await expect(page.getByText("digitized_mismatch", { exact: true })).toBeVisible();
    },
  },
  {
    name: "data of a figure",
    hash: `${STUDY}/data?source=Fig1`,
    ready: async (page) => {
      await expect(page.getByRole("list", { name: "Series" })).toBeVisible();
      await expect(page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" })).toBeVisible();
    },
  },
  {
    name: "data of a table",
    hash: `${STUDY}/data?source=Tab2&file=outputs_Tab2.tsv`,
    ready: async (page) => {
      await expect(page.getByRole("region", { name: "Raw extraction Demo2020_Tab2.tsv" })).toBeVisible();
      await expect(page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" })).toBeVisible();
    },
  },
  {
    name: "paper in a tab of its own",
    hash: `${STUDY}/paper/Demo2020.pdf`,
    ready: paperDrawn,
  },
  {
    name: "data of the paper",
    hash: `${STUDY}/data?source=paper`,
    ready: paperDrawn,
  },
  {
    // Beside the paper, the first source.
    name: "data of a shared table",
    hash: `${STUDY}/data?file=subjects.tsv`,
    ready: async (page) => {
      await expect(page.getByRole("combobox", { name: "Source of the rows" })).toBeVisible();
      await expect(page.getByRole("region", { name: "Rows of subjects.tsv" })).toBeVisible();
      await paperDrawn(page);
    },
  },
  {
    name: "notes of a table",
    hash: `${STUDY}/data?file=subjects.tsv`,
    ready: async (page) => {
      const description = await openSubjectNotes(page);
      await expect(description).toBeVisible();
      await paperDrawn(page);
    },
  },
  {
    name: "unsaved notes of a table",
    hash: `${STUDY}/data?file=subjects.tsv`,
    ready: async (page) => {
      const banner = page.locator(".unsaved-banner");
      if (!(await banner.isVisible())) {
        await (await openSubjectNotes(page)).fill("Healthy adult volunteers, edited.");
      }
      await expect(banner).toContainText("Unsaved changes to study.json: Notes of the subjects");
      await paperDrawn(page);
    },
  },
  {
    name: "activity",
    hash: `${STUDY}/activity`,
    ready: async (page) => {
      await expect(page.getByRole("listitem").filter({ hasText: "automatic" }).first()).toBeVisible();
    },
  },
];

interface Dialog {
  /** The accessible name of the dialog. */
  name: string;
  hash: string;
  /** Open the dialog from the screen of `hash`. */
  open(page: Page): Promise<void>;
}

const DIALOGS: Dialog[] = [
  {
    name: "Connection settings",
    hash: "#/",
    open: (page) => page.getByRole("button", { name: "Settings", exact: true }).click(),
  },
  {
    name: "Choose workspace",
    hash: "#/",
    open: async (page) => {
      await page.getByRole("button", { name: /^Workspace: / }).click();
      await page.getByRole("button", { name: "Choose workspace" }).click();
    },
  },
  {
    name: "Reference",
    hash: `${STUDY}/metadata`,
    open: (page) => page.getByRole("button", { name: "Correct title, authors, journal..." }).click(),
  },
  {
    name: "New review item",
    hash: `${STUDY}/review`,
    open: (page) => page.getByRole("button", { name: "New item" }).click(),
  },
  {
    name: "Acknowledge warning",
    hash: `${STUDY}/problems`,
    open: (page) =>
      page
        .getByRole("listitem")
        .filter({ has: page.getByText("digitized_mismatch", { exact: true }) })
        .getByRole("button", { name: "Acknowledge" })
        .click(),
  },
  {
    name: "Add table",
    hash: `${STUDY}/data`,
    open: async (page) => {
      // The section opens its first table beside the paper.
      await paperDrawn(page);
      await page.getByRole("button", { name: "Add table", exact: true }).click();
    },
  },
];

/** Attach a screenshot of the whole page, or of the window, where an open dialog and its scrim are. */
async function attachScreenshot(page: Page, testInfo: TestInfo, name: string, fullPage = true): Promise<void> {
  await testInfo.attach(name, { body: await page.screenshot({ fullPage }), contentType: "image/png" });
}

for (const theme of ["light", "dark"] as const) {
  for (const screen of SCREENS) {
    test(`${screen.name} in the ${theme} theme is accessible and fits a narrow window`, async ({ app, page }, testInfo) => {
      await page.emulateMedia({ colorScheme: theme });
      await app.open(screen.hash);
      // The app follows the theme of the system until the curator chooses one.
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await screen.ready(page);
      await expectAccessible(page);
      await attachScreenshot(page, testInfo, `${screen.name}-${theme}-wide.png`);

      await page.setViewportSize(NARROW);
      await screen.ready(page);
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
        .toBe(0);
      await expectAccessible(page);
      await attachScreenshot(page, testInfo, `${screen.name}-${theme}-narrow.png`);
    });
  }
}

for (const theme of ["light", "dark"] as const) {
  for (const dialog of DIALOGS) {
    test(`the ${dialog.name} dialog in the ${theme} theme is accessible and fits a narrow window`, async ({
      app,
      page,
    }, testInfo) => {
      await page.emulateMedia({ colorScheme: theme });
      await app.open(dialog.hash);
      await dialog.open(page);
      const shown = page.getByRole("dialog", { name: dialog.name });
      await expect(shown).toBeVisible();
      // The dialog takes the focus once its transition ended, so axe sees it as the curator does.
      await expect.poll(() => shown.evaluate((element) => element.contains(document.activeElement))).toBe(true);
      await expectAccessible(page);
      await attachScreenshot(page, testInfo, `${dialog.name}-${theme}-wide.png`, false);

      await page.setViewportSize(NARROW);
      await expect(shown).toBeVisible();
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
        .toBe(0);
      await expectAccessible(page);
      await attachScreenshot(page, testInfo, `${dialog.name}-${theme}-narrow.png`, false);
      await page.keyboard.press("Escape");
      await expect(shown).toBeHidden();
    });
  }
}

test("text is set in the bundled Inter, so that it has the same width on every system", async ({ app, page }) => {
  await app.open("#/");
  await expect(page.getByRole("table", { name: "Studies of the workspace" })).toBeVisible();
  const font = await page.evaluate(async () => {
    await document.fonts.ready;
    const inter = [...document.fonts].filter((face) => face.family.replaceAll('"', "") === "Inter Variable");
    return {
      body: getComputedStyle(document.body).fontFamily,
      loaded: inter.some((face) => face.status === "loaded"),
    };
  });
  expect(font.body).toMatch(/^"?Inter Variable"?,/);
  expect(font.loaded).toBe(true);
  // The license of the font is served beside it.
  const license = await page.evaluate(async () => {
    const response = await fetch("assets/Inter-LICENSE.txt");
    return { status: response.status, text: await response.text() };
  });
  expect(license.status).toBe(200);
  expect(license.text).toContain("SIL OPEN FONT LICENSE");
});
