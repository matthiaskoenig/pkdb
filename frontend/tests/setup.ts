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
