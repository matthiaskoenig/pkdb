import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "PKDB_DEV_");
  return {
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
