import { describe, expect, it } from "vitest";
import website from "../../vite.config";
import curation from "../../vite.curation.config";
import { pdfjsBanner, pdfjsNotice } from "../../scripts/pdfjs-assets";

function pluginNames(plugins: unknown[] | undefined): string[] {
  return (plugins ?? []).flat().flatMap((plugin) =>
    typeof plugin === "object" && plugin !== null && "name" in plugin && typeof plugin.name === "string" ? [plugin.name] : [],
  );
}

describe("the files of PDF.js in the builds", () => {
  it("are copied by the build of the website as by the build of the curation app", async () => {
    const config = await website({ command: "build", mode: "production" });
    expect(pluginNames(config.plugins)).toContain("pkdb-pdfjs-assets");
    expect(pluginNames(curation.plugins)).toContain("pkdb-pdfjs-assets");
    expect(config.build?.rolldownOptions?.output).toMatchObject({ postBanner: pdfjsBanner });
  });

  it("give the chunk of PDF.js, and only it, the license notice of PDF.js", () => {
    expect(pdfjsBanner({ moduleIds: ["/x/node_modules/pdfjs-dist/build/pdf.mjs"] })).toBe(pdfjsNotice());
    expect(pdfjsBanner({ moduleIds: ["/x/src/main.ts"] })).toBe("");
  });
});
