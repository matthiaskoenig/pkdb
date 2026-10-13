import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

/** The studies of the generated workspace (tools/curation_testing/large_workspace.py). */
const STUDIES = 1000;
/** The longest median time from a keystroke to its paint, and from the search to its result. */
const BUDGET_MS = 100;
/** The longest task that the polls may cause while jobs run. */
const LONG_TASK_MS = 200;
/** How long the search waits after the last keystroke: the debounce that Task 2 of #936 adds. */
const SEARCH_DELAY_MS = 150;
/** A surname of the generator: 25 of the 1,000 studies have it, and no title has it. */
const SURNAME = "dahlqvist";
const MATCHES = 25;
/** Typing rounds of the search: one warm-up round that is not measured, then the measured ones. */
const WARM_UP_ROUNDS = 1;
const ROUNDS = 5;
/** How long without a long task counts as quiet, a little more than two polls of the app. */
const QUIET_MS = 3500;
/** How long the jobs that were already running may need to finish after the pause. */
const QUIET_TIMEOUT_MS = 60_000;
/** How long the polls are watched while jobs run. */
const WATCH_MS = 10_000;

test.use({ studies: STUDIES });
// The tests share the server and run in order; playwright.curation.config.ts runs this file in a
// project of its own after all other spec files, so nothing else loads the processor.
test.describe.configure({ mode: "serial", timeout: QUIET_TIMEOUT_MS + 90_000 });

interface Latency {
  /** For each recorded input event, the milliseconds until the paint after it. */
  inputs: number[];
  /** The milliseconds from the last input event to the paint that showed exactly the matches, or null. */
  result: number | null;
  /** The durations of the long tasks since they were last cleared. */
  longTasks: number[];
}

/**
 * Measure in the page: each input event (while armed) until the next paint, the last input event
 * until the table shows exactly the matches of the surname and painted, and the long tasks. A task
 * queued from the next animation frame runs once that frame painted. The observer sits on the
 * overview container, which stays, while the count and the rows come and go.
 */
async function installLatencyProbe(page: Page): Promise<void> {
  await page.evaluate(
    ({ surname, matches }) => {
      const probe = {
        inputs: [] as number[],
        result: null as number | null,
        longTasks: [] as number[],
        last: 0,
        armed: false,
      };
      (window as unknown as { __latency: typeof probe }).__latency = probe;
      const afterPaint = (done: () => void) => requestAnimationFrame(() => setTimeout(done, 0));
      const showsMatches = () => {
        const rows = [...document.querySelectorAll(".study-table tbody tr:not([aria-hidden])")];
        return (
          rows.length === matches &&
          rows.every((row) => row.querySelector(".study-identity")?.textContent?.toLowerCase().includes(surname))
        );
      };
      // The result of the latest input: the table shows exactly the matches, painted after it. An
      // input that leaves the rows as they are (the last letters of the surname) changes no DOM, so
      // each input checks too.
      const markResult = () => {
        if (probe.result === null && probe.last !== 0 && showsMatches()) probe.result = performance.now() - probe.last;
      };
      document.addEventListener(
        "input",
        (event) => {
          const start = event.timeStamp;
          const armed = probe.armed;
          probe.last = start;
          probe.result = null;
          afterPaint(() => {
            if (armed) probe.inputs.push(performance.now() - start);
            markResult();
          });
        },
        { capture: true },
      );
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) probe.longTasks.push(entry.duration);
      }).observe({ type: "longtask" });
      const root = document.querySelector(".overview") ?? document.body;
      new MutationObserver(() => afterPaint(markResult)).observe(root, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    },
    { surname: SURNAME, matches: MATCHES },
  );
}

async function readLatency(page: Page): Promise<Latency> {
  return page.evaluate(() => {
    const { inputs, result, longTasks } = (window as unknown as { __latency: Latency }).__latency;
    return { inputs: [...inputs], result, longTasks: [...longTasks] };
  });
}

async function resetLatency(page: Page, armed: boolean): Promise<void> {
  await page.evaluate((on) => {
    const probe = (window as unknown as { __latency: Latency & { armed: boolean; last: number } }).__latency;
    probe.inputs.length = 0;
    probe.longTasks.length = 0;
    probe.result = null;
    probe.armed = on;
  }, armed);
}

/** Wait until a window of QUIET_MS passes without a long task, so the load of the page is over. */
async function waitForQuiet(page: Page): Promise<void> {
  await expect(async () => {
    await resetLatency(page, false);
    await page.waitForTimeout(QUIET_MS);
    expect((await readLatency(page)).longTasks).toEqual([]);
  }).toPass({ timeout: QUIET_TIMEOUT_MS, intervals: [0] });
}

/** The value that `fraction` of the values do not exceed. */
function percentile(values: number[], fraction: number): number {
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.ceil(fraction * sorted.length) - 1]!;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2;
}

test.beforeEach(async ({ app, page }) => {
  await app.open();
  await expect(page.getByText(`${STUDIES.toLocaleString("en-US")} studies`, { exact: true })).toBeVisible();
});

test("while jobs run, a poll never blocks the page for more than 200 ms", async ({ page }, testInfo) => {
  test.fail(true, "#936: every poll handles 5 to 6 MB of state and renders every study again");
  // The initial validations of the 1,000 studies are the jobs. The load of the page is over after
  // a few seconds; the polls are what is measured.
  await page.waitForTimeout(QUIET_MS);
  await installLatencyProbe(page);
  await resetLatency(page, false);
  await page.waitForTimeout(WATCH_MS);
  const { longTasks } = await readLatency(page);
  await testInfo.attach("long-tasks.json", { body: JSON.stringify(longTasks), contentType: "application/json" });
  expect(Math.max(0, ...longTasks), JSON.stringify(longTasks)).toBeLessThanOrEqual(LONG_TASK_MS);
});

test("typing in Search studies paints each keystroke and the result within 100 ms", async ({ page }, testInfo) => {
  test.fail(true, "#936: the overview filters and renders every study on each keystroke");
  // The validations of the 1,000 studies run for minutes, and every poll of the state would load
  // the page again. This test measures the keystrokes, so the polls answer "nothing changed".
  await page.route("**/local/state", (route) => route.fulfill({ status: 304 }));
  const search = page.getByRole("textbox", { name: "Search studies" });
  await search.click();
  await installLatencyProbe(page);
  await waitForQuiet(page);
  const inputs: number[] = [];
  const results: number[] = [];
  for (let round = 0; round < WARM_UP_ROUNDS + ROUNDS; round++) {
    const measured = round >= WARM_UP_ROUNDS;
    await resetLatency(page, measured);
    // The next round replaces the text of the last one: its first letter filters again at once.
    await page.keyboard.press("Control+A");
    await page.keyboard.type(SURNAME, { delay: 60 });
    await expect.poll(async () => (await readLatency(page)).result).not.toBeNull();
    await expect(page.getByText(`${MATCHES} of ${STUDIES.toLocaleString("en-US")} studies`)).toBeVisible();
    const latency = await readLatency(page);
    if (measured) {
      inputs.push(...latency.inputs);
      results.push(latency.result! - SEARCH_DELAY_MS);
    }
  }
  const summary = {
    inputs,
    results,
    medianInput: median(inputs),
    p90Input: percentile(inputs, 0.9),
    medianResult: median(results),
  };
  await testInfo.attach("latency.json", { body: JSON.stringify(summary, null, 2), contentType: "application/json" });
  // The median, so that one pause of the garbage collector does not decide.
  expect(summary.medianInput, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
  // The 90th percentile, so that the slow first keystroke of a search does not hide behind the fast ones.
  expect(summary.p90Input, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
  expect(summary.medianResult, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
});
