// Wait until a page of a Vuetify app stands still before a screenshot. Both renderers of the
// documentation images use it: tools/curation_docs/render.mjs and tools/website_docs/render.mjs.

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
