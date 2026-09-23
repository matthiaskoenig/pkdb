import { defineConfig, mergeConfig } from "vitest/config";
import vite from "./vite.config.ts";
export default defineConfig((env) =>
  mergeConfig(
    vite(env),
    defineConfig({
      test: {
        environment: "jsdom",
        server: { deps: { inline: ["vuetify"] } },
        setupFiles: ["./tests/setup.ts"],
        include: ["tests/unit/**/*.spec.ts", "tests/components/**/*.spec.ts"],
        restoreMocks: true,
      },
    }),
  ),
);
