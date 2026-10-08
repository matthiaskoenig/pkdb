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
        // Keep the test output to results: the performance hints suggest
        // shared environments, which would drop the per-file isolation.
        experimental: { diagnostics: false },
      },
    }),
  ),
);
