import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { fontLicenses } from "./scripts/font-licenses.ts";
import { pdfjsAssets, pdfjsBanner } from "./scripts/pdfjs-assets.ts";
// A string, not a URL object: under Vitest the URL class is the one of jsdom, which fileURLToPath and readFileSync refuse.
const HERE = dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "PKDB_DEV_");
  const { version } = JSON.parse(
    readFileSync(join(HERE, "package.json"), "utf8"),
  ) as { version: string };
  let commit = process.env.PKDB_BUILD_COMMIT?.trim() || "";
  if (!commit) {
    try {
      commit = execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: HERE,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
    } catch {
      // Source archives and Docker contexts may not contain Git metadata.
    }
  }
  if (!/^[a-f0-9]{40,64}$/i.test(commit)) commit = "";
  return {
    define: {
      __APP_VERSION__: JSON.stringify(version),
      __APP_COMMIT__: JSON.stringify(commit),
    },
    plugins: [
      vue(),
      fontLicenses(),
      pdfjsAssets(),
      {
        name: "pkdb-public-asset-reload",
        apply: "serve",
        hotUpdate({ file, server }) {
          if (
            this.environment.name === "client" &&
            server.config.publicDir &&
            file.startsWith(`${server.config.publicDir}/`)
          ) {
            this.environment.hot.send({ type: "full-reload", path: "*" });
            return [];
          }
        },
      },
    ],
    resolve: {
      alias: { "@": join(HERE, "src") },
    },
    server: {
      port: 8080,
      strictPort: true,
      watch: {
        usePolling:
          (process.env.PKDB_DEV_USE_POLLING ?? env.PKDB_DEV_USE_POLLING) === "true",
        interval: 250,
      },
      proxy: Object.fromEntries(
        ["/api", "/accounts", "/media", "/docs", "/redoc", "/openapi.json"].map(
          (path) => [
            path,
            {
              target:
                process.env.PKDB_DEV_API_TARGET ??
                env.PKDB_DEV_API_TARGET ??
                "http://127.0.0.1:18083",
            },
          ],
        ),
      ),
    },
    build: {
      sourcemap: false,
      // plotly.js-dist-min is one prebuilt 4.6 MB chunk that loads lazily and cannot be split.
      chunkSizeWarningLimit: 5000,
      // After the minifier, which keeps only @license notices: the lazy chunk of PDF.js, which
      // curators load for the paper of a study (#963), gets its notice back.
      rolldownOptions: { output: { postBanner: pdfjsBanner } },
    },
  };
});
