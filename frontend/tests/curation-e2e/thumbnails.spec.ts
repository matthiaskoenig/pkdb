import { cpSync } from "node:fs";
import { basename, join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";
import { pixelStats } from "./pixels.ts";

/**
 * A study folder whose large paper images painted white in the navigator, such as
 * `<pkdb_data>/caffeine/Walther1983`. The synthetic fixture never did, so the test of that
 * defect runs only with the folder; it is copied into the workspace of the test's server.
 */
const STUDY = process.env.PKDB_THUMBNAIL_STUDY;
/** Page loads of the study: a thumbnail showed white in most loads, not in every one. */
const LOADS = 2;

/**
 * The `src` of each thumbnail of the navigator that painted no pixel of its image once every
 * image loaded. A thumbnail decoded while it is painted shows its image at once. Each one is
 * measured once, scrolled into view as a curator does: waiting for `decode()` or for a later
 * screenshot let Chromium paint a thumbnail that it had shown white, and hid the defect.
 */
async function blankThumbnails(page: Page): Promise<string[]> {
  const thumbnails = page.locator("img.nav-thumb");
  await expect(thumbnails.first()).toBeVisible();
  await expect
    .poll(() =>
      thumbnails.evaluateAll((images) =>
        images.every((image) => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0),
      ),
    )
    .toBe(true);
  const blank: string[] = [];
  for (const thumbnail of await thumbnails.all())
    if ((await pixelStats(thumbnail)).ink === 0) blank.push((await thumbnail.getAttribute("src")) ?? "");
  return blank;
}

test("every thumbnail of the navigator paints its image", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data");
  await expect(page.locator("img.nav-thumb")).toHaveCount(2);
  expect(await blankThumbnails(page)).toEqual([]);
});

test.describe(() => {
  // A laptop window, in which the navigator of Walther1983 scrolls: its last thumbnail is
  // painted only once it scrolls into view.
  test.use({ viewport: { width: 1440, height: 768 } });

  test("the thumbnails of large paper images paint their image", async ({ app, curation, page }) => {
    test.skip(!STUDY, "Set PKDB_THUMBNAIL_STUDY to a study folder with large paper images, such as <pkdb_data>/caffeine/Walther1983");
    // Slowed page loads.
    test.slow();
    const name = basename(STUDY!);
    cpSync(STUDY!, join(curation.workspace, "caffeine", name), { recursive: true });
    await app.open("#/");
    // The watcher lists the copied study within a few seconds.
    await expect
      .poll(() => page.evaluate(async (id) => JSON.stringify(await (await fetch("/local/state")).json()).includes(`"${id}"`), `caffeine/${name}`))
      .toBe(true);
    // A computer eight times slower, on which Chromium showed a thumbnail white in nearly every
    // load; on a fast one it did in few.
    const session = await page.context().newCDPSession(page);
    await session.send("Emulation.setCPUThrottlingRate", { rate: 8 });
    await app.open(`#/studies/caffeine/${name}/data`);
    for (let load = 1; load <= LOADS; load++) {
      if (load > 1) await page.reload();
      expect(await blankThumbnails(page), `load ${load} of ${LOADS}`).toEqual([]);
    }
  });
});
