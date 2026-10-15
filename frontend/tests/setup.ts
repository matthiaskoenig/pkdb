import { beforeAll, vi } from "vitest";
import { config } from "@vue/test-utils";
import { makeVuetify } from "../src/plugins/vuetify";
import { isWebsiteTest } from "./websiteTests";
const vuetify = makeVuetify();
config.global.plugins = [vuetify];
// Every mounted component of a test file gets the study views of the curation app, except in a
// test of the website (tests/**/website-*.spec.ts), whose pages provide their own: there a page
// that forgets provideStudyViews fails as in the browser. The plugin imports the stores of the
// curation app, so it is imported only once the test file is: a module that this file imported
// would ignore the vi.mock calls of the test file, as tests of the curation app mock its modules,
// such as curation-app/metadata.
// Vitest requires an object pattern for the first argument, and the file is in the second.
// eslint-disable-next-line no-empty-pattern
beforeAll(async ({}, suite) => {
  if (isWebsiteTest(suite.file.filepath)) return;
  const { studyViewsPlugin } = await import("../src/curation-app/studyViews");
  config.global.plugins = [vuetify, studyViewsPlugin];
});
vi.stubGlobal(
  "ResizeObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);
vi.stubGlobal(
  "IntersectionObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);
// The stores of the curation app poll the local server every 1.5 s. A test that runs longer, as
// under load, would get a poll at a random point, with requests and reloads that it does not
// expect. So in tests a poll waits for the longest delay of setTimeout, and a test loads the
// state again with refresh(). tests/unit/curation-polling.spec.ts tests polling with fake timers.
vi.mock("../src/curation-app/composables/usePolling", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../src/curation-app/composables/usePolling")>()),
  POLL_INTERVAL_MS: 2 ** 31 - 1,
}));
// jsdom has no layout: scrolling an element into view does nothing.
Element.prototype.scrollIntoView = () => undefined;
// jsdom logs "Not implemented" for window.scrollTo, which the routers call on navigation. Tests
// that check the scroll position spy on it.
window.scrollTo = () => undefined;
