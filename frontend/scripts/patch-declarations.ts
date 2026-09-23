/**
 * Narrow declaration corrections for the pinned upstream releases.
 * No runtime files or application types are changed; strict library checking
 * remains enabled. Remove/reassess each correction when upgrading its package.
 *
 * Vuetify 4.2.1: generated GlobalComponents/GlobalDirectives arguments need a finite mapped
 * object type to meet Vue 3.5.43's Record constraint (an open interface lacks an
 * implicit index signature). Pick<T, keyof T> preserves precisely T's members.
 * Also disambiguate identical Slot barrel exports, align the ViewTransition
 * augmentation with the DOM's readonly property, and admit Vue's null previous
 * vnode in directive hooks (the runtime implementation does not use that arg).
 *
 * Router 5.3.1: experimental group records explicitly exclude name/path/hash
 * with undefined; the base must admit those declarations under
 * exactOptionalPropertyTypes. This does not change ordinary route types.
 */
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const modules = join(root, "node_modules");
const versions: Record<string, string> = {
  vuetify: "4.2.1",
  "vue-router": "5.3.1",
  "@vue/runtime-core": "3.5.43",
  typescript: "6.0.3",
};
for (const [name, expected] of Object.entries(versions)) {
  const metadata: unknown = JSON.parse(
    readFileSync(join(modules, name, "package.json"), "utf8"),
  );
  if (
    typeof metadata !== "object" ||
    metadata === null ||
    !("version" in metadata) ||
    metadata.version !== expected
  )
    throw new Error(
      `Reassess declaration corrections: expected ${name}@${expected}`,
    );
}

const changes = new Map<string, string>();
function read(path: string) {
  return changes.get(path) ?? readFileSync(path, "utf8");
}
function replaceOnce(path: string, before: string, after: string) {
  const value = read(path);
  if (value.includes(after)) return;
  if (value.split(before).length !== 2)
    throw new Error(`Unexpected upstream declaration shape: ${path}`);
  changes.set(path, value.replace(before, after));
}
function declarations(path: string): string[] {
  return readdirSync(path, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory()
      ? declarations(join(path, entry.name))
      : entry.name.endsWith(".d.ts")
        ? [join(path, entry.name)]
        : [],
  );
}
for (const interfaceName of ["GlobalComponents", "GlobalDirectives"]) {
  const reference = `import("vue").${interfaceName}`;
  const mapped = `Pick<${reference}, keyof ${reference}>`;
  let affectedFiles = 0;
  for (const path of declarations(join(modules, "vuetify/lib"))) {
    const value = read(path);
    if (!value.includes(reference)) continue;
    affectedFiles++;
    if (value.includes(mapped)) continue;
    changes.set(path, value.replaceAll(reference, mapped));
  }
  if (affectedFiles !== 210)
    throw new Error(
      `Reassess Vuetify ${interfaceName} declarations: expected 210 files, found ${affectedFiles}`,
    );
  const framework = join(modules, "vuetify/lib/framework.d.ts");
  const frameworkValue = read(framework);
  const namespaceReference = `vue.${interfaceName}`;
  const namespaceMapped = `Pick<${namespaceReference}, keyof ${namespaceReference}>`;
  if (!frameworkValue.includes(namespaceMapped)) {
    if (frameworkValue.split(namespaceReference).length !== 6)
      throw new Error(`Framework ${interfaceName} declaration count changed`);
    changes.set(
      framework,
      frameworkValue.replaceAll(namespaceReference, namespaceMapped),
    );
  }
}
replaceOnce(
  join(modules, "vuetify/lib/composables/directiveComponent.d.ts"),
  "prevVNode: VNode<any, any>) => void;",
  "prevVNode: VNode | null) => void;",
);
replaceOnce(
  join(modules, "vuetify/lib/framework.d.ts"),
  "interface ViewTransition {\n    finished: Promise<void>",
  "interface ViewTransition {\n    readonly finished: Promise<void>",
);
replaceOnce(
  join(modules, "vuetify/lib/util/index.d.ts"),
  "export * from './defineComponent.js';",
  "export * from './defineComponent.js';\nexport type { Slot } from './defineComponent.js';",
);

const router = join(modules, "vue-router/dist/index-D7ja2BKs.d.ts");
const routerText = read(router);
const start = routerText.indexOf(
  "interface EXPERIMENTAL_ResolverRecord_Base {",
);
const end = routerText.indexOf("\n}", start);
if (start < 0 || end < 0)
  throw new Error("Experimental router base declaration changed");
let base = routerText.slice(start, end);
for (const [field, type] of [
  ["name", "RecordName"],
  ["path", "MatcherPatternPath"],
  ["hash", "MatcherPatternHash"],
]) {
  const before = `${field}?: ${type};`;
  const after = `${field}?: ${type} | undefined;`;
  if (base.includes(after)) continue;
  if (!base.includes(before))
    throw new Error(`Experimental router ${field} declaration changed`);
  base = base.replace(before, after);
}
const correctedRouter =
  routerText.slice(0, start) + base + routerText.slice(end);
if (correctedRouter !== routerText) changes.set(router, correctedRouter);

// Validate every expected source above before touching the installed package.
for (const [path, content] of changes) writeFileSync(path, content);
console.log(
  `Verified pinned declaration corrections (${changes.size} files updated).`,
);
