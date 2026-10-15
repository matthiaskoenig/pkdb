import { readdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import type { Plugin } from "vite";

/**
 * The run-time files of PDF.js, which the paper viewer of the study views loads lazily from
 * `pdfjs/` of each build (the curation app and, for curators, the website; #963), and the
 * license notice of its chunk.
 */

/** The folder of pdfjs-dist, the PDF.js of the paper viewer. */
const PDFJS = dirname(createRequire(import.meta.url).resolve("pdfjs-dist/package.json"));

/**
 * The files of pdfjs-dist that PDF.js loads at run time, by their path below `pdfjs/` of the
 * build, with the license of PDF.js and those of its folders: the worker, the character maps,
 * the standard fonts, and the JavaScript decoders of JPEG 2000 and of JBIG2 and CCITT images,
 * which the views use since the Content Security Policy of the curation app allows no
 * WebAssembly. The .wasm files are left out.
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
export const isPdfjs = (id: string) => /[\\/]node_modules[\\/]pdfjs-dist[\\/]/.test(id);

/** Copies the run-time files of PDF.js to `pdfjs/` of the build, and serves them on the development server. */
export function pdfjsAssets(): Plugin {
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

let notice: string | null = null;

/** The banner of a chunk of the build: the license notice of PDF.js for its chunk, which the minifier drops, else nothing. */
export function pdfjsBanner(chunk: { moduleIds: readonly string[] }): string {
  if (!chunk.moduleIds.some(isPdfjs)) return "";
  notice ??= pdfjsNotice();
  return notice;
}
