import AxeBuilder from "@axe-core/playwright";
import type { Page, TestInfo } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";
const NARROW = { width: 390, height: 844 };

interface Screen {
  name: string;
  hash: string;
  /** Wait until the screen shows its content, also after the window changed its width. */
  ready(page: Page): Promise<void>;
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
    name: "sources",
    hash: `${STUDY}/sources`,
    ready: async (page) => {
      await expect(page.getByRole("tab", { name: "Fig1", selected: true })).toBeVisible();
      await expect(page.getByRole("list", { name: "Series" })).toBeVisible();
    },
  },
  {
    name: "tables",
    hash: `${STUDY}/tables?file=timecourses_Fig1.tsv`,
    ready: async (page) => {
      await expect(page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" })).toBeVisible();
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

async function expectAccessible(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const found = violations.map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`);
  expect(found, "axe violations").toEqual([]);
}

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  await testInfo.attach(name, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
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
