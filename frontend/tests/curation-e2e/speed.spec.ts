import type { Page, Response } from "@playwright/test";
import { SEARCH_DELAY_MS } from "../../src/curation-app/overview.ts";
import { OVERSCAN, ROW_HEIGHT } from "../../src/curation-app/studyTable.ts";
import { expect, expectAccessible, test } from "./fixtures.ts";

/** The studies of the generated workspace (tools/curation_testing/large_workspace.py). */
const STUDIES = 1000;
/** The longest median time from a keystroke to its paint, and from the search to its result. */
const BUDGET_MS = 100;
/** The longest task that the polls may cause while jobs run. */
const LONG_TASK_MS = 200;
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
/** How long the server may take after its start to queue the initial validations of the studies. */
const JOBS_START_MS = 60_000;

test.use({ studies: STUDIES });
// The tests share the server through worker-scoped fixtures; playwright.curation.config.ts runs
// this file in a project of its own after all other spec files, so nothing else loads the
// processor, and the tests of the file run in order in one worker. A failing test does not skip
// the others: they run in a new worker with a server of its own.
test.describe.configure({ timeout: QUIET_TIMEOUT_MS + 90_000 });

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
      // The final filter ran: the field holds the whole surname (a stale result of an earlier text
      // or of the last round cannot pass, as each round starts from the unfiltered table) and the
      // table shows exactly the matches.
      const showsMatches = () => {
        const field = document.querySelector<HTMLInputElement>('.overview-search input');
        if (field?.value.toLowerCase() !== surname) return false;
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

/** Whether `response` answers a poll of the state with a changed state (200), not with 304. */
function isChangedState(response: Response): boolean {
  return new URL(response.url()).pathname === "/local/state" && response.status() === 200;
}

/** The jobs of the state in `response` that are queued or running. */
async function unfinishedJobs(response: Response): Promise<number> {
  const { jobs } = (await response.json()) as { jobs: { status: string }[] };
  return jobs.filter((job) => job.status === "queued" || job.status === "running").length;
}

test("while jobs run, a poll never blocks the page for more than 200 ms", async ({ page }, testInfo) => {
  // The initial validations of the 1,000 studies are the jobs. The server queues them a few
  // seconds after its start, later on a slower machine, and runs them one after another for much
  // longer than the watch. So the watch starts once a poll shows them and the load of the page is
  // over, not at a fixed time after the start: before the jobs, few polls change the state, and
  // nothing would be measured.
  const jobsQueued = page.waitForResponse(
    async (response) => isChangedState(response) && (await unfinishedJobs(response)) > 0,
    { timeout: JOBS_START_MS },
  );
  await Promise.all([jobsQueued, page.waitForTimeout(QUIET_MS)]);
  await installLatencyProbe(page);
  await resetLatency(page, false);
  // For each poll that changed the state, the jobs that it shows still to run.
  const polls: Promise<number>[] = [];
  const count = (response: Response): void => {
    if (isChangedState(response)) polls.push(unfinishedJobs(response));
  };
  page.on("response", count);
  await page.waitForTimeout(WATCH_MS);
  page.off("response", count);
  const { longTasks } = await readLatency(page);
  const unfinished = await Promise.all(polls);
  await testInfo.attach("long-tasks.json", { body: JSON.stringify(longTasks), contentType: "application/json" });
  // The margin in the output of a passing run too: the attachments are kept only on failures.
  console.log(
    `polls: ${unfinished.length} changed states, ${longTasks.length} long tasks, ` +
      `the longest ${Math.round(Math.max(0, ...longTasks))} ms; jobs left ${unfinished.join(", ")}`,
  );
  // The jobs ran through the whole watch, so every poll of it had a new state to load.
  expect(unfinished.at(-1), "jobs left at the last poll that changed the state").toBeGreaterThan(0);
  expect(unfinished.length, "polls that changed the state").toBeGreaterThanOrEqual(3);
  expect(Math.max(0, ...longTasks), JSON.stringify(longTasks)).toBeLessThanOrEqual(LONG_TASK_MS);
});

test("typing in Search studies paints each keystroke and the result within 100 ms", async ({ page }, testInfo) => {
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
    // Each round starts from the unfiltered table, so only the filter of the whole surname can
    // show its matches; the rows of the last round must not stand in for the result.
    await page.keyboard.press("Control+A");
    await page.keyboard.press("Backspace");
    await expect(page.getByText(`${STUDIES.toLocaleString("en-US")} studies`, { exact: true })).toBeVisible();
    await resetLatency(page, measured);
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
  console.log(
    `search: keystroke median ${summary.medianInput.toFixed(1)} ms, p90 ${summary.p90Input.toFixed(1)} ms, ` +
      `result median ${summary.medianResult.toFixed(1)} ms after the delay`,
  );
  // The median, so that one pause of the garbage collector does not decide.
  expect(summary.medianInput, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
  // The 90th percentile, so that the slow first keystroke of a search does not hide behind the fast ones.
  expect(summary.p90Input, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
  expect(summary.medianResult, JSON.stringify(summary)).toBeLessThanOrEqual(BUDGET_MS);
});

function studyTable(page: Page) {
  return page.getByRole("table", { name: "Studies of the workspace" });
}

/** The study rows that the table rendered. */
function rendered(page: Page) {
  return page.locator("tr.study-row");
}

/**
 * The most rows that a window of 900 px renders: the rows in view, one more as the edges of the
 * window cut a row at the top and one at the bottom, and the overscan beyond each edge.
 */
const MOST_ROWS = Math.ceil(900 / ROW_HEIGHT) + 2 * OVERSCAN + 1;

test("renders only the rows in view and reaches the last study by scrolling", async ({ page }) => {
  await expect(studyTable(page)).toHaveAttribute("aria-rowcount", String(STUDIES + 1));
  expect(await rendered(page).count()).toBeLessThanOrEqual(MOST_ROWS);
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect(page.locator(`tr.study-row[aria-rowindex="${STUDIES + 1}"]`)).toBeInViewport();
  expect(await rendered(page).count()).toBeLessThanOrEqual(MOST_ROWS);
  await expectAccessible(page);
});

/**
 * Scroll the table with the mouse wheel, a notch of 100 px every 50 ms, expect the page to scroll by
 * every notch and then to come to rest, and return the faults of the painted frames: a rendered row
 * that is not at its place in the table, or a part of the window (its top, middle or bottom) that
 * shows the space of the rows that are not rendered.
 */
async function wheelThroughTable(page: Page): Promise<string[]> {
  await page.evaluate(() => {
    const probe = { faults: [] as string[], scrolls: 0 };
    (window as unknown as { __wheel: typeof probe }).__wheel = probe;
    document.addEventListener("scroll", () => probe.scrolls++, { capture: true, passive: true });
    const afterPaint = (done: () => void) => requestAnimationFrame(() => setTimeout(done, 0));
    const check = () => {
      const at = Math.round(window.scrollY);
      const body = document.querySelector(".study-table tbody")!.getBoundingClientRect().top;
      const rows = [...document.querySelectorAll("tr.study-row")];
      // Every row has the height of the first one, at any font size.
      const height = rows[0]!.getBoundingClientRect().height;
      for (const row of [rows[0]!, rows.at(-1)!]) {
        const place = (Number(row.getAttribute("aria-rowindex")) - 2) * height;
        const offset = row.getBoundingClientRect().top - body;
        if (Math.abs(offset - place) > 0.5) probe.faults.push(`${at}: row at ${offset} px, not ${place} px`);
      }
      for (const y of [0.3, 0.6, 0.99].map((part) => Math.round(window.innerHeight * part))) {
        if (document.elementFromPoint(720, y)?.closest("tr.study-space")) probe.faults.push(`${at}: space at ${y} px`);
      }
      afterPaint(check);
    };
    afterPaint(check);
  });
  const probe = () => page.evaluate(() => (window as unknown as { __wheel: { faults: string[]; scrolls: number } }).__wheel);
  await page.mouse.move(720, 500);
  // A quick hand on the wheel.
  for (let notch = 0; notch < 40; notch++) {
    await page.mouse.wheel(0, 100);
    await page.waitForTimeout(50);
  }
  // The page scrolled by every notch at once: the browser did not pull it back as rows came and went.
  await expect.poll(() => page.evaluate(() => window.scrollY), { timeout: 1000 }).toBe(4000);
  // And it rests: nothing scrolls it once the wheel stopped.
  const scrolls = (await probe()).scrolls;
  await page.waitForTimeout(1000);
  expect((await probe()).scrolls - scrolls, "scroll events in the second after the wheel stopped").toBe(0);
  expect(await page.evaluate(() => window.scrollY)).toBe(4000);
  return (await probe()).faults;
}

test("the rendered rows follow the mouse wheel at their places, without a blank band", async ({ page }) => {
  expect(await wheelThroughTable(page)).toEqual([]);
});

test("the taller rows of a large font follow the mouse wheel as well, and the page comes to rest", async ({ page }) => {
  // 87.5 % of the browser's font size "Very large", 24 px, as the app sets it. The content security
  // policy of the app refuses a style element, not a style set through the object model.
  await page.evaluate(() => document.documentElement.style.setProperty("font-size", "21px"));
  await expect
    .poll(() => page.evaluate(() => document.querySelector("tr.study-row")!.getBoundingClientRect().height))
    .toBeGreaterThan(ROW_HEIGHT);
  expect(await wheelThroughTable(page)).toEqual([]);
});

/**
 * The identities of the rendered rows: the text, whether the row shows less of it than it needs
 * (its own box or its cell cuts it), its tooltip, and how it overflows.
 */
function identities(page: Page) {
  return page.locator("tr.study-row .study-identity").evaluateAll((elements) =>
    elements.map((element) => {
      const style = getComputedStyle(element);
      const box = element.getBoundingClientRect();
      const cell = element.closest("td")!;
      const end = cell.getBoundingClientRect().right - parseFloat(getComputedStyle(cell).paddingRight);
      return {
        text: element.textContent ?? "",
        cut: element.scrollWidth > Math.min(box.right, end) - box.left + 1,
        title: element.getAttribute("title"),
        overflow: [style.overflow, style.textOverflow, style.whiteSpace].join(" "),
      };
    }),
  );
}

test("a study identity that its cell cuts ends with an ellipsis and stays whole in its name and tooltip", async ({
  page,
}) => {
  // The longest substance of the generated workspace.
  await page.getByRole("textbox", { name: "Search studies" }).fill("dextromethorphan");
  await expect(page.getByText(/^\d+ of 1,000 studies$/)).toBeVisible();
  // At the default font size every identity fits a window of 1440 px.
  expect((await identities(page)).filter((identity) => identity.cut)).toEqual([]);
  // A narrower window and a larger font leave the study column its least width, 12 rem.
  await page.setViewportSize({ width: 1000, height: 900 });
  await page.evaluate(() => document.documentElement.style.setProperty("font-size", "21px"));
  await expect.poll(async () => (await identities(page)).filter((identity) => identity.cut).length).toBeGreaterThan(0);
  const cut = (await identities(page)).filter((candidate) => candidate.cut);
  for (const identity of cut) {
    expect(identity.overflow).toBe("hidden ellipsis nowrap");
    // The tooltip of the app names it whole; a native one would show beside it.
    expect(identity.title).toBeNull();
    await expect(page.getByRole("link", { name: identity.text, exact: true })).toBeVisible();
  }
  // Every generated study has the tables of caffeine/Draft2021, which name caffeine. An identity of
  // the generator has letters, a slash and digits only.
  const [first] = cut;
  await page.getByRole("link", { name: first!.text, exact: true }).hover();
  await expect(page.getByRole("tooltip")).toHaveText(new RegExp(`^\\s*${first!.text}\\s*\\+ caffeine\\s*$`));
});

test("Select all selects every shown study, also the rows that are not rendered", async ({ page }) => {
  await page.getByRole("checkbox", { name: "Select all shown studies" }).check();
  await expect(page.getByText("1,000 studies selected")).toBeVisible();
  // A study that a filter hides leaves the selection.
  await page.getByRole("textbox", { name: "Search studies" }).fill(SURNAME);
  await expect(page.getByText("25 studies selected")).toBeVisible();
});

test("Tab moves through the rows below the window and keeps the focused row in view", async ({ page }) => {
  await page.locator('tr.study-row[aria-rowindex="2"] .cell-select input').focus();
  // Each row has two or three stops: its checkbox, its link and sometimes an issue.
  for (let press = 0; press < 150; press++) await page.keyboard.press("Tab");
  const focused = page.locator("tr.study-row:focus-within");
  await expect(focused).toBeInViewport();
  expect(Number(await focused.getAttribute("aria-rowindex"))).toBeGreaterThan(Math.ceil(900 / ROW_HEIGHT) + OVERSCAN);
});

test("keeps the keyboard focus in its row while Page Down scrolls it out of view", async ({ page }) => {
  const first = page.locator('tr.study-row[aria-rowindex="2"] .cell-select input');
  await first.focus();
  for (let press = 0; press < 5; press++) await page.keyboard.press("PageDown");
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(2000);
  await expect(first).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator('tr.study-row[aria-rowindex="2"] a.study-identity')).toBeFocused();
});

test("the columns keep their widths while the table scrolls", async ({ page }) => {
  // A new state may change the widths of the columns, as the cells change; this test is about
  // scrolling, so the polls answer "nothing changed".
  await page.route("**/local/state", (route) => route.fulfill({ status: 304 }));
  const widths = () =>
    studyTable(page)
      .locator("thead th")
      .evaluateAll((cells) => cells.map((cell) => cell.getBoundingClientRect().width));
  const top = await widths();
  // The first rendered row once the window followed: the middle, and the last rows of the table.
  for (const [fraction, row] of [
    [0.5, 400],
    [1, STUDIES - MOST_ROWS],
  ] as const) {
    await page.evaluate((part) => window.scrollTo(0, document.documentElement.scrollHeight * part), fraction);
    await expect
      .poll(() => page.evaluate(() => Number(document.querySelector("tr.study-row")?.getAttribute("aria-rowindex"))))
      .toBeGreaterThan(row);
    expect(await widths()).toEqual(top);
  }
});
