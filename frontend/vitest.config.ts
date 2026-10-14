import { defineConfig, mergeConfig } from "vitest/config";
import vite from "./vite.config.ts";
export default defineConfig((env) =>
  mergeConfig(
    vite(env),
    defineConfig({
      test: {
        environment: "jsdom",
        server: { deps: { inline: ["vuetify"] } },
        // setup-media.ts first: Vuetify, which setup.ts imports, looks for matchMedia on import.
        setupFiles: ["./tests/setup-media.ts", "./tests/setup.ts"],
        include: ["tests/unit/**/*.spec.ts", "tests/components/**/*.spec.ts"],
        restoreMocks: true,
        // A test of 1,000 rows takes under a second alone but up to ten times as long while
        // every core runs a jsdom test file; the default of 5 s then fails it at random.
        testTimeout: 20_000,
        // Keep the test output to results: the performance hints suggest
        // shared environments, which would drop the per-file isolation.
        experimental: { diagnostics: false },
      },
    }),
  ),
);
