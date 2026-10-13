import { describe, expect, it } from "vitest";
import { pdfjsFiles, pdfjsNotice } from "../../vite.curation.config";

describe("the files of PDF.js in the build of the curation app", () => {
  it("copies the worker, the character maps, the standard fonts and the JavaScript decoders with their licenses", () => {
    const files = [...pdfjsFiles().keys()];
    expect(files).toEqual(
      expect.arrayContaining([
        "pdf.worker.min.mjs",
        "LICENSE",
        "cmaps/LICENSE",
        "cmaps/Adobe-Japan1-UCS2.bcmap",
        "standard_fonts/FoxitSerif.pfb",
        "standard_fonts/LiberationSans-Regular.ttf",
        "standard_fonts/LICENSE_FOXIT",
        "standard_fonts/LICENSE_LIBERATION",
        "wasm/jbig2_nowasm_fallback.js",
        "wasm/openjpeg_nowasm_fallback.js",
        "wasm/LICENSE_JBIG2",
        "wasm/LICENSE_OPENJPEG",
        "wasm/LICENSE_PDFJS_JBIG2",
        "wasm/LICENSE_PDFJS_OPENJPEG",
      ]),
    );
  });

  it("leaves out the WebAssembly, which the Content Security Policy of the app does not run", () => {
    expect([...pdfjsFiles().keys()].filter((file) => file.endsWith(".wasm") || file.includes("quickjs"))).toEqual([]);
  });

  it("keeps the license notice of PDF.js, which the minifier drops from its chunk", () => {
    const notice = pdfjsNotice();
    expect(notice.startsWith("/**")).toBe(true);
    expect(notice.endsWith("*/")).toBe(true);
    expect(notice).toContain("@licstart");
    expect(notice).toContain("Licensed under the Apache License, Version 2.0");
  });
});
