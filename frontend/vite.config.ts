import { fileURLToPath, URL } from "node:url";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "PKDB_DEV_");
  const { version } = JSON.parse(
    readFileSync(new URL("./package.json", import.meta.url), "utf8"),
  ) as { version: string };
  let commit = process.env.PKDB_BUILD_COMMIT?.trim() || "";
  if (!commit) {
    try {
      commit = execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: fileURLToPath(new URL(".", import.meta.url)),
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
    plugins: [vue()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 8080,
      strictPort: true,
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
    build: { sourcemap: false },
  };
});
