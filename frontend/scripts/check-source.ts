import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "@vue/compiler-sfc";
import ts from "typescript";
const failures: string[] = [];
function inspect(path: string) {
  for (const entry of readdirSync(path, { withFileTypes: true })) {
    const file = join(path, entry.name);
    if (entry.isDirectory()) {
      inspect(file);
      continue;
    }
    if (/\.[cm]?jsx?$/.test(file)) {
      failures.push(`${file}: JavaScript source is not permitted`);
      continue;
    }
    if (!/\.(ts|vue)$/.test(file)) continue;
    const source = readFileSync(file, "utf8");
    if (/@ts-(nocheck|ignore)|eslint-disable[^\n]*no-explicit-any/.test(source))
      failures.push(`${file}: blanket type suppression`);
    let code = source;
    if (file.endsWith(".vue")) {
      const { descriptor, errors } = parse(source, { filename: file });
      if (errors.length) failures.push(`${file}: invalid Vue SFC`);
      const scripts = [descriptor.script, descriptor.scriptSetup].filter(
        (script) => script !== null,
      );
      if (descriptor.script) failures.push(`${file}: use typed script setup rather than an Options API script`);
      if (!scripts.length)
        failures.push(`${file}: expected a TypeScript script block`);
      for (const script of scripts)
        if (script.lang !== "ts")
          failures.push(`${file}: script must use lang="ts"`);
      code = scripts.map((script) => script.content).join("\n");
    }
    const ast = ts.createSourceFile(
      file,
      code,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TS,
    );
    function visit(node: ts.Node) {
      if (node.kind === ts.SyntaxKind.AnyKeyword)
        failures.push(`${file}: explicit any`);
      ts.forEachChild(node, visit);
    }
    visit(ast);
  }
}
inspect("src");
inspect("tests");
if (failures.length) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
} else
  console.log(
    "All application and test sources are TypeScript; Vue scripts and explicit-any checks passed.",
  );
