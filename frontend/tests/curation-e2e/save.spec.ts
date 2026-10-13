import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";

interface StudyJson {
  provenance?: { kind?: string; source_key?: string };
  [key: string]: unknown;
}

/** The path of study.json of Demo2020 in the workspace of the server. */
function studyJsonPath(workspace: string): string {
  return join(workspace, "caffeine/Demo2020/study.json");
}

/** study.json as it is on disk. */
function onDisk(path: string): StudyJson {
  return JSON.parse(readFileSync(path, "utf8")) as StudyJson;
}

const EDITED_KEY = "pkdb.manual.edited";

/** The bodies of the writes of study.json that the page sends from now on. */
function metadataWrites(page: Page): string[] {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname === "/local/studies/metadata")
      writes.push(request.postData() ?? "");
  });
  return writes;
}

/** Records for each S pressed whether the app prevented the default; a listener after the app's sees it. */
async function recordSaveKeys(page: Page): Promise<() => Promise<boolean[]>> {
  await page.evaluate(() => {
    const seen: boolean[] = [];
    Object.assign(window, { __saveKeys: seen });
    window.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "s") seen.push(event.defaultPrevented);
    });
  });
  return () => page.evaluate(() => (window as unknown as { __saveKeys: boolean[] }).__saveKeys);
}

test("Ctrl+S saves study.json from the field just edited, and without changes writes nothing", async ({ app, page }) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  const writes = metadataWrites(page);
  try {
    await app.open(`${STUDY}/metadata`);
    const sourceKey = page.getByRole("textbox", { name: "Source key" });
    await expect(sourceKey).toHaveValue("pkdb.manual");
    const prevented = await recordSaveKeys(page);

    // Without changes: nothing to save, and no save dialog of the browser either.
    await page.keyboard.press("Control+s");
    await expect.poll(prevented).toEqual([true]);
    expect(writes).toEqual([]);

    await sourceKey.fill(EDITED_KEY);
    await sourceKey.press("Control+s");
    await expect.poll(prevented).toEqual([true, true]);
    await expect.poll(() => onDisk(path).provenance?.source_key).toBe(EDITED_KEY);
    expect(writes).toHaveLength(1);
  } finally {
    writeFileSync(path, original);
  }
});
