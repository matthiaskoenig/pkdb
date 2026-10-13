import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import type { Plugin } from "vite";

const require = createRequire(import.meta.url);

/**
 * The license of each bundled font package, by its path in the build. The font files carry only
 * their copyright and the address of their license, and the SIL Open Font License asks that its
 * text travels with every copy of the fonts.
 */
export function fontLicenseFiles(): Map<string, string> {
  return new Map([
    ["assets/Inter-LICENSE.txt", require.resolve("@fontsource-variable/inter/LICENSE")],
    [
      "assets/fontawesome-free-LICENSE.txt",
      join(dirname(require.resolve("@fortawesome/fontawesome-free/package.json")), "LICENSE.txt"),
    ],
  ]);
}

/** Write the licenses of the bundled fonts beside the fonts of a build. */
export function fontLicenses(): Plugin {
  return {
    name: "pkdb-font-licenses",
    apply: "build",
    generateBundle() {
      for (const [fileName, source] of fontLicenseFiles())
        this.emitFile({ type: "asset", fileName, source: readFileSync(source) });
    },
  };
}
