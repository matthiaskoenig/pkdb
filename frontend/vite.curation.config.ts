import { readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig, type Plugin, type ProxyOptions } from "vite";
import { fontLicenses } from "./scripts/font-licenses.ts";

// A string, not a URL object: under Vitest the URL class is the one of jsdom, which fileURLToPath refuses.
const HERE = dirname(fileURLToPath(import.meta.url));
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

/** The folder of pdfjs-dist, the PDF.js of the paper viewer. */
const PDFJS = dirname(createRequire(import.meta.url).resolve("pdfjs-dist/package.json"));

/**
 * The files of pdfjs-dist that PDF.js loads at run time, by their path below `pdfjs/` of the
 * build, with the license of PDF.js and those of its folders: the worker, the character maps,
 * the standard fonts, and the JavaScript decoders of JPEG 2000 and of JBIG2 and CCITT images,
 * which the app uses since its Content Security Policy allows no WebAssembly. The .wasm files
 * are left out.
 */
export function pdfjsFiles(root = PDFJS): Map<string, string> {
  const files = new Map<string, string>([
    ["pdf.worker.min.mjs", join(root, "build", "pdf.worker.min.mjs")],
    ["LICENSE", join(root, "LICENSE")],
  ]);
  for (const folder of ["cmaps", "standard_fonts"])
    for (const name of readdirSync(join(root, folder))) files.set(`${folder}/${name}`, join(root, folder, name));
  for (const name of readdirSync(join(root, "wasm")))
    if (name.endsWith("_nowasm_fallback.js") || name.startsWith("LICENSE"))
      files.set(`wasm/${name}`, join(root, "wasm", name));
  return files;
}

/** The license notice at the top of pdf.mjs and pdf_viewer.mjs, which the minifier drops: it has no @license tag. */
export function pdfjsNotice(root = PDFJS): string {
  const path = join(root, "build", "pdf.mjs");
  const source = readFileSync(path, "utf8");
  const end = source.indexOf("*/");
  if (!source.startsWith("/**") || end < 0 || !source.slice(0, end).includes("@licstart"))
    throw new Error(`No license notice at the top of ${path}`);
  return source.slice(0, end + 2);
}

/** Whether a module of the bundle is a part of pdfjs-dist. */
const isPdfjs = (id: string) => /[\\/]node_modules[\\/]pdfjs-dist[\\/]/.test(id);

/** Copies the run-time files of PDF.js to `pdfjs/` of the build, and serves them on the development server. */
function pdfjsAssets(): Plugin {
  const files = pdfjsFiles();
  return {
    name: "pkdb-pdfjs-assets",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const path = request.url?.split("?")[0] ?? "";
        const source = path.startsWith("/pdfjs/") ? files.get(path.slice("/pdfjs/".length)) : undefined;
        if (!source) return next();
        response.setHeader("Content-Type", /\.m?js$/.test(source) ? "text/javascript" : "application/octet-stream");
        response.end(readFileSync(source));
      });
    },
    generateBundle() {
      for (const [path, source] of files)
        this.emitFile({ type: "asset", fileName: `pdfjs/${path}`, source: readFileSync(source) });
    },
  };
}

const PDFJS_NOTICE = pdfjsNotice();

export default defineConfig({
  plugins: [vue(), servedAsIndex(), pdfjsAssets(), fontLicenses()],
  resolve: { alias: { "@": join(HERE, "src") } },
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
    // plotly.js-dist-min is one prebuilt 4.6 MB chunk that loads lazily and cannot be split.
    chunkSizeWarningLimit: 5000,
    rolldownOptions: {
      input: join(HERE, entry),
      // After the minifier, which keeps only @license notices: the chunk of PDF.js gets its notice back.
      output: { postBanner: (chunk) => (chunk.moduleIds.some(isPdfjs) ? PDFJS_NOTICE : "") },
    },
  },
  server: { port: 8090, strictPort: true, proxy: { "/local": local(), "/avatars": local() } },
});
