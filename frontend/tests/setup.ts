import { vi } from "vitest";
import { config } from "@vue/test-utils";
import { makeVuetify } from "../src/plugins/vuetify";
config.global.plugins = [makeVuetify()];
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
