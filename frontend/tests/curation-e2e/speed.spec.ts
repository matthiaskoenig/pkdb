import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

/** The studies of the generated workspace (tools/curation_testing/large_workspace.py). */
const STUDIES = 1000;
/** The longest median time from a keystroke to its paint, and from the search to its result. */
const BUDGET_MS = 100;
/** How long the search waits after the last keystroke (Part 2 of the spec). */
const SEARCH_DELAY_MS = 150;
/** A surname of the generator: 25 of the 1,000 studies have it, and no title has it. */
const SURNAME = "dahlqvist";

/** How long the server may need to pause its automatic actions while it validates 1,000 studies. */
const PAUSE_MS = 120_000;

test.use({ studies: STUDIES });
// The timings need the processor to themselves: no sibling test runs beside them.
test.describe.configure({ mode: "serial", timeout: PAUSE_MS + 60_000 });

interface Latency {
  /** For each input event, the milliseconds until the paint after it. */
  inputs: number[];
  /** The milliseconds from the last input event to the paint that showed a new count, or null. */
  result: number | null;
  /** The durations of the long tasks since the probe was installed. */
  longTasks: number[];
}

/**
 * Measure in the page: each input event until the next paint, the last input event until the
 * count of the overview changed and painted, and the long tasks. A task queued from the next
 * animation frame runs once that frame painted.
 */
async function installLatencyProbe(page: Page): Promise<void> {
  await page.evaluate(() => {
    const probe = {
      inputs: [] as number[],
      result: null as number | null,
      longTasks: [] as number[],
      last: 0,
    };
    (window as unknown as { __latency: typeof probe }).__latency = probe;
    const afterPaint = (done: () => void) => requestAnimationFrame(() => setTimeout(done, 0));
    document.addEventListener(
      "input",
      (event) => {
        const start = event.timeStamp;
        probe.last = start;
        afterPaint(() => probe.inputs.push(performance.now() - start));
      },
      { capture: true },
    );
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) probe.longTasks.push(entry.duration);
    }).observe({ type: "longtask" });
    const count = document.querySelector(".overview-count");
    if (count)
      new MutationObserver(() => afterPaint(() => (probe.result = performance.now() - probe.last))).observe(count, {
        childList: true,
        characterData: true,
        subtree: true,
      });
  });
}

async function readLatency(page: Page): Promise<Latency> {
  return page.evaluate(() => {
    const { inputs, result, longTasks } = (window as unknown as { __latency: Latency }).__latency;
    return { inputs, result, longTasks };
  });
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2;
}

test.beforeEach(async ({ app, page }) => {
  await app.open();
  await expect(
    page.getByText(`${STUDIES.toLocaleString("en-US")} studies`, {
      exact: true,
    }),
  ).toBeVisible();
  // The initial validations of 1,000 studies would compete with the measurements for the processor.
  // The server is busy with them, so the pause takes longer than the default timeout.
  await page.getByRole("button", { name: "File watching: Active" }).click();
  await page.getByRole("button", { name: "Pause automatic actions" }).click();
  await expect(page.getByRole("button", { name: "File watching: Paused" })).toBeVisible({ timeout: PAUSE_MS });
  await page.keyboard.press("Escape");
});

test("typing in Search studies paints each keystroke and the result within 100 ms", async ({ page }, testInfo) => {
  test.fail(true, "#936: the overview filters and renders every study on each keystroke");
  await page.getByRole("textbox", { name: "Search studies" }).click();
  await installLatencyProbe(page);
  await page.keyboard.type(SURNAME, { delay: 60 });
  await expect(page.getByText(`25 of ${STUDIES.toLocaleString("en-US")} studies`)).toBeVisible();
  await expect.poll(async () => (await readLatency(page)).result).not.toBeNull();
  const latency = await readLatency(page);
  await testInfo.attach("latency.json", {
    body: JSON.stringify(latency, null, 2),
    contentType: "application/json",
  });
  // The median, so that one pause of the garbage collector does not decide.
  expect(median(latency.inputs), JSON.stringify(latency)).toBeLessThanOrEqual(BUDGET_MS);
  expect(latency.result! - SEARCH_DELAY_MS, JSON.stringify(latency)).toBeLessThanOrEqual(BUDGET_MS);
});
