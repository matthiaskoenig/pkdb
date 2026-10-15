// Frame a page of the study views and wait until it stands still before a screenshot. Both
// renderers of the documentation images use it: tools/curation_docs/render.mjs and
// tools/website_docs/render.mjs.

/**
 * Wait until nothing animates and the tab bars have kept their scroll position for two
 * animation frames: a chosen tab scrolls into view, and a ripple of a click fades.
 */
export async function settled(page) {
  await page.evaluate(() => {
    window.__renderFrames = { position: null, stable: 0 };
  });
  await page.waitForFunction(
    () => {
      const position = [...document.querySelectorAll(".v-slide-group__container")]
        .map((container) => container.scrollLeft)
        .join(",");
      const frames = window.__renderFrames;
      frames.stable = position === frames.position ? frames.stable + 1 : 0;
      frames.position = position;
      // Hidden loaders keep paused animations, so only running ones count.
      return frames.stable >= 2 && document.getAnimations().every((animation) => animation.playState !== "running");
    },
    undefined,
    { polling: "raf" },
  ).catch(async (error) => {
    const state = await page.evaluate(() => ({
      tabs: window.__renderFrames,
      running: document
        .getAnimations()
        .filter((animation) => animation.playState === "running")
        .map((animation) => {
          const target = animation.effect?.target;
          const chain = [];
          for (let node = target; node && chain.length < 8; node = node.parentElement) chain.push(`${node.tagName}.${node.getAttribute("class") ?? ""}[${node.getAttribute("aria-label") ?? ""}]`);
          return `${animation.animationName ?? animation.transitionProperty ?? "script"} ${JSON.stringify(target?.getBoundingClientRect())} ${chain.join(" < ")}`;
        }),
    }));
    throw new Error(`The page did not settle: ${JSON.stringify(state)}`, { cause: error });
  });
}

/**
 * Scroll a tab bar so that a whole tab starts at its left edge, while the chosen tab stays in
 * view: a tab bar that centers the chosen tab can cut the first visible one.
 */
export async function alignTabs(tabs) {
  await tabs.evaluate((list) => {
    const container = list.querySelector(".v-slide-group__container");
    const items = [...list.querySelectorAll('[role="tab"]')];
    const chosen = items.find((item) => item.getAttribute("aria-selected") === "true");
    if (!container || !chosen) return;
    const origin = container.getBoundingClientRect().left - container.scrollLeft;
    const start = (item) => item.getBoundingClientRect().left - origin;
    const end = (item) => item.getBoundingClientRect().right - origin;
    const widest = container.scrollWidth - container.clientWidth;
    // The start of a tab that the bar can scroll to, with the chosen tab in view.
    const possible = items
      .map(start)
      .filter((left) => left <= widest + 0.5 && start(chosen) >= left && end(chosen) <= left + container.clientWidth);
    const current = container.scrollLeft;
    const nearest = possible.sort((a, b) => Math.abs(a - current) - Math.abs(b - current))[0];
    if (nearest !== undefined) container.scrollLeft = nearest;
  });
}

/**
 * Whether a rows table with the measures of `columnEnds`, shown `change` pixels wider, shows its
 * columns cleanly at the right edge of its region: it fits, or more columns follow and the fade at
 * the end of the region (TableGrid.vue, 40 pixels wide) starts in the 8 pixels of padding at the
 * end of the last whole column or at most `reach` pixels into the next one, so that it fades out
 * the start of the next column, which shows that the rows scroll, and no text of a whole column.
 */
const FADE = 40;
const PADDING = 8;
const REACH = 12;
function wholeColumns({ width, content, ends }, change = 0, reach = REACH) {
  const shown = width + change;
  return (
    content <= shown + 0.5 || ends.some((end) => shown - end >= FADE - PADDING - 0.5 && shown - end <= FADE + reach + 0.5)
  );
}

/**
 * Move the separator between the source and the rows of the Data section so that no rows table in
 * `regions` (locators of their scrolling regions) cuts a column at the right (`wholeColumns`). Of
 * the shares of the separator that do this for every table, it takes the one nearest to the
 * current share at which the fades reach at most 4 pixels into the next columns, else at most
 * REACH pixels; the scroll positions of the tables stay.
 */
export async function alignColumns(page, regions) {
  const separator = page.getByRole("separator", { name: "Resize the source and the rows" });
  const split = await separator.evaluate((element) => {
    const box = element.parentElement.getBoundingClientRect();
    const own = element.getBoundingClientRect();
    return {
      left: box.left,
      width: box.width,
      share: Number(element.getAttribute("aria-valuenow")),
      min: Number(element.getAttribute("aria-valuemin")),
      max: Number(element.getAttribute("aria-valuemax")),
      x: own.left + own.width / 2,
      y: own.top + Math.min(own.height / 2, 200),
      grab: own.width / 2,
    };
  });
  const tables = await Promise.all(regions.map((region) => region.evaluate(columnEnds)));
  const whole = (change, reach) => tables.every((table) => wholeColumns(table, change, reach));
  const shares = [];
  for (let share = split.min; share <= split.max; share++) shares.push(share);
  shares.sort((a, b) => Math.abs(a - split.share) - Math.abs(b - split.share) || a - b);
  // The rows are the end pane: a larger share of the start pane narrows them.
  const change = (share) => ((split.share - share) / 100) * split.width;
  const chosen =
    shares.find((share) => whole(change(share), 4)) ?? shares.find((share) => whole(change(share), REACH));
  if (chosen === undefined) {
    const each = tables.map((table) => shares.filter((share) => wholeColumns(table, change(share))).sort((x, y) => x - y));
    throw new Error(`No position of the separator shows only whole columns of the rows; each table allows ${JSON.stringify(each)}.`);
  }
  if (chosen !== split.share) {
    await page.mouse.move(split.x, split.y);
    await page.mouse.down();
    await page.mouse.move(split.left + (chosen / 100) * split.width + split.grab, split.y, { steps: 4 });
    await page.mouse.up();
    await page.waitForFunction(
      ([element, share]) => element.getAttribute("aria-valuenow") === String(share),
      [await separator.elementHandle(), chosen],
    );
  }
  await settled(page);
  const cut = await cutColumns(page);
  if (cut.length) throw new Error(`The rows of ${cut.join(", ")} cut a column at the right.`);
}

/**
 * The width of a scrolling region of rows, the width of its content, and the right ends of the
 * columns of its table, in pixels from the left edge of what the region shows.
 */
function columnEnds(region) {
  const box = region.getBoundingClientRect();
  const origin = box.left + region.clientLeft;
  const header = region.querySelector("thead tr:last-child");
  const ends = [...(header?.children ?? [])].map((cell) => cell.getBoundingClientRect().right - origin);
  return { width: region.clientWidth, content: region.scrollWidth - region.scrollLeft, ends };
}

/**
 * Set the height of the window so that the panes of the Data section, which take the height of
 * the window, end `margin` pixels below their longest content: no pane shows a large empty area,
 * and none has to scroll.
 */
export async function fitPanes(page, { margin = 16 } = {}) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const spare = await page.evaluate(() => {
      const panes = [...document.querySelectorAll(".data-navigator, .pane-body, .rows-scroll")].filter(
        (element) => element.checkVisibility() && element.getBoundingClientRect().height > 0,
      );
      const bottom = Math.max(...panes.map((pane) => pane.getBoundingClientRect().bottom));
      // The panes that reach the bottom of the section, and what each has to spare there.
      return Math.min(
        ...panes
          .filter((pane) => Math.abs(pane.getBoundingClientRect().bottom - bottom) < 2)
          .map((pane) => {
            if (pane.scrollHeight > pane.clientHeight + 1) return pane.clientHeight - pane.scrollHeight;
            const end = Math.max(...[...pane.children].map((child) => child.getBoundingClientRect().bottom));
            return pane.getBoundingClientRect().bottom - pane.clientTop - end;
          }),
      );
    });
    const change = Math.round(margin - spare);
    if (Math.abs(change) <= 1) return;
    const { width, height } = page.viewportSize();
    await page.setViewportSize({ width, height: height + change });
    await settled(page);
  }
  throw new Error("The panes of the Data section did not fit their content.");
}

/** The names of the shown rows tables of the page that cut a column at the right edge of their region. */
export async function cutColumns(page) {
  const cut = [];
  for (const region of await page.locator(".rows-scroll").all()) {
    if (!(await region.evaluate((element) => element.checkVisibility()))) continue;
    const table = await region.evaluate(columnEnds);
    if (table.ends.length && !wholeColumns(table)) cut.push((await region.getAttribute("aria-label")) ?? "a table");
  }
  return cut;
}
