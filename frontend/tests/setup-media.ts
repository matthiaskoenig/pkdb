import { vi } from "vitest";
// jsdom has no matchMedia. Vuetify checks for it when it is first imported, so this file runs
// before tests/setup.ts imports Vuetify. Tests run with reduced motion: jsdom has no layout to
// animate, and the label animation of fields would only cost time.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn((query: string) => ({
    matches: query === "(prefers-reduced-motion: reduce)",
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
