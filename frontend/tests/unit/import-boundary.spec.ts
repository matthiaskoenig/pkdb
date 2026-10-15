import { describe, expect, it } from "vitest";
import { ESLint } from "eslint";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { sourceFailures } from "../../scripts/check-source";

// frontend/; Vite would rewrite a literal `new URL("../..", import.meta.url)` into a dev server address.
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

/** The messages of the import rule for `code` in a file at `filePath` (relative to frontend/). */
async function refusals(code: string, filePath: string): Promise<string[]> {
  const [result] = await new ESLint({ cwd: root }).lintText(code, { filePath });
  return (result?.messages ?? []).filter((message) => message.ruleId === "no-restricted-imports").map((message) => message.message);
}

const STORE = (path: string) => `import { useStudyStore } from "${path}";\nexport const store = useStudyStore;\n`;

describe("the boundary of the curation app", () => {
  it("refuses an import of the curation app in the shared study views", async () => {
    expect(await refusals(STORE("../curation-app/stores/study"), "src/study-views/probe.ts")).toHaveLength(1);
  }, 30_000);

  it("refuses an import of the curation app in the website", async () => {
    expect(await refusals(STORE("../../curation-app/stores/study"), "src/features/probe/probe.ts")).toHaveLength(1);
  }, 30_000);

  it("allows the curation app its own imports and those of the study views", async () => {
    expect(await refusals(STORE("./stores/study"), "src/curation-app/probe.ts")).toEqual([]);
    expect(await refusals('import { SECTIONS } from "../study-views/study";\nexport const all = SECTIONS;\n', "src/curation-app/probe.ts")).toEqual([]);
  }, 30_000);
});

describe("the boundary of the curation app in scripts/check-source.ts", () => {
  // The ways of naming a module that the import rule of ESLint does not see.
  const IMPORTS = [
    'export const store = () => import("../curation-app/stores/study");\n',
    'export type Store = import("../curation-app/stores/study").StudyStore;\n',
    'import type { TablesAction } from "../curation-app/stores/study";\nexport type Action = TablesAction;\n',
    'export { useStudyStore } from "../curation-app/stores/study";\n',
    'export type { TablesAction } from "../curation-app/stores/study";\n',
  ];

  it.each(IMPORTS)("refuses %s outside the curation app", (code) => {
    for (const file of [join("src", "study-views", "probe.ts"), join("src", "features", "probe", "probe.ts")])
      expect(sourceFailures(file, code)).toEqual([
        `${file}: imports ../curation-app/stores/study; only src/curation-app imports the curation app`,
      ]);
  });

  it("refuses them in the script of a Vue component too", () => {
    const file = join("src", "study-views", "Probe.vue");
    const code = `<script setup lang="ts">\nconst store = () => import("../curation-app/stores/study");\n</script>\n`;
    expect(sourceFailures(file, code)).toEqual([
      `${file}: imports ../curation-app/stores/study; only src/curation-app imports the curation app`,
    ]);
  });

  it.each(IMPORTS)("allows %s in the curation app", (code) => {
    expect(sourceFailures(join("src", "curation-app", "probe.ts"), code)).toEqual([]);
  });
});
