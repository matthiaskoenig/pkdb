import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig, type Plugin, type ProxyOptions } from "vite";

const entry = "curation-app.html";
// The origin of a running `pkdb curate`; a full launch URL works too.
const target = new URL(process.env.PKDB_CURATION_URL ?? "http://127.0.0.1:43117").origin;

function local(): ProxyOptions {
  return {
    target,
    changeOrigin: true,
    configure(proxy) {
      // The local server accepts requests only from its own origin.
      proxy.on("proxyReq", (request) => request.setHeader("Origin", target));
    },
  };
}

/** The local server serves the app as `index.html`, at `/`. */
function servedAsIndex(): Plugin {
  return {
    name: "pkdb-curation-index",
    enforce: "post",
    configureServer(server) {
      server.middlewares.use((request, _response, next) => {
        if (request.url === "/" || request.url === "/index.html") request.url = `/${entry}`;
        next();
      });
    },
    generateBundle(_options, bundle) {
      const html = bundle[entry];
      if (html?.type !== "asset") this.error(`${entry} is missing from the bundle`);
      delete bundle[entry];
      this.emitFile({ type: "asset", fileName: "index.html", source: html.source });
    },
  };
}

export default defineConfig({
  plugins: [vue(), servedAsIndex()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  base: "./",
  // frontend/public holds the website's files.
  publicDir: false,
  // The local server replaces the placeholder with a fresh nonce per response.
  html: { cspNonce: "__PKDB_NONCE__" },
  build: {
    outDir: "../python/src/pkdb/curation/static",
    emptyOutDir: true,
    // Fonts and images stay files: the CSP allows no data: fonts.
    assetsInlineLimit: 0,
    sourcemap: false,
    rolldownOptions: { input: fileURLToPath(new URL(`./${entry}`, import.meta.url)) },
  },
  server: { port: 8090, strictPort: true, proxy: { "/local": local(), "/avatars": local() } },
});
